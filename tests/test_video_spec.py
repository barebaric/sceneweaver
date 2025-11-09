import pytest
from pathlib import Path
from sceneweaver.spec import VideoSpec
from sceneweaver.errors import ValidationError

# A minimal, valid spec dictionary for successful test cases.
# We now use 'image' instead of the removed 'title_card'.
VALID_SPEC_DICT = {
    "settings": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "output_file": "output.mp4",
    },
    "scenes": [
        {
            "type": "image",
            "id": "intro",
            "duration": 5,
            "image": "placeholder.png",
        }
    ],
}


def test_load_valid_spec(base_dir: Path, dummy_image_path: Path):
    """Tests that a valid spec dictionary loads without errors."""
    # Create the placeholder image file the spec expects
    (base_dir / "placeholder.png").touch()

    spec = VideoSpec.from_dict(VALID_SPEC_DICT, base_dir)
    assert spec.settings.width == 1920
    assert len(spec.scenes) == 1
    assert spec.scenes[0].id == "intro"


def test_spec_missing_scene_id_raises_error(base_dir: Path):
    """Tests that validation fails if a scene is missing its 'id'."""
    spec_dict = {
        "settings": VALID_SPEC_DICT["settings"],
        # Scene is missing 'id'
        "scenes": [
            {"type": "image", "duration": 5, "image": "placeholder.png"}
        ],
    }
    with pytest.raises(ValidationError, match="missing a required 'id' field"):
        VideoSpec.from_dict(spec_dict, base_dir)


def test_spec_duplicate_scene_id_raises_error(base_dir: Path):
    """Tests that validation fails if two scenes have the same 'id'."""
    spec_dict = {
        "settings": VALID_SPEC_DICT["settings"],
        "scenes": [
            {
                "type": "image",
                "id": "duplicate",
                "duration": 2,
                "image": "a.png",
            },
            {
                "type": "image",
                "id": "duplicate",
                "duration": 2,
                "image": "b.png",
            },
        ],
    }
    with pytest.raises(ValidationError, match="Duplicate scene id found"):
        VideoSpec.from_dict(spec_dict, base_dir)


def test_spec_missing_settings_field_raises_error(base_dir: Path):
    """Tests that validation fails if a required setting is missing."""
    # Create the placeholder image file the spec expects
    (base_dir / "placeholder.png").touch()

    spec_dict = {
        "settings": {
            "width": 1920,
            "height": 1080,
            "output_file": "out.mp4",
        },  # Missing FPS
        "scenes": VALID_SPEC_DICT["scenes"],
    }
    with pytest.raises(
        ValidationError, match="Settings is missing required field: 'fps'"
    ):
        VideoSpec.from_dict(spec_dict, base_dir)
