"""
ViralClipper AI Studio - Gemini Analysis Module
Integrates with the official Google Gemini SDK (google-genai) to perform deep
comedy understanding, structural breakdown, and timeline generation.
"""
import json
import os
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.config import DEFAULT_GEMINI_MODEL
from src.clip_scorer import calculate_viral_score, ScoreBreakdown
from src.candidate_detector import CandidateClip


class TimelineAction(BaseModel):
    time: float = Field(..., description="Timestamp in seconds relative to video start")
    action: str = Field(..., description="zoom_in, punch_zoom, freeze_frame, reaction_asset, subtitle_emphasis, flash, shake, sound_effect")
    strength: Optional[float] = Field(0.15, description="Zoom/shake intensity (e.g. 0.1 to 0.3)")
    duration: Optional[float] = Field(1.0, description="Duration of effect in seconds")
    asset_tag: Optional[str] = Field(None, description="Tag for meme or SFX matching")


class GeminiClipAnalysis(BaseModel):
    clip_id: str = "clip_01"
    start_time: float
    end_time: float
    setup: str
    punchline: str
    reaction: str

    hook_score: float = Field(..., ge=0, le=100)
    flow_score: float = Field(default=80.0, ge=0, le=100)
    value_score: float = Field(default=80.0, ge=0, le=100)
    trend_score: float = Field(default=80.0, ge=0, le=100)
    opus_virality_score: int = Field(default=85, ge=0, le=99)

    hook_insight: str = ""
    flow_insight: str = ""
    value_insight: str = ""
    trend_insight: str = ""

    humor_score: float = Field(..., ge=0, le=100)
    punchline_score: float = Field(..., ge=0, le=100)
    reaction_score: float = Field(..., ge=0, le=100)
    standalone_score: float = Field(..., ge=0, le=100)
    rewatch_score: float = Field(..., ge=0, le=100)
    shareability_score: float = Field(..., ge=0, le=100)
    visual_score: float = Field(..., ge=0, le=100)

    viral_score: int = Field(..., ge=0, le=100)

    humor_type: str = "unexpected_answer"
    reaction_type: str = "disbelief"
    editing_style: str = "Meme"

    recommended_effects: List[str] = Field(default_factory=list)
    recommended_asset_tags: List[str] = Field(default_factory=list)

    reason: str = ""
    edit_timeline: List[TimelineAction] = Field(default_factory=list)
    analysis_engine: str = "Local Heuristic Engine"


