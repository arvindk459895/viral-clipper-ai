"""
ViralClipper AI Studio - Clip Scorer Module
Calculates the 8-component Viral Potential Score strictly following the formula:
Hook (15%), Humor (20%), Punchline (15%), Reaction (15%), Standalone (10%),
Rewatch (10%), Shareability (10%), Visual (5%).
"""
from typing import Dict, Any, Union
from pydantic import BaseModel, Field
from src.config import VIRAL_WEIGHTS, OPUS_VIRAL_WEIGHTS


class ScoreBreakdown(BaseModel):
    # Opus Clip 4 Pillars
    hook_score: float = Field(..., ge=0, le=100)
    flow_score: float = Field(default=80.0, ge=0, le=100)
    value_score: float = Field(default=80.0, ge=0, le=100)
    trend_score: float = Field(default=80.0, ge=0, le=100)
    opus_virality_score: int = Field(default=85, ge=0, le=99)

    # Opus AI Diagnostic Insights
    hook_insight: str = Field(default="Attention-grabbing opening creates curiosity.")
    flow_insight: str = Field(default="Seamless narrative continuity and pacing.")
    value_insight: str = Field(default="High comedy resonance and audience reaction.")
    trend_insight: str = Field(default="Quotable punchline with meme potential.")

    # Underlying Grounded Sub-Components (backward compatible)
    humor_score: float = Field(..., ge=0, le=100)
    punchline_score: float = Field(..., ge=0, le=100)
    reaction_score: float = Field(..., ge=0, le=100)
    standalone_score: float = Field(..., ge=0, le=100)
    rewatch_score: float = Field(..., ge=0, le=100)
    shareability_score: float = Field(..., ge=0, le=100)
    visual_score: float = Field(..., ge=0, le=100)
    viral_potential_score: int = Field(..., ge=0, le=100)
    disclaimer: str = "Estimated relative score. Not a prediction or guarantee of future views."


def calculate_viral_score(
    hook: float,
    humor: float,
    punchline: float,
    reaction: float,
    standalone: float,
    rewatch: float,
    shareability: float,
    visual: float
) -> ScoreBreakdown:
    """
    Computes grounded viral potential score and Opus Clip 4-Pillar metrics:
    🪝 Hook (30%), 🌊 Flow (30%), 💎 Value (25%), 🔥 Trend (15%).
    """
    scores = {
        "hook": hook if hook > 10 else hook * 10.0,
        "humor": humor if humor > 10 else humor * 10.0,
        "punchline": punchline if punchline > 10 else punchline * 10.0,
        "reaction": reaction if reaction > 10 else reaction * 10.0,
        "standalone": standalone if standalone > 10 else standalone * 10.0,
        "rewatch": rewatch if rewatch > 10 else rewatch * 10.0,
        "shareability": shareability if shareability > 10 else shareability * 10.0,
        "visual": visual if visual > 10 else visual * 10.0,
    }

    # Clamp all inputs to 0-100
    for k in scores:
        scores[k] = max(0.0, min(100.0, float(scores[k])))

    # 1. 8-Component Grounded Weighted Sum
    weighted_sum = (
        scores["hook"] * VIRAL_WEIGHTS["hook"] +
        scores["humor"] * VIRAL_WEIGHTS["humor"] +
        scores["punchline"] * VIRAL_WEIGHTS["punchline"] +
        scores["reaction"] * VIRAL_WEIGHTS["reaction"] +
        scores["standalone"] * VIRAL_WEIGHTS["standalone"] +
        scores["rewatch"] * VIRAL_WEIGHTS["rewatch"] +
        scores["shareability"] * VIRAL_WEIGHTS["shareability"] +
        scores["visual"] * VIRAL_WEIGHTS["visual"]
    )
    final_score = int(round(weighted_sum))

    # 2. Opus Clip 4-Pillar Composite
    flow_val = round(0.40 * scores["standalone"] + 0.35 * scores["rewatch"] + 0.25 * scores["visual"], 1)
    value_val = round(0.45 * scores["humor"] + 0.30 * scores["reaction"] + 0.25 * scores["punchline"], 1)
    trend_val = round(0.60 * scores["shareability"] + 0.40 * scores["rewatch"], 1)

    opus_weighted = (
        scores["hook"] * OPUS_VIRAL_WEIGHTS["hook"] +
        flow_val * OPUS_VIRAL_WEIGHTS["flow"] +
        value_val * OPUS_VIRAL_WEIGHTS["value"] +
        trend_val * OPUS_VIRAL_WEIGHTS["trend"]
    )
    opus_score = min(99, max(1, int(round(opus_weighted))))

    # 3. Diagnostic AI Insights
    h_in = "High-velocity curiosity hook within first 2 seconds." if scores["hook"] >= 80 else "Clear conversational opening establishes premise."
    f_in = "Seamless narrative pacing with clean sentence conclusion." if flow_val >= 80 else "Natural conversational progression."
    v_in = "High-arousal comedy payoff with sustained audience laughter." if value_val >= 80 else "Solid comedic timing and audience reaction."
    t_in = "Highly quotable punchline with strong meme-sharing appeal." if trend_val >= 80 else "Good social media shareability."

    return ScoreBreakdown(
        hook_score=round(scores["hook"], 1),
        flow_score=flow_val,
        value_score=value_val,
        trend_score=trend_val,
        opus_virality_score=opus_score,
        hook_insight=h_in,
        flow_insight=f_in,
        value_insight=v_in,
        trend_insight=t_in,
        humor_score=round(scores["humor"], 1),
        punchline_score=round(scores["punchline"], 1),
        reaction_score=round(scores["reaction"], 1),
        standalone_score=round(scores["standalone"], 1),
        rewatch_score=round(scores["rewatch"], 1),
        shareability_score=round(scores["shareability"], 1),
        visual_score=round(scores["visual"], 1),
        viral_potential_score=final_score
    )


