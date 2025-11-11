from typing import Any, Dict, Optional, cast

from moviepy import VideoClip
from moviepy.video.fx import Scroll

from .base_effect import BaseEffect


class ScrollEffect(BaseEffect):
    """Handles scrolling effect on a clip."""

    def __init__(
        self,
        type: str,
        duration: Optional[float] = None,
        w: Optional[int] = None,
        h: Optional[int] = None,
        x_speed: int = 0,
        y_speed: int = 0,
        x_start: int = 0,
        y_start: int = 0,
    ):
        super().__init__(type, duration or 0)
        self.w = w
        self.h = h
        self.x_speed = x_speed
        self.y_speed = y_speed
        self.x_start = x_start
        self.y_start = y_start

    def apply(self, clip: VideoClip) -> VideoClip:
        if self.duration > 0:
            clip = clip.with_duration(self.duration)

        effect = Scroll(
            w=self.w,
            h=self.h,
            x_speed=self.x_speed,
            y_speed=self.y_speed,
            x_start=self.x_start,
            y_start=self.y_start,
        )
        return cast(VideoClip, clip.with_effects([effect]))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScrollEffect":
        return cls(
            type=data["type"],
            duration=data.get("duration"),
            w=data.get("w"),
            h=data.get("h"),
            x_speed=data.get("x_speed", 0),
            y_speed=data.get("y_speed", 0),
            x_start=data.get("x_start", 0),
            y_start=data.get("y_start", 0),
        )
