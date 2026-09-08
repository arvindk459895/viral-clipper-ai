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


def run_ffmpeg(args: List[str], timeout: int = 180) -> Tuple[bool, str]:
    """Runs FFmpeg command synchronously and captures output."""
    cmd = ['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error'] + args
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


def clean_temp_dir() -> int:
    """Cleans files from the temporary directory. Returns number of files removed."""
    count = 0
    if TEMP_DIR.exists():
        for item in TEMP_DIR.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    count += 1
            except Exception:
                pass
    return count
