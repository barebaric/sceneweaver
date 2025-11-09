import argparse
import re
import sys
from pathlib import Path
import importlib.resources
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from .cache import CacheManager
from .errors import ValidationError
from .generator import VideoGenerator
from .recorder import AudioRecorder
from .spec.scene import BaseScene
from .template import TEMPLATE_YAML, TEMPLATE_BOILERPLATE_YAML
from .template_manager import TemplateManager


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


def handle_template_list(args):
    """Lists all available user and built-in templates."""
    manager = TemplateManager()
    user_templates_dir = manager.user_templates_dir

    user_templates = set()
    if user_templates_dir.is_dir():
        for item in user_templates_dir.iterdir():
            if item.is_dir() and (item / "template.yaml").is_file():
                user_templates.add(item.name)

    built_in_templates = set()
    try:
        resources = (
            importlib.resources.files("sceneweaver")
            / "resources"
            / "templates"
        )
        for item in resources.iterdir():
            if item.is_dir() and (item / "template.yaml").is_file():
                built_in_templates.add(item.name)
    except FileNotFoundError:
        pass  # No built-in templates found

    print("Available Templates:")
    all_names = sorted(list(user_templates | built_in_templates))

    if not all_names:
        print("  No templates found.")
        print(f"\nCreate your first template in:\n  {user_templates_dir}")
        return

    for name in all_names:
        if name in user_templates and name in built_in_templates:
            source = "[user override]"
        elif name in user_templates:
            source = "[user]"
        else:
            source = "[built-in]"
        print(f"  - {name:<25} {source}")


def handle_template_create(args):
    """Creates a new user template directory and boilerplate file."""
    template_name = args.template_name
    if not re.match(r"^[a-zA-Z0-9_-]+$", template_name):
        print(
            f"Error: Invalid template name '{template_name}'. "
            "Use only letters, numbers, underscores, and hyphens."
        )
        return

    manager = TemplateManager()
    user_templates_dir = manager.user_templates_dir
    new_template_path = user_templates_dir / template_name

    if new_template_path.exists():
        print(
            f"Error: Template '{template_name}' already exists "
            f"at:\n  {new_template_path}"
        )
        return

    print(f"Creating new template '{template_name}'...")
    new_template_path.mkdir(parents=True)

    # Use the imported constant instead of the hardcoded string
    (new_template_path / "template.yaml").write_text(
        TEMPLATE_BOILERPLATE_YAML.strip()
    )

    print("✅ Successfully created template.")
    print(
        f"Edit the new template file at:\n"
        f"  {new_template_path / 'template.yaml'}"
    )


def _slugify(text: str) -> str:
    """Converts a string to a safe, unique scene ID."""
    s = text.lower().strip()
    s = re.sub(r"[\s-]+", "_", s)
    s = re.sub(r"[^\w_]", "", s)
    return s


def _prompt_for_scene(scenes: list) -> tuple[str, int]:
    """Asks the user to select a scene and returns its ID and index."""
    print("Please select a scene:")
    for i, scene in enumerate(scenes):
        scene_id = scene.get("id", f"Scene {i + 1} (no id)")
        scene_type = scene.get("type", "unknown type")
        print(f"  {i + 1}. {scene_id} ({scene_type})")

    while True:
        try:
            choice = int(input(f"Enter number (1-{len(scenes)}): "))
            if 1 <= choice <= len(scenes):
                index = choice - 1
                return scenes[index]["id"], index
        except (ValueError, IndexError):
            pass
        print("Invalid selection. Please try again.")


def _prompt_for_scene_type() -> str:
    """Asks the user to select a scene type."""
    print("Please select a scene type to add:")
    available_types = BaseScene.get_available_types()
    for i, scene_type in enumerate(available_types):
        print(f"  {i + 1}. {scene_type}")

    while True:
        try:
            choice = int(input(f"Enter number (1-{len(available_types)}): "))
            if 1 <= choice <= len(available_types):
                return available_types[choice - 1]
        except (ValueError, IndexError):
            pass
        print("Invalid selection. Please try again.")


