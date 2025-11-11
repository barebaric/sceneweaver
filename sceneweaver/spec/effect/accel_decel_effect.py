from typing import Any, Dict, cast

from moviepy import VideoClip
from moviepy.video.fx import AccelDecel

from .base_effect import BaseEffect


class AccelDecelEffect(BaseEffect):
    """Handles acceleration and deceleration of a clip."""

    def __init__(
        self,
        type: str,
        duration: float,  # This will be the new_duration
        abruptness: float = 1.0,
        soonness: float = 1.0,
    ):
        super().__init__(type, duration)
        self.abruptness = abruptness
        self.soonness = soonness

    def apply(self, clip: VideoClip) -> VideoClip:
        effect = AccelDecel(
            new_duration=self.duration,
            abruptness=self.abruptness,
            soonness=self.soonness,
        )
        return cast(VideoClip, clip.with_effects([effect]))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccelDecelEffect":
        if "new_duration" not in data:
            raise ValueError("AccelDecelEffect requires 'new_duration'.")
        return cls(
            type=data["type"],
            duration=data["new_duration"],
            abruptness=data.get("abruptness", 1.0),
            soonness=data.get("soonness", 1.0),
        )
