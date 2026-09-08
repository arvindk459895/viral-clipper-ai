"""
Tests for Phase 4: Gemini Analysis, Viral Potential Scoring, and Edit Timeline Generation.
"""
from src.clip_scorer import calculate_viral_score, ScoreBreakdown
from src.gemini_analyzer import (
    GeminiClipAnalysis,
    TimelineAction,
    clean_json_response,
    generate_heuristic_analysis
)
from src.candidate_detector import CandidateClip


def test_viral_score_calculation():
    res = calculate_viral_score(100, 100, 100, 100, 100, 100, 100, 100)
    assert res.viral_potential_score == 100
    assert res.opus_virality_score == 99  # Opus caps at 99
    assert res.flow_score == 100
    assert res.value_score == 100
    assert res.trend_score == 100
    assert len(res.hook_insight) > 0

    res2 = calculate_viral_score(80, 90, 90, 80, 70, 80, 90, 80)
    assert res2.viral_potential_score == 84
    assert 1 <= res2.opus_virality_score <= 99
    assert "Estimated relative score" in res2.disclaimer
    assert len(res2.flow_insight) > 0
    assert len(res2.value_insight) > 0
    assert len(res2.trend_insight) > 0


def test_clean_json_response():
    raw_markdown = '''```json
{
  "key": "value"
}
```'''
    cleaned = clean_json_response(raw_markdown)
    assert '"key": "value"' in cleaned
    assert not cleaned.startswith("```")


def test_heuristic_analysis_generation():
    cand = CandidateClip(
        clip_id="cand_01",
        start_time=5.0,
        end_time=25.0,
        duration=20.0,
        hook_start=5.0,
        setup_start=7.0,
        punchline_time=18.0,
        reaction_end=25.0,
        text="Gym trainer ne pucha, goal kya hai? Maine bola, zinda rehna!",
        audio_events=["laughter@18.5s"],
        visual_energy=0.8,
        estimated_score=92.0
    )

    analysis = generate_heuristic_analysis(cand, editing_style="Meme")
    assert isinstance(analysis, GeminiClipAnalysis)
    assert analysis.clip_id == "cand_01"
    assert analysis.viral_score > 70
    assert analysis.humor_type in ["unexpected_answer", "self_deprecating", "roast"]
    assert len(analysis.edit_timeline) >= 4

    actions = [a.action for a in analysis.edit_timeline]
    assert "punch_zoom" in actions
    assert "freeze_frame" in actions


def test_grounded_virality_components():
    from src.clip_scorer import calculate_grounded_virality_components

    # High viral comedy moment with pre-punchline pause, question hook, and laughter
    res = calculate_grounded_virality_components(
        clip_text="Why did you do that? You had one job! And then the whole thing fell down.",
        clip_duration=24.0,
        punchline_time=18.0,
        start_time=2.0,
        end_time=26.0,
        laughter_duration=6.5,
        laughter_burst_count=5,
        laughter_intensity=0.9,
        has_pre_punchline_pause=True,
        has_vocal_peak=True,
        visual_energy=0.85,
        is_sponsor=False
    )
    assert res.viral_potential_score >= 85
    assert res.hook_score >= 80
    assert res.punchline_score >= 85

    # Sponsor ad should have heavily depressed humor and viral scores
    res_sponsor = calculate_grounded_virality_components(
        clip_text="Special thanks to our delivery partner, use code LATENT50 for discount.",
        clip_duration=30.0,
        punchline_time=20.0,
        start_time=0.0,
        end_time=30.0,
        laughter_duration=0.5,
        laughter_burst_count=0,
        laughter_intensity=0.2,
        has_pre_punchline_pause=False,
        has_vocal_peak=False,
        visual_energy=0.5,
        is_sponsor=True
    )
    assert res_sponsor.viral_potential_score < res.viral_potential_score
    assert res_sponsor.humor_score < 60


def test_calibrate_viral_scores():
    from src.clip_scorer import calibrate_viral_scores

    raw = [88.0, 88.0, 85.0, 78.0]
    calibrated = calibrate_viral_scores(raw)
    assert len(calibrated) == 4
    # Highest ranked should have higher score than lowest
    assert calibrated[0] > calibrated[-1]
    # Calibrated scores must be non-flat and strictly descending
    assert calibrated[0] >= calibrated[1] >= calibrated[2] >= calibrated[3]

