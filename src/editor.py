"""
ViralClipper AI Studio - Video Rendering Engine
Converts landscape video to 9:16 vertical Shorts, applies punchline zooms,
burns subtitles, composites approved reaction memes safely, and normalizes audio.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.config import OUTPUTS_DIR, TEMP_DIR, TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS
from src.utils import run_ffmpeg, sanitize_filename
from src.video_analysis import calculate_optimal_crop_center, get_video_properties
from src.effects import build_crop_filter, build_zoom_filter
from src.captions import generate_ass_subtitles
from src.candidate_detector import CandidateClip
from src.gemini_analyzer import GeminiClipAnalysis
from src.transcription import TranscriptSegment
from src.meme_selector import select_contextual_meme, MemePlacement
from src.meme_manager import AssetLibraryManager
from src.asset_license import AssetCategory


def render_short_clip(
    video_path: str,
    audio_path: str,
    candidate: CandidateClip,
    analysis: GeminiClipAnalysis,
    transcript_segments: List[TranscriptSegment],
    editing_style: str = "Modern",
    output_path: Optional[Path] = None,
    asset_manager: Optional[AssetLibraryManager] = None,
    framing_mode: str = "blur",
    top_header_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Renders a vertical 9:16 Short clip according to candidate timing,
    Gemini analysis, and specified editing style (Clean, Meme, Heavy Meme).
    Supports 'blur' framing (full stage visible with blurred background) and 'crop' framing.
    Displays persistent top header banner in upper blurred area throughout entire duration.
    Composites looped reaction memes and mixes audio sound effects on punchline beats.
    """
    clip_dur = max(1.0, candidate.end_time - candidate.start_time)
    safe_id = sanitize_filename(candidate.clip_id)
    style_suffix_map = {
        "clean": "clean",
        "modern": "modern",
        "meme": "meme",
        "heavy meme": "heavy",
        "heavy": "heavy"
    }
    safe_style = style_suffix_map.get(editing_style.lower(), sanitize_filename(editing_style.lower()))

    out_file = output_path or (OUTPUTS_DIR / f"{safe_id}_{safe_style}.mp4")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Build Subtitles with Persistent Top Header Banner
    ass_path = TEMP_DIR / f"{safe_id}_subs.ass"
    generate_ass_subtitles(
        segments=transcript_segments,
        clip_start=candidate.start_time,
        clip_end=candidate.end_time,
        output_path=ass_path,
        top_header_text=top_header_text
    )
    clean_ass_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

    # 2. Base Framing
    v_props = get_video_properties(video_path)
    crop_center = calculate_optimal_crop_center(
        video_path,
        candidate.start_time,
        candidate.end_time,
        num_samples=4
    )

    if framing_mode == "crop":
        base_v_filter = (
            f"crop={int(round(v_props.height * 9.0 / 16.0))}:{v_props.height}:"
            f"{max(0, min(v_props.width - int(round(v_props.height * 9.0 / 16.0)), int(round(crop_center * v_props.width - (v_props.height * 9.0 / 32.0)))))}:0,"
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos"
        )
    else:
        # Default: Full stage visible with ambient blurred background fill
        base_v_filter = (
            f"[0:v]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=25:5[bg];"
            f"[0:v]scale={TARGET_WIDTH}:-1[fg];"
            f"[bg][fg]overlay=0:(H-h)/2"
        )

    # Calculate punchline relative time (strictly inside clip)
    rel_punch = max(0.5, min(clip_dur - 1.5, candidate.punchline_time - candidate.start_time))

    mgr = asset_manager or AssetLibraryManager()
    all_memes = mgr.get_approved_assets(AssetCategory.GENERATED) + mgr.get_approved_assets(AssetCategory.MEME)
    all_sfx = mgr.get_approved_assets(AssetCategory.SFX)

    # Helper to find matching meme
    def get_meme_for_humor(humor_type: str, fallback_idx: int = 0) -> Optional[Path]:
        if not all_memes:
            return None
        tag_map = {
            "roast": ["roast", "fire"],
            "sarcasm": ["facepalm", "awkward"],
            "unexpected_answer": ["laugh", "what", "surprise"],
            "deadpan": ["awkward", "pause"],
            "self_deprecating": ["laugh", "dead"]
        }
        tags = tag_map.get(humor_type, ["laugh", "roast", "funny"])
        for a in all_memes:
            if any(t in " ".join(a.tags).lower() for t in tags):
                p = Path(a.file_path)
                if p.exists():
                    return p
        return Path(all_memes[fallback_idx % len(all_memes)].file_path)

    # Style Configurations
    inputs = [
        "-ss", str(candidate.start_time),
        "-t", str(clip_dur),
        "-i", str(video_path)
    ]

    is_heavy = editing_style.lower() in ["heavy meme", "heavy"]
    is_meme = is_heavy or editing_style.lower() in ["meme", "modern"]

    meme_1_path = get_meme_for_humor(analysis.humor_type, 0) if is_meme else None
    meme_2_path = get_meme_for_humor("unexpected_answer", 1) if is_heavy else None
    sfx_pop_path = Path("assets/sfx/pop.wav")
    sfx_whoosh_path = Path("assets/sfx/whoosh.wav")

    if is_heavy and meme_1_path and meme_2_path and sfx_pop_path.exists() and sfx_whoosh_path.exists():
        # HEAVY MEME: Impact zoom + Dual Reaction Badges + Dual SFX
        inputs.extend([
            "-loop", "1", "-t", str(clip_dur), "-i", str(meme_1_path),
            "-loop", "1", "-t", str(clip_dur), "-i", str(meme_2_path),
            "-i", str(sfx_whoosh_path),
            "-i", str(sfx_pop_path)
        ])

        m1_start = rel_punch
        m1_end = min(clip_dur, rel_punch + 3.2)
        m2_start = min(clip_dur - 0.8, rel_punch + 1.0)
        m2_end = min(clip_dur, m2_start + 3.0)

        # Video Filtergraph with zoom, subtitles, and dual memes
        v_filter = (
            f"{base_v_filter}[v_base];"
            f"[v_base]crop=w='iw/(1+0.20*between(t,{rel_punch-0.15:.2f},{rel_punch+0.7:.2f}))':"
            f"h='ih/(1+0.20*between(t,{rel_punch-0.15:.2f},{rel_punch+0.7:.2f}))':"
            f"x='(iw-ow)/2':y='(ih-oh)/2',scale={TARGET_WIDTH}:{TARGET_HEIGHT},"
            f"subtitles='{clean_ass_path}'[v_sub];"
            f"[1:v]scale=380:-1[m1];"
            f"[v_sub][m1]overlay=x=(W-w)/2:y=430:enable='between(t,{m1_start:.2f},{m1_end:.2f})'[v_m1];"
            f"[2:v]scale=300:-1[m2];"
            f"[v_m1][m2]overlay=x=W-w-50:y=H-h-260:enable='between(t,{m2_start:.2f},{m2_end:.2f})'[outv]"
        )

        whoosh_delay = max(0, int((rel_punch - 0.35) * 1000))
        pop_delay = int(rel_punch * 1000)
        a_filter = (
            f"[3:a]adelay={whoosh_delay}|{whoosh_delay}[a_w];"
            f"[4:a]adelay={pop_delay}|{pop_delay}[a_p];"
            f"[0:a][a_w][a_p]amix=inputs=3:duration=first[a_mix];"
            f"[a_mix]volume=1.2,loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
        )

        ffmpeg_args = (
            inputs +
            ["-filter_complex", f"{v_filter};{a_filter}", "-map", "[outv]", "-map", "[outa]"] +
            ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p"] +
            ["-c:a", "aac", "-b:a", "128k", "-t", str(clip_dur), str(out_file)]
        )

    elif is_meme and meme_1_path and sfx_pop_path.exists():
        # MEME STYLE: Punchline zoom + 1 Prominent Reaction Badge + 1 Synchronized SFX
        inputs.extend([
            "-loop", "1", "-t", str(clip_dur), "-i", str(meme_1_path),
            "-i", str(sfx_pop_path)
        ])

        m1_start = rel_punch
        m1_end = min(clip_dur, rel_punch + 3.5)

        v_filter = (
            f"{base_v_filter}[v_base];"
            f"[v_base]crop=w='iw/(1+0.16*between(t,{rel_punch-0.15:.2f},{rel_punch+0.7:.2f}))':"
            f"h='ih/(1+0.16*between(t,{rel_punch-0.15:.2f},{rel_punch+0.7:.2f}))':"
            f"x='(iw-ow)/2':y='(ih-oh)/2',scale={TARGET_WIDTH}:{TARGET_HEIGHT},"
            f"subtitles='{clean_ass_path}'[v_sub];"
            f"[1:v]scale=380:-1[m1];"
            f"[v_sub][m1]overlay=x=(W-w)/2:y=430:enable='between(t,{m1_start:.2f},{m1_end:.2f})'[outv]"
        )

        pop_delay = int(rel_punch * 1000)
        a_filter = (
            f"[2:a]adelay={pop_delay}|{pop_delay}[a_p];"
            f"[0:a][a_p]amix=inputs=2:duration=first[a_mix];"
            f"[a_mix]volume=1.2,loudnorm=I=-16:TP=-1.5:LRA=11[outa]"
        )

        ffmpeg_args = (
            inputs +
            ["-filter_complex", f"{v_filter};{a_filter}", "-map", "[outv]", "-map", "[outa]"] +
            ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p"] +
            ["-c:a", "aac", "-b:a", "128k", "-t", str(clip_dur), str(out_file)]
        )

    else:
        # CLEAN STYLE: Full stage/crop + dynamic ASS subtitles + clean normalized studio audio
        v_filter = f"{base_v_filter},subtitles='{clean_ass_path}'[outv]"
        ffmpeg_args = (
            inputs +
            ["-filter_complex", v_filter, "-map", "[outv]", "-map", "0:a?"] +
            ["-af", "volume=1.2,loudnorm=I=-16:TP=-1.5:LRA=11"] +
            ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p"] +
            ["-c:a", "aac", "-b:a", "128k", "-t", str(clip_dur), str(out_file)]
        )

    ok, err = run_ffmpeg(ffmpeg_args, timeout=120)

    # Fallback to simple clean render if advanced complex filter failed
    if not ok or not out_file.exists() or out_file.stat().st_size == 0:
        clean_fallback_args = [
            "-ss", str(candidate.start_time),
            "-t", str(clip_dur),
            "-i", str(video_path),
            "-filter_complex", f"{base_v_filter}[outv]",
            "-map", "[outv]",
            "-map", "0:a?",
            "-af", "volume=1.2",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            str(out_file)
        ]
        ok_fb, err_fb = run_ffmpeg(clean_fallback_args, timeout=120)
        if not ok_fb or not out_file.exists():
            raise RuntimeError(f"Rendering failed: {err_fb}")

    meme_label = "None"
    if is_heavy and meme_1_path and meme_2_path:
        meme_label = f"{meme_1_path.stem} + {meme_2_path.stem}"
    elif is_meme and meme_1_path:
        meme_label = meme_1_path.stem

    return {
        "output_path": str(out_file),
        "duration": clip_dur,
        "editing_style": editing_style,
        "resolution": f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
        "crop_center": crop_center,
        "viral_score": analysis.viral_score,
        "meme_used": meme_label,
        "framing_mode": framing_mode,
        "top_header_text": top_header_text
    }
