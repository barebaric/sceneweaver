from typing import Any, Dict, Optional
from moviepy import VideoClip


class BaseTransition:
    """Base class for all two-clip transitions."""

    def __init__(self, type: str, duration: float):
        self.type = type
        self.duration = duration

    def apply(self, from_clip: VideoClip, to_clip: VideoClip) -> VideoClip:
        """Creates a new clip representing the transition."""
        raise NotImplementedError(
            f"The apply method for transition type '{self.type}' is "
            "not implemented."
        )

    @classmethod
    def from_dict(
        cls, data: Optional[Dict[str, Any]]
    ) -> Optional["BaseTransition"]:
        """Factory method to create specific transition instances."""
        if data is None:
            return None

        from .crossfade_transition import CrossfadeTransition

        transition_type = data.get("type")
        if transition_type == "cross-fade":
            return CrossfadeTransition.from_dict(data)
        raise ValueError(f"Unknown transition type: {transition_type}")