def clean_json_response(text: str) -> str:
    """Strips markdown code fences and extraneous text from LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def generate_heuristic_analysis(candidate: CandidateClip, editing_style: str = "Meme") -> GeminiClipAnalysis:
    """
    High-quality heuristic comedy analyzer used when running in demo mode
    or when testing without a live Gemini API key.
    """
    # Dynamic comedy cues and humor classification
    text_lower = candidate.text.lower()
    humor_type = "unexpected_answer"
    reaction_type = "laugh"
    recommended_tags = ["laugh", "funny"]
    effects = ["punch_zoom", "freeze_frame", "subtle_sfx"]

    if "gym" in text_lower or "workout" in text_lower or "prarthana" in text_lower:
        humor_type = "self_deprecating"
        reaction_type = "laugh"
        recommended_tags = ["funny", "laugh", "rofl"]
        effects = ["punch_zoom", "freeze_frame", "pop"]
    elif "roast" in text_lower or "bhai" in text_lower or "viva" in text_lower or "interrogat" in text_lower:
        humor_type = "roast"
        reaction_type = "disbelief"
        recommended_tags = ["disbelief", "facepalm"]
        effects = ["punch_zoom", "impact", "shake"]
    elif "dance" in text_lower or "score" in text_lower or "average" in text_lower or "seven" in text_lower:
        humor_type = "sarcasm"
        reaction_type = "disbelief"
        recommended_tags = ["shock", "facepalm"]
        effects = ["punch_zoom", "freeze_frame", "whoosh"]
    elif "ruin" in text_lower or "battery" in text_lower or "moment" in text_lower:
        humor_type = "deadpan"
        reaction_type = "disbelief"
        recommended_tags = ["disbelief", "awkward"]
        effects = ["punch_zoom", "freeze_frame", "scratch"]

    # Use candidate's pre-computed grounded metrics if available, or compute dynamically
    if getattr(candidate, "hook_score", 0.0) > 0.0:
        dyn_hook = candidate.hook_score
        dyn_humor = candidate.humor_score
        dyn_punchline = candidate.punchline_score
        dyn_reaction = candidate.reaction_score
        dyn_standalone = candidate.standalone_score
        dyn_rewatch = candidate.rewatch_score
        dyn_shareability = candidate.shareability_score
        dyn_visual = max(60.0, min(95.0, candidate.visual_energy * 100.0))
        final_viral = int(round(candidate.estimated_score))
    else:
        ev_str = " ".join(candidate.audio_events)
        has_laugh = "laughter" in ev_str
        has_peak = "peak" in ev_str or "shouting" in ev_str
        has_pause = "silence" in ev_str
        has_hook_words = any(w in text_lower for w in ["kya", "bhai", "socho", "what", "why", "how", "are", "look"]) or "?" in candidate.text

        laugh_burst_count = sum(1 for e in candidate.audio_events if "laughter" in e)
        dyn_humor = min(98.0, max(60.0, candidate.estimated_score + (4.0 if has_laugh else -10.0)))
        dyn_punchline = min(96.0, 74.0 + (11.0 if has_peak else 0.0) + (9.0 if has_pause else 0.0))
        dyn_hook = min(95.0, 76.0 + (14.0 if has_hook_words else 0.0))
        dyn_reaction = min(96.0, 72.0 + (laugh_burst_count * 3.5))
        dyn_standalone = 85.0 if candidate.duration >= 20.0 else 74.0
        dyn_rewatch = min(94.0, 68.0 + (len(candidate.audio_events) * 2.5))
        dyn_shareability = round((dyn_humor + dyn_punchline) / 2.0, 1)
        dyn_visual = min(95.0, max(65.0, candidate.visual_energy * 100.0))

        breakdown = calculate_viral_score(
            hook=dyn_hook, humor=dyn_humor, punchline=dyn_punchline,
            reaction=dyn_reaction, standalone=dyn_standalone, rewatch=dyn_rewatch,
            shareability=dyn_shareability, visual=dyn_visual
        )
        final_viral = breakdown.viral_potential_score

    # Build smart edit timeline
    punch_t = candidate.punchline_time
    timeline = [
        TimelineAction(time=candidate.start_time, action="zoom_in", strength=0.08, duration=max(1.0, punch_t - candidate.start_time)),
        TimelineAction(time=max(candidate.start_time, punch_t - 0.2), action="punch_zoom", strength=0.18, duration=0.8),
        TimelineAction(time=punch_t, action="subtitle_emphasis", duration=1.2),
        TimelineAction(time=punch_t + 0.3, action="freeze_frame", duration=0.4),
        TimelineAction(time=punch_t + 0.8, action="reaction_asset", asset_tag=recommended_tags[0], duration=1.5),
        TimelineAction(time=punch_t + 0.8, action="sound_effect", asset_tag="pop", duration=0.5)
    ]

    # Split text into setup and punchline
    text_len = len(candidate.text)
    split_idx = text_len // 2
    if "." in candidate.text:
        dots = [m.start() for m in re.finditer(r'\.|\?|\!', candidate.text)]
        if dots:
            best_dot = min(dots, key=lambda d: abs(d - split_idx))
            split_idx = best_dot + 1

    setup_part = candidate.text[:split_idx].strip()
    punch_part = candidate.text[split_idx:].strip()

    dynamic_reason = (
        f"Anchored at punchline {candidate.punchline_time:.1f}s. "
        f"High retention {humor_type.replace('_', ' ')} comedic arc with strong crowd reaction."
    )

    return GeminiClipAnalysis(
        clip_id=candidate.clip_id,
        start_time=candidate.start_time,
        end_time=candidate.end_time,
        setup=setup_part if setup_part else candidate.text,
        punchline=punch_part if punch_part else candidate.text,
        reaction=f"Audience and panel erupt in {reaction_type} following punchline.",
        hook_score=round(dyn_hook, 1),
        flow_score=getattr(candidate, "flow_score", 85.0) or 85.0,
        value_score=getattr(candidate, "value_score", 88.0) or 88.0,
        trend_score=getattr(candidate, "trend_score", 84.0) or 84.0,
        opus_virality_score=getattr(candidate, "opus_virality_score", 88) or 88,
        hook_insight=getattr(candidate, "hook_insight", "") or "Attention-grabbing opening creates curiosity.",
        flow_insight=getattr(candidate, "flow_insight", "") or "Seamless narrative continuity and pacing.",
        value_insight=getattr(candidate, "value_insight", "") or "High comedy resonance and audience reaction.",
        trend_insight=getattr(candidate, "trend_insight", "") or "Quotable punchline with meme potential.",
        humor_score=round(dyn_humor, 1),
        punchline_score=round(dyn_punchline, 1),
        reaction_score=round(dyn_reaction, 1),
        standalone_score=round(dyn_standalone, 1),
        rewatch_score=round(dyn_rewatch, 1),
        shareability_score=round(dyn_shareability, 1),
        visual_score=round(dyn_visual, 1),
        viral_score=final_viral,
        humor_type=humor_type,
        reaction_type=reaction_type,
        editing_style=editing_style,
        recommended_effects=effects,
        recommended_asset_tags=recommended_tags,
        reason=dynamic_reason,
        edit_timeline=timeline,
        analysis_engine="Local Acoustic Heuristics (Offline)"
    )


def analyze_candidate_with_gemini(
    candidate: CandidateClip,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_GEMINI_MODEL,
    editing_style: str = "Meme"
) -> GeminiClipAnalysis:
    """
    Sends candidate context to Gemini using the official google-genai SDK,
    validates strict JSON output, and constructs an edit timeline.
    Falls back to heuristic analysis if API key is not configured or on network error.
    """
    key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return generate_heuristic_analysis(candidate, editing_style)

    try:
        from google import genai
        client = genai.Client(api_key=key)

        prompt = f"""You are an expert viral short-form video editor implementing the Opus Clip (ClipGenius) 4-Pillar Virality methodology for YouTube Shorts, Reels, and TikTok.

