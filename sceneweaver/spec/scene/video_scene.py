from typing import Dict, Any, Optional, List
from pathlib import Path
from moviepy import VideoFileClip, VideoClip
from ..annotation.base_annotation import BaseAnnotation
from ..audio_spec import AudioTrackSpec
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class VideoScene(BaseScene):
    def __init__(
        self,
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
            "video",
            base_dir=base_dir,
            id=id,
            cache=cache,
            annotations=annotations,
            effects=effects,
            transition=transition,
            audio=audio,
        )
        self.file = file

    def prepare(self) -> List[Path]:
        resolved_assets = super().prepare()
        expanded_path = Path(self.file).expanduser()
        absolute_path = (
            expanded_path
            if expanded_path.is_absolute()
            else (self.base_dir / expanded_path).resolve()
        )
        resolved_assets.append(absolute_path)
        return resolved_assets

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        video_path = self.find_asset(self.file, assets)
        if not video_path:
            return None

        # Note: VideoFileClip might already have audio. The new audio tracks
        # from the spec will REPLACE the original audio.
        base_clip = VideoFileClip(str(video_path))
        visual_duration = base_clip.duration

        annotated_clip = self._apply_annotations_to_clip(base_clip, settings)
        clip_with_audio = self._apply_audio_to_clip(annotated_clip, assets)

        # Enforce the original video's duration AFTER audio is attached.
        return clip_with_audio.with_duration(visual_duration)

    @classmethod
    def get_template(cls) -> Dict[str, Any]:
        return {"type": "video", "file": "path/to/your/video.mp4"}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "VideoScene":
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
            file=data["file"],
            base_dir=base_dir,
            id=data.get("id"),
            cache=cache_config,
            annotations=annotations,
            effects=effects,
            transition=transition,
            audio=audio_tracks,
        )
