"""
Unit and integration tests for YouTube Channel Connection & 1-Click Shorts Scheduler.
"""
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from src.youtube_publisher import (
    YouTubeChannelManager,
    ChannelInfo,
    format_youtube_title,
    format_youtube_tags,
    schedule_youtube_short,
    get_scheduled_shorts,
    delete_scheduled_short
)
from src.config import TEMP_DIR, OUTPUTS_DIR


def test_format_youtube_title():
    # Enforces #Shorts appended if missing
    t1 = format_youtube_title("When gym trainer asks for goals")
    assert "#Shorts" in t1
    assert t1.startswith("When gym trainer asks for goals")

    # Does not duplicate #Shorts if already present
    t2 = format_youtube_title("Hilarious moment #Shorts")
    assert t2 == "Hilarious moment #Shorts"

    # Enforces <= 100 chars
    long_title = "A" * 120
    t3 = format_youtube_title(long_title)
    assert len(t3) <= 100
    assert "#Shorts" in t3


def test_format_youtube_tags():
    # Removes '#' prefix, deduplicates, and splits by commas/spaces
    raw = ["#comedy", "standup comedy", "#funny", "comedy", "viral", "#shorts"]
    tags = format_youtube_tags(raw)
    assert "comedy" in tags
    assert "standup comedy" in tags
    assert "funny" in tags
    assert "viral" in tags
    assert "shorts" in tags
    assert len(tags) == 5  # "comedy" deduplicated

    # Works with comma-separated string
    str_tags = format_youtube_tags("comedy, desi humor, #jokes, laughs")
    assert "jokes" in str_tags
    assert "desi humor" in str_tags


def test_youtube_channel_manager_demo_mode(tmp_path):
    token_file = tmp_path / "token.json"
    secrets_file = tmp_path / "secrets.json"
    mgr = YouTubeChannelManager(token_path=token_file, client_secrets_path=secrets_file)

    # Disconnected initially (if demo file doesn't exist)
    mgr.disconnect()
    assert not mgr.is_connected()
    assert mgr.get_channel_info() is None

    # Connect demo mode
    info = mgr.connect_demo_mode(channel_name="Akash Comedy Central", handle="@AkashComedy")
    assert mgr.is_connected()
    assert mgr.is_demo_mode()
    assert info.title == "Akash Comedy Central"
    assert info.handle == "@AkashComedy"
    assert info.subscriber_count == 48500

    # Retrieve info
    retrieved = mgr.get_channel_info()
    assert retrieved is not None
    assert retrieved.title == "Akash Comedy Central"

    # Disconnect
    mgr.disconnect()
    assert not mgr.is_connected()


def test_schedule_youtube_short_demo_mode(tmp_path):
    # Setup dummy video file
    dummy_vid = tmp_path / "test_short.mp4"
    dummy_vid.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"A" * 1024)

    # Setup dummy thumbnail
    dummy_thumb = tmp_path / "test_thumb.jpg"
    dummy_thumb.write_bytes(b"\xff\xd8\xff\xe0" + b"B" * 512)

    # Channel manager in demo mode
    mgr = YouTubeChannelManager()
    mgr.connect_demo_mode(channel_name="Samay Raina Fan Studio", handle="@SamayClips")

    # Target release 24 hours from now
    target_time = datetime.now() + timedelta(hours=24)

    result = schedule_youtube_short(
        video_path=dummy_vid,
        title="Mard hoon main dialogue roast",
        description="Samay Raina iconic moment.\nOriginal Source: Still Alive Special",
        tags=["samay raina", "comedy", "standup", "viral"],
        hashtags=["#Shorts", "#SamayRaina", "#Comedy"],
        publish_at=target_time,
        privacy_status="private",
        thumbnail_path=dummy_thumb,
        channel_manager=mgr
    )

    assert result["title"].endswith("#Shorts")
    assert len(result["video_id"]) == 11
    assert "https://youtube.com/shorts/" in result["youtube_url"]
    assert "https://studio.youtube.com/video/" in result["studio_url"]
    assert result["status"] == "SCHEDULED"
    assert result["scheduled_time_utc"] is not None
    assert result["channel_handle"] == "@SamayClips"

    # Verify queue record persistence
    queue = get_scheduled_shorts()
    matching = [item for item in queue if item["video_id"] == result["video_id"]]
    assert len(matching) == 1
    assert matching[0]["title"] == result["title"]

    # Test queue deletion
    deleted = delete_scheduled_short(result["video_id"])
    assert deleted is True
    assert not any(item["video_id"] == result["video_id"] for item in get_scheduled_shorts())
