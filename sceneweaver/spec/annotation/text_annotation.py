from typing import Tuple, Dict, Any, Optional
from PIL import ImageDraw, ImageFont, ImageColor
from .base_annotation import BaseAnnotation


class TextAnnotation(BaseAnnotation):
    def __init__(
        self,
        content: str,
        position: Optional[Tuple[float, float]] = None,
        location: Optional[str] = None,
        fontsize: int = 36,
        color: str = "white",
        bg_color: str = "black",
        bg_opacity: float = 0.7,
    ):
        super().__init__("text")
        if position is None and location is None:
            raise ValueError(
                "Text annotation requires either 'position' or 'location'."
            )
        if position is not None and location is not None:
            raise ValueError(
                "Text annotation cannot have both 'position' and 'location'."
            )
        self.position = position
        self.location = location
        self.content = content
        self.fontsize = fontsize
        self.color = color
        self.bg_color = bg_color
        self.bg_opacity = bg_opacity

    def draw(
        self, draw_context: ImageDraw.ImageDraw, canvas_size: Tuple[int, int]
    ):
        canvas_width, canvas_height = canvas_size

        try:
            font = ImageFont.truetype("DejaVuSans.ttf", size=self.fontsize)
        except IOError:
            font = ImageFont.load_default(size=self.fontsize)

        if self.position:
            pos_pct_x, pos_pct_y = self.position
            pos_x = (pos_pct_x / 100) * canvas_width
            pos_y = (pos_pct_y / 100) * canvas_height
            draw_context.text(
                (pos_x, pos_y), self.content, font=font, fill=self.color
            )
            return

        if self.location:
            # Get bounding box of the text
            left, top, right, bottom = draw_context.textbbox(
                (0, 0), self.content, font=font
            )
            text_width = right - left
            text_height = bottom - top

            if self.location == "bottom":
                bg_height = text_height * 2.5
                bg_y = canvas_height - bg_height
                text_y = bg_y + (bg_height - text_height) / 2
            elif self.location == "top":
                bg_height = text_height * 2.5
                bg_y = 0
                text_y = (bg_height - text_height) / 2
            else:  # center
                bg_height = 0
                bg_y = 0
                text_y = (canvas_height - text_height) / 2

            text_x = (canvas_width - text_width) / 2

            # Draw background for top/bottom locations
            if self.location in ["top", "bottom"]:
                rgb_color = ImageColor.getrgb(self.bg_color)
                opacity = int(255 * self.bg_opacity)
                fill_color = rgb_color + (opacity,)
                draw_context.rectangle(
                    [0, bg_y, canvas_width, bg_y + bg_height], fill=fill_color
                )

            draw_context.text(
                (text_x, text_y), self.content, font=font, fill=self.color
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TextAnnotation":
        content = data.get("content") or data.get("caption")
        if not content:
            raise ValueError(
                "Text annotation requires a 'content' or 'caption' field."
            )
        return cls(
            position=tuple(data["position"]) if "position" in data else None,
            location=data.get("location"),
            content=content,
            fontsize=data.get("fontsize", 36),
            color=data.get("color", "white"),
            bg_color=data.get("bg_color", "black"),
            bg_opacity=data.get("bg_opacity", 0.7),
        )
