"""
Tests for Faceless AI Commentary Mode:
AI Voice synthesis, Originality Commentary Engine, Quality Validation,
Original Visual Generation, Originality & Compliance Auditing, and Video Assembly.
"""
from pathlib import Path
import pytest

from src.ai_voice import generate_ai_voice, AVAILABLE_VOICE_STYLES, VOICE_PERSONAS
from src.commentary_engine import (
    generate_heuristic_commentary,
    clean_banned_phrases,
    BANNED_GENERIC_PHRASES,
    CommentaryScript
)
from src.commentary_validator import (
    heuristic_validate_commentary,
    validate_commentary_quality
)
from src.visual_generator import (
    generate_editorial_title_card,
    generate_cartoon_reaction,
    generate_diagram_card,
    generate_faceless_visual_package
)
from src.originality_report import generate_originality_report
from src.candidate_detector import CandidateClip
from src.faceless_editor import render_faceless_commentary_short
from src.youtube import create_demo_media
from src.transcription import get_demo_transcript


def test_ai_voice_synthesis_and_metadata(tmp_path):
    """Verifies that neural AI voice synthesis generates audio with accurate metadata and zero cloning."""
    out_mp3 = tmp_path / "test_voice.mp3"
    res = generate_ai_voice(
        text="Observe how quickly this everyday question turns into absolute comedy.",
        voice_style="comedic",
        output_path=out_mp3,
        clip_id="test_clip"
    )

    assert Path(res["audio_path"]).exists()
    assert res["duration_sec"] > 1.0
    assert res["voice_provider"].startswith("edge-tts")
    assert res["voice_id"] == VOICE_PERSONAS["comedic"]["voice_id"]
    assert res["is_synthetic"] is True
    assert res["is_clone"] is False
    assert "generation_timestamp" in res


def test_ai_voice_supported_styles():
    """Verifies all required voice personas are registered."""
    for style in ["energetic", "comedic", "sarcastic", "documentary", "calm", "female", "male", "neutral"]:
        assert style in AVAILABLE_VOICE_STYLES
        assert "voice_id" in VOICE_PERSONAS[style]


def test_banned_generic_phrases_filter():
    """Verifies that generic fluff like 'that was crazy' or 'lol' is completely stripped."""
    dirty_text = "That was crazy! The punchline hit so hard lol, wait till you see this."
    cleaned = clean_banned_phrases(dirty_text)
    for banned in BANNED_GENERIC_PHRASES:
        assert banned not in cleaned.lower()


def test_heuristic_commentary_generation():
    """Verifies that the originality engine generates substantive 4-part comedic commentary."""
    cand = CandidateClip(
        clip_id="cand_test",
        start_time=5.0,
        end_time=25.0,
        duration=20.0,
        hook_start=5.0,
        setup_start=7.0,
        punchline_time=18.0,
        reaction_end=25.0,
        text="Gym trainer asked what is your goal? I said just staying alive!",
        audio_events=["laughter@18.5s"],
        visual_energy=0.8,
        estimated_score=92.0
    )
    script = generate_heuristic_commentary(cand, humor_type="self_deprecating")

    assert len(script.hook) > 15
    assert len(script.context_commentary) > 20
    assert len(script.analysis_reaction) > 20
    assert len(script.conclusion) > 15
    assert len(script.editorial_angle) > 5
    # Must NOT contain generic fluff
    for banned in BANNED_GENERIC_PHRASES:
        assert banned not in script.hook.lower()
        assert banned not in script.context_commentary.lower()
        assert banned not in script.analysis_reaction.lower()


def test_commentary_quality_validation():
    """Verifies quality check scores and rejects weak or generic commentary."""
    good_script = CommentaryScript(
        hook="Notice how an everyday conversation turns into an unexpected psychological test.",
        context_commentary="The setup establishes high expectations, but the contestant completely subverts the question.",
        analysis_reaction="The humor works because of the brutal contrast between ambition and basic survival.",
        conclusion="A classic demonstration of self-deprecating subversion catching everyone off guard.",
        editorial_angle="Subversion of aspirational fitness culture",
        humor_breakdown="Contrast between fitness expectations and relatable laziness"
    )
    res_good = heuristic_validate_commentary(good_script, threshold=70)
    assert res_good.passed is True
    assert res_good.overall_score >= 70
    assert len(res_good.banned_phrases_found) == 0

    bad_script = CommentaryScript(
        hook="That was crazy wow!",
        context_commentary="So funny lol.",
        analysis_reaction="LMAO this is wild.",
        conclusion="OMG subscribe.",
        editorial_angle="fluff",
        humor_breakdown="fluff"
    )
    res_bad = heuristic_validate_commentary(bad_script, threshold=70)
    assert res_bad.passed is False
    assert len(res_bad.banned_phrases_found) > 0


