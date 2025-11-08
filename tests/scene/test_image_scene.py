import pytest
from pathlib import Path
from moviepy import VideoClip
from sceneweaver.spec.scene import ImageScene
from sceneweaver.spec.video_settings import VideoSettings
from sceneweaver.errors import ValidationError


def test_image_scene_creation_and_validation(dummy_image_path: Path):
    """Tests creation and validation logic for ImageScene."""
    # Valid scene with duration
    data = {
        "id": "img1",
        "duration": 5,
        "image": str(dummy_image_path),
        "stretch": True,
    }
    scene = ImageScene.from_dict(data)
    assert scene.duration == 5
    assert scene.stretch is True

    # Valid scene with frames
    data_frames = {
        "id": "img2",
        "frames": 150,
        "image": str(dummy_image_path),
        "stretch": True,
    }
    scene_frames = ImageScene.from_dict(data_frames)
    assert scene_frames.frames == 150

    # Missing both duration and frames should fail
    with pytest.raises(
        ValidationError, match="requires either 'duration' or 'frames'"
    ):
        ImageScene.from_dict({"id": "img3", "image": "path.png"})


def test_image_scene_prepare(base_dir: Path, dummy_image_path: Path):
    """Tests the prepare method for resolving the image path."""
    # Use a relative path from the base_dir
    relative_path = dummy_image_path.relative_to(base_dir)
    scene = ImageScene(id="img1", duration=2, image=str(relative_path))

    prepared_assets = scene.prepare(base_dir)

    assert len(prepared_assets) == 1
    # Check that the resolved path is the absolute path to the dummy image
    assert prepared_assets[0] == dummy_image_path.resolve()


def test_image_scene_prepare_missing_file(base_dir: Path):
    """Tests that prepare raises an error if the image file doesn't exist."""
    scene = ImageScene(id="img1", duration=2, image="non_existent_file.png")
    with pytest.raises(ValidationError, match="image file not found"):
        scene.prepare(base_dir)


def test_image_scene_render(
    video_settings: VideoSettings, dummy_image_path: Path
):
    """Tests the render method of ImageScene."""
    scene = ImageScene.from_dict(
        {
            "id": "img1",
            "frames": 60,  # 2 seconds at 30 fps
            "image": str(dummy_image_path),
            "stretch": True,
        }
    )

    assets = [dummy_image_path]
    clip = scene.render(assets, video_settings)

    assert isinstance(clip, VideoClip)
    # 60 frames / 30 fps = 2.0 seconds
    assert clip.duration == 2.0
    # With stretch=True, the clip size should match the canvas size
    assert clip.size == (video_settings.width, video_settings.height)
