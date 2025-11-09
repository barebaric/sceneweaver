from typing import Dict, Any, Optional, List
from pathlib import Path
import re
import glob
from moviepy import ImageSequenceClip, VideoClip
from ..annotation.base_annotation import BaseAnnotation
from ..audio_spec import AudioTrackSpec
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class VideoImagesScene(BaseScene):
    def __init__(
        self,
        fps: int,
        file: str,
        base_dir: Path,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[BaseAnnotation]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
    ):
        super().__init__(
            "video-images",
            base_dir=base_dir,
            id=id,
            cache=cache,
            annotations=annotations,
            effects=effects,
            transition=transition,
            audio=audio,
        )
        self.fps = fps
        self.file = file

    def prepare(self) -> List[Path]:
        resolved_assets = super().prepare()
        expanded_path = Path(self.file).expanduser()
        pattern = str(
            expanded_path
            if expanded_path.is_absolute()
            else (self.base_dir / expanded_path).resolve()
        )

        def natural_sort_key(s):
            return [
                int(text) if text.isdigit() else text.lower()
                for text in re.split("([0-9]+)", s)
            ]

        image_files = sorted(
            [Path(p) for p in glob.glob(pattern)],
            key=lambda x: natural_sort_key(x.name),
        )
        resolved_assets.extend(image_files)
        return resolved_assets

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        # Filter out non-image assets like audio files for this operation
        image_assets = [
            p
            for p in assets
            if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]
        ]
        if not image_assets:
            print(f"Warning: No images found for pattern: {self.file}")
            return None

        base_clip = ImageSequenceClip(
            [str(p) for p in image_assets], fps=self.fps
        )
        visual_duration = base_clip.duration

        annotated_clip = self._apply_annotations_to_clip(base_clip, settings)
        clip_with_audio = self._apply_audio_to_clip(annotated_clip, assets)

        # Enforce the scene's duration AFTER audio is attached.
        return clip_with_audio.with_duration(visual_duration)

    @classmethod
    def get_template(cls) -> Dict[str, Any]:
        return {
            "type": "video-images",
            "fps": 25,
            "file": "path/to/frames/*.png",
        }

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "VideoImagesScene":
        cache_config = None
        if "cache" in data:
            cache_value = data.get("cache")
            if cache_value is False:
                cache_config = None
            elif cache_value is True:
                cache_config = {}
            elif cache_value is None:
                cache_config = {}
            elif isinstance(cache_value, dict):
                cache_config = cache_value

        annotations = [
            BaseAnnotation.from_dict(ann, base_dir)
            for ann in data.get("annotations", [])
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

        audio_data = data.get("audio", [])
        if isinstance(audio_data, dict):  # Allow single audio object
            audio_data = [audio_data]
        audio_tracks = [
            AudioTrackSpec.from_dict(track, base_dir) for track in audio_data
        ]

        return cls(
            fps=data["fps"],
            file=data["file"],
            base_dir=base_dir,
            id=data.get("id"),
            cache=cache_config,
            annotations=annotations,
            effects=effects,
            transition=transition,
            audio=audio_tracks,
        )
