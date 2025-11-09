import importlib.resources
from pathlib import Path
from .errors import TemplateNotFoundError


class TemplateManager:
    def resolve(self, template_name: str) -> Path:
        """
        Finds a template directory. For now, only searches built-in templates.
        Returns a concrete Path to the template directory.
        """
        # Built-in templates
        try:
            # We need a context manager to get a concrete path
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
                        f"Template '{template_name}' found, but it is "
                        "missing a 'template.yaml' file."
                    )
                return template_dir

        except (FileNotFoundError, ModuleNotFoundError):
            raise TemplateNotFoundError(
                f"Built-in template '{template_name}' not found."
            )