def test_visual_generator_outputs(tmp_path):
    """Verifies generation of original cartoon reactions, title cards, and diagrams."""
    title_p = tmp_path / "title_card.png"
    generate_editorial_title_card("Why This Joke Broke the Room", "Comedic Subversion Analysis", title_p)
    assert title_p.exists()
    assert title_p.stat().st_size > 1000

    react_p = tmp_path / "reaction.png"
    generate_cartoon_reaction("laugh", "Pure Timing", react_p)
    assert react_p.exists()

    diag_p = tmp_path / "diagram.png"
    generate_diagram_card("The Assumed Goal", "Staying Alive", diag_p)
    assert diag_p.exists()


def test_originality_report_metrics():
    """Verifies quantitative editorial breakdown and internal risk assessments."""
    rep = generate_originality_report(
        source_duration_sec=14.0,
        ai_commentary_sec=12.0,
        ai_visuals_sec=8.0,
        editorial_purpose="Structural subversion and audience reaction timing analysis"
    )
    assert rep.source_footage_sec == 14.0
    assert rep.total_duration_sec == 34.0
    assert rep.originality_assessment == "STRONG"
    assert rep.reuse_risk == "LOW"
    assert rep.copyright_risk == "LOW"
    assert rep.youtube_disclosure_required is True
    assert "YouTube Policy Notice" in rep.youtube_disclosure_reminder
    assert "CRITICAL DISCLAIMER" in rep.disclaimer


def test_end_to_end_faceless_render(tmp_path):
    """Renders a complete Faceless AI Commentary Short using demo media."""
    media = create_demo_media(output_dir=tmp_path, duration=15)
    transcript = get_demo_transcript(15.0)

    cand = CandidateClip(
        clip_id="demo_faceless_01",
        start_time=1.0,
        end_time=12.0,
        duration=11.0,
        hook_start=1.0,
        setup_start=2.0,
        punchline_time=8.0,
        reaction_end=12.0,
        text="Toh maine gym join kiya, trainer bola goal kya hai? Maine bola zinda rehna!",
        audio_events=["laughter@8.5s"],
        visual_energy=0.85,
        estimated_score=94.0
    )
    script = generate_heuristic_commentary(cand)

    out_mp4 = tmp_path / "test_faceless_output.mp4"
    res = render_faceless_commentary_short(
        video_path=media["video_path"],
        audio_path=media["audio_path"],
        candidate=cand,
        script=script,
        transcript_segments=transcript.segments,
        voice_style="comedic",
        output_path=out_mp4,
        top_header_text="WHY TIMING MATTERS 😂"
    )

    assert Path(res["output_path"]).exists()
    assert Path(res["output_path"]).stat().st_size > 50000
    assert res["mode"] == "faceless_commentary"
    assert res["originality_report"]["originality_assessment"] in ["STRONG", "MODERATE"]


def test_hinglish_commentary_detection_and_generation():
    """Verifies that Hindi/Hinglish input automatically triggers natural conversational Hinglish commentary."""
    from src.commentary_engine import is_hindi_or_hinglish
    cand = CandidateClip(
        clip_id="cand_hinglish",
        start_time=2.0,
        end_time=22.0,
        duration=20.0,
        hook_start=2.0,
        setup_start=4.0,
        punchline_time=16.0,
        reaction_end=22.0,
        text="Toh maine gym join kiya, trainer bola goal kya hai? Maine bola zinda rehna!",
        audio_events=["laughter@16.5s"],
        visual_energy=0.8,
        estimated_score=95.0
    )
    assert is_hindi_or_hinglish(cand.text) is True
    script = generate_heuristic_commentary(cand, language="auto")
    assert script.language == "hinglish"
    assert any(w in script.hook.lower() for w in ["dekho", "bhai", "sawal", "kaise"])
    assert script.hook_emotion in ["excited", "cheerful"]
    assert script.analysis_emotion in ["cheerful", "laugh"]


def test_emotional_neural_voice_synthesis(tmp_path):
    """Verifies synthesis with emotion styles (laugh, sad, loved) and Indian neural voice resolution."""
    from src.ai_voice import resolve_voice_profile
    profile = resolve_voice_profile("energetic", language="hinglish")
    assert "IN" in profile["locale"] or "hi-" in profile["locale"]

    out_file = tmp_path / "test_laugh_voice.mp3"
    res = generate_ai_voice(
        text="Bhai dekho kya zabardast comeback diya hai!",
        voice_style="comedic",
        emotion="laugh",
        language="hinglish",
        output_path=out_file
    )
    assert Path(res["audio_path"]).exists()
    assert res["duration_sec"] > 0.5
    assert res["emotion"] == "laugh"


def test_wrapped_diagram_text_never_overflows(tmp_path):
    """Verifies that lengthy premise and subversion strings wrap cleanly with zero error."""
    out_png = tmp_path / "wrapped_card.png"
    long_premise = "Set within a high-stakes roast dynamic, the performer introduces an ordinary premise before taking an unexpected turn."
    long_subversion = "Notice the subtle escalation in the comedian's cadence right before dropping the punchline and catching the entire room off guard."
    generate_diagram_card(long_premise, long_subversion, out_png)
    assert out_png.exists()
    assert out_png.stat().st_size > 10000
