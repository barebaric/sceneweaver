from typing import Any, Dict, Optional, Tuple

import numpy as np
from PIL import Image
from moviepy import VideoClip

from ..zoom_spec import ZoomSpec
from .base_effect import BaseEffect


class ZoomEffect(BaseEffect):
    """Handles a zoom effect on a clip."""

    def __init__(
        self,
        type: str,
        duration: Optional[float] = None,
        start_rect: Optional[Tuple[int, int, int, int]] = None,
        end_rect: Optional[Tuple[int, int, int, int]] = None,
    ):
        super().__init__(type, duration or 0)
        self.zoom_spec = ZoomSpec(
            start_rect=start_rect or (0, 0, 100, 100),
            end_rect=end_rect or (0, 0, 100, 100),
        )

    def apply(self, clip: VideoClip) -> VideoClip:
        zoom_duration = self.duration if self.duration > 0 else clip.duration
        clip_w, clip_h = clip.size

        start_x, start_y, start_w, start_h = self.zoom_spec.start_rect
        end_x, end_y, end_w, end_h = self.zoom_spec.end_rect

        def zoom_func(get_frame, t):
            frame = get_frame(t)

            progression = min(1.0, t / zoom_duration)

            # Interpolate rect values
            curr_x = start_x + progression * (end_x - start_x)
            curr_y = start_y + progression * (end_y - start_y)
            curr_w = start_w + progression * (end_w - start_w)
            curr_h = start_h + progression * (end_h - start_h)

            # Convert from percent to pixels
            x_pix = int(clip_w * curr_x / 100)
            y_pix = int(clip_h * curr_y / 100)
            w_pix = int(clip_w * curr_w / 100)
            h_pix = int(clip_h * curr_h / 100)

            # Crop with numpy slicing
            cropped_frame = frame[y_pix : y_pix + h_pix, x_pix : x_pix + w_pix]

            # Resize back to original size using PIL
            pil_img = Image.fromarray(cropped_frame)
            resized_img = pil_img.resize(clip.size, Image.Resampling.LANCZOS)
            return np.array(resized_img)

        # Use transform, which creates a new clip with transformed frames.
        return clip.transform(zoom_func)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ZoomEffect":
        zoom_spec = ZoomSpec.from_dict(data)
        return cls(
            type=data["type"],
            duration=data.get("duration"),
            start_rect=zoom_spec.start_rect,
            end_rect=zoom_spec.end_rect,
        )