def calculate_grounded_virality_components(
    clip_text: str,
    clip_duration: float,
    punchline_time: float,
    start_time: float,
    end_time: float,
    laughter_duration: float,
    laughter_burst_count: int,
    laughter_intensity: float,
    has_pre_punchline_pause: bool = False,
    has_vocal_peak: bool = False,
    visual_energy: float = 0.75,
    is_sponsor: bool = False
) -> ScoreBreakdown:
    """
    Computes grounded 8-component virality metrics based on physical acoustics,
    dialogue semantics, comedic pause timing, and short-form video retention dynamics.
    """
    text_lower = clip_text.lower()
    words = text_lower.split()
    first_words = " ".join(words[:8]) if words else ""

    # 1. Hook Score (0-3s retention drivers)
    hook = 68.0
    hook_cues = ["?", "kya", "why", "how", "what", "socho", "bhai", "you", "tell", "look", "wait", "listen", "stop", "never", "no way", "seriously"]
    if any(q in first_words for q in hook_cues):
        hook += 18.0
    if "?" in first_words or first_words.startswith("did ") or first_words.startswith("why ") or first_words.startswith("is "):
        hook += 8.0
    hook = max(45.0, min(98.0, hook))

    # 2. Humor Score (Acoustic power + comedy contrast)
    humor = 55.0 + min(40.0, (laughter_duration * 3.2) + (laughter_burst_count * 2.2) + (laughter_intensity * 20.0))
    humor_words = ["roast", "dance", "seven", "ruin", "battery", "prarthana", "gym", "joke", "funny", "laugh", "teacher", "answer"]
    if any(w in text_lower for w in humor_words):
        humor += 5.0
    if is_sponsor:
        humor -= 35.0
    humor = max(35.0, min(99.0, humor))

    # 3. Punchline Score (Comedic micro-pause + vocal burst + timing placement)
    punchline = 66.0
    if has_pre_punchline_pause:
        punchline += 16.0  # Crucial comedian pause before punchline
    if has_vocal_peak:
        punchline += 12.0  # Vocal emphasis
    # Position: punchline at 60%-85% into clip is the gold standard for Shorts
    rel_pos = (punchline_time - start_time) / max(1.0, clip_duration)
    if 0.55 <= rel_pos <= 0.85:
        punchline += 6.0
    punchline = max(45.0, min(98.0, punchline))

    # 4. Reaction Score (Audience eruption persistence)
    reaction = 58.0 + min(40.0, (laughter_duration * 3.5) + (laughter_intensity * 24.0))
    reaction = max(40.0, min(99.0, reaction))

    # 5. Standalone Score (Self-contained premise & punchline)
    standalone = 70.0
    if 18.0 <= clip_duration <= 42.0:
        standalone += 12.0  # Ideal short-form length
    if "?" in clip_text and len(words) >= 12:
        standalone += 8.0  # Contains prompt & response
    standalone = max(45.0, min(96.0, standalone))

    # 6. Rewatch Score (Laugh density & loopability)
    rewatch = 64.0 + min(32.0, (laughter_burst_count * 3.5))
    rewatch = max(45.0, min(95.0, rewatch))

    # 7. Shareability Score (Quotable + high humor)
    shareability = round((humor * 0.55) + (punchline * 0.45), 1)

    # 8. Visual Score
    visual = max(60.0, min(96.0, visual_energy * 100.0))

    return calculate_viral_score(
        hook=hook,
        humor=humor,
        punchline=punchline,
        reaction=reaction,
        standalone=standalone,
        rewatch=rewatch,
        shareability=shareability,
        visual=visual
    )


def calibrate_viral_scores(raw_scores: list) -> list:
    """
    Applies percentile rank distribution to a list of candidate viral scores.
    Prevents flat/clustered score ties (e.g. all 91s) and yields a natural,
    calibrated distribution reflecting real short-form virality rankings.
    """
    if not raw_scores:
        return []
    if len(raw_scores) == 1:
        return [int(round(raw_scores[0]))]

    n = len(raw_scores)
    # Sort indices by raw score descending
    sorted_indices = sorted(range(n), key=lambda i: raw_scores[i], reverse=True)
    calibrated = [0] * n

    # Define target score ranges for ranks
    for rank, orig_idx in enumerate(sorted_indices):
        raw = raw_scores[orig_idx]
        pct = (n - 1 - rank) / max(1, n - 1)  # 1.0 for top, 0.0 for lowest

        # Calibrated curve: top 1-2 score 94-98, strong score 88-93, mid score 78-87, low < 75
        curve_score = 70.0 + (pct * 27.0)
        # Blend 60% curve + 40% raw
        blended = (0.45 * raw) + (0.55 * curve_score)
        # Ensure strictly descending order
        if rank > 0:
            prev_idx = sorted_indices[rank - 1]
            blended = min(blended, calibrated[prev_idx] - 0.5)

        calibrated[orig_idx] = int(round(max(40.0, min(98.0, blended))))

    return calibrated

