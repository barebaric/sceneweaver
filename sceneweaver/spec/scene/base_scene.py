from typing import Dict, Any, Optional, List
from pathlib import Path
from moviepy import VideoClip
from ...errors import ValidationError
from ..video_settings import VideoSettings


class BaseScene:
    """Base class for all scene types."""

    def __init__(
        self,
        type: str,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
    ):
        self.type = type
        self.id = id
        self.cache = cache

    def validate(self):
        """Validates the scene's configuration."""
        if not self.id:
            raise ValidationError(
                f"Scene of type '{self.type}' is missing a "
                "required 'id' field."
            )

    def prepare(self, base_dir: Path) -> List[Path]:
        """
        Prepares the scene by resolving all necessary asset paths.
        This method should be overridden by subclasses that use external files.
        """
        return []

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        """
        Renders the scene into a MoviePy VideoClip.
        This method must be implemented by all concrete subclasses.
        """
        raise NotImplementedError(
            f"The render method for scene type '{self.type}' is "
            "not implemented."
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "BaseScene":
        """Factory method to create specific scene instances."""
        # Local imports to prevent circular dependency issues
        from .title_card_scene import TitleCardScene
        from .image_scene import ImageScene
        from .video_scene import VideoScene
        from .video_images_scene import VideoImagesScene

        scene_type = data.get("type")
        if scene_type == "title_card":
            return TitleCardScene.from_dict(data, base_dir)
        if scene_type == "image":
            return ImageScene.from_dict(data, base_dir)
        if scene_type == "video":
            return VideoScene.from_dict(data, base_dir)
        if scene_type == "video-images":
            return VideoImagesScene.from_dict(data, base_dir)
        raise ValidationError(f"Unknown scene type: {scene_type}")
