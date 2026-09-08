"""
ViralClipper AI Studio - Thumbnail Generator Module
Extracts the strongest facial reaction frames and composites bold,
authentic, non-misleading cover typography (2 options per Short).
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

from src.config import OUTPUTS_DIR, TEMP_DIR
from src.video_analysis import extract_keyframe
from src.candidate_detector import CandidateClip
from src.gemini_analyzer import GeminiClipAnalysis


class ThumbnailResult(BaseModel):
    option_1_path: str
    option_2_path: str
    hook_text_1: str
    hook_text_2: str


POPULAR_HOOK_TEXTS = [
    "WHAT?! ",
    "NO WAY ",
    "HE SAID WHAT? ",
    "THAT REACTION ",
    "WAIT FOR IT ",
    "CANNOT UNSEE "
]


def render_thumbnail_text(
    frame_path: str,
    text: str,
    output_path: str
) -> str:
    """
    Overlays bold, high-contrast viral typography with drop shadow onto the frame.
    """
    img = Image.open(frame_path).convert("RGBA")
    w, h = img.size

    # Create overlay drawing
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Position in upper-third or bottom-third with high contrast
    font_size = max(36, int(h * 0.09))
    text_x = int(w * 0.5)
    text_y = int(h * 0.82)

    # Dark translucent banner behind text for maximum legibility
    banner_h = int(font_size * 1.8)
    banner_top = text_y - banner_h // 2
    draw.rectangle([0, banner_top, w, banner_top + banner_h], fill=(0, 0, 0, 160))

    # Bold text with outline
    stroke_w = max(2, int(font_size * 0.08))
    draw.text(
        (text_x, text_y),
        text,
        fill=(255, 220, 0, 255),
        anchor="mm",
        stroke_width=stroke_w,
        stroke_fill=(0, 0, 0, 255)
    )

    final_img = Image.alpha_composite(img, overlay).convert("RGB")
    final_img.save(output_path, "JPEG", quality=92)
    return output_path


def generate_thumbnails(
    video_path: str,
    candidate: CandidateClip,
    analysis: GeminiClipAnalysis,
    output_dir: Optional[Path] = None
) -> ThumbnailResult:
    """
    Generates 2 distinct thumbnail options for the candidate Short:
    - Option 1: Reaction frame (right after punchline) with high-intensity reaction text
    - Option 2: Setup / anticipation frame with curiosity text
    """
    out_dir = output_dir or OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # Timestamps for the two thumbnail variants
    t1 = min(candidate.end_time - 0.2, candidate.punchline_time + 0.4)
    t2 = max(candidate.start_time + 0.5, candidate.punchline_time - 1.5)

    raw_frame_1 = TEMP_DIR / f"{candidate.clip_id}_thumb_raw1.jpg"
    raw_frame_2 = TEMP_DIR / f"{candidate.clip_id}_thumb_raw2.jpg"

    extract_keyframe(video_path, t1, str(raw_frame_1))
    extract_keyframe(video_path, t2, str(raw_frame_2))

    # Select authentic texts based on humor/reaction type
    if analysis.reaction_type == "laugh":
        text_1 = "THAT REACTION "
        text_2 = "NO WAY "
    elif analysis.reaction_type == "disbelief":
        text_1 = "WHAT?! "
        text_2 = "HE SAID WHAT? "
    else:
        text_1 = "WAIT FOR IT "
        text_2 = "CANNOT UNSEE "

    out_path_1 = str(out_dir / f"{candidate.clip_id}_thumbnail_1.jpg")
    out_path_2 = str(out_dir / f"{candidate.clip_id}_thumbnail_2.jpg")

    render_thumbnail_text(str(raw_frame_1), text_1, out_path_1)
    render_thumbnail_text(str(raw_frame_2), text_2, out_path_2)

    return ThumbnailResult(
        option_1_path=out_path_1,
        option_2_path=out_path_2,
        hook_text_1=text_1,
        hook_text_2=text_2
    )
