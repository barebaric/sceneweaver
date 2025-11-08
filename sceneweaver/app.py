import argparse
import sys
from pathlib import Path

from .cache import CacheManager
from .errors import ValidationError
from .generator import VideoGenerator
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

    args = parser.parse_args()
    try:
        args.func(args)
    except ValidationError as e:
        print(f"\nValidation Error in your spec file: {e}", file=sys.stderr)
        sys.exit(1)
