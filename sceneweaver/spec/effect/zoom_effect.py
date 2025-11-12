from typing import Any, Dict, Optional, cast

from moviepy import VideoClip, ColorClip, CompositeVideoClip
from moviepy.video.fx import Resize

from .base_effect import BaseEffect


class ZoomEffect(BaseEffect):
    """
    Handles a smooth, centered zoom effect on a clip. It ensures the output
    is always a full-sized, centered clip, making it safe for transitions.
    """

    def __init__(
        self,
        type: str,
        duration: Optional[float] = None,
        start_zoom: float = 1.0,
        end_zoom: float = 1.0,
    ):
        super().__init__(type, duration or 0)
        self.start_zoom = start_zoom
        self.end_zoom = end_zoom

    def apply(self, clip: VideoClip) -> VideoClip:
        zoom_duration = (
            self.duration if self.duration > 0 else (clip.duration or 0)
        )

        def resize_func(t):
            """Calculates the new size of the clip at time `t`."""
            progression = (
                min(1.0, t / zoom_duration) if zoom_duration > 0 else 1.0
            )
            current_zoom = (
                self.start_zoom
                + (self.end_zoom - self.start_zoom) * progression
            )

            new_width = max(1, int(clip.size[0] * current_zoom))
            new_height = max(1, int(clip.size[1] * current_zoom))

            return (new_width, new_height)

        # Instantiate the Resize effect
        resize_effect = Resize(resize_func)

        # Apply the effect using the robust with_effects() method
        resized_clip = cast(VideoClip, clip.with_effects([resize_effect]))

        # Manually composite the resized clip onto a full-sized transparent
        # canvas. This guarantees the output is always centered and full-size,
        # preventing "drift" during transitions.
        canvas = ColorClip(
            size=clip.size, color=(0, 0, 0), duration=clip.duration
        ).with_opacity(0)

        # The resized_clip is already a new object, so we can position it.
        centered_clip = CompositeVideoClip(
            [canvas, resized_clip.with_position("center")]
        )

        return cast(VideoClip, centered_clip)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZoomEffect":
        return cls(
            type=data["type"],
            duration=data.get("duration"),
            start_zoom=data.get("start_zoom", 1.0),
            end_zoom=data.get("end_zoom", 1.0),
        )
