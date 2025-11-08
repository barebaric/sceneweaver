from typing import Tuple, Dict, Any
from pathlib import Path
from PIL import ImageDraw
from ..video_settings import VideoSettings
from .base_annotation import BaseAnnotation


class ArrowAnnotation(BaseAnnotation):
    def __init__(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        color: str = "red",
        width: int = 5,
    ):
        super().__init__("arrow")
        self.start = start
        self.end = end
        self.color = color
        self.width = width

    def draw(
        self,
        draw_context: ImageDraw.ImageDraw,
        canvas_size: Tuple[int, int],
        settings: VideoSettings,
    ):
        """Draws the arrow line."""
        canvas_width, canvas_height = canvas_size
        start_pct_x, start_pct_y = self.start
        end_pct_x, end_pct_y = self.end

        start_x = (start_pct_x / 100) * canvas_width
        start_y = (start_pct_y / 100) * canvas_height
        end_x = (end_pct_x / 100) * canvas_width
        end_y = (end_pct_y / 100) * canvas_height

        draw_context.line(
            [(start_x, start_y), (end_x, end_y)],
            fill=self.color,
            width=self.width,
        )

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "ArrowAnnotation":
        return cls(
            start=tuple(data["start"]),
            end=tuple(data["end"]),
            color=data.get("color", "red"),
            width=data.get("width", 5),
        )
