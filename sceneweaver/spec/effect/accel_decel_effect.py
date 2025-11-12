from typing import Any, Dict, cast

from moviepy import VideoClip
from moviepy.video.fx import AccelDecel

from .base_effect import BaseEffect


class AccelDecelEffect(BaseEffect):
    """
    Handles acceleration and deceleration of a clip. The easing curve is
    controlled by the `abruptness` parameter, mirroring MoviePy's behavior.
    - abruptness > 0: Slow -> Fast -> Slow (ease-in-out)
    - abruptness < 0: Fast -> Slow -> Fast (ease-out-in)
    """

    def __init__(
        self,
        type: str,
        duration: float,
        abruptness: float = 1.5,
        soonness: float = 1.0,
        min_speed: float = 0.0,
    ):
        super().__init__(type, duration)
        self.abruptness = abruptness
        self.soonness = soonness
        self.min_speed = min(1.0, max(0.0, min_speed))  # Clamp between 0 and 1
        self.has_progress_transform = True

    def apply(self, clip: VideoClip) -> VideoClip:
        """
        Default post-processing implementation for non-SVG scenes.
        This directly passes the parameters to MoviePy's AccelDecel effect.
        Note: `min_speed` is not supported by the base MoviePy effect.
        """
        effect = AccelDecel(
            new_duration=self.duration,
            abruptness=self.abruptness,
            soonness=self.soonness,
        )
        return cast(VideoClip, clip.with_effects([effect]))

    def transform_progress(self, linear_progress: float) -> float:
        """
        Applies an easing function, mixing it with a linear progression
        controlled by `min_speed` to prevent the animation from stopping.
        """
        t = linear_progress
        if self.abruptness == 0:
            return t  # No effect

        p = abs(self.abruptness)
        eased_progress = 0.0

        if self.abruptness > 0:
            # Slow -> Fast -> Slow (ease-in-out)
            if t < 0.5:
                eased_progress = (2 * t) ** p / 2
            else:
                eased_progress = 1 - (-2 * t + 2) ** p / 2
        else:  # abruptness < 0
            # Fast -> Slow -> Fast (ease-out-in)
            if t < 0.5:
                eased_progress = (1 - (1 - 2 * t) ** p) / 2
            else:
                eased_progress = ((2 * t - 1) ** p) / 2 + 0.5

        # Linearly interpolate between the pure eased curve and linear progress
        # based on the min_speed factor.
        return (eased_progress * (1 - self.min_speed)) + (t * self.min_speed)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccelDecelEffect":
        duration = data.get("duration")

        if duration is None:
            raise ValueError(
                "AccelDecelEffect requires either a 'duration' key."
            )

        return cls(
            type=data["type"],
            duration=duration,
            abruptness=data.get("abruptness", 1.5),
            soonness=data.get("soonness", 1.0),
            min_speed=data.get("min_speed", 0.0),
        )
