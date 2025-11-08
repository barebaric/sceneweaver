from typing import Dict, Any, Optional, List
from pathlib import Path
import re
import glob
from moviepy import ImageSequenceClip, VideoClip
from .base_scene import BaseScene
from ..video_settings import VideoSettings


class VideoImagesScene(BaseScene):
    """A scene created from a sequence of image files."""

    def __init__(
        self,
        fps: int,
        file: str,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
    ):
        super().__init__("video-images", id=id, cache=cache)
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
        return ImageSequenceClip([str(p) for p in assets], fps=self.fps)

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

        return cls(
            fps=data["fps"],
            file=data["file"],
            id=data.get("id"),
            cache=cache_config,
        )
