from typing import Dict, Any, Optional, List, Type, Union
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
        base_dir: Path,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[BaseAnnotation]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
    ):
        self.type = type
        self.id = id
        self.base_dir = base_dir
        self.cache = cache
        self.annotations = annotations or []
        self.effects = effects or []
        self.transition = transition
        self.audio = audio or []
        self.duration: Optional[Union[float, str]] = None
        self.frames: Optional[int] = None
        self._calculated_duration: Optional[float] = None

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

    def prepare(self) -> List[Path]:
        """Prepares the scene by resolving all necessary asset paths."""
        resolved_assets = []
        if self.audio:
            for track in self.audio:
                expanded_path = Path(track.file).expanduser()
                absolute_path = (
                    expanded_path
                    if expanded_path.is_absolute()
                    else (self.base_dir / expanded_path).resolve()
                )
                if not absolute_path.is_file():
                    raise ValidationError(
                        f"In scene '{self.id}', audio file not found at "
                        f"resolved path: {absolute_path}"
                    )
                resolved_assets.append(absolute_path)
        return resolved_assets

    def _get_duration_from_audio(self, assets: List[Path]) -> Optional[float]:
        """Calculates the total duration from all audio tracks."""
        if not self.audio:
            return None

        max_end_time = 0.0
        for track in self.audio:
            audio_path = self.find_asset(track.file, assets)
            if audio_path:
                with AudioFileClip(str(audio_path)) as clip:
                    # The end time is the clip's duration plus its start offset
                    end_time = clip.duration + track.shift
                    if end_time > max_end_time:
                        max_end_time = end_time

        return max_end_time if max_end_time > 0 else None

    def _get_fixed_duration(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[float]:
        """
        Determines a scene's duration if it's explicitly fixed.
        This base implementation handles frames and numeric duration.
        Subclasses with intrinsic durations (like VideoScene) must override it.
        """
        if self.frames is not None:
            assert settings.fps is not None
            return self.frames / settings.fps
        if isinstance(self.duration, (int, float)):
            return float(self.duration)
        if isinstance(self.duration, str):
            try:
                return float(self.duration)
            except ValueError:
                return None  # It's a declarative string like "auto" or "%"
        return None

    def resolve_duration(
        self,
        context_duration: Optional[float],
        assets: List[Path],
        settings: VideoSettings,
    ):
        """
        Calculates and sets the final _calculated_duration for the scene.
        This is the single entry point for all duration logic.
        """
        if self._calculated_duration is not None:
            return  # Already resolved

        # Case 1: The scene has its own fixed duration.
        fixed_duration = self._get_fixed_duration(assets, settings)
        if fixed_duration is not None:
            self._calculated_duration = fixed_duration
            return

        # Case 2: The scene has a relative duration ('auto', '%', or None).
        # It needs a context to resolve against.
        effective_context = context_duration
        if effective_context is None:
            # A top-level scene uses its own audio as its context.
            effective_context = self._get_duration_from_audio(assets)

        if effective_context is None:
            raise ValidationError(
                f"Scene '{self.id}' has a relative duration but no context "
                "was available. Add an 'audio' track to this scene or place "
                "it in a template that provides a duration."
            )

        # Resolve relative duration against the context.
        if self.duration is None or self.duration == "auto":
            self._calculated_duration = effective_context
        elif isinstance(self.duration, str) and self.duration.endswith("%"):
            try:
                percent = float(self.duration[:-1])
                self._calculated_duration = effective_context * (percent / 100)
            except ValueError:
                raise ValidationError(f"Invalid % value: '{self.duration}'")
        else:
            # This case should ideally not be hit if parsing is correct
            raise ValidationError(
                f"Unhandled duration format: {self.duration}"
            )

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
                raise FileNotFoundError(
                    f"Could not find asset for audio file: {track.file}"
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
        """Renders the scene into a MoviePy VideoClip."""
        raise NotImplementedError(
            f"Render method for scene type '{self.type}' is not implemented."
        )

    @classmethod
    def get_template(cls) -> Dict[str, Any]:
        """Returns a dictionary with default values for a new scene."""
        raise NotImplementedError("get_template must be implemented.")

    @classmethod
    def _get_scene_types(cls) -> Dict[str, Type["BaseScene"]]:
        """Central registry of scene types."""
        from .image_scene import ImageScene
        from .svg_scene import SvgScene
        from .template_scene import TemplateScene
        from .video_scene import VideoScene
        from .video_images_scene import VideoImagesScene

        return {
            "image": ImageScene,
            "svg": SvgScene,
            "template": TemplateScene,
            "video": VideoScene,
            "video-images": VideoImagesScene,
        }

    @classmethod
    def get_available_types(cls) -> List[str]:
        """Returns a list of all known scene type names."""
        # We don't want users to be able to add 'template' scenes directly
        # via the CLI prompt, as they are meant for expansion only.
        available_types = list(cls._get_scene_types().keys())
        available_types.remove("template")
        return available_types

    @classmethod
    def get_scene_class(cls, scene_type: str) -> Type["BaseScene"]:
        """Returns the class for a given scene type name."""
        scene_map = cls._get_scene_types()
        if scene_type not in scene_map:
            raise ValueError(f"Unknown scene type: {scene_type}")
        return scene_map[scene_type]

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "BaseScene":
        """
        Factory method to create specific scene instances from a dictionary.
        """
        scene_type = data.get("type")
        if not scene_type:
            raise ValidationError("Scene data is missing the 'type' field.")
        scene_class = cls.get_scene_class(scene_type)
        return scene_class.from_dict(data, base_dir)
