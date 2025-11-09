from typing import Dict, Any, Optional, List
from pathlib import Path


class AudioFilterSpec:
    """Placeholder for future audio filter implementation."""

    def __init__(self, fade_in: float = 0.0, fade_out: float = 0.0):
        self.fade_in = fade_in
        self.fade_out = fade_out

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioFilterSpec":
        return cls(
            fade_in=data.get("fade-in", 0.0),
            fade_out=data.get("fade-out", 0.0),
        )


class AudioTrackSpec:
    def __init__(
        self,
        file: str,
        shift: float = 0.0,
        filters: Optional[AudioFilterSpec] = None,
    ):
        self.file = file
        self.shift = shift
        self.filters = filters

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], base_dir: Path
    ) -> "AudioTrackSpec":
        if "file" not in data:
            raise ValueError("Audio track is missing required 'file' field.")

        filters = (
            AudioFilterSpec.from_dict(data["filters"])
            if "filters" in data
            else None
        )
        return cls(
            file=data["file"],
            shift=data.get("shift", 0.0),
            filters=filters,
        )

    @classmethod
    def from_list(
        cls, data: List[Dict[str, Any]], base_dir: Path
    ) -> List["AudioTrackSpec"]:
        """Creates a list of audio tracks from a list of dictionaries."""
        if not data:
            return []
        # Allow single audio object as well as a list
        if isinstance(data, dict):
            data = [data]
        return [cls.from_dict(d, base_dir) for d in data]
