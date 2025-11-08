from typing import Dict, Any, List, Tuple
from PIL import Image, ImageDraw


class BaseAnnotation:
    """Base class for all annotation types."""

    def __init__(self, type: str):
        self.type = type

    def draw(
        self, draw_context: ImageDraw.ImageDraw, canvas_size: Tuple[int, int]
    ):
        """
        Draws the annotation onto the provided PIL Draw context.
        This method must be implemented by all concrete subclasses.
        """
        raise NotImplementedError(
            f"The draw method for annotation type '{self.type}' is "
            "not implemented."
        )

    @classmethod
    def create_overlay_for_list(
        cls, size: Tuple[int, int], annotations: List["BaseAnnotation"]
    ):
        """Creates a single PIL Image overlay from a list of annotations."""
        overlay = Image.new("RGBA", size, (255, 255, 255, 0))
        draw_context = ImageDraw.Draw(overlay)
        for an in annotations:
            an.draw(draw_context, size)
        return overlay

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseAnnotation":
        """Factory method to create specific scene instances."""
        # Local imports to prevent circular dependency issues
        from .highlight_annotation import HighlightAnnotation
        from .arrow_annotation import ArrowAnnotation
        from .text_annotation import TextAnnotation

        ann_type = data.get("type")
        if ann_type == "highlight":
            return HighlightAnnotation.from_dict(data)
        if ann_type == "arrow":
            return ArrowAnnotation.from_dict(data)
        if ann_type == "text":
            return TextAnnotation.from_dict(data)
        raise ValueError(f"Unknown annotation type: {ann_type}")
