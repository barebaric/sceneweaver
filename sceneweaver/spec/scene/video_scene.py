from typing import Dict, Any, Optional, List
from pathlib import Path
from moviepy import VideoFileClip, VideoClip
from .base_scene import BaseScene
from ..video_settings import VideoSettings


class VideoScene(BaseScene):
    def __init__(
        self,
        file: str,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
    ):
        super().__init__("video", id=id, cache=cache)
        self.file = file

    def prepare(self, base_dir: Path) -> List[Path]:
        expanded_path = Path(self.file).expanduser()
        absolute_path = (
            expanded_path
            if expanded_path.is_absolute()
            else (base_dir / expanded_path).resolve()
        )
        return [absolute_path]

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        if not assets:
            return None
        return VideoFileClip(str(assets[0]))

    @classmethod
    def from_dict(cls, data: Dict[str, Any], base_dir: Path) -> "VideoScene":
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
            file=data["file"],
            id=data.get("id"),
            cache=cache_config,
        )
