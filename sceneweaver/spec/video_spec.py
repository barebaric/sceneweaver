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

        # Source 3: Global defaults from the main spec's settings.
        global_scene_defaults = settings.scene_defaults

        scenes = []
        template_manager = TemplateManager()
        jinja_env = Environment()

        for user_scene_block in scenes_data:
            if user_scene_block.get("type") != "template":
                # Regular scenes: Merge global defaults with user's spec.
                final_scene_data = {
                    **global_scene_defaults,
                    **user_scene_block,
                }
                new_scene = BaseScene.from_dict(final_scene_data, base_dir)
                scenes.append(new_scene)
                continue

            # Template scenes are replaced by real scenes here.
            template_name = user_scene_block["name"]
            template_dir = template_manager.resolve(template_name)
            template_spec_path = template_dir / "template.yaml"
            template_content = template_spec_path.read_text(encoding="utf-8")
            template = jinja_env.from_string(template_content)

            # Build context for Jinja rendering
            base_context = {"font": settings.font}
            user_with_params = user_scene_block.get("with", {})
            context = {**base_context, **user_with_params}

            rendered_yaml_str = template.render(context)
            scenes_from_template = yaml.safe_load(rendered_yaml_str) or []

            if isinstance(scenes_from_template, dict):
                scenes_from_template = [scenes_from_template]

            if not scenes_from_template:
                continue

            user_direct_overrides = {
                k: v
                for k, v in user_scene_block.items()
                if k not in ["type", "name", "with"]
            }

            # Process the first scene separately
            first_scene_dict = scenes_from_template[0]
            final_first_scene_data = {
                **global_scene_defaults,
                **first_scene_dict,
                **user_direct_overrides,
            }
            scenes.append(
                BaseScene.from_dict(final_first_scene_data, template_dir)
            )

            # Process the rest of the scenes without user overrides
            for subsequent_scene_dict in scenes_from_template[1:]:
                final_subsequent_data = {
                    **global_scene_defaults,
                    **subsequent_scene_dict,
                }
                scenes.append(
                    BaseScene.from_dict(final_subsequent_data, template_dir)
                )

        instance = cls(settings=settings, scenes=scenes)
        instance.validate()
        return instance
