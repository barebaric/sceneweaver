#!/usr/bin/env python3
"""
Script to generate screenshots for all built-in templates and create
documentation.

This script:
1. Creates an image of the output of each built-in template
2. Stores the image within the template's directory
3. Creates an overview in docs/templates.md showing all template images
"""

import importlib.resources
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import argparse

from jinja2 import Environment
from moviepy import VideoFileClip
import yaml

from sceneweaver.template_manager import TemplateManager
from sceneweaver.spec.video_settings import VideoSettings
from sceneweaver.spec.scene.template_scene import TemplateScene
from sceneweaver.loader import load_spec

# Template strings for documentation
OVERVIEW_TEMPLATE = """# SceneWeaver Templates Overview

This document provides an overview of all built-in SceneWeaver templates.

## Available Templates

{template_content}
"""

TEMPLATE_USAGE_TEMPLATE = """scenes:
  - type: template
    name: {template_name}
    id: my_{template_name}
    with:
{parameters}"""

README_TEMPLATE = """# {template_name} Template

This is a built-in SceneWeaver template for creating {template_name} scenes.

## Usage

```yaml
scenes:
  - type: template
    name: {template_name}
    id: my_{template_name}
    with:
{usage_parameters}
```

## Preview

![{template_name} preview](screenshot.png)

## Parameters

{parameters_description}
"""

TABLE_HEADER_TEMPLATE = """| Template | Preview |
|----------|---------|
"""


def get_builtin_templates() -> List[str]:
    """Get list of all built-in template names."""
    templates_path = (
        importlib.resources.files("sceneweaver") / "resources" / "templates"
    )
    template_names = []

    for item in templates_path.iterdir():
        if item.is_dir():
            # Check if template.yaml exists in this directory
            try:
                template_file = item / "template.yaml"
                if template_file.is_file():
                    template_names.append(item.name)
            except (AttributeError, NotImplementedError):
                # Skip if we can't check the file
                continue

    return sorted(template_names)


def extract_yaml_from_example(template_name: str) -> Dict[str, Any]:
    """Extract YAML parameters from a template's example.yaml file."""
    try:
        example_data = TemplateScene.get_example(template_name)

        # Extract the 'with' parameters from the scene
        if isinstance(example_data, dict) and "scenes" in example_data:
            scenes = example_data["scenes"]
            if isinstance(scenes, list) and len(scenes) > 0:
                scene = scenes[0]
                if isinstance(scene, dict) and "with" in scene:
                    return scene["with"]

        return {}
    except Exception as e:
        print(f"Error loading example for {template_name}: {e}")
        return {}


