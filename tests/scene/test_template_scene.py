from pathlib import Path
import pytest
from PIL import Image

from sceneweaver.spec import VideoSpec
from sceneweaver.errors import TemplateNotFoundError
from sceneweaver.template_manager import TemplateManager
from sceneweaver.spec.scene import ImageScene, SvgScene, TemplateScene


@pytest.fixture
def base_dir_with_template(tmp_path: Path, monkeypatch) -> Path:
    """
    Creates a temporary directory with a spec file and a multi-scene template.
    Also mocks the template manager to find it.
    """
    # 1. Create the template files
    template_dir = tmp_path / "my_templates" / "multi_scene"
    template_dir.mkdir(parents=True)

    (template_dir / "template.yaml").write_text("""
- type: image
  id: internal_image
  image: "image.png"
  duration: 2

- type: svg
  id: internal_svg
  duration: 3
  template: "template.svg"
  params:
    text: "{{ text | default('Default') }}"
    """)
    # Create the assets the template refers to
    Image.new("RGB", (1, 1)).save(template_dir / "image.png")
    (template_dir / "template.svg").write_text("<svg></svg>")

    # 2. Monkeypatch the TemplateManager
    original_init = TemplateManager.__init__

    def patched_init(self):
        original_init(self)
        self.user_templates_dir = tmp_path / "my_templates"

    monkeypatch.setattr(TemplateManager, "__init__", patched_init)

    return tmp_path


def test_template_is_loaded_as_single_scene(base_dir_with_template: Path):
    """
    Tests that a template block is now loaded as a single TemplateScene
    instance, not expanded into a flat list.
    """
    spec_dict = {
        "settings": {
            "width": 1,
            "height": 1,
            "fps": 1,
            "output_file": "a.mp4",
        },
        "scenes": [
            {"type": "template", "id": "my_component", "name": "multi_scene"}
        ],
    }
    spec = VideoSpec.from_dict(spec_dict, base_dir_with_template)

    assert len(spec.scenes) == 1
    scene = spec.scenes[0]

    assert isinstance(scene, TemplateScene)
    assert scene.id == "my_component"
    assert scene.name == "multi_scene"


def test_template_scene_internally_loads_spec(base_dir_with_template: Path):
    """
    Tests that the created TemplateScene correctly parses and holds its
    internal VideoSpec with the correct number of internal scenes.
    """
    spec_dict = {
        "settings": {
            "width": 1,
            "height": 1,
            "fps": 1,
            "output_file": "a.mp4",
        },
        "scenes": [
            {"type": "template", "id": "comp_1", "name": "multi_scene"}
        ],
    }
    spec = VideoSpec.from_dict(spec_dict, base_dir_with_template)
    template_scene = spec.scenes[0]
    assert isinstance(template_scene, TemplateScene)

    internal_spec = template_scene.internal_spec
    assert isinstance(internal_spec, VideoSpec)
    assert len(internal_spec.scenes) == 2

    assert isinstance(internal_spec.scenes[0], ImageScene)
    assert internal_spec.scenes[0].id == "internal_image"
    assert isinstance(internal_spec.scenes[1], SvgScene)
    assert internal_spec.scenes[1].id == "internal_svg"


def test_internal_asset_path_is_relative_to_template(
    base_dir_with_template: Path,
):
    """
    CRITICAL: Tests that an asset path within a template (`image.png`) is
    resolved relative to the template directory.
    """
    spec_dict = {
        "settings": {
            "width": 1,
            "height": 1,
            "fps": 1,
            "output_file": "a.mp4",
        },
        "scenes": [
            {"type": "template", "id": "comp_1", "name": "multi_scene"}
        ],
    }
    spec = VideoSpec.from_dict(spec_dict, base_dir_with_template)
    template_scene = spec.scenes[0]
    assert isinstance(template_scene, TemplateScene)

    resolved_assets = template_scene.prepare()

    assert len(resolved_assets) == 2
    image_asset = next(p for p in resolved_assets if p.name == "image.png")
    svg_asset = next(p for p in resolved_assets if p.name == "template.svg")

    assert image_asset.exists()
    assert svg_asset.exists()
    assert "my_templates/multi_scene" in str(image_asset)
    assert "my_templates/multi_scene" in str(svg_asset)


def test_jinja_rendering_with_params(base_dir_with_template: Path):
    """Tests that the `with` block correctly passes parameters to Jinja."""
    spec_dict = {
        "settings": {
            "width": 1,
            "height": 1,
            "fps": 1,
            "output_file": "a.mp4",
        },
        "scenes": [
            {
                "type": "template",
                "id": "comp_1",
                "name": "multi_scene",
                "with": {"text": "Hello from Spec!"},
            }
        ],
    }
    spec = VideoSpec.from_dict(spec_dict, base_dir_with_template)
    template_scene = spec.scenes[0]
    assert isinstance(template_scene, TemplateScene)

    # Add assertion to satisfy Pylance
    assert template_scene.internal_spec is not None
    internal_scene = template_scene.internal_spec.scenes[1]
    assert isinstance(internal_scene, SvgScene)
    assert internal_scene.params["text"] == "Hello from Spec!"


def test_template_not_found_raises_error(monkeypatch, tmp_path: Path):
    """
    Tests that a `TemplateNotFoundError` is raised for a missing template.
    """
    spec_dict = {
        "settings": {
            "width": 1,
            "height": 1,
            "fps": 1,
            "output_file": "a.mp4",
        },
        "scenes": [
            {"type": "template", "id": "t1", "name": "non_existent_template"}
        ],
    }

    def mock_resolve(self, name):
        raise TemplateNotFoundError(f"Template '{name}' not found.")

    monkeypatch.setattr(TemplateManager, "resolve", mock_resolve)
    with pytest.raises(
        TemplateNotFoundError,
        match="Template 'non_existent_template' not found",
    ):
        VideoSpec.from_dict(spec_dict, tmp_path)
