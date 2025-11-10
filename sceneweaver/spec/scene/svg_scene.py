import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
import cairosvg
from jinja2 import Environment, FileSystemLoader
from moviepy import ImageSequenceClip, VideoClip, ColorClip, CompositeVideoClip
from PIL import ImageColor
from ...errors import ValidationError
from ..audio_spec import AudioTrackSpec
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class SvgScene(BaseScene):
    def __init__(
        self,
        template: str,
        base_dir: Path,
        duration: Optional[Union[float, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
        composite_on: Optional[str] = "black",
    ):
        super().__init__(
            "svg",
            base_dir=base_dir,
            id=id,
            cache=cache,
            effects=effects,
            transition=transition,
            audio=audio,
        )
        self.duration = duration
        self.template = template
        self.params = params or {}
        # Convert the color string to an RGB tuple upon initialization
        self.composite_on: Optional[Tuple[int, int, int]] = None
        if composite_on:
            # getrgb can return RGBA, but ColorClip only wants RGB.
            # So we slice the result to ensure we only get the first 3 values.
            rgba_or_rgb = ImageColor.getrgb(composite_on)
            self.composite_on = rgba_or_rgb[:3]

    def validate(self):
        super().validate()
        if not self.template:
            raise ValidationError(
                f"Scene '{self.id}' is missing the required 'template' field."
            )

    def prepare(self) -> List[Any]:
        resolved_assets = super().prepare()
        template_path = (self.base_dir / self.template).resolve()
        if not template_path.is_file():
            raise ValidationError(
                f"In scene '{self.id}', template file not found at "
                f"resolved path: {template_path}"
            )
        resolved_assets.append(template_path)
        return resolved_assets

    def render(
        self, assets: List[Any], settings: VideoSettings
    ) -> Optional[VideoClip]:
        assert self._calculated_duration is not None, (
            "Duration must be resolved."
        )
        assert settings.width and settings.height and settings.fps

        user_template_path = self.find_asset(self.template, assets)
        if not user_template_path or not isinstance(user_template_path, Path):
            raise FileNotFoundError(f"Template not found: {self.template}")

        env = Environment(
            loader=FileSystemLoader(searchpath=user_template_path.parent)
        )
        template = env.get_template(user_template_path.name)
        env.globals.update(min=min, max=max, round=round, abs=abs)

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            frame_paths = []
            total_frames = int(self._calculated_duration * settings.fps)

            print(f"Rendering {total_frames} frames for scene '{self.id}'...")
            for i in range(total_frames):
                timestamp = i / settings.fps
                context = {
                    **self.params,
                    "timestamp": timestamp,
                    "frame": i,
                    "duration": self._calculated_duration,
                    "progress": timestamp / self._calculated_duration
                    if self._calculated_duration > 0
                    else 0,
                }
                rendered_svg_str = template.render(context)
                output_path = temp_dir / f"frame_{i:05d}.png"

                cairosvg.svg2png(
                    bytestring=rendered_svg_str.encode("utf-8"),
                    write_to=str(output_path),
                    output_width=settings.width,
                    output_height=settings.height,
                )
                frame_paths.append(str(output_path))

            if not frame_paths:
                print(
                    f"Warning: No frames were generated for scene '{self.id}'."
                )
                return None

            # Create the transparent overlay clip.
            overlay_clip = ImageSequenceClip(
                frame_paths, fps=settings.fps, with_mask=True, load_images=True
            )

            visual_clip: VideoClip
            if self.composite_on:
                background = ColorClip(
                    size=(settings.width, settings.height),
                    color=self.composite_on,
                    duration=self._calculated_duration,
                )
                visual_clip = CompositeVideoClip([background, overlay_clip])
            else:
                visual_clip = overlay_clip

        clip_with_audio = self._apply_audio_to_clip(visual_clip, assets)
        return clip_with_audio.with_duration(self._calculated_duration)

    @classmethod
    def get_template(cls) -> Dict[str, Any]:
        return {
            "type": "svg",
            "duration": 5,
            "template": "path/to/your/template.svg",
            "params": {"text_variable": "Hello World"},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "SvgScene":
        if "template" not in data:
            raise ValidationError(
                "SvgScene missing required field: 'template'"
            )
        audio_data = data.get("audio", [])
        if isinstance(audio_data, dict):
            audio_data = [audio_data]
        audio_tracks = [
            AudioTrackSpec.from_dict(track, base_dir) for track in audio_data
        ]
        effects = [
            BaseEffect.from_dict(eff) for eff in data.get("effects", [])
        ]
        transition_data = data.get("transition")
        transition = (
            BaseTransition.from_dict(transition_data)
            if transition_data
            else None
        )

        instance = cls(
            duration=data.get("duration"),
            template=data["template"],
            base_dir=base_dir,
            params=data.get("params"),
            id=data.get("id"),
            cache=data.get("cache"),
            effects=effects,
            transition=transition,
            audio=audio_tracks,
            composite_on=data.get("composite_on", "black"),
        )
        instance.validate()
        return instance
