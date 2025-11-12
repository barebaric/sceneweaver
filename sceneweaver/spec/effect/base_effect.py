from typing import Any, Dict, List
from moviepy import VideoClip


class BaseEffect:
    """Base class for all video effects."""

    def __init__(self, type: str, duration: float):
        self.type = type
        self.duration = duration
        self.has_progress_transform = False
        self.is_consumed = False

    def apply(self, clip: VideoClip) -> VideoClip:
        """
        Applies the effect to the given clip.
        This method must be implemented by all concrete subclasses.
        """
        raise NotImplementedError(
            f"The apply method for effect type '{self.type}' is "
            "not implemented."
        )

    def transform_progress(self, linear_progress: float) -> float:
        """
        Allows an effect to modify the progress variable for scenes that
        support it (like SvgScene). By default, it does nothing.
        """
        return linear_progress

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseEffect":
        """Factory method to create specific effect instances."""
        from .accel_decel_effect import AccelDecelEffect
        from .fade_effect import FadeEffect
        from .scroll_effect import ScrollEffect
        from .slide_effect import SlideEffect
        from .zoom_effect import ZoomEffect

        effect_type = data.get("type")
        if effect_type == "accel-decel":
            return AccelDecelEffect.from_dict(data)
        elif effect_type in ["fade-in", "fade-out"]:
            return FadeEffect.from_dict(data)
        elif effect_type == "scroll":
            return ScrollEffect.from_dict(data)
        elif effect_type in ["slide-in", "slide-out"]:
            return SlideEffect.from_dict(data)
        elif effect_type == "zoom":
            return ZoomEffect.from_dict(data)
        raise ValueError(f"Unknown effect type: {effect_type}")

    @classmethod
    def from_list(cls, data: List[Dict[str, Any]]) -> List["BaseEffect"]:
        """Creates a list of effects from a list of dictionaries."""
        if not data:
            return []
        return [cls.from_dict(d) for d in data]