def create_template_screenshot(template_name: str, template_dir: Path) -> Path:
    """Create a screenshot for a template and return the path to the image."""
    print(f"Generating screenshot for template: {template_name}")

    # Extract parameters from example.yaml
    template_params = extract_yaml_from_example(template_name)
    if not template_params:
        print(f"Warning: No parameters found for {template_name}, using empty")
        template_params = {}

    # Setup video settings
    settings = VideoSettings(
        width=1920,
        height=1080,
        fps=30,
        output_file="temp.mp4",
        font="DejaVuSans",
    )

    # Get template manager
    template_manager = TemplateManager()

    # Create a temporary spec file for this template
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        spec_file = temp_path / "temp_spec.yaml"

        # Create spec content
        spec_content = {
            "settings": {
                "width": settings.width,
                "height": settings.height,
                "fps": settings.fps,
                "output_file": "temp.mp4",
                "font": settings.font,
            },
            "scenes": [
                {
                    "type": "template",
                    "name": template_name,
                    "id": f"demo_{template_name}",
                    "with": template_params,
                }
            ],
        }

        # Write spec file
        with open(spec_file, "w") as f:
            yaml.dump(spec_content, f)

        # Load and process the spec
        spec, spec_dict = load_spec(spec_file, temp_path)

        # Create Jinja environment for template processing
        jinja_env = Environment()

        # Create template scene
        scene_data = spec_dict["scenes"][0]
        template_scene = TemplateScene.from_dict(scene_data, temp_path)
        template_scene._load_internal_spec(
            settings, jinja_env, template_manager
        )

        # Prepare assets and resolve durations
        assets = template_scene.prepare()

        # Resolve duration for the template scene
        template_scene.resolve_duration(None, assets, settings)

        # Resolve durations for internal scenes
        assert template_scene.internal_spec is not None
        for internal_scene in template_scene.internal_spec.scenes:
            internal_scene.resolve_duration(
                template_scene._calculated_duration, assets, settings
            )

        # Render the scene
        clip = template_scene.render(assets, settings)

        if not clip:
            raise RuntimeError(f"Failed to render template {template_name}")

        # Generate video file
        video_path = temp_path / "temp_video.mp4"
        clip.write_videofile(
            str(video_path),
            fps=settings.fps,
            codec="libx264",
            audio_codec="aac",
        )

        # Extract a frame from the video
        video_clip = VideoFileClip(str(video_path))
        # Get frame at 1 second or middle
        frame_time = min(1.0, video_clip.duration / 2)
        frame = video_clip.get_frame(frame_time)

        # Save frame as PNG
        output_path = template_dir / "screenshot.png"

        # Convert frame to PIL Image and save
        from PIL import Image

        if frame is not None:
            img = Image.fromarray(frame)
            img.save(output_path)
        else:
            raise RuntimeError("Failed to extract frame from video")

        video_clip.close()
        clip.close()

        return output_path


def format_parameters(parameters: Dict[str, Any]) -> str:
    """Format parameters for documentation."""
    param_lines = []
    for param, value in parameters.items():
        if isinstance(value, str):
            param_lines.append(f"      {param}: '{value}'")
        elif isinstance(value, (int, float)):
            param_lines.append(f"      {param}: {value}")
        elif isinstance(value, list):
            param_lines.append(f"      {param}:")
            for item in value:
                if isinstance(item, dict):
                    line = "        - "
                    for k, v in item.items():
                        if isinstance(v, str):
                            line += f"{k}: '{v}' "
                        else:
                            line += f"{k}: {v} "
                    param_lines.append(line)
    return "\n".join(param_lines)


def load_parameter_docs(template_dir: Path) -> str:
    """Load parameter documentation from params.yaml file."""
    params_path = template_dir / "params.yaml"

    if not params_path.is_file():
        print(f"Warning: params.yaml not found in {template_dir}")
        return "- No parameter documentation available"

    try:
        with open(params_path, "r", encoding="utf-8") as f:
            params_data = yaml.safe_load(f)

        if (
            not isinstance(params_data, dict)
            or "parameters" not in params_data
        ):
            return "- Invalid parameter documentation format"

        param_lines = []
        parameters = params_data["parameters"]

        for param_name, param_info in parameters.items():
            if not isinstance(param_info, dict):
                continue

            param_type = param_info.get("type", "unknown")
            param_desc = param_info.get(
                "description", "No description available"
            )
            param_optional = param_info.get("optional", False)
            param_default = param_info.get("default")

            # Add optional/required info
            if param_optional:
                param_desc += " (optional)"
            else:
                param_desc += " (required)"

            # Add default value to description if available
            if param_default is not None:
                if param_default == "":
                    param_desc += ", default: empty string"
                else:
                    param_desc += f", default: '{param_default}'"

            # Handle subparameters for complex types like arrays
            if "subparameters" in param_info:
                param_lines.append(
                    f"- `{param_name}` ({param_type}): {param_desc}"
                )
                for sub_name, sub_info in param_info["subparameters"].items():
                    if isinstance(sub_info, dict):
                        sub_type = sub_info.get("type", "unknown")
                        sub_desc = sub_info.get(
                            "description", "No description"
                        )
                        sub_optional = sub_info.get("optional", False)
                        sub_default = sub_info.get("default")

                        # Add optional/required info for subparameter
                        if sub_optional:
                            sub_desc += " (optional)"
                        else:
                            sub_desc += " (required)"

                        # Add default value to subparameter description
                        if sub_default is not None:
                            sub_desc += f", default: {sub_default}"

                        param_lines.append(
                            f"  - `{sub_name}` ({sub_type}): {sub_desc}"
                        )
            else:
                param_lines.append(
                    f"- `{param_name}` ({param_type}): {param_desc}"
                )

        return "\n".join(param_lines)

    except Exception as e:
        print(f"Error loading params.yaml from {template_dir}: {e}")
        return f"- Error loading parameter documentation: {e}"


