import pytest
from pathlib import Path
from PIL import Image
from sceneweaver.spec.video_settings import VideoSettings


# This fixture provides a standard VideoSettings object for use in tests.
@pytest.fixture
def video_settings() -> VideoSettings:
    """Provides a default VideoSettings instance for tests."""
    return VideoSettings(
        width=1280, height=720, fps=30, output_file="test.mp4"
    )


# This fixture creates a temporary directory for each test function,
# which is useful for tests that need to read or write files.
@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    """Provides a temporary directory path for tests."""
    return tmp_path


# This fixture creates a dummy PNG image file within the temporary directory.
# It's essential for testing scenes that require an image asset.
@pytest.fixture
def dummy_image_path(base_dir: Path) -> Path:
    """Creates a dummy image file in the base_dir and returns its path."""
    image_path = base_dir / "test_image.png"
    # Create a small, black 10x10 pixel image
    img = Image.new("RGB", (10, 10), color="black")
    img.save(image_path)
    return image_path
