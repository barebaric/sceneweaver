from typing import Dict, Any, Optional
from pathlib import Path
from moviepy import VideoClip

from ...errors import ValidationError
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class TemplateScene(BaseScene):
    def __init__(
        self,
        name: str,
        with_params: Dict[str, Any],
        base_dir: Path,
        id: Optional[str] = None,
    ):
        super().__init__("template", base_dir=base_dir, id=id)
        self.name = name
        self.with_params = with_params  # `with` is a keyword

    def render(
        self, assets: list[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        # This scene type is a placeholder and should be expanded during
        # the spec loading phase. It should never be rendered directly.
        raise NotImplementedError(
            "TemplateScene should not be rendered. It must be expanded "
            "before the rendering pipeline begins."
        )

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "TemplateScene":
        if "name" not in data:
            raise ValidationError(
                "Scene type 'template' is missing required field: 'name'."
            )

        # The user writes `with`, but we store it as `with_params`
        # to avoid using a Python keyword.
        return cls(
            name=data["name"],
            with_params=data.get("with", {}),
            id=data.get("id"),
            base_dir=base_dir,
        )
