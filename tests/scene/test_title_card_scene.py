import pytest
from pathlib import Path
from moviepy import VideoClip

from sceneweaver.spec.scene import TitleCardScene
from sceneweaver.spec.video_settings import VideoSettings
from sceneweaver.errors import ValidationError


def test_title_card_creation_and_validation(
    base_dir: Path, dummy_audio_path: Path
):
    """Tests successful creation and validation logic for TitleCardScene."""
    # Valid with duration
    data = {"id": "t1", "duration": 5, "title": "Test Title"}
    scene = TitleCardScene.from_dict(data, base_dir)
    assert scene.duration == 5
    assert scene.title == "Test Title"

    # Valid with audio instead of duration
    data_audio = {
        "id": "t2",
        "title": "Audio Title",
        "audio": [{"file": str(dummy_audio_path)}],
    }
    scene_audio = TitleCardScene.from_dict(data_audio, base_dir)
    assert scene_audio.duration is None
    assert len(scene_audio.audio) == 1

    # Missing both duration and audio should raise an error
    invalid_data = {"id": "t3", "title": "Another Title"}
    with pytest.raises(
        ValidationError,
        match="requires 'duration' if no 'audio' is provided",
    ):
        TitleCardScene.from_dict(invalid_data, base_dir)


def test_title_card_render(video_settings: VideoSettings):
    """Tests the render method of TitleCardScene."""
    scene = TitleCardScene(id="t1", duration=3.5, title="Render Test")

    # The 'assets' list is empty for a title card, as it generates all content.
    clip = scene.render([], video_settings)

    assert isinstance(clip, VideoClip)
    assert clip.duration == 3.5
    assert clip.size == (video_settings.width, video_settings.height)


def test_title_card_render_with_audio_duration(
    video_settings: VideoSettings, dummy_audio_path: Path, base_dir: Path
):
    """Tests that duration is correctly inferred from an audio file."""
    scene = TitleCardScene.from_dict(
        {
            "id": "t1",
            "title": "Audio Duration Test",
            "audio": [{"file": str(dummy_audio_path)}],
        },
        base_dir=base_dir,
    )

    assets = scene.prepare(base_dir)
    clip = scene.render(assets, video_settings)

    assert isinstance(clip, VideoClip)
    assert clip.duration == pytest.approx(2.5)  # From dummy_audio_path
    assert clip.audio is not None
