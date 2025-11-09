# sceneweaver/renderer.py
from typing import List, Optional
from moviepy import VideoClip, concatenate_videoclips
from .spec.scene.base_scene import BaseScene


def render_scene_list_to_clip(
    scenes: List[BaseScene], clips: List[VideoClip]
) -> Optional[VideoClip]:
    """
    Assembles a list of scenes and their corresponding rendered clips into a
    single VideoClip, applying transitions between them.
    """
    if not clips:
        return None

    final_segments = []
    # The list can contain `None` as clips are consumed by transitions.
    clips_to_process: List[Optional[VideoClip]] = list(clips)

    i = 0
    while i < len(clips_to_process):
        clip_a = clips_to_process[i]
        if not clip_a:
            i += 1
            continue

        scene_a = scenes[i]
        clip_b = (
            clips_to_process[i + 1]
            if (i + 1) < len(clips_to_process)
            else None
        )

        if scene_a.transition and clip_b:
            transition = scene_a.transition
            d = transition.duration

            # Differentiate between top-level and internal transitions
            # for clarity
            log_prefix = "Applying"
            if (
                isinstance(scenes[0], BaseScene)
                and scenes[0].type == "template"
            ):
                log_prefix = "Applying internal"

            print(
                f"{log_prefix} {transition.type} ({d}s) between "
                f"'{scene_a.id}' and '{scenes[i + 1].id}'"
            )

            if clip_a.duration > d:
                final_segments.append(
                    clip_a.subclipped(0, clip_a.duration - d)
                )

            transition_clip = transition.apply(clip_a, clip_b)
            final_segments.append(transition_clip)

            if clip_b.duration > d:
                clips_to_process[i + 1] = clip_b.subclipped(d)
            else:
                clips_to_process[i + 1] = None
        else:
            final_segments.append(clip_a)

        i += 1

    valid_segments = [c for c in final_segments if c is not None]
    if not valid_segments:
        return None

    return concatenate_videoclips(valid_segments, method="compose")
