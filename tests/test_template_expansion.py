import pytest
from pathlib import Path
from sceneweaver.spec import VideoSpec
from sceneweaver.errors import TemplateNotFoundError
from sceneweaver.template_manager import TemplateManager
from sceneweaver.spec.scene import ImageScene

# A minimal spec that uses a template.
# We will modify this dictionary for different test cases.
BASE_TEMPLATE_SPEC = {
    "settings": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "output_file": "output.mp4",
        "font": "GlobalFont",  # A font that doesn't exist on the system
    },
    "scenes": [
        {
            "type": "template",
            "id": "test_template_scene",
            "name": "simple",
            "duration": 5,  # Add duration to satisfy ImageScene validation
            "with": {"title": "My Test Title"},
        }
    ],
}


@pytest.fixture(autouse=True)
def mock_find_font(monkeypatch):
    """
    Automatically mocks the `find_font` function for all tests in this file
    to prevent OSError from trying to load a non-existent font.
    """
    # The mock simply returns the font identifier it was given.
    monkeypatch.setattr(
        "sceneweaver.spec.video_settings.find_font",
        lambda font, base_dir: font,
    )


def test_basic_template_expansion(
    monkeypatch, base_dir: Path, simple_template_path: Path
):
    """
    Tests that a template block is correctly replaced by the scene(s)
    it defines.
    """
    # Mock the TemplateManager to return our fake template path
    monkeypatch.setattr(
        TemplateManager, "resolve", lambda self, name: simple_template_path
    )
    # The template needs an image, so we must create it. The scene's `base_dir`
    # is the template dir, so the image must be placed there.
    (simple_template_path / "image.png").touch()

    spec = VideoSpec.from_dict(BASE_TEMPLATE_SPEC, base_dir)

    assert len(spec.scenes) == 1
    scene = spec.scenes[0]
    assert scene.type == "image"
    # The ID from the user's block should be applied
    assert scene.id == "test_template_scene"


def test_template_asset_path_is_relative_to_template(
    monkeypatch, base_dir: Path, template_with_asset_path: Path
):
    """
    CRITICAL: Tests that an asset path within a template (`logo.png`) is
    resolved relative to the template directory, not the main spec's directory.
    """
    monkeypatch.setattr(
        TemplateManager, "resolve", lambda self, name: template_with_asset_path
    )
    spec_dict = {
        "settings": BASE_TEMPLATE_SPEC["settings"],
        "scenes": [
            {
                "type": "template",
                "id": "asset_test",
                "name": "with_asset",
                "duration": 5,  # Add duration to satisfy ImageScene
            }
        ],
    }

    # This should succeed because the ImageScene's base_dir will be the
    # template's directory, where "logo.png" exists. It would fail if it
    # looked in `base_dir`.
    spec = VideoSpec.from_dict(spec_dict, base_dir)
    scene = spec.scenes[0]

    # The `prepare` method resolves assets. Let's call it to be sure.
    resolved_assets = scene.prepare()
    assert len(resolved_assets) == 1
    assert resolved_assets[0].name == "logo.png"
    assert resolved_assets[0].exists()


def test_merge_priority_user_overrides_template(
    monkeypatch, base_dir: Path, simple_template_path: Path
):
    """
    Tests Priority 1 > 2. User's spec (`duration: 10`) overrides
    template's default.
    """
    # Add a duration to the template file
    (simple_template_path / "template.yaml").write_text(
        """
- type: image
  image: "image.png"
  duration: 2 # Template's default
"""
    )
    monkeypatch.setattr(
        TemplateManager, "resolve", lambda self, name: simple_template_path
    )
    (simple_template_path / "image.png").touch()

    spec_dict = {
        "settings": BASE_TEMPLATE_SPEC["settings"],
        "scenes": [
            {
                "type": "template",
                "id": "override_test",
                "name": "simple",
                "duration": 10,  # User's override
            }
        ],
    }
    spec = VideoSpec.from_dict(spec_dict, base_dir)
    scene = spec.scenes[0]
    # Add an isinstance check to inform the type checker
    assert isinstance(scene, ImageScene)
    assert scene.duration == 10


