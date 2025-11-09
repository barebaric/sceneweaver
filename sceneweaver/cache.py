import hashlib
import json
import shutil
import time
from pathlib import Path
from typing import Dict, Any, Optional, Union, Sequence
from importlib.resources.abc import Traversable
import platformdirs
import yaml


def parse_size(size_str: str) -> int:
    """Converts a size string like '10GB' to bytes."""
    size_str = size_str.upper().strip()
    units = {"KB": 1, "MB": 2, "GB": 3, "TB": 4}
    for unit, power in units.items():
        if size_str.endswith(unit):
            value = float(size_str[: -len(unit)])
            return int(value * (1024**power))
    return int(size_str)


class CacheManager:
    def __init__(self):
        self.cache_dir = Path(
            platformdirs.user_cache_dir("sceneweaver", "app")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.cache_dir / "metadata.yaml"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        if not self.metadata_path.exists():
            return {"scenes": {}}
        with open(self.metadata_path, "r") as f:
            data = yaml.safe_load(f) or {}
            if "scenes" not in data:
                return {"scenes": {}}
            return data

    def _save_metadata(self):
        with open(self.metadata_path, "w") as f:
            yaml.safe_dump(self.metadata, f)

    def _get_scene_hash(
        self,
        scene_dict: Dict[str, Any],
        assets: Sequence[Union[Path, Traversable]],
    ) -> str:
        hasher = hashlib.sha256()

        scene_str = json.dumps(scene_dict, sort_keys=True, default=str)
        hasher.update(scene_str.encode("utf-8"))

        # Sort by string representation to ensure consistent order
        sorted_assets = sorted(assets, key=str)
        for asset_path in sorted_assets:
            if asset_path.is_file():
                with asset_path.open("rb") as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
        return hasher.hexdigest()

    def get(
        self,
        composite_scene_id: str,
        scene_dict: Dict[str, Any],
        assets: Sequence[Union[Path, Traversable]],
    ) -> Optional[Path]:
        entry = self.metadata["scenes"].get(composite_scene_id)
        if not entry:
            return None

        new_hash = self._get_scene_hash(scene_dict, assets)
        if new_hash != entry.get("current_hash"):
            return None

        cached_file = self.cache_dir / entry["filename"]
        if cached_file.exists():
            print(f"Cache hit for scene (ID: {composite_scene_id}).")
            return cached_file
        else:
            del self.metadata["scenes"][composite_scene_id]
            self._save_metadata()
            return None

    def put(
        self,
        composite_scene_id: str,
        scene_dict: Dict[str, Any],
        assets: Sequence[Union[Path, Traversable]],
        temp_clip_path: Path,
        cache_settings: Optional[Dict[str, Any]],
    ) -> Path:
        new_hash = self._get_scene_hash(scene_dict, assets)
        old_entry = self.metadata["scenes"].get(composite_scene_id)

        if old_entry and old_entry.get("current_hash") != new_hash:
            old_file = self.cache_dir / old_entry.get("filename", "")
            if old_file.exists():
                print(f"Deleting outdated cache file: {old_file.name}")
                old_file.unlink()

        new_filename = f"{new_hash}.mp4"
        destination_path = self.cache_dir / new_filename

        shutil.move(temp_clip_path, destination_path)
        print(
            f"Cached scene '{composite_scene_id}' to {destination_path.name}"
        )

        self.metadata["scenes"][composite_scene_id] = {
            "current_hash": new_hash,
            "filename": new_filename,
            "timestamp": time.time(),
            "size": destination_path.stat().st_size,
        }
        self._save_metadata()

        if cache_settings is not None:
            self._enforce_max_size(cache_settings)
        return destination_path

    def _enforce_max_size(self, cache_config: Dict[str, Any]):
        # ... (method remains the same)
        max_size_str = cache_config.get("max-size", "500MB")
        max_size_bytes = parse_size(max_size_str)

        scene_items = self.metadata["scenes"].items()
        sorted_items = sorted(scene_items, key=lambda x: x[1]["timestamp"])

        current_size = sum(item["size"] for _, item in scene_items)

        while current_size > max_size_bytes and sorted_items:
            oldest_id, oldest_entry = sorted_items.pop(0)

            file_to_delete = self.cache_dir / oldest_entry["filename"]
            if file_to_delete.exists():
                print(
                    f"Cache full. Deleting oldest item: {file_to_delete.name}"
                )
                current_size -= file_to_delete.stat().st_size
                file_to_delete.unlink()

            del self.metadata["scenes"][oldest_id]

        self._save_metadata()

    def clean(self):
        # ... (method remains the same)
        if self.cache_dir.exists():
            print(f"Cleaning cache at: {self.cache_dir}")
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = {"scenes": {}}
        self._save_metadata()
