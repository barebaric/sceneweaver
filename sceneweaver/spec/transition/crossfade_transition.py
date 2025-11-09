from typing import Dict, Any, Optional
from moviepy import VideoClip, CompositeVideoClip
from moviepy.video.fx import CrossFadeIn, CrossFadeOut
from .base_transition import BaseTransition


class CrossfadeTransition(BaseTransition):
    """Creates a cross-fade transition between two clips."""

    def apply(self, from_clip: VideoClip, to_clip: VideoClip) -> VideoClip:
        from_trans = from_clip.subclipped(from_clip.duration - self.duration)
        to_trans = to_clip.subclipped(0, self.duration)

        # Apply the cross-fade effects using the robust .with_effects() method
        from_faded = from_trans.with_effects(
            [CrossFadeOut(duration=self.duration)]
        )
        to_faded = to_trans.with_effects([CrossFadeIn(duration=self.duration)])

        # Composite them. The 'to' clip (fading in) should be on top.
        return CompositeVideoClip(
            [from_faded, to_faded.with_start(0)]
        ).with_duration(self.duration)

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Any]]
    ) -> Optional["CrossfadeTransition"]:
        if data is None:
            return None
        return cls(type=data["type"], duration=data["duration"])
