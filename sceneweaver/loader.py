from pathlib import Path
import yaml
from .spec import VideoSpec


def load_spec(spec_path: Path, base_dir: Path) -> tuple[VideoSpec, dict]:
    """
    Loads a video specification from a YAML file.

    Returns a tuple containing the VideoSpec object and the raw dictionary
    from which it was created, which is useful for caching.
    """
    if not spec_path.is_file():
        raise FileNotFoundError(f"Specification file not found: {spec_path}")

    print(f"Loading video specification from: {spec_path}")
    with open(spec_path, "r") as f:
        spec_dict = yaml.safe_load(f)

    if not spec_dict:
        raise ValueError("Specification file is empty or invalid.")

    spec = VideoSpec.from_dict(spec_dict, base_dir)
    return spec, spec_dict
