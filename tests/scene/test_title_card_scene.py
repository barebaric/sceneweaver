import pytest
from moviepy import VideoClip

from sceneweaver.spec.scene import TitleCardScene
from sceneweaver.spec.video_settings import VideoSettings
from sceneweaver.errors import ValidationError


def test_title_card_creation_and_validation():
    """Tests successful creation and validation logic for TitleCardScene."""
    # Valid data
    data = {"id": "t1", "duration": 5, "title": "Test Title"}
    scene = TitleCardScene.from_dict(data)
    assert scene.id == "t1"
    assert scene.duration == 5
    assert scene.title == "Test Title"

    # Missing duration should raise an error
    invalid_data = {"id": "t2", "title": "Another Title"}
    with pytest.raises(
        ValidationError, match="missing required field: 'duration'"
    ):
        TitleCardScene.from_dict(invalid_data)


def test_title_card_render(video_settings: VideoSettings):
    """Tests the render method of TitleCardScene."""
    scene = TitleCardScene(id="t1", duration=3.5, title="Render Test")

    # The 'assets' list is empty for a title card, as it generates all content.
    clip = scene.render([], video_settings)

    assert isinstance(clip, VideoClip)
    assert clip.duration == 3.5
    assert clip.size == (video_settings.width, video_settings.height)
