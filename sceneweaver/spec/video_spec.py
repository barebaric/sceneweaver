from typing import List, Dict, Any
from pathlib import Path
from jinja2 import Environment
from ..errors import ValidationError
from ..template_manager import TemplateManager
from .video_settings import VideoSettings
from .scene.base_scene import BaseScene

# Import VALID_TEMPLATE_KEYS to use it for filtering
from .scene.template_scene import TemplateScene, VALID_TEMPLATE_KEYS


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
        if not isinstance(self.settings, VideoSettings):
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
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path, is_internal: bool = False
    ) -> "VideoSpec":
        settings_data = data.get("settings", {})
        scenes_data = data.get("scenes", [])

        if isinstance(settings_data, VideoSettings):
            settings = settings_data
        else:
            settings = VideoSettings.from_dict(settings_data, base_dir)

        global_scene_defaults = settings.scene_defaults

        scenes: List[BaseScene] = []
        template_manager = TemplateManager()
        jinja_env = Environment()

        for user_scene_block in scenes_data:
            scene_type = user_scene_block.get("type")

            if scene_type == "template" and not is_internal:
                # For templates, only apply defaults that are valid for them.
                template_safe_defaults = {
                    k: v
                    for k, v in global_scene_defaults.items()
                    if k in VALID_TEMPLATE_KEYS
                }
                final_scene_data = {
                    **template_safe_defaults,
                    **user_scene_block,
                }
                instance = TemplateScene.from_dict(final_scene_data, base_dir)
                instance._load_internal_spec(
                    settings, jinja_env, template_manager
                )
                scenes.append(instance)
            else:
                # For all other scenes, apply all defaults.
                final_scene_data = {
                    **global_scene_defaults,
                    **user_scene_block,
                }
                new_scene = BaseScene.from_dict(final_scene_data, base_dir)
                scenes.append(new_scene)

        instance = cls(settings=settings, scenes=scenes)
        if not is_internal:
            instance.validate()
        return instance
