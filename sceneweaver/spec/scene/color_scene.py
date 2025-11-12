from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from moviepy import ColorClip, VideoClip
from PIL import ImageColor

from ...errors import ValidationError
from ..audio_spec import AudioTrackSpec
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class ColorScene(BaseScene):
    """A scene that displays a single solid color."""

    def __init__(
        self,
        color: str,
        base_dir: Path,
        id: Optional[str] = None,
        duration: Optional[Any] = None,
        frames: Optional[int] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
        composite_mode: str = "layer",
    ):
        super().__init__(
            "color",
            base_dir=base_dir,
            id=id,
            cache=None,  # Caching is not useful for simple color clips
            effects=[],
            transition=None,
            audio=audio,
            composite_mode=composite_mode,
        )
        self.duration = duration
        self.frames = frames
        rgba_or_rgb = ImageColor.getrgb(color)
        self.color: Tuple[int, int, int] = rgba_or_rgb[:3]

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        assert self._calculated_duration is not None
        assert settings.width and settings.height
        canvas_size = (settings.width, settings.height)

        base_clip = ColorClip(
            size=canvas_size,
            color=self.color,
            duration=self._calculated_duration,
        )
        return self._apply_audio_to_clip(base_clip, assets)

    @classmethod
    def get_template(cls) -> Dict[str, Any]:
        return {
            "type": "color",
            "duration": 5,
            "color": "#ff00ff",
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "ColorScene":
        if "color" not in data:
            raise ValidationError("ColorScene is missing 'color' field.")

        audio_tracks = AudioTrackSpec.from_list(
            data.get("audio", []), base_dir
        )

        return cls(
            color=data["color"],
            base_dir=base_dir,
            id=data.get("id"),
            duration=data.get("duration"),
            frames=data.get("frames"),
            audio=audio_tracks,
            composite_mode=data.get("composite_mode", "layer"),
        )
