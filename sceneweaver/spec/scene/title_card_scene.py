from typing import Optional, Dict, Any, List
from pathlib import Path
from moviepy import TextClip, ColorClip, CompositeVideoClip, VideoClip
from ...errors import ValidationError
from ...font import find_font
from ..annotation.base_annotation import BaseAnnotation
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class TitleCardScene(BaseScene):
    def __init__(
        self,
        duration: Optional[float],
        title: Optional[str],
        subtitle: Optional[str] = None,
        background_color: str = "black",
        font: Optional[str] = None,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[BaseAnnotation]] = None,
    ):
        super().__init__(
            "title_card", id=id, cache=cache, annotations=annotations
        )
        self.duration = duration
        self.title = title
        self.subtitle = subtitle
        self.background_color = background_color
        self.font = font

    def validate(self):
        super().validate()
        if self.duration is None:
            raise ValidationError(
                f"Scene '{self.id}' is missing required field: 'duration'."
            )
        if self.title is None:
            raise ValidationError(
                f"Scene '{self.id}' is missing required field: 'title'."
            )

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        assert self.duration is not None
        assert self.title is not None
        assert settings.width is not None
        assert settings.height is not None

        # Use scene-specific font if available, otherwise use global default
        font_to_use = self.font if self.font is not None else settings.font

        size = (settings.width, settings.height)
        title = TextClip(
            text=self.title,
            font=font_to_use,
            font_size=70,
            margin=(0, 20),
            color="white",
        ).with_position("center")

        subtitle_y_pos = (size[1] / 2) + 70
        subtitle_text = self.subtitle or ""
        subtitle = TextClip(
            text=subtitle_text,
            font=font_to_use,
            font_size=40,
            margin=(0, 20),
            color="lightgrey",
        ).with_position(("center", subtitle_y_pos))

        color_map = {
            "black": (0, 0, 0),
            "white": (255, 255, 255),
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
        }
        bg_color_tuple = color_map.get(
            self.background_color.lower(), (0, 0, 0)
        )

        background = ColorClip(
            size, color=bg_color_tuple, duration=self.duration
        )

        base_clip = CompositeVideoClip([background, title, subtitle])
        final_clip = base_clip.with_duration(self.duration)

        return self._apply_annotations_to_clip(final_clip, settings)

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "TitleCardScene":
        cache_config = None
        if "cache" in data:
            cache_value = data["cache"]
            if cache_value is False:
                cache_config = None
            elif cache_value is True:
                cache_config = {}
            elif cache_value is None:
                cache_config = {}
            elif isinstance(cache_value, dict):
                cache_config = cache_value

        font_identifier = data.get("font")
        validated_font = None
        if font_identifier:
            validated_font = find_font(font_identifier, base_dir)

        annotations = [
            BaseAnnotation.from_dict(ann, base_dir)
            for ann in data.get("annotations", [])
        ]

        instance = cls(
            duration=data.get("duration"),
            title=data.get("title"),
            subtitle=data.get("subtitle"),
            background_color=data.get("background_color", "black"),
            font=validated_font,
            id=data.get("id"),
            cache=cache_config,
            annotations=annotations,
        )
        instance.validate()
        return instance
