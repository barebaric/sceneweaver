from typing import Any, Dict, List, Optional
from pathlib import Path

from moviepy import CompositeVideoClip, VideoClip, ColorClip

from ...errors import ValidationError
from ..audio_spec import AudioTrackSpec
from ..effect.base_effect import BaseEffect
from ..transition.base_transition import BaseTransition
from ..video_settings import VideoSettings
from .base_scene import BaseScene


class CompositeScene(BaseScene):
    """A scene composed of multiple layers of other scenes."""

    def __init__(
        self,
        scenes: List[BaseScene],
        base_dir: Path,
        id: Optional[str] = None,
        duration: Optional[Any] = None,
        frames: Optional[int] = None,
        cache: Optional[Dict[str, Any]] = None,
        effects: Optional[List[BaseEffect]] = None,
        transition: Optional[BaseTransition] = None,
        audio: Optional[List[AudioTrackSpec]] = None,
    ):
        super().__init__(
            "composite",
            base_dir=base_dir,
            id=id,
            cache=cache,
            effects=effects,
            transition=transition,
            audio=audio,
        )
        self.scenes = scenes
        self.duration = duration
        self.frames = frames

    def prepare(self) -> List[Path]:
        resolved_assets = super().prepare()
        for scene in self.scenes:
            resolved_assets.extend(scene.prepare())
        # Remove duplicates
        return list(dict.fromkeys(resolved_assets))

    def resolve_duration(
        self,
        context_duration: Optional[float],
        assets: List[Path],
        settings: VideoSettings,
    ):
        # First, resolve the composite's own duration. This will act as the
        # context for its children.
        super().resolve_duration(context_duration, assets, settings)

        # Now, resolve the duration of all child scenes using the composite's
        # calculated duration as their context.
        assert self._calculated_duration is not None
        for scene in self.scenes:
            scene.resolve_duration(self._calculated_duration, assets, settings)

    def render(
        self, assets: List[Path], settings: VideoSettings
    ) -> Optional[VideoClip]:
        if not self.scenes:
            return None

        final_layers: List[VideoClip] = []
        i = 0
        while i < len(self.scenes):
            base_scene = self.scenes[i]

            if base_scene.composite_mode != "layer":
                raise ValidationError(
                    "A composition group must start with a 'layer' scene. "
                    f"Scene '{base_scene.id}' has mode "
                    f"'{base_scene.composite_mode}'."
                )

            # Extract effects from the base scene that need to be synchronized
            # across the entire masking group (e.g., easing).
            progress_effects = [
                e for e in base_scene.effects if e.has_progress_transform
            ]
            other_effects = [
                e for e in base_scene.effects if not e.has_progress_transform
            ]

            # Render the base clip of the group
            base_clip = base_scene.render(assets, settings)
            if not base_clip:
                i += 1
                continue

            # Process subsequent mask layers in the group
            j = i + 1
            while (
                j < len(self.scenes)
                and self.scenes[j].composite_mode != "layer"
            ):
                mask_scene = self.scenes[j]

                # Temporarily inject the base scene's progress effects into
                # the mask scene to ensure they render with the same timing.
                original_mask_effects = mask_scene.effects
                mask_scene.effects = original_mask_effects + progress_effects

                mask_clip_raw = mask_scene.render(assets, settings)

                # Restore original effects to avoid side effects
                mask_scene.effects = original_mask_effects
                # --- END SYNCHRONIZATION ---

                if not mask_clip_raw:
                    j += 1
                    continue

                if base_clip.duration is not None:
                    mask_clip_raw = mask_clip_raw.with_duration(
                        base_clip.duration
                    )

                if mask_scene.composite_mode == "exclude":
                    # This mode uses the mask layer to punch a hole in the
                    # base_clip. `.with_mask()` *replaces* the base_clip's
                    # own transparency mask, so instead we combine the
                    # base_clip's original mask with the new knockout mask.

                    stencil_mask = mask_clip_raw.to_mask()
                    current_mask = base_clip.mask
                    if current_mask is None:
                        # If base is fully opaque, create a full white mask
                        # for it.
                        current_mask = ColorClip(
                            size=base_clip.size,
                            color=(1.0, 1.0, 1.0),
                            is_mask=True,
                            duration=base_clip.duration,
                        )

                    # Create a "punch" clip that is black where the stencil is.
                    black_punch = ColorClip(
                        size=base_clip.size,
                        color=(0, 0, 0),
                        duration=base_clip.duration,
                    ).with_mask(stencil_mask)
                    # Composite the punch over the base mask to subtract the
                    # shape.
                    new_mask_rgb = CompositeVideoClip(
                        [
                            current_mask.to_RGB(),  # type: ignore
                            black_punch,
                        ]
                    )
                    base_clip = base_clip.with_mask(new_mask_rgb.to_mask())

                j += 1

            # Apply the base scene's *other* effects to the final group clip
            group_clip = base_clip
            for effect in other_effects:
                group_clip = effect.apply(group_clip)

            final_layers.append(group_clip)
            i = j

        if not final_layers:
            return None

        # Composite the final, processed layers together
        if len(final_layers) == 1:
            result_clip = final_layers[0]
        else:
            result_clip = CompositeVideoClip(final_layers, use_bgclip=True)

        return self._apply_audio_to_clip(result_clip, assets)

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "CompositeScene":
        child_scenes_data = data.get("scenes", [])
        child_scenes = [
            BaseScene.from_dict(d, base_dir) for d in child_scenes_data
        ]

        effects = BaseEffect.from_list(data.get("effects", []))
        transition = BaseTransition.from_dict(data.get("transition"))
        audio = AudioTrackSpec.from_list(data.get("audio", []), base_dir)

        return cls(
            scenes=child_scenes,
            base_dir=base_dir,
            id=data.get("id"),
            duration=data.get("duration"),
            frames=data.get("frames"),
            cache=data.get("cache"),
            effects=effects,
            transition=transition,
            audio=audio,
        )