def _record_and_update_spec(
    spec_path: Path, yaml: YAML, spec_dict: dict, target_scene_id: str
) -> bool:
    """
    Handles the full audio recording and spec update flow for a given scene.
    """
    base_dir = spec_path.parent
    settings = spec_dict.get("settings", {})
    scenes = spec_dict.get("scenes", [])

    target_scene_index = -1
    for i, s in enumerate(scenes):
        if s.get("id") == target_scene_id:
            target_scene_index = i
            break

    if target_scene_index == -1:  # Sanity check
        print(
            f"Error: Scene with id '{target_scene_id}' not found "
            f"in {spec_path}",
            file=sys.stderr,
        )
        return False

    recording_dir_name = settings.get("audio_recording_path", "audio")
    output_dir = base_dir / recording_dir_name
    output_dir.mkdir(exist_ok=True)

    output_filename = f"{target_scene_id}.wav"
    output_path = output_dir / output_filename
    relative_audio_path = f"{recording_dir_name}/{output_filename}"

    should_record = True
    if output_path.exists():
        overwrite = input(
            f"Warning: Audio file already exists at {output_path}.\n"
            "Do you want to overwrite it? (y/N): "
        )
        if overwrite.lower() != "y":
            print("Using existing audio file.")
            should_record = False

    if should_record:
        recorder = AudioRecorder(output_path)
        was_successful = recorder.record()
        if not was_successful:
            print("\nAudio was not saved. The spec file will not be modified.")
            return False

    # Automatically update the YAML spec file
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

    # If duration is now redundant because audio was added, remove it.
    if "duration" in target_scene:
        del target_scene["duration"]

    with open(spec_path, "w") as f:
        yaml.dump(spec_dict, f)

    print(f"✅ Successfully updated '{target_scene_id}' in {spec_path.name}.")
    return True


def handle_scene_add(args):
    spec_arg = args.spec_file
    new_scene_id = None
    if ":" in spec_arg:
        spec_file_str, new_scene_id = spec_arg.split(":", 1)
    else:
        spec_file_str = spec_arg

    spec_path = Path(spec_file_str).resolve()
    if not spec_path.is_file():
        print(f"Error: Spec file not found at {spec_path}", file=sys.stderr)
        sys.exit(1)

    yaml = YAML()
    with open(spec_path, "r") as f:
        spec_dict = yaml.load(f)

    existing_ids = {s.get("id") for s in spec_dict.get("scenes", [])}
    if new_scene_id and new_scene_id in existing_ids:
        print(
            f"Error: A scene with ID '{new_scene_id}' already exists.",
            file=sys.stderr,
        )
        sys.exit(1)

    scene_type = args.scene_type
    if not scene_type:
        scene_type = _prompt_for_scene_type()

    try:
        scene_class = BaseScene.get_scene_class(scene_type)
        template = scene_class.get_template()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Always prompt for required fields based on scene type
    title_text_for_id = "new_scene"
    if scene_type == "svg":
        template["template"] = input("Enter path to the SVG template file: ")
        template["params"] = {
            "text": input("Enter a text parameter for the SVG: "),
        }
        title_text_for_id = Path(template["template"]).stem
    elif scene_type == "image":
        template["image"] = input("Enter the path to the image file: ")
        title_text_for_id = Path(template["image"]).stem
    elif scene_type == "video":
        template["file"] = input("Enter the path to the video file: ")
        title_text_for_id = Path(template["file"]).stem
    elif scene_type == "video-images":
        template["file"] = input(
            "Enter the glob pattern for the image sequence "
            "(e.g., frames/*.png): "
        )
        title_text_for_id = f"image_sequence_{scene_type}"

    # Determine the final scene ID
    scene_id = new_scene_id
    if not scene_id:
        base_id = _slugify(title_text_for_id)
        scene_id = base_id
        count = 2
        while scene_id in existing_ids:
            scene_id = f"{base_id}_{count}"
            count += 1

    new_scene = CommentedMap(template)
    new_scene["id"] = scene_id

    spec_dict.setdefault("scenes", []).append(new_scene)

    with open(spec_path, "w") as f:
        yaml.dump(spec_dict, f)

    print(f"✅ Added new scene '{scene_id}' to {spec_path.name}.")

    record_now = input("Record audio for this new scene now? (y/N): ")
    if record_now.lower() == "y":
        with open(spec_path, "r") as f:
            updated_spec_dict = yaml.load(f)
        _record_and_update_spec(spec_path, yaml, updated_spec_dict, scene_id)


