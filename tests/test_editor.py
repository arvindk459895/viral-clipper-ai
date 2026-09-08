"""
Tests for Phase 5: Video Effects, Subtitle Generation, and 9:16 Video Rendering.
"""
from pathlib import Path
from src.effects import build_crop_filter, build_zoom_filter, build_flash_filter
from src.captions import format_ass_time, generate_ass_subtitles
from src.transcription import get_demo_transcript
from src.candidate_detector import CandidateClip
from src.gemini_analyzer import generate_heuristic_analysis
from src.editor import render_short_clip
from src.youtube import create_demo_media
from src.video_analysis import get_video_properties


def test_crop_filter_geometry():
    # Center crop (0.5) for 1280x720 to 1080x1920
    crop_f = build_crop_filter(crop_center_x=0.5, in_w=1280, in_h=720, out_w=1080, out_h=1920)
    assert "crop=404:720" in crop_f or "crop=405:720" in crop_f
    assert "scale=1080:1920" in crop_f


def test_zoom_filter_expression():
    zoom_f = build_zoom_filter(start_t=5.0, end_t=25.0, punch_t=18.0)
    assert "between(t," in zoom_f
    assert "scale=1080:1920" in zoom_f


def test_ass_time_formatting():
    assert format_ass_time(0.0) == "0:00:00.00"
    assert format_ass_time(65.45) == "0:01:05.45"
    assert format_ass_time(3600.0) == "1:00:00.00"


def test_generate_ass_subtitles(tmp_path):
    transcript = get_demo_transcript(25.0)
    ass_out = tmp_path / "test_subs.ass"
    generate_ass_subtitles(transcript.segments, clip_start=0.0, clip_end=15.0, output_path=ass_out)
    assert ass_out.exists()
    content = ass_out.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Dialogue:" in content


def test_top_header_banner_generation(tmp_path):
    transcript = get_demo_transcript(25.0)
    ass_out = tmp_path / "test_banner.ass"
    generate_ass_subtitles(
        transcript.segments,
        clip_start=0.0,
        clip_end=20.0,
        output_path=ass_out,
        top_header_text="WAIT FOR THE END 😂"
    )
    assert ass_out.exists()
    content = ass_out.read_text(encoding="utf-8")
    assert "Style: TopHeader" in content
    assert "Dialogue: 1,0:00:00.00,0:00:20.00,TopHeader,,0,0,0,,WAIT FOR THE END 😂" in content


def test_render_short_clip_end_to_end(tmp_path):
    # Create 5s demo video
    media = create_demo_media(output_dir=tmp_path, duration=5)
    transcript = get_demo_transcript(5.0)

    candidate = CandidateClip(
        clip_id="test_clip_01",
        start_time=0.5,
        end_time=4.5,
        duration=4.0,
        hook_start=0.5,
        setup_start=1.0,
        punchline_time=3.0,
        reaction_end=4.5,
        text="Toh maine bola bhai, workout chalu karte hain kal se.",
        visual_energy=0.75,
        estimated_score=90.0
    )

    analysis = generate_heuristic_analysis(candidate, editing_style="Modern")
    out_mp4 = tmp_path / "rendered_short.mp4"

    res = render_short_clip(
        video_path=media["video_path"],
        audio_path=media["audio_path"],
        candidate=candidate,
        analysis=analysis,
        transcript_segments=transcript.segments,
        editing_style="Modern",
        output_path=out_mp4
    )

    assert Path(res["output_path"]).exists()
    assert Path(res["output_path"]).stat().st_size > 0
    props = get_video_properties(res["output_path"])
    assert props.width == 1080
    assert props.height == 1920
    assert props.duration >= 3.5
