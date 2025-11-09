import importlib.resources
from pathlib import Path
import platformdirs
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
