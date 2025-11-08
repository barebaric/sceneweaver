import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from moviepy import VideoClip, VideoFileClip, concatenate_videoclips
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
        self.spec, self.spec_dict = load_spec(self.spec_path)

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
    ) -> Optional[Path]:
        """
        Processes a single scene, handling caching and rendering.
        Returns the path to the generated clip file, or None if skipped.
        """
        print(f"Processing scene {index + 1}: {scene.id} ({scene.type})")

        clip_path: Optional[Path] = None
        # Caching requires a stable scene ID.
        use_cache = scene.cache is not None and not self.force
        assets = scene.prepare(self.base_dir)

        composite_id = f"{self.spec_path}::{scene.id}"

        if use_cache:
            clip_path = self.cache.get(composite_id, raw_scene, assets)

        if not clip_path:
            if use_cache:
                print("Cache miss. Generating scene...")
            else:
                print("Generating scene...")

            clip = scene.render(assets, self.settings)

            if clip:
                # Apply a final resize if the generated clip doesn't match the
                # target size.
                if clip.size != list(self.size):
                    clip = clip.with_effects([Resize(height=self.size[1])])
                    assert isinstance(clip, VideoClip)

                temp_clip_path = temp_dir / f"scene_{index}.mp4"
                with tempfile.NamedTemporaryFile(suffix=".aac") as temp_audio:
                    clip.write_videofile(
                        str(temp_clip_path),
                        fps=self.settings.fps,
                        codec="libx264",
                        audio_codec="aac",
                        temp_audiofile=temp_audio.name,
                    )

                clip_path = temp_clip_path
                if use_cache:
                    clip_path = self.cache.put(
                        composite_id,
                        raw_scene,
                        assets,
                        temp_clip_path,
                        scene.cache,
                    )

            else:
                print(f"Skipping scene {index + 1} as no clip was generated.")

        return clip_path

    def _assemble_final_video(self, clip_paths: List[Path]):
        """Concatenates all scene clips and writes the final video file."""
        if not clip_paths:
            print("No scenes were processed or generated. Exiting.")
            return

        print("All scenes processed. Concatenating clips...")
        final_clips = [VideoFileClip(str(p)) for p in clip_paths]
        final_video = concatenate_videoclips(final_clips, method="compose")

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
            scenes_to_process = [self.spec.scenes[i] for i in indices]
            raw_scenes_to_process = [
                self.spec_dict["scenes"][i] for i in indices
            ]

        with tempfile.TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)
            final_clip_paths: List[Path] = []
            for i, (scene, raw_scene) in enumerate(
                zip(scenes_to_process, raw_scenes_to_process)
            ):
                clip_path = self._process_scene(scene, raw_scene, temp_dir, i)
                if clip_path:
                    final_clip_paths.append(clip_path)

            self._assemble_final_video(final_clip_paths)
