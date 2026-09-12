"""
ViralClipper AI Studio - Utility Helpers
Handles timestamps, system commands, URL validation, and temp file management.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.config import TEMP_DIR


def is_valid_youtube_url(url: str) -> bool:
    """Validates whether a URL is a valid YouTube video link."""
    if not url or not isinstance(url, str):
        return False
    patterns = [
        r'^(https?://)?(www\.)?(youtube\.com/watch\?v=[\w-]{11})',
        r'^(https?://)?(www\.)?(youtu\.be/[\w-]{11})',
        r'^(https?://)?(www\.)?(youtube\.com/shorts/[\w-]{11})',
        r'^(https?://)?(www\.)?(youtube\.com/embed/[\w-]{11})',
        r'^(https?://)?(www\.)?(youtube\.com/v/[\w-]{11})',
        r'^(https?://)?(m\.)?(youtube\.com/watch\?v=[\w-]{11})',
    ]
    return any(re.match(p, url.strip()) for p in patterns)


def extract_video_id(url: str) -> Optional[str]:
    """Extracts the 11-character YouTube video ID."""
    if not url:
        return None
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def format_timestamp(seconds: float) -> str:
    """Formats seconds into MM:SS or HH:MM:SS string."""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_timestamp_full(seconds: float) -> str:
    """Formats seconds into HH:MM:SS.mmm for FFmpeg subtitles or markers."""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def parse_timestamp(ts_str: str) -> float:
    """Parses MM:SS or HH:MM:SS string into seconds."""
    parts = ts_str.strip().split(':')
    if len(parts) == 2:
        return float(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return float(ts_str)


def sanitize_filename(name: str) -> str:
    """Replaces illegal characters for cross-platform filesystem safety."""
    clean = re.sub(r'[\/\:*?"<>|]', '_', name)
    clean = re.sub(r'[\s]+', '_', clean)
    return clean.strip('_')[:80]


def get_ffmpeg_executable() -> str:
    """Finds ffmpeg executable from PATH or bundled imageio-ffmpeg."""
    ffmpeg_sys = shutil.which("ffmpeg")
    if ffmpeg_sys:
        return ffmpeg_sys
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def run_ffmpeg(args: List[str], timeout: int = 180) -> Tuple[bool, str]:
    """Runs FFmpeg command synchronously and captures output."""
    exe = get_ffmpeg_executable()
    cmd = [exe, '-y', '-hide_banner', '-loglevel', 'error'] + args
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False
        )
        if proc.returncode != 0:
            return False, proc.stderr or "FFmpeg error"
        return True, proc.stdout
    except subprocess.TimeoutExpired:
        return False, f"FFmpeg timed out after {timeout} seconds"
    except Exception as e:
        return False, str(e)


def get_audio_duration(audio_path: str) -> float:
    """Returns the duration of an audio file in seconds without depending on pydub/audioop."""
    p = Path(audio_path)
    if not p.exists():
        return 0.0

    # 1. Try soundfile
    try:
        import soundfile as sf
        info = sf.info(str(p))
        return float(info.duration)
    except Exception:
        pass

    # 2. Try wave
    try:
        import wave
        with wave.open(str(p), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return float(frames) / float(rate)
    except Exception:
        pass

    # 3. Try ffprobe
    try:
        exe = shutil.which("ffprobe")
        if not exe:
            exe_ffmpeg = get_ffmpeg_executable()
            exe = exe_ffmpeg.replace("ffmpeg", "ffprobe")
        if exe and Path(exe).exists():
            cmd = [exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                return float(res.stdout.strip())
    except Exception:
        pass

    # Fallback default duration
    return 2.0
