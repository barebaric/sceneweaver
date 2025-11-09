from typing import Dict, Any, cast
from moviepy import VideoClip
from moviepy.video.fx import FadeIn, FadeOut
from .base_effect import BaseEffect


class FadeEffect(BaseEffect):
    """Handles fade-in and fade-out effects."""

    def apply(self, clip: VideoClip) -> VideoClip:
        if self.type == "fade-in":
            # The correct, robust method: instantiate the effect class
            # and apply it using .with_effects()
            effect = FadeIn(duration=self.duration)
            return cast(VideoClip, clip.with_effects([effect]))
        if self.type == "fade-out":
            effect = FadeOut(duration=self.duration)
            return cast(VideoClip, clip.with_effects([effect]))
        # Should not happen due to factory validation
        return clip

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FadeEffect":
        return cls(type=data["type"], duration=data["duration"])
