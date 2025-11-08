from typing import Dict, Any, Optional
from ..errors import ValidationError


class VideoSettings:
    def __init__(
        self,
        width: Optional[int],
        height: Optional[int],
        fps: Optional[int],
        output_file: Optional[str],
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.output_file = output_file

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
    def from_dict(cls, data: Dict[str, Any]) -> "VideoSettings":
        instance = cls(
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            output_file=data.get("output_file"),
        )
        instance.validate()
        return instance
