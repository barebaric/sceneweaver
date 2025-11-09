from typing import Dict, Any, Optional, List
from pathlib import Path
import re
import glob
from moviepy import ImageSequenceClip, VideoClip
from ..annotation.base_annotation import BaseAnnotation
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class VideoImagesScene(BaseScene):
    """A scene created from a sequence of image files."""

    def __init__(
        self,
        fps: int,
        file: str,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[BaseAnnotation]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
    ):
        super().__init__(
            "video-images",
            id=id,
            cache=cache,
            annotations=annotations,
            effects=effects,
            transition=transition,
        )
        self.fps = fps
        self.file = file

    def prepare(self, base_dir: Path) -> List[Path]:
        expanded_path = Path(self.file).expanduser()
        pattern = str(
            expanded_path
            if expanded_path.is_absolute()
            else (base_dir / expanded_path).resolve()
        )

        def natural_sort_key(s):
            return [
                int(text) if text.isdigit() else text.lower()
                for text in re.split("([0-9]+)", s)
            ]

        return sorted(
            [Path(p) for p in glob.glob(pattern)],
            key=lambda x: natural_sort_key(x.name),
        )

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        if not assets:
            print(f"Warning: No images found for pattern: {self.file}")
            return None
        base_clip = ImageSequenceClip([str(p) for p in assets], fps=self.fps)
        return self._apply_annotations_to_clip(base_clip, settings)

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "VideoImagesScene":
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

        annotations = [
            BaseAnnotation.from_dict(ann, base_dir)
            for ann in data.get("annotations", [])
        ]
        effects = [
            BaseEffect.from_dict(eff) for eff in data.get("effects", [])
        ]
        transition = (
            BaseTransition.from_dict(data["transition"])
            if "transition" in data
            else None
        )

        return cls(
            fps=data["fps"],
            file=data["file"],
            id=data.get("id"),
            cache=cache_config,
            annotations=annotations,
            effects=effects,
            transition=transition,
        )
