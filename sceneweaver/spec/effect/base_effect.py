from typing import Any, Dict, List
from moviepy import VideoClip


class BaseEffect:
    """Base class for all video effects."""

    def __init__(self, type: str, duration: float):
        self.type = type
        self.duration = duration

    def apply(self, clip: VideoClip) -> VideoClip:
        """
        Applies the effect to the given clip.
        This method must be implemented by all concrete subclasses.
        """
        raise NotImplementedError(
            f"The apply method for effect type '{self.type}' is "
            "not implemented."
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEffect":
        """Factory method to create specific effect instances."""
        from .fade_effect import FadeEffect

        effect_type = data.get("type")
        if effect_type in ["fade-in", "fade-out"]:
            return FadeEffect.from_dict(data)
        raise ValueError(f"Unknown effect type: {effect_type}")

    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> List["BaseEffect"]:
        """Creates a list of effects from a list of dictionaries."""
        if not data:
            return []
        return [cls.from_dict(d) for d in data]
