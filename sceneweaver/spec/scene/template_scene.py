from typing import Dict, Any, Optional, List, TYPE_CHECKING, Set
from pathlib import Path
import yaml
from jinja2 import Environment
from moviepy import VideoClip
from ...errors import ValidationError
from ...renderer import render_scene_list_to_clip
from ...template_manager import TemplateManager
from ..annotation import BaseAnnotation
from ..audio_spec import AudioTrackSpec
from ..effect import BaseEffect
from ..transition import BaseTransition
from ..video_settings import VideoSettings
from .base_scene import BaseScene

if TYPE_CHECKING:
    from ..video_spec import VideoSpec

# These are all the keys that a 'template' block is allowed to have.
VALID_TEMPLATE_KEYS: Set[str] = {
    "type",
    "name",
    "with",
    "id",
    "cache",
    "annotations",
    "effects",
    "transition",
    "audio",
}


class TemplateScene(BaseScene):
    def __init__(
        self,
        name: str,
        with_params: Dict[str, Any],
        base_dir: Path,
        id: Optional[str] = None,
        cache: Optional[Dict[str, Any]] = None,
        annotations: Optional[List[BaseAnnotation]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
    ):
        super().__init__(
            "template",
            base_dir=base_dir,
            id=id,
            cache=cache,
            annotations=annotations,
            effects=effects,
            transition=transition,
            audio=audio,
        )
        self.name = name
        self.with_params = with_params
        self.internal_spec: Optional["VideoSpec"] = None
        self.rendered_yaml: Optional[str] = None

    def _load_internal_spec(
        self,
        settings: VideoSettings,
        jinja_env: Environment,
        template_manager: TemplateManager,
    ):
        """Loads and parses the template YAML into an internal VideoSpec."""
        from ..video_spec import VideoSpec

        template_dir = template_manager.resolve(self.name)
        template_spec_path = template_dir / "template.yaml"
        if not template_spec_path.is_file():
            raise ValidationError(
                f"Template '{self.name}' is missing a 'template.yaml' file."
            )

        template_content = template_spec_path.read_text(encoding="utf-8")
        template = jinja_env.from_string(template_content)

        base_context = {"font": settings.font}
        context = {**base_context, **self.with_params}
        rendered_yaml_str = template.render(context)

        self.rendered_yaml = rendered_yaml_str
        scenes_data = yaml.safe_load(self.rendered_yaml) or []
        if not isinstance(scenes_data, list):
            scenes_data = [scenes_data]

        internal_spec_dict = {"settings": settings, "scenes": scenes_data}
        self.internal_spec = VideoSpec.from_dict(
            internal_spec_dict, template_dir, is_internal=True
        )

    def prepare(self) -> List[Path]:
        """Prepares assets for the template and all its internal scenes."""
        resolved_assets = super().prepare()

        assert self.internal_spec is not None
        for scene in self.internal_spec.scenes:
            resolved_assets.extend(scene.prepare())

        return list(dict.fromkeys(resolved_assets))

    def render(
        self, assets: list[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        """
        Renders the internal scenes and assembles them into a single clip.
        """
        print(f"Rendering internal scenes for template '{self.id}'...")
        assert self.internal_spec is not None

        internal_clips: List[VideoClip] = []
        for internal_scene in self.internal_spec.scenes:
            clip = internal_scene.render(assets, settings)
            if clip:
                internal_clips.append(clip)

        if not internal_clips:
            print(f"Warning: Template '{self.id}' produced no video clips.")
            return None

        # Assemble the internal clips and return the result directly.
        # The generator will handle applying this scene's own overrides.
        return render_scene_list_to_clip(
            self.internal_spec.scenes, internal_clips
        )

    def to_dict(self) -> Dict[str, Any]:
        """Creates a serializable dictionary representation for caching."""
        # Use the stored rendered_yaml for the hash
        return {
            "type": self.type,
            "id": self.id,
            "name": self.name,
            "with": self.with_params,
            "rendered_template": self.rendered_yaml,
            "cache_config": self.cache,
        }

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "TemplateScene":
        """Factory method to create a TemplateScene from a dictionary."""
        if "name" not in data:
            raise ValidationError(
                "Scene type 'template' is missing required field: 'name'."
            )

        # Validate that no unknown keys are present.
        for key in data:
            if key not in VALID_TEMPLATE_KEYS:
                raise ValidationError(
                    f"Invalid key '{key}' found on a template block. "
                    f"To control the template's internal behavior, pass "
                    f"'{key}' as a parameter inside the 'with' block instead."
                )

        return cls(
            name=data["name"],
            with_params=data.get("with", {}),
            id=data.get("id"),
            base_dir=base_dir,
            cache=data.get("cache"),
            annotations=BaseAnnotation.from_list(
                data.get("annotations", []), base_dir
            ),
            effects=BaseEffect.from_list(data.get("effects", [])),
            transition=BaseTransition.from_dict(data.get("transition")),
            audio=AudioTrackSpec.from_list(data.get("audio", []), base_dir),
        )