def handle_scene_record_audio(args):
    spec_arg = args.spec_file
    target_scene_id = None
    if ":" in spec_arg:
        spec_file_str, target_scene_id = spec_arg.split(":", 1)
    else:
        spec_file_str = spec_arg

    spec_path = Path(spec_file_str).resolve()
    if not spec_path.is_file():
        print(f"Error: Spec file not found at {spec_path}", file=sys.stderr)
        sys.exit(1)

    yaml = YAML()
    with open(spec_path, "r") as f:
        spec_dict = yaml.load(f)

    scenes = spec_dict.get("scenes", [])
    if not scenes:
        print("Spec file has no scenes to record audio for. Aborting.")
        return

    if target_scene_id:
        # A scene ID was provided directly. Validate it.
        if not any(s.get("id") == target_scene_id for s in scenes):
            print(
                f"Error: Scene with ID '{target_scene_id}' not found "
                f"in {spec_path}",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        # No scene ID provided, so prompt the user.
        target_scene_id, _ = _prompt_for_scene(scenes)

    _record_and_update_spec(spec_path, yaml, spec_dict, target_scene_id)


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

    # Scene Subcommand Parser
    parser_scene = subparsers.add_parser(
        "scene", help="Manage scenes in a spec file."
    )
    scene_subparsers = parser_scene.add_subparsers(
        dest="scene_command", required=True
    )

    parser_scene_add = scene_subparsers.add_parser(
        "add", help="Add a new scene to the spec."
    )
    parser_scene_add.add_argument(
        "spec_file",
        type=str,
        help=(
            "Path to the spec file. Use 'spec.yaml:scene_id' to "
            "specify the new scene's ID."
        ),
    )
    parser_scene_add.add_argument(
        "scene_type",
        nargs="?",
        default=None,
        help="Optional: type of scene to add (e.g., image, svg).",
    )
    parser_scene_add.set_defaults(func=handle_scene_add)

    parser_scene_record = scene_subparsers.add_parser(
        "audio", help="Record audio for an existing scene."
    )
    parser_scene_record.add_argument(
        "spec_file",
        type=str,
        help=(
            "Path to the spec file. Use 'spec.yaml:scene_id' to "
            "target a scene directly."
        ),
    )
    parser_scene_record.set_defaults(func=handle_scene_record_audio)

    # Template Subcommand Parser
    parser_template = subparsers.add_parser(
        "template", help="Manage user-defined templates."
    )
    template_subparsers = parser_template.add_subparsers(
        dest="template_command", required=True
    )

    parser_template_list = template_subparsers.add_parser(
        "list", help="List all available templates."
    )
    parser_template_list.set_defaults(func=handle_template_list)

    parser_template_create = template_subparsers.add_parser(
        "create", help="Create a new user template."
    )
    parser_template_create.add_argument(
        "template_name",
        type=str,
        help="Name for the new template (e.g., 'my-lower-third').",
    )
    parser_template_create.set_defaults(func=handle_template_create)

    args = parser.parse_args()
    try:
        args.func(args)
    except ValidationError as e:
        print(f"\nValidation Error in your spec file: {e}", file=sys.stderr)
        sys.exit(1)
