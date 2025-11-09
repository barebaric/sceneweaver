from typing import Dict, Any, Optional
from pathlib import Path
from ..errors import ValidationError
from ..font import find_font


class VideoSettings:
    def __init__(
        self,
        width: Optional[int],
        height: Optional[int],
        fps: Optional[int],
        output_file: Optional[str],
        font: str = "DejaVuSans",
        audio_recording_path: str = "audio",
        scene_defaults: Optional[Dict[str, Any]] = None,
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.output_file = output_file
        self.font = font
        self.audio_recording_path = audio_recording_path
        self.scene_defaults = scene_defaults or {}

    def validate(self):
        """Validates the video settings."""
        if self.width is None:
            raise ValidationError(
                "Settings is missing required field: 'width'."
            )
        if self.height is None:
            raise ValidationError(
                "Settings is missing required field: 'height'."
            )
        if self.fps is None:
            raise ValidationError("Settings is missing required field: 'fps'.")
        if self.output_file is None:
            raise ValidationError(
                "Settings is missing required field: 'output_file'."
            )

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "VideoSettings":
        font_identifier = data.get("font", "DejaVuSans")
        validated_font = find_font(font_identifier, base_dir)

        instance = cls(
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            output_file=data.get("output_file"),
            font=validated_font,
            audio_recording_path=data.get("audio_recording_path", "audio"),
            scene_defaults=data.get("scene_defaults", {}),
        )
        instance.validate()
        return instance
