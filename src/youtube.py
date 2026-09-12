"""
ViralClipper AI Studio - YouTube Ingestion Module
Wraps yt-dlp to extract video metadata, download source video, and extract audio.
Includes multi-client 403-bypass fallbacks and direct local video file ingestion.
"""
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from pydantic import BaseModel, Field
import yt_dlp

from src.config import TEMP_DIR, CREDENTIALS_DIR
from src.utils import is_valid_youtube_url, sanitize_filename, run_ffmpeg


class VideoMetadata(BaseModel):
    video_id: str = Field(..., description="YouTube 11-character video ID or local file ID")
    title: str = Field(..., description="Title of the video")
    channel: str = Field(..., description="Channel name / author")
    duration: float = Field(..., description="Duration of video in seconds")
    thumbnail_url: Optional[str] = Field(None, description="URL of primary thumbnail")
    upload_date: Optional[str] = Field(None, description="Upload date in YYYYMMDD format")
    description: Optional[str] = Field(None, description="Video description snippet")
    view_count: Optional[int] = Field(0, description="Approximate view count")


class YouTubeIngestionError(Exception):
    """Custom exception for YouTube extraction and download errors."""
    pass


def _extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'(?:shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return ""


def _oembed_fallback(url: str, video_id: str) -> Optional[VideoMetadata]:
    """Fallback metadata extraction using YouTube oEmbed API (no format checking)."""
    import urllib.request
    import json as _json
    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode())
        return VideoMetadata(
            video_id=video_id,
            title=data.get('title', 'Untitled Video'),
            channel=data.get('author_name', 'Unknown Channel'),
            duration=0.0,  # oEmbed doesn't provide duration
            thumbnail_url=data.get('thumbnail_url'),
            upload_date=None,
            description='',
            view_count=0
        )
    except Exception:
        return None


def extract_metadata(url: str) -> VideoMetadata:
    """Extracts metadata from a YouTube video without downloading media files.
    Uses multiple fallback strategies to handle SABR-only and bot-gated videos."""
    if not is_valid_youtube_url(url):
        raise YouTubeIngestionError(f"Invalid YouTube URL format: {url}")

    video_id = _extract_video_id(url)
    cookie_file = CREDENTIALS_DIR / "youtube_cookies.txt"
    has_cookies = cookie_file.exists() and cookie_file.stat().st_size > 0

    # Strategy 1: Full extraction with ignore_no_formats_error
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'ignore_no_formats_error': True,
        'check_formats': False,
        'format': 'best',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }
    if has_cookies:
        ydl_opts['cookiefile'] = str(cookie_file)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get('title'):
                return VideoMetadata(
                    video_id=info.get('id', video_id or 'unknown_id'),
                    title=info.get('title', 'Untitled Video'),
                    channel=info.get('uploader') or info.get('channel', 'Unknown Channel'),
                    duration=float(info.get('duration') or 0.0),
                    thumbnail_url=info.get('thumbnail') or (info.get('thumbnails', [{}])[-1].get('url') if info.get('thumbnails') else None),
                    upload_date=info.get('upload_date'),
                    description=(info.get('description') or '')[:300],
                    view_count=info.get('view_count', 0)
                )
    except Exception:
        pass  # Fall through to next strategy

    # Strategy 2: extract_flat (lightweight, no format resolution)
    ydl_opts_flat = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
    }
    if has_cookies:
        ydl_opts_flat['cookiefile'] = str(cookie_file)
    try:
        with yt_dlp.YoutubeDL(ydl_opts_flat) as ydl:
            info = ydl.extract_info(url, download=False)
            if info and info.get('title'):
                return VideoMetadata(
                    video_id=info.get('id', video_id or 'unknown_id'),
                    title=info.get('title', 'Untitled Video'),
                    channel=info.get('uploader') or info.get('channel', 'Unknown Channel'),
                    duration=float(info.get('duration') or 0.0),
                    thumbnail_url=info.get('thumbnail'),
                    upload_date=info.get('upload_date'),
                    description=(info.get('description') or '')[:300],
                    view_count=info.get('view_count', 0)
                )
    except Exception:
        pass  # Fall through to oEmbed

    # Strategy 3: YouTube oEmbed API (always works, no yt-dlp format issues)
    if video_id:
        oembed_meta = _oembed_fallback(url, video_id)
        if oembed_meta:
            return oembed_meta

    raise YouTubeIngestionError(
        "Could not extract video metadata after all strategies. "
        "The video may be private, region-locked, or YouTube is blocking this server. "
        "Please try the 'Upload Local Video' tab instead."
    )


