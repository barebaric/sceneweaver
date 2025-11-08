from typing import Tuple, Dict, Any
from pathlib import Path
from PIL import ImageDraw, ImageColor
from ..video_settings import VideoSettings
from .base_annotation import BaseAnnotation


class HighlightAnnotation(BaseAnnotation):
    def __init__(
        self,
        rect: Tuple[float, float, float, float],
        color: str = "yellow",
        opacity: float = 0.4,
    ):
        super().__init__("highlight")
        self.rect = rect
        self.color = color
        self.opacity = opacity

    def draw(
        self,
        draw_context: ImageDraw.ImageDraw,
        canvas_size: Tuple[int, int],
        settings: VideoSettings,
    ):
        """Draws the highlight rectangle."""
        canvas_width, canvas_height = canvas_size
        px, py, pw, ph = self.rect

        x1 = (px / 100) * canvas_width
        y1 = (py / 100) * canvas_height
        w = (pw / 100) * canvas_width
        h = (ph / 100) * canvas_height
        x2 = x1 + w
        y2 = y1 + h

        # Use ImageColor to parse any valid color string (including hex)
        rgb_color = ImageColor.getrgb(self.color)

        # Apply opacity
        opacity = int(255 * self.opacity)
        fill_color = rgb_color + (opacity,)

        draw_context.rectangle([x1, y1, x2, y2], fill=fill_color)

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "HighlightAnnotation":
        return cls(
            rect=tuple(data["rect"]),
            color=data.get("color", "yellow"),
            opacity=data.get("opacity", 0.4),
        )
