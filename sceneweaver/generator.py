import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast
from moviepy import (
    VideoClip,
    VideoFileClip,
    CompositeVideoClip,
)
from moviepy.audio.fx import AudioNormalize
from moviepy.video.fx import Resize
from .cache import CacheManager
from .loader import load_spec
from .spec import VideoSettings, VideoSpec
from .spec.scene import BaseScene, TemplateScene
from .renderer import render_scene_list_to_clip


class VideoGenerator:
    def __init__(self, spec_file: str, force: bool = False):
        self.spec_file_str = spec_file
        self.force = force

        self.target_scene_id: Optional[str] = None
        self._parse_spec_argument()

        self.spec_path = Path(self.spec_file_str).resolve()
        self.base_dir = self.spec_path.parent

        self.spec: VideoSpec
        self.spec_dict: Dict[str, Any]
        self.spec, self.spec_dict = load_spec(self.spec_path, self.base_dir)

        self.settings: VideoSettings = self.spec.settings

        # Assert that settings are valid, informing the type checker
        assert self.settings.width is not None
        assert self.settings.height is not None
        self.size: Tuple[int, int] = (
            self.settings.width,
            self.settings.height,
        )

        self.cache = CacheManager()

    def _parse_spec_argument(self):
        """Parses 'path/to/spec.yaml:scene_id' format."""
        if ":" in self.spec_file_str:
            self.spec_file_str, self.target_scene_id = (
                self.spec_file_str.split(":", 1)
            )

    def _process_scene(
        self,
        scene: BaseScene,
        raw_scene_from_spec: Dict[str, Any],
        temp_dir: Path,
        index: int,
    ) -> Optional[VideoClip]:
        """
        Processes a single scene, handling caching and rendering.
        Returns the rendered VideoClip object, or None if skipped.
        """
        print(f"Processing scene {index + 1}: {scene.id} ({scene.type})")

        # Caching requires a stable scene ID.
        use_cache = scene.cache is not None and not self.force
        assets = scene.prepare()

        composite_id = f"{self.spec_path}::{scene.id}"

        # Determine the correct dictionary to use for hashing
        if isinstance(scene, TemplateScene):
            scene_dict_for_hash = scene.to_dict()
        else:
            scene_dict_for_hash = raw_scene_from_spec

        if use_cache:
            cached_path = self.cache.get(
                composite_id, scene_dict_for_hash, assets
            )
            if cached_path:
                return VideoFileClip(str(cached_path))

        if use_cache:
            print("Cache miss. Generating scene...")
        else:
            print("Generating scene...")

        # 1. Render the base visual clip for ANY scene type.
        base_clip = scene.render(assets, self.settings)

        if not base_clip:
            print(f"Skipping scene {index + 1} as no clip was generated.")
            return None

        # 2. Apply standard pre-cache overrides (audio, annotations).
        #    This now happens uniformly for ALL scene types.
        clip_with_overrides = scene._apply_annotations_to_clip(
            base_clip, self.settings
        )
        clip_with_overrides = scene._apply_audio_to_clip(
            clip_with_overrides, assets
        )

        # 3. Apply final adjustments before caching.
        final_clip = clip_with_overrides
        if final_clip.size != list(self.size):
            final_clip = final_clip.with_effects([Resize(height=self.size[1])])
            assert isinstance(final_clip, VideoClip)

        if use_cache:
            temp_clip_path = temp_dir / f"scene_{index}.mp4"
            with tempfile.NamedTemporaryFile(suffix=".aac") as temp_audio:
                final_clip.write_videofile(
                    str(temp_clip_path),
                    fps=self.settings.fps,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=temp_audio.name,
                )

            self.cache.put(
                composite_id,
                scene_dict_for_hash,
                assets,
                temp_clip_path,
                scene.cache,
            )

        return final_clip

    def _assemble_and_write(
        self, clips: List[VideoClip], scenes: List[BaseScene]
    ):
        """Assembles clips with transitions and writes the final video."""
        print("\n--- Stage 3: Assembling with Transitions ---")

        final_video = render_scene_list_to_clip(scenes, clips)

        if not final_video:
            print("No clips to assemble. Exiting.")
            return

        print("\nAll scenes processed. Concatenating final segments...")

        # Normalize the audio of the final clip to ensure consistent volume
        if final_video.audio:
            print("Normalizing final audio...")
            # Instantiate the AudioNormalize class and apply it
            effect = AudioNormalize()
            final_video = cast(
                CompositeVideoClip, final_video.with_effects([effect])
            )

        assert self.settings.output_file is not None
        expanded_path = Path(self.settings.output_file).expanduser()
        output_path = (
            expanded_path
            if expanded_path.is_absolute()
            else (self.base_dir / expanded_path).resolve()
        )
        print(f"Writing final video to {output_path}...")

        with tempfile.NamedTemporaryFile(suffix=".aac") as temp_audio:
            final_video.write_videofile(
                str(output_path),
                fps=self.settings.fps,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=temp_audio.name,
            )
        print("Done!")

    def generate(self):
        """The main method to generate the video."""
        scenes_to_process = self.spec.scenes
        raw_scenes_to_process = self.spec_dict.get("scenes", [])

        if self.target_scene_id:
            print(f"Targeting scene with ID: {self.target_scene_id}")
            indices = [
                i
                for i, s in enumerate(self.spec.scenes)
                if s.id == self.target_scene_id
            ]
            if not indices:
                raise ValueError(
                    f"Scene with ID '{self.target_scene_id}' not found."
                )
            # When targeting a single scene, we don't apply transitions
            scenes_to_process = [self.spec.scenes[i] for i in indices]
            raw_scenes_to_process = [
                self.spec_dict["scenes"][i] for i in indices
            ]
            for s in scenes_to_process:
                s.transition = None
                s.effects = []

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            # Stage 1: Render Base Clips
            print("--- Stage 1: Rendering Base Clips ---")
            rendered_data = []
            for i, (scene, raw_scene) in enumerate(
                zip(scenes_to_process, raw_scenes_to_process)
            ):
                clip = self._process_scene(scene, raw_scene, temp_dir, i)
                if clip:
                    # Keep scene and clip aligned for later stages
                    rendered_data.append({"scene": scene, "clip": clip})

            if not rendered_data:
                print("No clips were rendered. Exiting.")
                return

            base_clips = [rd["clip"] for rd in rendered_data]
            scenes_with_clips = [rd["scene"] for rd in rendered_data]

            # Stage 2: Apply Single-Clip Effects
            print("\n--- Stage 2: Applying Effects ---")
            effect_clips = []
            for i, scene in enumerate(scenes_with_clips):
                modified_clip = base_clips[i]
                if scene.effects:
                    for effect in scene.effects:
                        print(
                            f"Applying effect '{effect.type}' "
                            f"({effect.duration}s) to scene '{scene.id}'"
                        )
                        modified_clip = effect.apply(modified_clip)
                effect_clips.append(modified_clip)

            # Stage 3: Assemble with Transitions and Write
            self._assemble_and_write(effect_clips, scenes_with_clips)
