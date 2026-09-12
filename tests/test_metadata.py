"""
Tests for Phase 8: Metadata Generation (Titles, Description, Hashtags) and Thumbnails.
"""
from pathlib import Path
from src.candidate_detector import CandidateClip
from src.gemini_analyzer import GeminiClipAnalysis
from src.metadata import generate_clip_metadata, ClipMetadata
from src.thumbnail import generate_thumbnails, ThumbnailResult
from src.youtube import create_demo_media


def test_metadata_generation():
    candidate = CandidateClip(
        clip_id="clip_meta_01",
        start_time=5.0,
        end_time=25.0,
        duration=20.0,
        hook_start=5.0,
        setup_start=7.0,
        punchline_time=18.0,
        reaction_end=25.0,
        text="Gym trainer ne pucha, goal kya hai? Maine bola, zinda rehna!",
        visual_energy=0.8,
        estimated_score=92.0
    )

    analysis = GeminiClipAnalysis(
        clip_id="clip_meta_01", start_time=5.0, end_time=25.0, setup="s", punchline="p", reaction="r",
        hook_score=90, humor_score=92, punchline_score=90, reaction_score=85, standalone_score=85,
        rewatch_score=80, shareability_score=85, visual_score=80, viral_score=88,
        humor_type="self_deprecating", reaction_type="laugh", editing_style="Meme",
        reason="Hilarious punchline about gym motivation."
    )

    meta = generate_clip_metadata(candidate, analysis, channel_name="Test Comedy Club")
    assert isinstance(meta, ClipMetadata)
    assert len(meta.titles) == 3
    assert all(20 <= len(t) <= 100 for t in meta.titles)
    assert 5 <= len(meta.hashtags) <= 15
    assert "#Shorts" in meta.hashtags
    assert "Rights Notice" in meta.description
    assert "Copyright and monetization decisions" in meta.description


def test_thumbnail_generation(tmp_path):
    media = create_demo_media(output_dir=tmp_path, duration=5)
    candidate = CandidateClip(
        clip_id="clip_thumb_01",
        start_time=0.5,
        end_time=4.5,
        duration=4.0,
        hook_start=0.5,
        setup_start=1.0,
        punchline_time=2.5,
        reaction_end=4.5,
        text="Sample joke punchline",
        visual_energy=0.7,
        estimated_score=88.0
    )

    analysis = GeminiClipAnalysis(
        clip_id="clip_thumb_01", start_time=0.5, end_time=4.5, setup="s", punchline="p", reaction="r",
        hook_score=88, humor_score=88, punchline_score=88, reaction_score=88, standalone_score=85,
        rewatch_score=80, shareability_score=85, visual_score=80, viral_score=86,
        humor_type="unexpected_answer", reaction_type="disbelief"
    )

    res = generate_thumbnails(media["video_path"], candidate, analysis, output_dir=tmp_path)
    assert isinstance(res, ThumbnailResult)
    assert Path(res.option_1_path).exists()
    assert Path(res.option_2_path).exists()
    assert Path(res.option_1_path).stat().st_size > 0
    assert Path(res.option_2_path).stat().st_size > 0
    assert len(res.hook_text_1) > 0
    assert len(res.hook_text_2) > 0
