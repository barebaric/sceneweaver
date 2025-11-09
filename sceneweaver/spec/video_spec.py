from typing import List, Dict, Any
from pathlib import Path
from ..errors import ValidationError
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
        for scene_data in scenes_data:
            # Merge defaults with scene-specific data here.
            # Scene-specific values will overwrite defaults.
            merged_data = {**scene_defaults, **scene_data}
            scenes.append(BaseScene.from_dict(merged_data, base_dir))

        instance = cls(settings=settings, scenes=scenes)
        instance.validate()
        return instance
