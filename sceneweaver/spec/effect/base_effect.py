from typing import Dict, Any
from moviepy import VideoClip


class BaseEffect:
    """Base class for all single-clip effects."""

    def __init__(self, type: str, duration: float):
        self.type = type
        self.duration = duration

    def apply(self, clip: VideoClip) -> VideoClip:
        """Applies the effect to the given clip and returns the result."""
        raise NotImplementedError(
            f"The apply method for effect type '{self.type}' is "
            "not implemented."
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEffect":
        """Factory method to create specific effect instances."""
        # Local import to avoid circular dependency
        from .fade_effect import FadeEffect

        effect_type = data.get("type")
        if effect_type in ["fade-in", "fade-out"]:
            return FadeEffect.from_dict(data)
        raise ValueError(f"Unknown effect type: {effect_type}")
