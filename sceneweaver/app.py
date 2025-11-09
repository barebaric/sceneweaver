import argparse
import sys
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from .cache import CacheManager
from .errors import ValidationError
from .generator import VideoGenerator
from .recorder import AudioRecorder
from .template import TEMPLATE_YAML


def handle_generate(args):
    generator = VideoGenerator(spec_file=args.spec_file, force=args.force)
    generator.generate()


def handle_clean(args):
    cache = CacheManager()
    cache.clean()
    print("Cache has been cleared.")


def handle_create(args):
    spec_path = Path(args.spec_file)
    if spec_path.exists():
        print(f"Error: File already exists at {spec_path}")
        return

    spec_path.write_text(TEMPLATE_YAML)
    print(f"Created a new example specification file at: {spec_path}")


def handle_record_audio(args):
    spec_arg = args.spec_file
    if ":" not in spec_arg:
        print(
            "Error: The record-audio command requires a scene ID.",
            file=sys.stderr,
        )
        print(
            "Example: pixi record-audio my_video.yaml:scene_id",
            file=sys.stderr,
        )
        sys.exit(1)

    spec_file_str, target_scene_id = spec_arg.split(":", 1)
    spec_path = Path(spec_file_str).resolve()
    base_dir = spec_path.parent

    if not spec_path.is_file():
        print(f"Error: Spec file not found at {spec_path}", file=sys.stderr)
        sys.exit(1)

    yaml = YAML()
    with open(spec_path, "r") as f:
        spec_dict = yaml.load(f)

    settings = spec_dict.get("settings", {})
    scenes = spec_dict.get("scenes", [])

    target_scene_index = -1
    for i, s in enumerate(scenes):
        if s.get("id") == target_scene_id:
            target_scene_index = i
            break

    if target_scene_index == -1:
        print(
            f"Error: Scene with id '{target_scene_id}' not found "
            f"in {spec_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    recording_dir_name = settings.get("audio_recording_path", "audio")
    output_dir = base_dir / recording_dir_name
    output_dir.mkdir(exist_ok=True)

    output_filename = f"{target_scene_id}.wav"
    output_path = output_dir / output_filename
    relative_audio_path = f"{recording_dir_name}/{output_filename}"

    if output_path.exists():
        overwrite = input(
            f"Warning: Audio file already exists at {output_path}.\n"
            "Do you want to overwrite it? (y/N): "
        )
        if overwrite.lower() != "y":
            print("Aborted.")
            return

    recorder = AudioRecorder(output_path)
    was_successful = recorder.record()

    if not was_successful:
        print("\nAudio was not saved. The spec file will not be modified.")
        return

    # --- Automatically update the YAML spec file ---
    print(f"\nUpdating spec file: {spec_path}")
    target_scene = spec_dict["scenes"][target_scene_index]
    new_audio_track = {"file": relative_audio_path}

    if "audio" not in target_scene:
        new_audio_list = CommentedSeq([new_audio_track])

        # Determine the best position to insert the new 'audio' key
        # to maintain clean formatting.
        insert_pos = len(target_scene)  # Default to the end
        keys_to_insert_before = ["effects", "transition"]
        for key in keys_to_insert_before:
            if key in target_scene:
                # Find the index of the key and use that as the position
                for i, k in enumerate(target_scene.keys()):
                    if k == key:
                        insert_pos = i
                        break
                break  # Stop after finding the first match

        target_scene.insert(insert_pos, "audio", new_audio_list)

    elif isinstance(target_scene["audio"], list):
        # If 'audio' is already a list, only append if the exact track
        # is not already present.
        found = any(
            isinstance(track, dict)
            and track.get("file") == relative_audio_path
            for track in target_scene["audio"]
        )
        if not found:
            target_scene["audio"].append(new_audio_track)
        # If found, do nothing. The user was just re-recording the audio file.
    else:
        # If 'audio' exists but isn't a list (i.e., it's malformed),
        # overwrite it.
        print(
            f"Warning: 'audio' key in scene '{target_scene_id}' was not "
            "a list. Overwriting it."
        )
        target_scene["audio"] = [new_audio_track]

    with open(spec_path, "w") as f:
        yaml.dump(spec_dict, f)

    print(
        f"✅ Successfully recorded audio and updated '{target_scene_id}' "
        f"in {spec_path.name}."
    )


def main():
    parser = argparse.ArgumentParser(
        description="A command-line tool for creating videos from a YAML spec."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_generate = subparsers.add_parser(
        "generate", help="Generate a video from a spec file."
    )
    parser_generate.add_argument(
        "spec_file",
        type=str,
        help="Path to the .yaml spec file. To target a scene, "
        "use 'path/to/spec.yaml:scene_id'.",
    )
    parser_generate.add_argument(
        "--force",
        action="store_true",
        help="Force re-rendering of all scenes, ignoring any cached results.",
    )
    parser_generate.set_defaults(func=handle_generate)

    parser_clean = subparsers.add_parser(
        "clean", help="Clean the scene cache."
    )
    parser_clean.set_defaults(func=handle_clean)

    parser_create = subparsers.add_parser(
        "create", help="Create a new example spec file."
    )
    parser_create.add_argument(
        "spec_file",
        type=str,
        help="Path where the new spec file should be created.",
    )
    parser_create.set_defaults(func=handle_create)

    parser_record = subparsers.add_parser(
        "record-audio", help="Record audio and link it to a specific scene."
    )
    parser_record.add_argument(
        "spec_file",
        type=str,
        help=(
            "Path to the spec file and scene ID, e.g., "
            "'path/to/spec.yaml:scene_id'."
        ),
    )
    parser_record.set_defaults(func=handle_record_audio)

    args = parser.parse_args()
    try:
        args.func(args)
    except ValidationError as e:
        print(f"\nValidation Error in your spec file: {e}", file=sys.stderr)
        sys.exit(1)
