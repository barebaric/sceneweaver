from typing import Optional, List, Dict, Any
from pathlib import Path
import numpy as np
from moviepy import ImageClip, CompositeVideoClip, VideoClip, ColorClip
from moviepy.video.fx import Crop, Resize
from PIL import ImageColor
from ...errors import ValidationError
from ..annotation.base_annotation import BaseAnnotation
from ..audio_spec import AudioTrackSpec
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings
from ..zoom_spec import ZoomSpec
from .base_scene import BaseScene


class ImageScene(BaseScene):
    def __init__(
        self,
        base_dir: Path,
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
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
    ):
        super().__init__(
            "image",
            base_dir=base_dir,
            id=id,
            cache=cache,
            annotations=annotations,
            effects=effects,
            transition=transition,
            audio=audio,
        )
        self.duration = duration
        self.frames = frames
        self.image = image
        self.zoom = zoom
        self.stretch = stretch
        self.position = position
        self.width = width
        self.height = height
        self.bg_color = ImageColor.getrgb(bg_color)
        self._calculated_duration: Optional[float] = None

    def validate(self):
        super().validate()
        if self.duration is None and self.frames is None and not self.audio:
            raise ValidationError(
                f"Scene '{self.id}' requires 'duration', 'frames', or 'audio'."
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

    def prepare(self) -> List[Path]:
        resolved_assets = super().prepare()
        assert self.image is not None
        expanded_path = Path(self.image).expanduser()
        absolute_path = (
            expanded_path
            if expanded_path.is_absolute()
            else (self.base_dir / expanded_path).resolve()
        )

        if not absolute_path.is_file():
            raise ValidationError(
                f"In scene '{self.id}', image file not found at "
                f"resolved path: {absolute_path}"
            )

        resolved_assets.append(absolute_path)
        return resolved_assets

    def _create_background_with_image(
        self, content_clip: VideoClip, settings: VideoSettings
    ) -> VideoClip:
        """
        Takes a content clip and places it on a canvas according to the
        scene's stretch, size, and position settings.
        """
        assert settings.width and settings.height
        canvas_size = (settings.width, settings.height)

        if self.stretch:
            stretched_clip = content_clip.with_effects([Resize(canvas_size)])
            assert isinstance(stretched_clip, VideoClip)
            return stretched_clip
        else:
            processed_clip = content_clip
            if self.width or self.height:
                resize_kwargs = {}
                if self.width:
                    resize_kwargs["width"] = (self.width / 100) * canvas_size[
                        0
                    ]
                elif self.height:
                    resize_kwargs["height"] = (
                        self.height / 100
                    ) * canvas_size[1]
                resized_clip = content_clip.with_effects(
                    [Resize(**resize_kwargs)]
                )
                assert isinstance(resized_clip, VideoClip)
                processed_clip = resized_clip

            background = ColorClip(
                canvas_size,
                color=self.bg_color,
                duration=self._calculated_duration,
            )
            positioned_content = processed_clip.with_position(self.position)
            return CompositeVideoClip([background, positioned_content])

    def _render_zoomed_scene(
        self, img_clip: ImageClip, settings: VideoSettings
    ) -> VideoClip:
        """Renders the scene with a zoom effect."""
        assert self.zoom is not None
        zoom_spec = self.zoom
        assert (
            self._calculated_duration is not None
            and self._calculated_duration > 0
        )

        def resize_func(t):
            x1_start, y1_start, w_start, h_start = zoom_spec.start_rect
            x1_end, y1_end, w_end, h_end = zoom_spec.end_rect
            progress = t / self._calculated_duration
            w = w_start + (w_end - w_start) * progress
            h = h_start + (h_end - h_start) * progress
            x = x1_start + (x1_end - x1_start) * progress
            y = y1_start + (y1_end - y1_start) * progress
            return (x, y, w, h)

        # Apply the crop/zoom effect to the main image clip
        zoomed_img_clip = img_clip.fx(  # type: ignore
            Crop,
            x1=lambda t: resize_func(t)[0],
            y1=lambda t: resize_func(t)[1],
            width=lambda t: resize_func(t)[2],
            height=lambda t: resize_func(t)[3],
        )
        assert isinstance(zoomed_img_clip, VideoClip)

        clips_to_composite = [zoomed_img_clip]

        # If annotations exist, apply the *same* crop/zoom and add them
        if self.annotations:
            overlay_pil = BaseAnnotation.create_overlay_for_list(
                img_clip.size, self.annotations, settings
            )
            annotation_clip = ImageClip(
                np.array(overlay_pil), transparent=True
            ).with_duration(self._calculated_duration)

            zoomed_annotation_clip = annotation_clip.fx(
                Crop,
                x1=lambda t: resize_func(t)[0],
                y1=lambda t: resize_func(t)[1],
                width=lambda t: resize_func(t)[2],
                height=lambda t: resize_func(t)[3],
            )
            clips_to_composite.append(zoomed_annotation_clip)

        content_layer = CompositeVideoClip(clips_to_composite)

        return self._create_background_with_image(content_layer, settings)

    def _render_static_scene(
        self, img_clip: ImageClip, settings: VideoSettings
    ) -> VideoClip:
        """Renders the scene without a zoom effect."""
        # First, place the image on the canvas.
        background_with_image = self._create_background_with_image(
            img_clip, settings
        )

        # Then, apply annotations to the composited clip.
        return self._apply_annotations_to_clip(background_with_image, settings)

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        assert self.image is not None
        image_path = self.find_asset(self.image, assets)
        if not image_path:
            return None

        # Determine duration hierarchy: frames > duration > audio
        if self.frames is not None:
            assert settings.fps is not None
            self._calculated_duration = self.frames / settings.fps
        elif self.duration is not None:
            self._calculated_duration = self.duration
        else:
            self._calculated_duration = self._get_duration_from_audio(assets)

        if self._calculated_duration is None:
            raise ValidationError(
                f"Could not determine duration for scene '{self.id}'."
            )

        img_clip = ImageClip(str(image_path)).with_duration(
            self._calculated_duration
        )

        visual_clip: VideoClip
        if self.zoom:
            visual_clip = self._render_zoomed_scene(img_clip, settings)
        else:
            visual_clip = self._render_static_scene(img_clip, settings)

        clip_with_audio = self._apply_audio_to_clip(visual_clip, assets)

        return clip_with_audio.with_duration(self._calculated_duration)

    @classmethod
    def get_template(cls) -> Dict[str, Any]:
        return {
            "type": "image",
            "duration": 5,
            "image": "path/to/your/image.png",
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "ImageScene":
        annotations = [
            BaseAnnotation.from_dict(ann, base_dir)
            for ann in data.get("annotations", [])
        ]
        zoom = ZoomSpec.from_dict(data["zoom"]) if "zoom" in data else None

        audio_data = data.get("audio", [])
        if isinstance(audio_data, dict):  # Allow single audio object
            audio_data = [audio_data]
        audio_tracks = [
            AudioTrackSpec.from_dict(track, base_dir) for track in audio_data
        ]

        cache_config = None
        if "cache" in data:
            cache_value = data.get("cache")
            if cache_value is False:
                cache_config = None
            elif cache_value is True or cache_value is None:
                cache_config = {}
            elif isinstance(cache_value, dict):
                cache_config = cache_value

        effects = [
            BaseEffect.from_dict(eff) for eff in data.get("effects", [])
        ]

        transition_data = data.get("transition")
        transition = (
            BaseTransition.from_dict(transition_data)
            if transition_data
            else None
        )

        duration_val = data.get("duration")
        duration = float(duration_val) if duration_val is not None else None

        instance = cls(
            base_dir=base_dir,
            duration=duration,
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
            effects=effects,
            transition=transition,
            audio=audio_tracks,
        )
        instance.validate()
        return instance
