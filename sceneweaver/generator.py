import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast
from moviepy import (
    VideoClip,
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
)
from moviepy.audio.fx import AudioNormalize
from moviepy.video.fx import Resize
from .cache import CacheManager
from .loader import load_spec
from .spec import VideoSettings, VideoSpec
from .spec.scene import BaseScene


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
        raw_scene: Dict[str, Any],
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

        if use_cache:
            cached_path = self.cache.get(composite_id, raw_scene, assets)
            if cached_path:
                clip = VideoFileClip(str(cached_path))
                # Ensure audio is loaded from cached file
                if clip.audio is None and scene.audio:
                    audio_clips = []
                    for track in scene.audio:
                        audio_path = scene.find_asset(track.file, assets)
                        if audio_path:
                            audio_clip = AudioFileClip(str(audio_path))
                            if track.shift != 0:
                                audio_clip = audio_clip.with_start(track.shift)
                            audio_clips.append(audio_clip)
                    if audio_clips:
                        clip = clip.with_audio(CompositeAudioClip(audio_clips))
                return clip

        if use_cache:
            print("Cache miss. Generating scene...")
        else:
            print("Generating scene...")

        clip = scene.render(assets, self.settings)

        if not clip:
            print(f"Skipping scene {index + 1} as no clip was generated.")
            return None

        # Apply a final resize if the generated clip doesn't match the
        # target size.
        if clip.size != list(self.size):
            clip = clip.with_effects([Resize(height=self.size[1])])
            assert isinstance(clip, VideoClip)

        if use_cache:
            temp_clip_path = temp_dir / f"scene_{index}.mp4"
            with tempfile.NamedTemporaryFile(suffix=".aac") as temp_audio:
                clip.write_videofile(
                    str(temp_clip_path),
                    fps=self.settings.fps,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=temp_audio.name,
                )

            self.cache.put(
                composite_id,
                raw_scene,
                assets,
                temp_clip_path,
                scene.cache,
            )

        return clip

    def _assemble_and_write(
        self, clips: List[VideoClip], scenes: List[BaseScene]
    ):
        """Assembles clips with transitions and writes the final video."""
        if not clips:
            print("No clips to assemble. Exiting.")
            return

        print("\n--- Stage 3: Assembling with Transitions ---")
        final_segments = []
        # Use a copy of the list to allow in-place modification for subclip
        clips_to_process = list(clips)

        i = 0
        while i < len(clips_to_process):
            clip_a = clips_to_process[i]
            scene_a = scenes[i]

            # Check for an outgoing transition
            if scene_a.transition and (i + 1) < len(clips_to_process):
                transition = scene_a.transition
                d = transition.duration
                clip_b = clips_to_process[i + 1]

                print(
                    f"Applying {transition.type} ({d}s) between "
                    f"'{scene_a.id}' and '{scenes[i + 1].id}'"
                )

                # Add main part of clip A
                if clip_a.duration > d:
                    final_segments.append(
                        clip_a.subclipped(0, clip_a.duration - d)
                    )

                # Create and add the transition clip
                transition_clip = transition.apply(clip_a, clip_b)
                final_segments.append(transition_clip)

                # Shorten clip B for the next iteration if needed
                if clip_b.duration > d:
                    clips_to_process[i + 1] = clip_b.subclipped(d)
                else:
                    # The next clip is consumed entirely by the transition
                    clips_to_process[i + 1] = None  # type: ignore
            else:
                # No transition, just add the whole clip
                if clip_a:
                    final_segments.append(clip_a)

            i += 1

        print("\nAll scenes processed. Concatenating final segments...")
        final_video = concatenate_videoclips(
            [c for c in final_segments if c is not None], method="compose"
        )

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
