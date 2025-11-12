from typing import Dict, Any, Optional, List, TYPE_CHECKING, Set
from pathlib import Path
from ruamel.yaml import YAML
from jinja2 import Environment
from jinja2.meta import find_undeclared_variables
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
from .composite_scene import CompositeScene


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
    "composite_mode",
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
        composite_mode: str = "layer",
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
            composite_mode=composite_mode,
        )
        self.name = name
        self.with_params = with_params
        self.internal_spec: Optional["VideoSpec"] = None
        self.rendered_yaml: Optional[str] = None
        self.duration = duration
        self.frames = frames

    def _get_fixed_duration(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[float]:
        """
        Templates can get their duration from their own properties or from
        the `with` block, which takes precedence.
        """
        with_duration = self.with_params.get("duration")
        with_frames = self.with_params.get("frames")

        if with_frames is not None:
            assert settings.fps is not None
            return with_frames / settings.fps
        if isinstance(with_duration, (int, float)):
            return float(with_duration)

        return super()._get_fixed_duration(assets, settings)

    @staticmethod
    def _get_implicit_template_params() -> Set[str]:
        """
        Returns a set of parameter names that are implicitly available in a
        template's Jinja context. These are fundamental scene properties.
        """
        return {"duration", "font", "frames"}

    def _validate_template_params(self, template_dir: Path):
        """
        Validates that parameters used in template.yaml match those defined in
        params.yaml.
        Raises ValidationError if there are mismatches.
        """
        params_path = template_dir / "params.yaml"
        if not params_path.is_file():
            return

        template_path = template_dir / "template.yaml"
        if not template_path.is_file():
            raise ValidationError(
                f"Template '{self.name}' is missing a 'template.yaml' file."
            )

        # Load params.yaml to get defined parameters
        yaml_parser = YAML(typ="safe")
        with open(params_path, "r", encoding="utf-8") as f:
            params_data = yaml_parser.load(f) or {}

        if "parameters" in params_data and isinstance(
            params_data.get("parameters"), dict
        ):
            defined_params = set(params_data["parameters"].keys())
        else:
            defined_params = set()

        # Retrieve implicit parameters available in the Jinja context.
        # 'font' is from global settings; others are fundamental scene
        # properties.
        implicit_params = self._get_implicit_template_params()
        implicit_params.add("font")
        expected_params = defined_params.union(implicit_params)

        # Load template.yaml to find used parameters
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()

        # Use Jinja's parser to reliably find all undeclared variables
        env = Environment()
        try:
            ast = env.parse(template_content)
            used_params = find_undeclared_variables(ast)
        except Exception as e:  # Catch potential Jinja parsing errors
            raise ValidationError(
                f"Template '{self.name}' has a syntax error in "
                f"'template.yaml': {e}"
            ) from e

        # Check for parameters used in template but not defined
        undefined_params = used_params - expected_params
        if undefined_params:
            raise ValidationError(
                f"Template '{self.name}' uses undefined parameters: "
                f"{', '.join(sorted(undefined_params))}. "
                f"These parameters are not defined in 'params.yaml'."
            )

        # Check for parameters defined in params.yaml but not used in template
        unused_defined_params = defined_params - used_params
        if unused_defined_params:
            raise ValidationError(
                f"Template '{self.name}' specifies parameters in "
                f"`params.yaml` that are not used in the template: "
                f"{', '.join(sorted(unused_defined_params))}."
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

        with_duration = self.with_params.get("duration")
        jinja_duration = (
            with_duration if with_duration is not None else self.duration
        )
        if jinja_duration is not None and "duration" not in context:
            context["duration"] = jinja_duration

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
        """
        Resolves the template's own duration, then propagates that context
        down to its internal scenes.
        """
        if self._calculated_duration is not None:
            return  # Already resolved

        assert self.internal_spec is not None

        # First, try to resolve the template's duration from its own properties
        # (duration, frames, audio) or from the parent context.
        try:
            super().resolve_duration(context_duration, assets, settings)
            # If successful, this duration becomes the context for all
            # children.
            for child in self.internal_spec.scenes:
                child.resolve_duration(
                    self._calculated_duration, assets, settings
                )
            return
        except ValidationError:
            # This is expected if the template has a relative duration but no
            # context (e.g., duration: "auto" or just no duration).
            # We now must calculate duration from the children.
            pass

        # Calculate duration from children (bottom-up).
        is_sequence = not (
            len(self.internal_spec.scenes) == 1
            and isinstance(self.internal_spec.scenes[0], CompositeScene)
        )

        if is_sequence:
            # For a sequence, sum the children's durations.
            total_duration = 0.0
            transition_total = 0.0
            for i, child in enumerate(self.internal_spec.scenes):
                child.resolve_duration(None, assets, settings)
                child_dur = child._calculated_duration
                if child_dur is None:
                    raise ValidationError(
                        f"In template '{self.id}', child scene '{child.id}' "
                        "has a relative duration, which is not allowed when "
                        "the template's duration is calculated from its "
                        "children."
                    )
                total_duration += child_dur
                if child.transition and i < len(self.internal_spec.scenes) - 1:
                    transition_total += child.transition.duration
            self._calculated_duration = total_duration - transition_total
        else:
            # For a layered composition, find the max child duration.
            max_duration = 0.0
            composite_child = self.internal_spec.scenes[0]
            # Resolve the composite's children first.
            for scene in composite_child.scenes:  # type: ignore
                scene.resolve_duration(None, assets, settings)
                if scene._calculated_duration is None:
                    raise ValidationError(
                        f"Could not resolve duration for child '{scene.id}'"
                    )
                if scene._calculated_duration > max_duration:
                    max_duration = scene._calculated_duration
            self._calculated_duration = max_duration

        # After calculating from children, re-resolve them with the new
        # context.
        for child in self.internal_spec.scenes:
            child.resolve_duration(self._calculated_duration, assets, settings)

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

        internal_scenes = self.internal_spec.scenes
        if not internal_scenes:
            return None

        # Render raw clips first
        base_clips: List[Optional[VideoClip]] = []
        for scene in internal_scenes:
            assert scene._calculated_duration is not None
            base_clips.append(scene.render(assets, settings))

        # Apply effects to each internal clip
        effect_clips: List[VideoClip] = []
        for i, scene in enumerate(internal_scenes):
            modified_clip = base_clips[i]
            if modified_clip:
                if scene.effects:
                    for effect in scene.effects:
                        if effect.is_consumed:
                            continue
                        modified_clip = effect.apply(modified_clip)
                effect_clips.append(modified_clip)

        if not effect_clips:
            return None

        # Assemble the final clip with transitions
        final_clip = render_scene_list_to_clip(internal_scenes, effect_clips)

        if final_clip:
            return final_clip.with_duration(self._calculated_duration)
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Creates a serializable dictionary representation for caching."""
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
            composite_mode=data.get("composite_mode", "layer"),
        )
