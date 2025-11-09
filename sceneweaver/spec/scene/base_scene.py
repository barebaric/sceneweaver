from typing import Dict, Any, Optional, List
from pathlib import Path
import numpy as np
from moviepy import (
    VideoClip,
    ImageClip,
    CompositeVideoClip,
    AudioFileClip,
    CompositeAudioClip,
)
from ...errors import ValidationError
from ..annotation.base_annotation import BaseAnnotation
from ..audio_spec import AudioTrackSpec
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings


class BaseScene:
    """Base class for all scene types."""

    def __init__(
        self,
        type: str,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[BaseAnnotation]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
    ):
        self.type = type
        self.id = id
        self.cache = cache
        self.annotations = annotations or []
        self.effects = effects or []
        self.transition = transition
        self.audio = audio or []

    def validate(self):
        """Validates the scene's configuration."""
        if not self.id:
            raise ValidationError(
                f"Scene of type '{self.type}' is missing a "
                "required 'id' field."
            )

    def find_asset(self, file_name: str, assets: List[Path]) -> Optional[Path]:
        """Finds a resolved asset path from the prepared list."""
        for asset_path in assets:
            if asset_path.name == Path(file_name).name:
                return asset_path
        return None

    def prepare(self, base_dir: Path) -> List[Path]:
        """
        Prepares the scene by resolving all necessary asset paths.
        This method should be overridden by subclasses that use external files.
        """
        resolved_assets = []
        if self.audio:
            for track in self.audio:
                expanded_path = Path(track.file).expanduser()
                absolute_path = (
                    expanded_path
                    if expanded_path.is_absolute()
                    else (base_dir / expanded_path).resolve()
                )
                if not absolute_path.is_file():
                    raise ValidationError(
                        f"In scene '{self.id}', audio file not found at "
                        f"resolved path: {absolute_path}"
                    )
                resolved_assets.append(absolute_path)
        return resolved_assets

    def _apply_annotations_to_clip(
        self, base_clip: VideoClip, settings: VideoSettings
    ) -> VideoClip:
        """Applies the scene's annotations to a rendered clip."""
        if not self.annotations:
            return base_clip

        assert settings.width and settings.height
        canvas_size = (settings.width, settings.height)

        overlay_pil = BaseAnnotation.create_overlay_for_list(
            canvas_size, self.annotations, settings
        )
        annotation_clip = ImageClip(
            np.array(overlay_pil), transparent=True
        ).with_duration(base_clip.duration)

        return CompositeVideoClip([base_clip, annotation_clip])

    def _apply_audio_to_clip(
        self, base_clip: VideoClip, assets: List[Path]
    ) -> VideoClip:
        """Loads and attaches audio tracks to the scene's clip."""
        if not self.audio:
            return base_clip

        print(f"Attaching audio to scene '{self.id}'...")
        audio_clips = []
        for track in self.audio:
            audio_path = self.find_asset(track.file, assets)
            if not audio_path:
                # This should ideally not happen if prepare() is correct
                raise FileNotFoundError(
                    f"Could not find prepared asset for audio file: "
                    f"{track.file}"
                )

            audio_clip = AudioFileClip(str(audio_path))

            # Apply shift
            if track.shift != 0:
                audio_clip = audio_clip.with_start(track.shift)

            # TODO: Apply filters from track.filters

            audio_clips.append(audio_clip)

        if audio_clips:
            scene_audio = CompositeAudioClip(audio_clips)
            return base_clip.with_audio(scene_audio)

        return base_clip

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
