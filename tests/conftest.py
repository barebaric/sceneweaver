import pytest
from pathlib import Path
from PIL import Image
import numpy as np
from scipy.io.wavfile import write
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


@pytest.fixture
def dummy_audio_path(base_dir: Path) -> Path:
    """Creates a dummy audio file of a known duration and returns its path."""
    audio_path = base_dir / "test_audio.wav"
    sample_rate = 44100
    duration_seconds = 2.5
    frequency = 440  # A4 note

    num_samples = int(duration_seconds * sample_rate)
    t = np.linspace(
        0.0, duration_seconds, num_samples, endpoint=False, dtype=np.float32
    )
    amplitude = np.iinfo(np.int16).max * 0.5
    data = amplitude * np.sin(2.0 * np.pi * frequency * t)

    write(audio_path, sample_rate, data.astype(np.int16))
    return audio_path


@pytest.fixture
def templates_dir(tmp_path: Path) -> Path:
    """Creates a base directory for mock templates."""
    tdir = tmp_path / "templates"
    tdir.mkdir()
    return tdir


@pytest.fixture
def simple_template_path(templates_dir: Path) -> Path:
    """Creates a simple mock template and returns its path."""
    template_path = templates_dir / "simple"
    template_path.mkdir()
    (template_path / "template.yaml").write_text(
        """
- type: image
  image: "image.png"
  params:
    title: "{{ title | default('Default Title') }}"
"""
    )
    return template_path


@pytest.fixture
def template_with_asset_path(templates_dir: Path) -> Path:
    """Creates a mock template that includes its own asset."""
    template_path = templates_dir / "with_asset"
    template_path.mkdir()
    (template_path / "template.yaml").write_text(
        """
- type: image
  image: "logo.png" # This asset is inside the template dir
"""
    )
    # Create the asset file that the template refers to
    img = Image.new("RGB", (5, 5), color="red")
    img.save(template_path / "logo.png")
    return template_path


@pytest.fixture
def multi_scene_template_path(templates_dir: Path) -> Path:
    """Creates a mock template that expands to two scenes."""
    template_path = templates_dir / "multi"
    template_path.mkdir()
    (template_path / "template.yaml").write_text(
        """
- type: image
  id: scene_one
  image: "a.png"
- type: image
  id: scene_two
  image: "b.png"
"""
    )
    return template_path
