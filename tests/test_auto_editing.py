"""
Tests for Phase 7: Automatic Joke-to-Meme Editing and Safe Compositing.
"""
from pathlib import Path
from src.gemini_analyzer import GeminiClipAnalysis
from src.meme_manager import AssetLibraryManager
from src.meme_selector import select_contextual_meme, MemePlacement
from src.candidate_detector import CandidateClip
from src.transcription import get_demo_transcript
from src.youtube import create_demo_media
from src.editor import render_short_clip


def test_joke_to_meme_selection(tmp_path):
    mgr = AssetLibraryManager(library_path=tmp_path / "lib.json")

    # 1. Clean style should never insert memes
    analysis_clean = GeminiClipAnalysis(
        clip_id="c1", start_time=0.0, end_time=15.0, setup="s", punchline="p", reaction="r",
        hook_score=90, humor_score=90, punchline_score=90, reaction_score=90, standalone_score=90,
        rewatch_score=90, shareability_score=90, visual_score=90, viral_score=90,
        humor_type="roast", editing_style="Clean"
    )
    assert select_contextual_meme(analysis_clean, mgr, editing_style="Clean") is None

    # 2. Roast humor selects roast/funny meme
    analysis_roast = GeminiClipAnalysis(
        clip_id="c2", start_time=0.0, end_time=15.0, setup="s", punchline="p", reaction="r",
        hook_score=90, humor_score=90, punchline_score=90, reaction_score=90, standalone_score=90,
        rewatch_score=90, shareability_score=90, visual_score=90, viral_score=90,
        humor_type="roast", editing_style="Meme"
    )
    meme_roast = select_contextual_meme(analysis_roast, mgr, editing_style="Meme")
    assert meme_roast is not None
    assert isinstance(meme_roast, MemePlacement)
    assert 1.0 <= meme_roast.duration <= 2.0
    assert meme_roast.position == "bottom_right"

    # 3. Awkward humor selects awkward meme
    analysis_awkward = GeminiClipAnalysis(
        clip_id="c3", start_time=0.0, end_time=15.0, setup="s", punchline="p", reaction="r",
        hook_score=85, humor_score=85, punchline_score=85, reaction_score=85, standalone_score=85,
        rewatch_score=85, shareability_score=85, visual_score=85, viral_score=85,
        humor_type="awkward", editing_style="Meme"
    )
    meme_awk = select_contextual_meme(analysis_awkward, mgr, editing_style="Meme")
    assert meme_awk is not None
    assert "awkward" in meme_awk.asset_id.lower() or "pause" in meme_awk.asset_id.lower() or "dead" in meme_awk.asset_id.lower()


def test_render_short_clip_with_meme_overlay(tmp_path):
    media = create_demo_media(output_dir=tmp_path, duration=5)
    transcript = get_demo_transcript(5.0)
    mgr = AssetLibraryManager(library_path=tmp_path / "lib.json")

    candidate = CandidateClip(
        clip_id="meme_clip_01",
        start_time=0.5,
        end_time=4.5,
        duration=4.0,
        hook_start=0.5,
        setup_start=1.0,
        punchline_time=2.5,
        reaction_end=4.5,
        text="Gym trainer ne pucha, goal kya hai? Maine bola, zinda rehna!",
        visual_energy=0.8,
        estimated_score=94.0
    )

    analysis = GeminiClipAnalysis(
        clip_id="meme_clip_01", start_time=0.5, end_time=4.5, setup="s", punchline="p", reaction="r",
        hook_score=92, humor_score=94, punchline_score=95, reaction_score=90, standalone_score=88,
        rewatch_score=85, shareability_score=90, visual_score=80, viral_score=91,
        humor_type="self_deprecating", editing_style="Meme"
    )

    out_mp4 = tmp_path / "meme_short_output.mp4"
    res = render_short_clip(
        video_path=media["video_path"],
        audio_path=media["audio_path"],
        candidate=candidate,
        analysis=analysis,
        transcript_segments=transcript.segments,
        editing_style="Meme",
        output_path=out_mp4,
        asset_manager=mgr
    )

    assert Path(res["output_path"]).exists()
    assert Path(res["output_path"]).stat().st_size > 0
    assert res["meme_used"] != "None"
