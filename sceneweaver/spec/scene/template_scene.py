import re
from typing import Dict, Any, Optional, List, TYPE_CHECKING, Set
from pathlib import Path
from ruamel.yaml import YAML
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
    "duration",
    "frames",
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
        duration: Optional[Any] = None,
        frames: Optional[int] = None,
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
        self.duration = duration
        self.frames = frames

    def _validate_template_params(self, template_dir: Path):
        """
        Validates that parameters used in template.yaml match those defined in
        params.yaml.
        Raises ValidationError if there are mismatches.
        """
        params_path = template_dir / "params.yaml"
        template_path = template_dir / "template.yaml"

        if not params_path.is_file():
            raise ValidationError(
                f"Template '{self.name}' is missing a 'params.yaml' file."
            )

        if not template_path.is_file():
            raise ValidationError(
                f"Template '{self.name}' is missing a 'template.yaml' file."
            )

        # Load params.yaml to get expected parameters
        yaml_parser = YAML(typ="safe")
        with open(params_path, "r", encoding="utf-8") as f:
            params_data = yaml_parser.load(f)

        if not params_data or "parameters" not in params_data:
            raise ValidationError(
                f"Template '{self.name}' has an invalid 'params.yaml' file. "
                "It must contain a 'parameters' section."
            )

        expected_params = set(params_data["parameters"].keys())

        # Load template.yaml to find used parameters
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Find all Jinja2 variables in the template
        # Pattern to match the following patterns:
        #   {{ variable_name }}
        #   {{ variable_name | filter(...) }}
        var_pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\||\}\})"
        used_params = set(re.findall(var_pattern, template_content))

        # Also find variables used in Jinja2 control structures
        # Pattern to match patterns like:
        #   {% for item in items %}
        #   {% if variable %}
        control_pattern = (
            r"\{%\s*(?:for|if)\s+.*\s+in\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*%\}"
        )
        used_params.update(re.findall(control_pattern, template_content))

        # Check for parameters used in template but not defined in params.yaml
        undefined_params = used_params - expected_params
        if undefined_params:
            raise ValidationError(
                f"Template '{self.name}' uses undefined parameters: "
                f"{', '.join(sorted(undefined_params))}. "
                f"These parameters are not defined in 'params.yaml'."
            )

        # Check for required parameters defined in params.yaml but not used in
        # template
        unused_params = []
        for param_name in expected_params:
            if param_name not in used_params:
                unused_params.append(param_name)

        if unused_params:
            raise ValidationError(
                f"Template '{self.name}' specifies parameters in "
                f"`params.yaml` that are not used in the template: "
                f"{', '.join(sorted(unused_params))}."
            )

    def _load_internal_spec(
        self,
        settings: VideoSettings,
        jinja_env: Environment,
        template_manager: TemplateManager,
    ):
        """Loads and parses the template YAML into an internal VideoSpec."""
        from ..video_spec import VideoSpec

        template_dir = template_manager.resolve(self.name)

        # Validate that params.yaml matches template.yaml
        self._validate_template_params(template_dir)

        template_spec_path = template_dir / "template.yaml"
        if not template_spec_path.is_file():
            raise ValidationError(
                f"Template '{self.name}' is missing a 'template.yaml' file."
            )

        template_content = template_spec_path.read_text(encoding="utf-8")
        template = jinja_env.from_string(template_content)
        context = {"font": settings.font, **self.with_params}
        if self.duration is not None and "duration" not in context:
            context["duration"] = self.duration
        if self.frames is not None and "frames" not in context:
            context["frames"] = self.frames

        rendered_yaml_str = template.render(context)

        self.rendered_yaml = rendered_yaml_str
        yaml_parser = YAML(typ="safe")
        scenes_data = yaml_parser.load(self.rendered_yaml) or []
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

    def resolve_duration(
        self,
        context_duration: Optional[float],
        assets: List[Path],
        settings: VideoSettings,
    ):
        """Orchestrates duration resolution for self and all child scenes."""
        if self._calculated_duration is not None:
            return  # Already resolved

        assert self.internal_spec is not None

        # Determine the template's own potential context duration first.
        parent_context_duration = self._get_fixed_duration(
            assets, settings
        ) or self._get_duration_from_audio(assets)

        # Check if all children are self-sufficient (have fixed durations).
        child_fixed_durations = [
            c._get_fixed_duration(assets, settings)
            for c in self.internal_spec.scenes
        ]

        if all(d is not None for d in child_fixed_durations):
            # Case A: All children are fixed. Their sum defines the duration.
            total_child_duration = sum(
                d for d in child_fixed_durations if d is not None
            )
            self._calculated_duration = total_child_duration
            # Set each child's duration to its own fixed value.
            for i, child in enumerate(self.internal_spec.scenes):
                child._calculated_duration = child_fixed_durations[i]
        else:
            # Case B: At least one child is relative and needs context.
            if parent_context_duration is None:
                raise ValidationError(
                    f"Template '{self.id}' has relative child scenes but no "
                    "duration source itself (e.g., 'audio' or 'duration')."
                )

            self._calculated_duration = parent_context_duration
            # Resolve all children against the parent's context.
            for child in self.internal_spec.scenes:
                child.resolve_duration(
                    parent_context_duration, assets, settings
                )

    def render(
        self, assets: list[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        """
        Renders the internal scenes and assembles them into a single clip.
        """
        assert (
            self.internal_spec is not None
            and self._calculated_duration is not None
        )
        print(f"Rendering internal scenes for template '{self.id}'...")

        internal_clips: List[VideoClip] = []
        for internal_scene in self.internal_spec.scenes:
            assert internal_scene._calculated_duration is not None
            clip = internal_scene.render(assets, settings)
            if clip:
                internal_clips.append(clip)

        if not internal_clips:
            print(f"Warning: Template '{self.id}' produced no video clips.")
            return None

        # Assemble and return. The main generator applies this scene's audio.
        final_clip = render_scene_list_to_clip(
            self.internal_spec.scenes, internal_clips
        )
        if final_clip:
            return final_clip.with_duration(self._calculated_duration)
        return None

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
                "Template scene missing required field: 'name'"
            )
        for key in data:
            if key not in VALID_TEMPLATE_KEYS:
                raise ValidationError(
                    f"Invalid key '{key}' on template '{data.get('id')}'. "
                    f"Pass it inside the 'with' block instead."
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
            duration=data.get("duration"),
            frames=data.get("frames"),
        )

    @classmethod
    def get_asset_path(cls, template_name: str, asset_name: str) -> Path:
        """Get the path to an asset file for a template."""
        template_manager = TemplateManager()
        template_dir = template_manager.resolve(template_name)
        asset_path = template_dir / asset_name

        if not asset_path.is_file():
            raise ValidationError(
                f"Template '{template_name}' is missing an "
                f"'{asset_name}' file."
            )

        return asset_path

    @classmethod
    def get_example(cls, template_name: str) -> Dict[str, Any]:
        """Get example parameters for a template from its example.yaml file."""
        example_path = cls.get_asset_path(template_name, "example.yaml")

        yaml_parser = YAML(typ="safe")
        try:
            with open(example_path, "r", encoding="utf-8") as f:
                example_data = yaml_parser.load(f)
            return example_data or {}
        except Exception as e:
            raise ValidationError(
                f"Error loading example.yaml for template "
                f"'{template_name}': {e}"
            )