def download_video_and_audio(
    url: str,
    output_dir: Optional[Path] = None,
    max_height: int = 720,
    progress_cb: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    Downloads YouTube video using Android/iOS player clients to avoid HTTP 403 throttling.
    Strictly separates video downloading from audio extraction.
    """
    if not is_valid_youtube_url(url):
        raise YouTubeIngestionError(f"Invalid YouTube URL: {url}")

    if progress_cb:
        progress_cb("Extracting video metadata...")
    meta = extract_metadata(url)

    out_dir = output_dir or TEMP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_title = sanitize_filename(meta.title)
    video_filename = f"{meta.video_id}_{safe_title}.mp4"
    video_path = out_dir / video_filename
    audio_path = out_dir / f"{meta.video_id}_{safe_title}_audio.wav"

    # Check if video was already downloaded in temp directory
    existing_videos = list(out_dir.glob(f"{meta.video_id}*.mp4"))
    if existing_videos and existing_videos[0].stat().st_size > 1000:
        video_path = existing_videos[0]
        download_success = True
        if progress_cb:
            progress_cb(f"Found existing downloaded video ({video_path.stat().st_size / (1024*1024):.1f} MB)")
    else:
        # Strategy list: Try android/ios first, then web with resilient fallback
        strategies = [
            {
                'format': f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/18/best',
                'extractor_args': {'youtube': {'player_client': ['android', 'ios']}}
            },
            {
                'format': '18/best[height<=720]/best',
                'extractor_args': {'youtube': {'player_client': ['android']}}
            },
            {
                'format': '18/best[height<=720]/best',
                'extractor_args': {'youtube': {'player_client': ['ios']}}
            },
            {
                'format': f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best',
                'extractor_args': {'youtube': {'player_client': ['mweb', 'web_creator']}}
            },
            {
                'format': 'best',
                'extractor_args': {'youtube': {'player_client': ['web']}}
            }
        ]

        download_success = False
        last_err_msg = ""

        if progress_cb:
            progress_cb(f"Downloading video streams for '{meta.title[:30]}...' (Max {max_height}p)")

        def dl_hook(d):
            if d.get('status') == 'downloading' and progress_cb:
                pct = d.get('_percent_str', '').strip()
                spd = d.get('_speed_str', '').strip()
                progress_cb(f"Downloading YouTube media: {pct} ({spd})")

        cookie_file = CREDENTIALS_DIR / "youtube_cookies.txt"
        has_cookies = cookie_file.exists() and cookie_file.stat().st_size > 0

        for strat in strategies:
            ydl_opts = {
                'format': strat['format'],
                'outtmpl': str(video_path),
                'extractor_args': strat['extractor_args'],
                'quiet': True,
                'no_warnings': True,
                'overwrites': True,
                'merge_output_format': 'mp4',
                'progress_hooks': [dl_hook]
            }
            if has_cookies:
                ydl_opts['cookiefile'] = str(cookie_file)
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                if video_path.exists() and video_path.stat().st_size > 1000:
                    download_success = True
                    break
                else:
                    matching = list(out_dir.glob(f"{meta.video_id}*.mp4"))
                    if matching and matching[0].stat().st_size > 1000:
                        video_path = matching[0]
                        download_success = True
                        break
            except Exception as e:
                last_err_msg = str(e)

    if not download_success:
        clean_err = "HTTP 403: Forbidden on direct web stream" if ("403" in last_err_msg or "Forbidden" in last_err_msg) else last_err_msg
        raise YouTubeIngestionError(
            f"Failed to download video stream from YouTube ({clean_err}). "
            f"YouTube token throttling or regional restrictions prevented the video download. "
            f"Please try another URL, upload the video file directly in the 'Upload Local Video' tab, or use Offline Demo Mode."
        )

    # ONLY AFTER video successfully exists on disk: Extract 16kHz mono WAV audio
    existing_audios = list(out_dir.glob(f"{meta.video_id}*.wav"))
    if existing_audios and existing_audios[0].stat().st_size > 1000:
        audio_path = existing_audios[0]
        if progress_cb:
            progress_cb(f"Reusing verified audio track ({audio_path.name})")
    else:
        if progress_cb:
            progress_cb("Extracting audio track from downloaded video...")

        ffmpeg_audio_args = [
            '-i', str(video_path),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '16000',
            '-ac', '1',
            str(audio_path)
        ]
        success, err = run_ffmpeg(ffmpeg_audio_args)
        if not success or not audio_path.exists() or audio_path.stat().st_size == 0:
            raise YouTubeIngestionError(f"Audio extraction from downloaded video failed: {err}")

def select_best_subtitle_file(sub_files: List[Path], prefer_hindi: bool = True) -> Optional[Path]:
    """
    Selects the best matching subtitle file from a list of candidates.
    Prioritizes Hindi/Hinglish (hi, hi-Latn) over English (en-IN, en) for Indian/Hindi comedy,
    avoiding poor English auto-translations on Hindi dialogue.
    """
    if not sub_files:
        return None

    def _priority(p: Path) -> int:
        name = p.name.lower()
        if prefer_hindi:
            if ".hi." in name or "_hi." in name or "-hi." in name or "hi-latn" in name:
                return 0
            if "en-in" in name:
                return 1
            if ".en." in name or "_en." in name:
                return 2
        else:
            if "en-in" in name or ".en." in name or "_en." in name:
                return 0
            if ".hi." in name or "_hi." in name:
                return 1
        return 5

    sorted_subs = sorted(sub_files, key=_priority)
    return sorted_subs[0]


    # Check or download YouTube subtitles (.vtt or .srt)
    subtitle_path = None
    existing_subs = list(out_dir.glob(f"{meta.video_id}*.vtt")) + list(out_dir.glob(f"{meta.video_id}*.srt"))
    best_existing = select_best_subtitle_file(existing_subs)
    if best_existing:
        subtitle_path = str(best_existing)
        if progress_cb:
            progress_cb(f"Found YouTube subtitles ({Path(subtitle_path).name})")
    else:
        try:
            sub_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['hi', 'hi-Latn', 'en-IN', 'en'],
                'subtitlesformat': 'vtt/srt/best',
                'outtmpl': str(out_dir / f"{meta.video_id}_sub.%(ext)s"),
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True
            }
            with yt_dlp.YoutubeDL(sub_opts) as ydl:
                ydl.download([url])
            found_subs = list(out_dir.glob(f"{meta.video_id}*.vtt")) + list(out_dir.glob(f"{meta.video_id}*.srt"))
            best_found = select_best_subtitle_file(found_subs)
            if best_found:
                subtitle_path = str(best_found)
                if progress_cb:
                    progress_cb(f"Downloaded YouTube subtitles ({Path(subtitle_path).name})")
        except Exception:
            pass

    return {
        "metadata": meta,
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "subtitle_path": subtitle_path,
        "duration": meta.duration
    }


def ingest_local_video(
    file_path: str,
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Ingests an uploaded local video file, probes duration, and extracts 16kHz WAV audio.
    Provides 100% reliable offline / local video processing without any YouTube dependencies.
    """
    in_path = Path(file_path)
    if not in_path.exists():
        raise YouTubeIngestionError(f"Local video file not found: {file_path}")

    out_dir = output_dir or TEMP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(in_path.stem)
    audio_path = out_dir / f"{safe_name}_audio.wav"

    # Probe duration with OpenCV
    from src.video_analysis import get_video_properties
    try:
        v_props = get_video_properties(str(in_path))
        duration = v_props.duration
    except Exception:
        duration = 30.0

    meta = VideoMetadata(
        video_id=f"local_{safe_name[:10]}",
        title=in_path.stem.replace('_', ' ').title(),
        channel="User Uploaded Video",
        duration=float(duration),
        thumbnail_url="",
        upload_date="",
        description="User uploaded local video file.",
        view_count=0
    )

    # Extract 16kHz mono WAV audio
    ffmpeg_audio_args = [
        '-i', str(in_path),
        '-vn',
        '-acodec', 'pcm_s16le',
        '-ar', '16000',
        '-ac', '1',
        str(audio_path)
    ]
    ok, err = run_ffmpeg(ffmpeg_audio_args)
    if not ok or not audio_path.exists():
        raise YouTubeIngestionError(f"Failed to extract audio from local video: {err}")

    return {
        "metadata": meta,
        "video_path": str(in_path),
        "audio_path": str(audio_path),
        "duration": duration
    }


def create_demo_media(output_dir: Optional[Path] = None, duration: int = 25) -> Dict[str, Any]:
    """
    Generates a synthetic local video and audio clip using FFmpeg for demo and offline testing.
    Emulates an interview/dialogue scene with speech tones and laugh-like audio bursts.
    """
    out_dir = output_dir or TEMP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / "demo_comedy_source.mp4"
    audio_path = out_dir / "demo_comedy_source_audio.wav"

    # Generate synthetic video with audio test tone
    ffmpeg_video_args = [
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size=1280x720:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        str(video_path)
    ]
    ok, err = run_ffmpeg(ffmpeg_video_args)
    if not ok or not video_path.exists():
        raise YouTubeIngestionError(f"Failed to generate synthetic demo video: {err}")

    # Extract 16kHz mono WAV
    ffmpeg_audio_args = [
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path)
    ]
    ok_a, err_a = run_ffmpeg(ffmpeg_audio_args)
    if not ok_a or not audio_path.exists():
        raise YouTubeIngestionError(f"Failed to extract demo audio: {err_a}")

    meta = VideoMetadata(
        video_id="DEMO_COMEDY_01",
        title="Demo Indian Comedy & Panel Show (Hinglish Standup Special)",
        channel="ViralClipper Demo Channel",
        duration=float(duration),
        thumbnail_url="",
        upload_date="20260907",
        description="Offline demo clip for testing candidate detection, zoom effects, captions, and export.",
        view_count=500000
    )

    return {
        "metadata": meta,
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "duration": float(duration)
    }
