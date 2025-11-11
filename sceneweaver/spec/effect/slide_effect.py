from typing import Any, Dict, cast

from moviepy import VideoClip
from moviepy.video.fx import SlideIn, SlideOut

from .base_effect import BaseEffect


class SlideEffect(BaseEffect):
    """Handles slide-in and slide-out effects."""

    def __init__(self, type: str, duration: float, side: str = "left"):
        super().__init__(type, duration)
        if side not in ["left", "right", "top", "bottom"]:
            raise ValueError(
                "Slide effect side must be one of 'left', 'right', 'top', "
                "'bottom'"
            )
        self.side = side

    def apply(self, clip: VideoClip) -> VideoClip:
        if self.type == "slide-in":
            effect = SlideIn(duration=self.duration, side=self.side)
            return cast(VideoClip, clip.with_effects([effect]))
        if self.type == "slide-out":
            effect = SlideOut(duration=self.duration, side=self.side)
            return cast(VideoClip, clip.with_effects([effect]))
        return clip  # Should not be reached

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlideEffect":
        return cls(
            type=data["type"],
            duration=data["duration"],
            side=data.get("side", "left"),
        )
