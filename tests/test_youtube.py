"""
Tests for Phase 2: YouTube Ingestion, Metadata Extraction, and Audio Extraction.
"""
import pytest
from pathlib import Path
from src.youtube import VideoMetadata, extract_metadata, create_demo_media, YouTubeIngestionError


def test_video_metadata_model():
    meta = VideoMetadata(
        video_id="dQw4w9WgXcQ",
        title="Rick Astley - Never Gonna Give You Up",
        channel="RickAstleyVEVO",
        duration=212.0,
        thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
    )
    assert meta.video_id == "dQw4w9WgXcQ"
    assert meta.duration == 212.0
    assert meta.channel == "RickAstleyVEVO"


def test_invalid_url_raises_error():
    with pytest.raises(YouTubeIngestionError) as exc_info:
        extract_metadata("https://invalid-video-site.com/fake")
    assert "Invalid YouTube URL format" in str(exc_info.value)


def test_create_demo_media_and_audio_extraction(tmp_path):
    media = create_demo_media(output_dir=tmp_path, duration=5)
    assert "video_path" in media
    assert "audio_path" in media
    assert "metadata" in media

    video_p = Path(media["video_path"])
    audio_p = Path(media["audio_path"])

    assert video_p.exists()
    assert video_p.stat().st_size > 0
    assert audio_p.exists()
    assert audio_p.stat().st_size > 0
    assert media["metadata"].duration == 5.0
