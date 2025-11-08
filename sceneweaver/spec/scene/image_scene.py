from typing import Optional, List, Dict, Any
from pathlib import Path
import numpy as np
from moviepy import (
    ImageClip,
    CompositeVideoClip,
    VideoClip,
    ColorClip,
)
from moviepy.video.fx import Crop, Resize
from PIL import ImageColor
from ...errors import ValidationError
from .base_scene import BaseScene
from ..annotation.base_annotation import BaseAnnotation
from ..zoom_spec import ZoomSpec
from ..video_settings import VideoSettings


class ImageScene(BaseScene):
    def __init__(
        self,
        image: Optional[str],
        duration: Optional[float] = None,
        frames: Optional[int] = None,
        annotations: Optional[List[BaseAnnotation]] = None,
        zoom: Optional[ZoomSpec] = None,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        stretch: bool = False,
        position: Any = "center",
        width: Optional[int] = None,
        height: Optional[int] = None,
        bg_color: str = "black",
    ):
        super().__init__("image", id=id, cache=cache)
        self.duration = duration
        self.frames = frames
        self.image = image
        self.annotations = annotations or []
        self.zoom = zoom
        self.stretch = stretch
        self.position = position
        self.width = width
        self.height = height
        self.bg_color = ImageColor.getrgb(bg_color)
        self._calculated_duration: Optional[float] = None

    def validate(self):
        super().validate()
        if self.duration is None and self.frames is None:
            raise ValidationError(
                f"Scene '{self.id}' requires either 'duration' or 'frames'."
            )
        if self.duration is not None and self.frames is not None:
            raise ValidationError(
                f"Scene '{self.id}' cannot have both 'duration' and 'frames'."
            )
        if self.image is None:
            raise ValidationError(
                f"Scene '{self.id}' is missing required field: 'image'."
            )
        if not self.stretch:
            if self.width is not None and self.height is not None:
                raise ValidationError(
                    f"Scene '{self.id}': cannot specify both 'width' and "
                    "'height' when 'stretch' is false."
                )

    def prepare(self, base_dir: Path) -> List[Path]:
        assert self.image is not None
        expanded_path = Path(self.image).expanduser()
        absolute_path = (
            expanded_path
            if expanded_path.is_absolute()
            else (base_dir / expanded_path).resolve()
        )

        if not absolute_path.is_file():
            raise ValidationError(
                f"In scene '{self.id}', image file not found at "
                f"resolved path: {absolute_path}"
            )

        return [absolute_path]

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        if not assets:
            return None

        if self.frames is not None:
            assert settings.fps is not None
            self._calculated_duration = self.frames / settings.fps
        else:
            self._calculated_duration = self.duration

        assert self._calculated_duration is not None

        image_path = assets[0]
        assert settings.width
        assert settings.height
        canvas_size = (settings.width, settings.height)
        img_clip = ImageClip(str(image_path)).with_duration(
            self._calculated_duration
        )

        annotation_clip = None
        if self.annotations:
            overlay_pil = BaseAnnotation.create_overlay_for_list(
                img_clip.size, self.annotations
            )
            annotation_clip = ImageClip(
                np.array(overlay_pil), transparent=True
            ).with_duration(self._calculated_duration)

        if self.zoom:
            zoom_params = self.zoom
            assert zoom_params is not None
            assert self._calculated_duration > 0

            def resize_func(t):
                x1_start, y1_start, w_start, h_start = zoom_params.start_rect
                x1_end, y1_end, w_end, h_end = zoom_params.end_rect
                progress = t / self._calculated_duration
                w = w_start + (w_end - w_start) * progress
                h = h_start + (h_end - h_start) * progress
                x = x1_start + (x1_end - x1_start) * progress
                y = y1_start + (y1_end - y1_start) * progress
                return (x, y, w, h)

            img_clip = img_clip.fx(
                Crop,
                x1=lambda t: resize_func(t)[0],
                y1=lambda t: resize_func(t)[1],
                width=lambda t: resize_func(t)[2],
                height=lambda t: resize_func(t)[3],
            )

            if annotation_clip:
                annotation_clip = annotation_clip.fx(
                    Crop,
                    x1=lambda t: resize_func(t)[0],
                    y1=lambda t: resize_func(t)[1],
                    width=lambda t: resize_func(t)[2],
                    height=lambda t: resize_func(t)[3],
                )

        clips_to_composite = [img_clip]
        if annotation_clip:
            clips_to_composite.append(annotation_clip)

        content_layer = CompositeVideoClip(clips_to_composite)

        if self.stretch:
            # Default behavior: stretch to fill the screen
            final_clip = content_layer.with_effects([Resize(canvas_size)])
        else:
            # Preserve aspect ratio, place on a background, and position
            resized_content = content_layer
            if self.width or self.height:
                # Resize if width or height is specified
                resize_kwargs = {}
                if self.width:
                    resize_kwargs["width"] = (self.width / 100) * canvas_size[
                        0
                    ]
                elif self.height:
                    resize_kwargs["height"] = (
                        self.height / 100
                    ) * canvas_size[1]

                # Apply resize using the original with_effects structure
                resized_content = content_layer.with_effects(
                    [Resize(**resize_kwargs)]
                )

            # If neither width nor height is given, use natural image size

            background = ColorClip(
                canvas_size,
                color=self.bg_color,
                duration=self._calculated_duration,
            )

            # Position the content layer on the background
            positioned_content = resized_content.with_position(  # type:ignore
                self.position
            )

            final_clip = CompositeVideoClip([background, positioned_content])

        return final_clip.with_duration(self._calculated_duration)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageScene":
        annotations = [
            BaseAnnotation.from_dict(ann)
            for ann in data.get("annotations", [])
        ]
        zoom = ZoomSpec.from_dict(data["zoom"]) if "zoom" in data else None

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

        instance = cls(
            duration=data.get("duration"),
            frames=data.get("frames"),
            image=data.get("image"),
            annotations=annotations,
            zoom=zoom,
            id=data.get("id"),
            cache=cache_config,
            stretch=data.get("stretch", True),
            position=data.get("position", "center"),
            width=data.get("width"),
            height=data.get("height"),
            bg_color=data.get("bg_color", "black"),
        )
        instance.validate()
        return instance
