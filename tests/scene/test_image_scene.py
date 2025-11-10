import pytest
from pathlib import Path
from moviepy import VideoClip
from sceneweaver.spec.scene import ImageScene
from sceneweaver.spec.video_settings import VideoSettings
from sceneweaver.errors import ValidationError


def test_image_scene_creation(
    dummy_image_path: Path, dummy_audio_path: Path, base_dir: Path
):
    """
    Tests that ImageScene can be created with various valid configurations.
    """
    # Valid scene with duration
    data = {
        "id": "img1",
        "duration": 5,
        "image": str(dummy_image_path),
        "stretch": True,
    }
    scene = ImageScene.from_dict(data, base_dir)
    assert scene.duration == 5
    assert scene.stretch is True

    # Valid scene with frames
    data_frames = {
        "id": "img2",
        "frames": 150,
        "image": str(dummy_image_path),
    }
    scene_frames = ImageScene.from_dict(data_frames, base_dir)
    assert scene_frames.frames == 150

    # Valid scene with audio (which implies duration)
    data_audio = {
        "id": "img3",
        "image": str(dummy_image_path),
        "audio": [{"file": str(dummy_audio_path)}],
    }
    scene_audio = ImageScene.from_dict(data_audio, base_dir)
    assert len(scene_audio.audio) == 1

    # A scene with no duration source is valid, as it's considered "relative".
    # It will fail during `resolve_duration` if no context is provided.
    data_no_duration = {"id": "img4", "image": str(dummy_image_path)}
    scene_no_duration = ImageScene.from_dict(data_no_duration, base_dir)
    assert scene_no_duration.duration is None
    assert scene_no_duration.frames is None
    assert not scene_no_duration.audio


def test_image_scene_prepare(base_dir: Path, dummy_image_path: Path):
    """Tests the prepare method for resolving the image path."""
    # Use a relative path from the base_dir
    relative_path = dummy_image_path.relative_to(base_dir)
    scene = ImageScene(
        base_dir=base_dir, id="img1", duration=2, image=str(relative_path)
    )

    # prepare() now takes no arguments
    prepared_assets = scene.prepare()

    assert len(prepared_assets) == 1
    # Check that the resolved path is the absolute path to the dummy image
    assert prepared_assets[0] == dummy_image_path.resolve()


def test_image_scene_prepare_missing_file(base_dir: Path):
    """Tests that prepare raises an error if the image file doesn't exist."""
    scene = ImageScene(
        base_dir=base_dir, id="img1", duration=2, image="non_existent_file.png"
    )
    with pytest.raises(ValidationError, match="image file not found"):
        # prepare() now takes no arguments
        scene.prepare()


def test_image_scene_render(
    video_settings: VideoSettings, dummy_image_path: Path, base_dir: Path
):
    """Tests the render method of ImageScene after resolving duration."""
    scene = ImageScene.from_dict(
        {
            "id": "img1",
            "frames": 60,  # 2 seconds at 30 fps
            "image": str(dummy_image_path),
            "stretch": True,
        },
        base_dir=base_dir,
    )

    # The render method still needs the prepared assets
    assets = scene.prepare()
    scene.resolve_duration(None, assets, video_settings)
    clip = scene.render(assets, video_settings)

    assert isinstance(clip, VideoClip)
    # 60 frames / 30 fps = 2.0 seconds
    assert clip.duration == 2.0
    # With stretch=True, the clip size should match the canvas size
    assert clip.size == (video_settings.width, video_settings.height)


def test_image_scene_render_with_audio_duration(
    video_settings: VideoSettings,
    dummy_image_path: Path,
    dummy_audio_path: Path,
    base_dir: Path,
):
    """Tests that duration is correctly inferred from an audio file."""
    scene = ImageScene.from_dict(
        {
            "id": "img1",
            "image": str(dummy_image_path),
            "audio": [{"file": str(dummy_audio_path)}],
        },
        base_dir=base_dir,
    )
    assets = scene.prepare()

    # Resolve duration before rendering. The scene uses its own
    # audio as context.
    scene.resolve_duration(None, assets, video_settings)

    clip = scene.render(assets, video_settings)

    assert isinstance(clip, VideoClip)
    assert clip.duration == pytest.approx(2.5)  # From dummy_audio_path
    assert clip.audio is not None
