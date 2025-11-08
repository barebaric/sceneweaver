from typing import Tuple, Dict, Any


class ZoomSpec:
    def __init__(
        self,
        start_rect: Tuple[int, int, int, int],
        end_rect: Tuple[int, int, int, int],
    ):
        self.start_rect = start_rect
        self.end_rect = end_rect

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZoomSpec":
        return cls(
            start_rect=tuple(data["start_rect"]),
            end_rect=tuple(data["end_rect"]),
        )
