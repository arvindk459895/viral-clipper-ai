"""
ViralClipper AI Studio - Video Effects Engine
Implements punch zooms, slow zooms, camera shake, white flashes, freeze frames,
and motion transitions using FFmpeg and OpenCV filters.
"""
from typing import List, Dict, Any, Optional


def build_crop_filter(
    crop_center_x: float,
    in_w: int = 1280,
    in_h: int = 720,
    out_w: int = 1080,
    out_h: int = 1920
) -> str:
    """
    Constructs an FFmpeg filter string to crop a landscape 16:9 frame to 9:16 vertical
    centered on the speaker face (crop_center_x: 0.0 to 1.0).
    """
    crop_w = int(round(in_h * 9.0 / 16.0))
    if crop_w % 2 != 0:
        crop_w -= 1

    max_x_offset = in_w - crop_w
    target_x = int(round(crop_center_x * in_w - crop_w / 2.0))
    clamped_x = max(0, min(max_x_offset, target_x))

    return f"crop={crop_w}:{in_h}:{clamped_x}:0,scale={out_w}:{out_h}:flags=lanczos"


def build_fit_blur_filter(
    out_w: int = 1080,
    out_h: int = 1920
) -> str:
    """
    Constructs an FFmpeg filter string to fit a full 16:9 widescreen video into 9:16 vertical
    with a beautiful blurred ambient background. Ensures 100% of the stage and all speakers
    are completely visible without cutting anyone off.
    """
    return (
        f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h},boxblur=25:5[bg];"
        f"[0:v]scale={out_w}:-1[fg];"
        f"[bg][fg]overlay=0:(H-h)/2"
    )


def build_zoom_filter(
    start_t: float,
    end_t: float,
    punch_t: float,
    punch_strength: float = 0.18,
    out_w: int = 1080,
    out_h: int = 1920
) -> str:
    """
    Builds a high-performance dynamic punch zoom filter using FFmpeg dynamic cropping:
    Spikes zoom on punchline delivery (punch_t) and scales back seamlessly.
    """
    rel_punch = max(0.0, punch_t - start_t)
    t1 = max(0.0, round(rel_punch - 0.15, 2))
    t2 = max(t1 + 0.3, round(rel_punch + 0.70, 2))
    strength = round(punch_strength, 2)

    return (
        f"crop=w='iw/(1+{strength}*between(t,{t1},{t2}))':"
        f"h='ih/(1+{strength}*between(t,{t1},{t2}))':"
        f"x='(iw-ow)/2':y='(ih-oh)/2',"
        f"scale={out_w}:{out_h}"
    )


def build_shake_filter(shake_t: float, duration: float = 0.4, intensity: int = 12) -> str:
    """Creates a brief camera-shake jitter filter on high-energy shouts or impacts."""
    return (
        f"crop=w=iw-{intensity*2}:h=ih-{intensity*2}:"
        f"x='if(between(t,{shake_t:.2f},{shake_t + duration:.2f}),{intensity}+{intensity}*sin(50*t),{intensity})':"
        f"y='if(between(t,{shake_t:.2f},{shake_t + duration:.2f}),{intensity}+{intensity}*cos(50*t),{intensity})',"
        f"scale=1080:1920"
    )


def build_flash_filter(flash_t: float, duration: float = 0.25) -> str:
    """Creates an impact white flash filter for sudden reveals or punchlines."""
    return (
        f"fade=t=out:st={flash_t:.2f}:d={duration/2:.2f}:c=white,"
        f"fade=t=in:st={flash_t + duration/2:.2f}:d={duration/2:.2f}:c=white"
    )
