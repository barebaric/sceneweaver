import importlib.resources
from pathlib import Path
from typing import Optional
import platformdirs
from ruamel.yaml import YAML
from .errors import TemplateNotFoundError


class TemplateManager:
    def __init__(self):
        self.user_templates_dir = (
            Path(platformdirs.user_config_dir("sceneweaver", "app"))
            / "templates"
        )

    def resolve(self, template_name: str) -> Path:
        """
        Finds a template directory, searching user templates first, then
        built-in.
        Returns a concrete Path to the template directory.
        """
        # 1. Search for user-defined templates first.
        if self.user_templates_dir.is_dir():
            potential_path = self.user_templates_dir / template_name
            if potential_path.is_dir():
                template_spec_path = potential_path / "template.yaml"
                if template_spec_path.is_file():
                    return potential_path

        # 2. If not found, fall back to built-in templates.
        try:
            with importlib.resources.as_file(
                importlib.resources.files("sceneweaver")
                / "resources"
                / "templates"
                / template_name
            ) as template_dir:
                if not template_dir.is_dir():
                    raise FileNotFoundError  # Caught below

                template_spec_path = template_dir / "template.yaml"
                if not template_spec_path.is_file():
                    raise TemplateNotFoundError(
                        f"Built-in template '{template_name}' is missing "
                        "a 'template.yaml' file."
                    )
                return template_dir
        except (FileNotFoundError, ModuleNotFoundError):
            pass  # Fall through to the final error

        raise TemplateNotFoundError(
            f"Template '{template_name}' not found in user directories or "
            "as a built-in template."
        )

    def _get_asset_path(
        self, template_name: str, asset_name: str, required: bool = True
    ) -> Optional[Path]:
        """
        Get the path to an asset file for a template.
        Raises TemplateNotFoundError if the template cannot be resolved or if
        the asset is required and missing.
        """
        template_dir = self.resolve(template_name)
        asset_path = template_dir / asset_name

        if required and not asset_path.is_file():
            raise TemplateNotFoundError(
                f"Template '{template_name}' is missing a required "
                f"file: '{asset_name}'."
            )

        if not asset_path.is_file():
            return None
        return asset_path

    def get_params(self, template_name: str) -> dict:
        """Get parameters for a template from its params.yaml file."""
        params_path = self._get_asset_path(template_name, "params.yaml")

        if not params_path:
            raise TemplateNotFoundError(
                f"Template '{template_name}' is missing a required file: "
                "'params.yaml'."
            )

        yaml_parser = YAML(typ="safe")
        try:
            with open(params_path, "r", encoding="utf-8") as f:
                params_data = yaml_parser.load(f)

            # Normalize to return the 'parameters' block or an empty dict
            return params_data.get("parameters") or {}
        except Exception as e:
            raise TemplateNotFoundError(
                f"Error loading or parsing params.yaml for template "
                f"'{template_name}': {e}"
            )

    def get_example(self, template_name: str) -> str:
        """
        Get example usage for a template from its example.yaml file.
        Returns a generic fallback string if example.yaml is not found.
        """
        example_path = self._get_asset_path(
            template_name, "example.yaml", required=False
        )
        if not example_path:
            return (
                "# Example usage not provided (missing example.yaml)\n"
                f"- type: template\n"
                f"  name: {template_name}\n"
                f"  id: my_scene_id\n"
                "  with:\n"
                "    # ... parameters go here ...\n"
            )
        return example_path.read_text(encoding="utf-8")