def test_merge_priority_template_overrides_global(
    monkeypatch, base_dir: Path, simple_template_path: Path
):
    """
    Tests Priority 2 > 3. Template's default overrides global
    `scene_defaults`.
    """
    # Add a duration to the template file
    (simple_template_path / "template.yaml").write_text(
        """
- type: image
  image: "image.png"
  duration: 5 # Template's default
"""
    )
    monkeypatch.setattr(
        TemplateManager, "resolve", lambda self, name: simple_template_path
    )
    (simple_template_path / "image.png").touch()

    spec_dict = {
        "settings": {
            **BASE_TEMPLATE_SPEC["settings"],
            "scene_defaults": {"duration": 99},  # Global default
        },
        "scenes": [
            {"type": "template", "id": "global_test", "name": "simple"}
        ],
    }

    spec = VideoSpec.from_dict(spec_dict, base_dir)
    scene = spec.scenes[0]
    assert isinstance(scene, ImageScene)
    assert scene.duration == 5


def test_merge_priority_global_is_used_as_fallback(
    monkeypatch, base_dir: Path, simple_template_path: Path
):
    """Tests Priority 3 is used when user and template provide no value."""
    # Template has no duration key
    (simple_template_path / "template.yaml").write_text(
        """
- type: image
  image: "image.png"
"""
    )
    monkeypatch.setattr(
        TemplateManager, "resolve", lambda self, name: simple_template_path
    )
    (simple_template_path / "image.png").touch()

    spec_dict = {
        "settings": {
            **BASE_TEMPLATE_SPEC["settings"],
            "scene_defaults": {"duration": 99},  # Global default
        },
        "scenes": [
            {"type": "template", "id": "fallback_test", "name": "simple"}
        ],
    }

    spec = VideoSpec.from_dict(spec_dict, base_dir)
    scene = spec.scenes[0]
    assert isinstance(scene, ImageScene)
    assert scene.duration == 99


def test_multi_scene_template_expansion(
    monkeypatch, base_dir: Path, multi_scene_template_path: Path
):
    """Tests that a template with multiple scenes expands correctly."""
    monkeypatch.setattr(
        TemplateManager,
        "resolve",
        lambda self, name: multi_scene_template_path,
    )
    (multi_scene_template_path / "a.png").touch()
    (multi_scene_template_path / "b.png").touch()

    spec_dict = {
        "settings": {
            **BASE_TEMPLATE_SPEC["settings"],
            # KEY FIX: Provide a global duration so scene2 becomes valid.
            "scene_defaults": {"duration": 1},
        },
        "scenes": [
            {
                "type": "template",
                "name": "multi",
                "duration": 50,  # This will be applied to the first scene
                "id": "multi_id",  # This will be applied to the first scene
            }
        ],
    }
    # This call should now succeed
    spec = VideoSpec.from_dict(spec_dict, base_dir)
    scene1 = spec.scenes[0]
    scene2 = spec.scenes[1]

    assert len(spec.scenes) == 2

    assert isinstance(scene1, ImageScene)
    assert scene1.id == "multi_id"
    assert scene1.duration == 50

    assert isinstance(scene2, ImageScene)
    assert scene2.id == "scene_two"
    # scene2 should get the global default duration
    assert scene2.duration == 1


def test_template_not_found_raises_error(monkeypatch, base_dir: Path):
    """
    Tests that a `TemplateNotFoundError` is raised for a missing template.
    """

    # Mock resolve to always fail
    def mock_resolve(self, name):
        raise TemplateNotFoundError(f"Template '{name}' not found.")

    monkeypatch.setattr(TemplateManager, "resolve", mock_resolve)
    with pytest.raises(
        TemplateNotFoundError, match="Template 'simple' not found"
    ):
        VideoSpec.from_dict(BASE_TEMPLATE_SPEC, base_dir)
