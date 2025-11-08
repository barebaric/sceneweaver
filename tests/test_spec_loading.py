import pytest

from sceneweaver.spec import VideoSpec
from sceneweaver.errors import ValidationError

# A minimal, valid spec dictionary for successful test cases.
VALID_SPEC_DICT = {
    "settings": {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "output_file": "output.mp4",
    },
    "scenes": [
        {"type": "title_card", "id": "intro", "duration": 5, "title": "Hello"}
    ],
}


def test_load_valid_spec():
    """Tests that a valid spec dictionary loads without errors."""
    spec = VideoSpec.from_dict(VALID_SPEC_DICT)
    assert spec.settings.width == 1920
    assert len(spec.scenes) == 1
    assert spec.scenes[0].id == "intro"


def test_spec_missing_scene_id_raises_error():
    """Tests that validation fails if a scene is missing its 'id'."""
    spec_dict = {
        "settings": VALID_SPEC_DICT["settings"],
        "scenes": [{"type": "title_card", "duration": 5, "title": "No ID"}],
    }
    with pytest.raises(ValidationError, match="missing a required 'id' field"):
        VideoSpec.from_dict(spec_dict)


def test_spec_duplicate_scene_id_raises_error():
    """Tests that validation fails if two scenes have the same 'id'."""
    spec_dict = {
        "settings": VALID_SPEC_DICT["settings"],
        "scenes": [
            {
                "type": "title_card",
                "id": "duplicate",
                "duration": 2,
                "title": "A",
            },
            {
                "type": "image",
                "id": "duplicate",
                "duration": 2,
                "image": "a.png",
            },
        ],
    }
    with pytest.raises(ValidationError, match="Duplicate scene id found"):
        VideoSpec.from_dict(spec_dict)


def test_spec_missing_settings_field_raises_error():
    """Tests that validation fails if a required setting is missing."""
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
        VideoSpec.from_dict(spec_dict)