def generate_readme_file(
    template_name: str, template_dir: Path, parameters: Dict[str, Any]
):
    """Generate a README.md file for a template."""
    print(f"Generating README for template: {template_name}")

    # Format parameters for usage example
    usage_params = format_parameters(parameters)

    # Load parameter descriptions from params.yaml
    param_description = load_parameter_docs(template_dir)

    # Generate README content
    readme_content = README_TEMPLATE.format(
        template_name=template_name,
        usage_parameters=usage_params,
        parameters_description=param_description,
    )

    # Write README file
    readme_path = template_dir / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"README generated at: {readme_path}")


def create_templates_overview(
    template_data: List[Dict[str, Any]], output_path: Path
):
    """Create the overview markdown file with all templates in a tabular
    layout."""
    # Create table rows
    table_rows = []
    for template_info in template_data:
        template_name = template_info["name"]
        image_path = template_info["image_path"]
        # Make template name a link to the documentation with correct path
        template_link = (
            f"[{template_name}](../sceneweaver/resources/templates/"
            f"{template_name}/README.md)"
        )

        # Create table row with smaller image (300px width)
        row = (
            f'| {template_link} | <img src="{image_path}" width="300" '
            f'alt="{template_name} preview" /> |'
        )
        table_rows.append(row)

    # Combine all content
    table_content = TABLE_HEADER_TEMPLATE + "\n".join(table_rows)

    content = OVERVIEW_TEMPLATE.format(template_content=table_content)

    with open(output_path, "w") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(
        description="Generate screenshots and documentation for "
        "SceneWeaver templates"
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="docs",
        help="Output directory for documentation",
    )
    parser.add_argument(
        "--templates-dir", "-t", help="Override templates directory"
    )
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Get all built-in templates
    template_names = get_builtin_templates()
    template_list = ", ".join(template_names)
    print(f"Found {len(template_names)} built-in templates: {template_list}")

    template_data = []
    template_manager = TemplateManager()

    for template_name in template_names:
        try:
            # Get template directory
            if args.templates_dir:
                template_dir = Path(args.templates_dir) / template_name
            else:
                template_dir = template_manager.resolve(template_name)

            # Extract parameters from example.yaml
            template_params = extract_yaml_from_example(template_name)
            if not template_params:
                print(f"Warning: No parameters found for {template_name}")
                template_params = {}

            # Generate README file
            generate_readme_file(template_name, template_dir, template_params)

            # Create screenshot
            image_path = create_template_screenshot(
                template_name, template_dir
            )
            print(f"Screenshot saved to: {image_path}")

            # Format parameters for overview
            parameters_str = format_parameters(template_params)

            # Collect data for overview
            rel_path = f"../sceneweaver/resources/templates/{template_name}"
            relative_image_path = f"{rel_path}/screenshot.png"
            desc = f"A template for creating {template_name} scenes"
            template_data.append(
                {
                    "name": template_name,
                    "description": desc,
                    "image_path": relative_image_path,
                    "parameters": parameters_str,
                }
            )

        except Exception as e:
            import traceback

            print(f"Error processing template {template_name}: {e}")
            print("Full traceback:")
            traceback.print_exc()
            continue

    # Create overview documentation
    overview_path = output_dir / "templates.md"
    create_templates_overview(template_data, overview_path)
    print(f"Overview documentation created at: {overview_path}")

    print("\nScreenshot generation completed!")


if __name__ == "__main__":
    main()