Analyze this comedy candidate clip:
- Start Time: {candidate.start_time}s
- End Time: {candidate.end_time}s (Duration: {candidate.duration:.1f}s)
- Punchline Delivery Anchor: {candidate.punchline_time}s
- Audio Events: {', '.join(candidate.audio_events)}
- Dialogue Transcript: "{candidate.text}"

Evaluate using the 4 Opus Clip Virality Pillars:
1. HOOK (30% weight, 0-100): First 2-3s curiosity gap, vocal velocity, opening question or bold provocation.
2. FLOW (30% weight, 0-100): Information pacing, absence of dead air, conversational continuity, standalone clarity.
3. VALUE / EMOTION (25% weight, 0-100): Comedy roast power, laughter intensity, punchline contrast, emotional high.
4. TREND / SHAREABILITY (15% weight, 0-100): Quotability, relatable punchlines, meme-ability.

Return STRICT JSON with these exact fields:
{{
  "start_time": {candidate.start_time},
  "end_time": {candidate.end_time},
  "setup": "<setup of joke>",
  "punchline": "<punchline of joke>",
  "reaction": "<audience or speaker reaction>",
  "hook_score": <0-100>,
  "flow_score": <0-100>,
  "value_score": <0-100>,
  "trend_score": <0-100>,
  "opus_virality_score": <1-99>,
  "hook_insight": "<1 sentence on hook effectiveness>",
  "flow_insight": "<1 sentence on narrative flow and pacing>",
  "value_insight": "<1 sentence on comedy value and laughter reaction>",
  "trend_insight": "<1 sentence on quotability and meme potential>",
  "humor_score": <0-100>,
  "punchline_score": <0-100>,
  "reaction_score": <0-100>,
  "standalone_score": <0-100>,
  "rewatch_score": <0-100>,
  "shareability_score": <0-100>,
  "visual_score": <0-100>,
  "viral_score": <0-100>,
  "humor_type": "<unexpected_answer, sarcasm, roast, awkward, shock, fail, confusion, self_deprecating, deadpan, chaos>",
  "reaction_type": "<disbelief, laugh, shock, confusion, facepalm, awkward, celebration>",
  "editing_style": "{editing_style}",
  "recommended_effects": ["punch_zoom", "freeze_frame", "pop"],
  "recommended_asset_tags": ["disbelief", "laugh"],
  "reason": "<1-2 sentence explanation of why this moment is viral>",
  "edit_timeline": [
    {{"time": {candidate.punchline_time - 0.2}, "action": "punch_zoom", "strength": 0.18, "duration": 0.8}},
    {{"time": {candidate.punchline_time}, "action": "subtitle_emphasis", "duration": 1.2}},
    {{"time": {candidate.punchline_time + 0.4}, "action": "reaction_asset", "asset_tag": "laugh", "duration": 1.2}}
  ]
}}
Note: "start_time" and "end_time" must ensure the joke is NEVER cut mid-sentence or before the crowd reaction finishes.
"""

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )

        cleaned_json = clean_json_response(response.text)
        data = json.loads(cleaned_json)

        # Refine candidate boundary times if Gemini safely adjusted them
        gemini_start = float(data.get("start_time", candidate.start_time))
        gemini_end = float(data.get("end_time", candidate.end_time))
        if candidate.start_time - 8.0 <= gemini_start <= candidate.punchline_time - 4.0:
            candidate.start_time = round(gemini_start, 2)
        if candidate.punchline_time + 4.0 <= gemini_end <= candidate.end_time + 15.0:
            candidate.end_time = round(gemini_end, 2)
        candidate.duration = round(candidate.end_time - candidate.start_time, 2)

        # Validate with clip scorer
        breakdown = calculate_viral_score(
            hook=float(data.get("hook_score", 85)),
            humor=float(data.get("humor_score", 85)),
            punchline=float(data.get("punchline_score", 85)),
            reaction=float(data.get("reaction_score", 85)),
            standalone=float(data.get("standalone_score", 80)),
            rewatch=float(data.get("rewatch_score", 80)),
            shareability=float(data.get("shareability_score", 80)),
            visual=float(data.get("visual_score", 75))
        )

        # Opus specific fields from LLM response or computed fallback
        opus_sc = int(data.get("opus_virality_score", breakdown.opus_virality_score))
        opus_sc = min(99, max(1, opus_sc))
        flow_sc = float(data.get("flow_score", breakdown.flow_score))
        value_sc = float(data.get("value_score", breakdown.value_score))
        trend_sc = float(data.get("trend_score", breakdown.trend_score))
        hook_ins = str(data.get("hook_insight", breakdown.hook_insight))
        flow_ins = str(data.get("flow_insight", breakdown.flow_insight))
        val_ins = str(data.get("value_insight", breakdown.value_insight))
        trend_ins = str(data.get("trend_insight", breakdown.trend_insight))

        timeline_items = []
        raw_timeline = data.get("edit_timeline", [])
        if isinstance(raw_timeline, list):
            for item in raw_timeline:
                try:
                    timeline_items.append(TimelineAction(**item))
                except Exception:
                    pass

        if not timeline_items:
            timeline_items = [
                TimelineAction(time=candidate.punchline_time - 0.2, action="punch_zoom", strength=0.18, duration=0.8),
                TimelineAction(time=candidate.punchline_time, action="subtitle_emphasis", duration=1.2),
                TimelineAction(time=candidate.punchline_time + 0.3, action="freeze_frame", duration=0.4)
            ]

        return GeminiClipAnalysis(
            clip_id=candidate.clip_id,
            start_time=candidate.start_time,
            end_time=candidate.end_time,
            setup=str(data.get("setup", "")),
            punchline=str(data.get("punchline", "")),
            reaction=str(data.get("reaction", "")),
            hook_score=breakdown.hook_score,
            flow_score=flow_sc,
            value_score=value_sc,
            trend_score=trend_sc,
            opus_virality_score=opus_sc,
            hook_insight=hook_ins,
            flow_insight=flow_ins,
            value_insight=val_ins,
            trend_insight=trend_ins,
            humor_score=breakdown.humor_score,
            punchline_score=breakdown.punchline_score,
            reaction_score=breakdown.reaction_score,
            standalone_score=breakdown.standalone_score,
            rewatch_score=breakdown.rewatch_score,
            shareability_score=breakdown.shareability_score,
            visual_score=breakdown.visual_score,
            viral_score=breakdown.viral_potential_score,
            humor_type=str(data.get("humor_type", "unexpected_answer")),
            reaction_type=str(data.get("reaction_type", "disbelief")),
            editing_style=editing_style,
            recommended_effects=list(data.get("recommended_effects", ["punch_zoom"])),
            recommended_asset_tags=list(data.get("recommended_asset_tags", ["laugh"])),
            reason=str(data.get("reason", "Strong comedic punchline with high audience engagement.")),
            edit_timeline=timeline_items,
            analysis_engine=f"Google Gemini ({model_name})"
        )

    except Exception as e:
        print(f"[Gemini Analysis Warning] API call failed ({type(e).__name__}: {e}). Falling back to local heuristics.")
        res = generate_heuristic_analysis(candidate, editing_style)
        res.reason = f"(Offline Heuristic Fallback - {type(e).__name__}) {res.reason}"
        return res
