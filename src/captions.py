"""
ViralClipper AI Studio - Captions Module
Generates word-highlighted, high-contrast viral subtitles (ASS format)
supporting Hindi, Hinglish, and English with emoji emphasis and safe-zone placement.
"""
from pathlib import Path
from typing import List, Optional
from src.transcription import TranscriptSegment, TranscriptWord
from src.utils import format_timestamp_full


def format_ass_time(seconds: float) -> str:
    """Formats seconds into ASS timestamp format: H:MM:SS.cs (centiseconds)."""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{hours:d}:{mins:02d}:{secs:02d}.{cs:02d}"


def clean_subtitle_text(text: str) -> str:
    """Strips HTML tags (<i>, </i>, <font>, <c>), braces, and unescaped symbols from subtitles."""
    import re
    # Remove HTML / XML tags like <i>, </i>, <c>, </c>, <font color="...">
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Remove ASS special formatting braces that might break rendering
    cleaned = cleaned.replace("{", "").replace("}", "")
    # Normalize multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def wrap_header_text(text: str, max_chars_per_line: int = 28) -> str:
    """Wraps text for ASS header banner display using \\N for line breaks, up to 2 lines."""
    clean = clean_subtitle_text(text).replace("#Shorts", "").replace("#shorts", "").strip()
    words = clean.split()
    if not words:
        return ""
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        if current_len + len(w) + (1 if current_line else 0) <= max_chars_per_line:
            current_line.append(w)
            current_len += len(w) + 1
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
    if current_line:
        lines.append(" ".join(current_line))
    return "\\N".join(lines[:2])


def generate_ass_subtitles(
    segments: List[TranscriptSegment],
    clip_start: float,
    clip_end: float,
    output_path: Path,
    top_header_text: Optional[str] = None
) -> Path:
    """
    Generates an ASS subtitle file tailored for 1080x1920 vertical Shorts.
    - Persistent top headline banner displayed above video throughout entire duration
    - Word chunking (2-4 words at a time for fast scanning)
    - Active word / punchline word highlight in bright gold
    - Bold font with heavy black outline for high contrast against background
    - Safe zone: placed vertically at MarginV=320 to clear Shorts UI
    """
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ViralShorts,Arial,56,&H00FFFFFF,&H0033FFFF,&H00000000,&H80000000,1,0,0,0,100,100,2,0,1,6,3,2,60,60,320,1
Style: TopHeader,Arial,54,&H00FFFFFF,&H0000FFFF,&H00000000,&HA0000000,1,0,0,0,100,100,2,0,1,6,3,8,60,60,240,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    gold_highlight_start = "{\\c&H0000FFFF&\\b1}"
    white_normal_start = "{\\c&H00FFFFFF&\\b1}"

    # 1. Persistent Top Header Banner (spans entire duration of clip)
    if top_header_text and top_header_text.strip():
        wrapped_header = wrap_header_text(top_header_text)
        clip_dur = max(0.5, clip_end - clip_start)
        header_end_str = format_ass_time(clip_dur)
        events.append(f"Dialogue: 1,0:00:00.00,{header_end_str},TopHeader,,0,0,0,,{wrapped_header}")

    for seg in segments:
        if seg.end < clip_start or seg.start > clip_end:
            continue

        if seg.words:
            chunk = []
            chunk_start = None
            for w in seg.words:
                if w.end < clip_start or w.start > clip_end:
                    continue
                if chunk_start is None:
                    chunk_start = max(0.0, w.start - clip_start)

                chunk.append(w)
                if len(chunk) >= 3 or w.word.endswith((".", "!", "?")):
                    chunk_end = max(chunk_start + 0.3, w.end - clip_start)
                    styled_words = []
                    for cw in chunk:
                        w_clean = clean_subtitle_text(cw.word)
                        if not w_clean:
                            continue
                        if any(c in w_clean.lower() for c in ["!", "?", "bhai", "gym", "zinda", "what", "rehna", "prarthana"]):
                            styled_words.append(gold_highlight_start + w_clean + white_normal_start)
                        else:
                            styled_words.append(w_clean)

                    if styled_words:
                        text_line = " ".join(styled_words)
                        start_str = format_ass_time(chunk_start)
                        end_str = format_ass_time(chunk_end)
                        events.append(f"Dialogue: 0,{start_str},{end_str},ViralShorts,,0,0,0,,{text_line}")
                    chunk = []
                    chunk_start = None

            if chunk and chunk_start is not None:
                chunk_end = max(chunk_start + 0.3, chunk[-1].end - clip_start)
                clean_words = [clean_subtitle_text(w.word) for w in chunk if clean_subtitle_text(w.word)]
                if clean_words:
                    text_line = " ".join(clean_words)
                    start_str = format_ass_time(chunk_start)
                    end_str = format_ass_time(chunk_end)
                    events.append(f"Dialogue: 0,{start_str},{end_str},ViralShorts,,0,0,0,,{text_line}")

        else:
            s_rel = max(0.0, seg.start - clip_start)
            e_rel = min(clip_end - clip_start, seg.end - clip_start)
            if e_rel > s_rel:
                clean_seg_text = clean_subtitle_text(seg.text)
                if clean_seg_text:
                    start_str = format_ass_time(s_rel)
                    end_str = format_ass_time(e_rel)
                    events.append(f"Dialogue: 0,{start_str},{end_str},ViralShorts,,0,0,0,,{clean_seg_text}")

    content = header + "\n".join(events) + "\n"
    output_path.write_text(content, encoding="utf-8")
    return output_path
