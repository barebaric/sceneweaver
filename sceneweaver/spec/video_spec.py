from typing import List, Dict, Any
from pathlib import Path
import yaml
from jinja2 import Environment
from ..errors import ValidationError
from ..template_manager import TemplateManager
from .video_settings import VideoSettings
from .scene.base_scene import BaseScene


class VideoSpec:
    def __init__(self, settings: VideoSettings, scenes: List[BaseScene]):
        self.settings = settings
        self.scenes = scenes

    def validate(self):
        """Validates the entire video specification."""
        if not self.settings:
            raise ValidationError(
                "Specification is missing a 'settings' block."
            )
        self.settings.validate()

        if not self.scenes:
            raise ValidationError(
                "Specification must have at least one scene."
            )

        scene_ids = set()
        for scene in self.scenes:
            scene.validate()
            assert scene.id is not None
            if scene.id in scene_ids:
                raise ValidationError(
                    f"Duplicate scene id found: '{scene.id}'. "
                    "Scene IDs must be unique."
                )
            scene_ids.add(scene.id)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "VideoSpec":
        settings_data = data.get("settings", {})
        scenes_data = data.get("scenes", [])

        settings = VideoSettings.from_dict(settings_data, base_dir)
        scene_defaults = settings.scene_defaults

        scenes = []
        template_manager = TemplateManager()
        jinja_env = Environment()

        for scene_data in scenes_data:
            merged_data = {**scene_defaults, **scene_data}

            if merged_data.get("type") != "template":
                # Regular scene, use the main spec's directory
                new_scene = BaseScene.from_dict(merged_data, base_dir)
                scenes.append(new_scene)
                continue

            # Template scenes are replaced by real scenes here.
            template_name = merged_data["name"]
            template_dir = template_manager.resolve(template_name)

            template_spec_path = template_dir / "template.yaml"
            template_content = template_spec_path.read_text(encoding="utf-8")

            template = jinja_env.from_string(template_content)

            context = merged_data.get("with", {})
            if "id" in merged_data:
                context["id"] = merged_data["id"]

            rendered_yaml_str = template.render(context)
            scenes_from_template = yaml.safe_load(rendered_yaml_str) or []

            if isinstance(scenes_from_template, dict):
                scenes_from_template = [scenes_from_template]

            for scene_dict in scenes_from_template:
                # Use the template's directory as the base for asset resolution
                new_scene = BaseScene.from_dict(scene_dict, template_dir)
                scenes.append(new_scene)

        instance = cls(settings=settings, scenes=scenes)
        instance.validate()
        return instance
