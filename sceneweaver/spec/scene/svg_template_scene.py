# FILE: sceneweaver/spec/scene/svg_template_scene.py

import importlib.resources
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from importlib.resources.abc import Traversable

import cairosvg
from jinja2 import Environment, FileSystemLoader
from moviepy import ImageSequenceClip, VideoClip

from ...errors import ValidationError
from ..audio_spec import AudioTrackSpec
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class SvgTemplateScene(BaseScene):
    def __init__(
        self,
        duration: float,
        template: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
    ):
        super().__init__(
            "svg_template",
            id=id,
            cache=cache,
            effects=effects,
            transition=transition,
            audio=audio,
        )
        self.duration = duration
        self.template = template
        self.params = params or {}

    @staticmethod
    def _get_default_template_path() -> Traversable:
        """Returns the path to the default built-in SVG template."""
        return (
            importlib.resources.files("sceneweaver")
            / "resources"
            / "templates"
            / "default_svg"
            / "template.svg"
        )

    def validate(self):
        super().validate()
        if self.duration is None or self.duration <= 0:
            raise ValidationError(
                f"Scene '{self.id}' requires a positive 'duration'."
            )

    def prepare(self, base_dir: Path) -> List[Any]:
        resolved_assets = super().prepare(base_dir)
        if self.template:
            template_path = (base_dir / self.template).resolve()
            if not template_path.is_file():
                raise ValidationError(
                    f"In scene '{self.id}', template file not found at "
                    f"resolved path: {template_path}"
                )
            resolved_assets.append(template_path)
        else:
            # Add the default template to the assets list for caching
            path = cast(Path, self._get_default_template_path())
            resolved_assets.append(path)
        return resolved_assets

    def render(
        self, assets: List[Any], settings: VideoSettings
    ) -> Optional[VideoClip]:
        assert settings.width is not None and settings.height is not None
        assert settings.fps is not None and self.duration is not None

        env: Environment
        template_content: str

        if self.template:
            # Logic for user-provided template
            user_template_path = self.find_asset(self.template, assets)
            if not user_template_path or not isinstance(
                user_template_path, Path
            ):
                raise FileNotFoundError(f"Template not found: {self.template}")

            env = Environment(
                loader=FileSystemLoader(searchpath=user_template_path.parent)
            )
            template = env.get_template(user_template_path.name)
        else:
            # --- MINIMAL CHANGE START ---
            # For packaged resources, we get the parent directory first
            default_template_dir = (
                importlib.resources.files("sceneweaver")
                / "resources"
                / "templates"
                / "default_svg"
            )
            default_template_path = default_template_dir / "template.svg"
            template_content = default_template_path.read_text(
                encoding="utf-8"
            )

            with importlib.resources.as_file(
                default_template_dir
            ) as base_path:
                env = Environment(
                    loader=FileSystemLoader(searchpath=base_path)
                )
            template = env.from_string(template_content)
            # --- MINIMAL CHANGE END ---

        env.globals.update(min=min, max=max, round=round, abs=abs)

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            frame_paths = []
            total_frames = int(self.duration * settings.fps)

            print(f"Rendering {total_frames} frames for scene '{self.id}'...")
            for i in range(total_frames):
                timestamp = i / settings.fps
                context = {
                    **self.params,
                    "timestamp": timestamp,
                    "frame": i,
                    "duration": self.duration,
                    "progress": timestamp / self.duration
                    if self.duration > 0
                    else 0,
                }
                rendered_svg_str = template.render(context)
                output_path = temp_dir / f"frame_{i:05d}.png"

                # Core rendering logic using CairoSVG
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

            # Load images into RAM before the temp dir is deleted
            visual_clip = ImageSequenceClip(
                frame_paths, fps=settings.fps, load_images=True
            )

        clip_with_audio = self._apply_audio_to_clip(visual_clip, assets)
        return clip_with_audio.with_duration(self.duration)

    @classmethod
    def get_template(cls) -> Dict[str, Any]:
        return {
            "type": "svg_template",
            "duration": 5,
            "params": {
                "title": "Default SVG Title",
                "subtitle": "Rendered with CairoSVG",
            },
        }

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "SvgTemplateScene":
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
            duration=data["duration"],
            template=data.get("template"),
            params=data.get("params"),
            id=data.get("id"),
            cache=data.get("cache"),
            effects=effects,
            transition=transition,
            audio=audio_tracks,
        )
        instance.validate()
        return instance
