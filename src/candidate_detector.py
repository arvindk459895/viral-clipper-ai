"""
ViralClipper AI Studio - Candidate Moment Detector
Identifies comedic and high-energy candidate clips using comedy structure:
HOOK -> SETUP -> PAUSE -> PUNCHLINE -> REACTION -> LAUGHTER.
Performs timestamp search, boundary expansion, and overlap deduplication.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from pydantic import BaseModel, Field

from src.transcription import TranscriptResult, TranscriptSegment
from src.audio_analysis import AudioAnalysisResult


class CandidateClip(BaseModel):
    clip_id: str
    start_time: float
    end_time: float
    duration: float
    hook_start: float
    setup_start: float
    punchline_time: float
    reaction_end: float
    # Opus 3-Act Narrative Arc
    act1_hook_end: float = 0.0
    act2_setup_end: float = 0.0
    act3_punchline_time: float = 0.0
    # Opus 4 Pillars & Insights
    flow_score: float = 0.0
    value_score: float = 0.0
    trend_score: float = 0.0
    opus_virality_score: int = 0
    hook_insight: str = ""
    flow_insight: str = ""
    value_insight: str = ""
    trend_insight: str = ""
    text: str
    audio_events: List[str] = Field(default_factory=list)
    visual_energy: float = 0.5
    estimated_score: float = 0.0
    hook_score: float = 0.0
    humor_score: float = 0.0
    punchline_score: float = 0.0
    reaction_score: float = 0.0
    standalone_score: float = 0.0
    rewatch_score: float = 0.0
    shareability_score: float = 0.0
    is_sponsor: bool = False


def calculate_overlap_ratio(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    """Calculates Intersection over Union (IoU) of two time intervals."""
    intersection = max(0.0, min(end_a, end_b) - max(start_a, start_b))
    union = max(end_a, end_b) - min(start_a, start_b)
    return intersection / union if union > 0 else 0.0


def deduplicate_candidates(candidates: List[CandidateClip], max_iou: float = 0.35) -> List[CandidateClip]:
    """Applies Non-Maximum Suppression (NMS) to eliminate heavily overlapping clips."""
    sorted_clips = sorted(candidates, key=lambda c: c.estimated_score, reverse=True)
    kept: List[CandidateClip] = []

    for clip in sorted_clips:
        overlap = False
        for k in kept:
            iou = calculate_overlap_ratio(clip.start_time, clip.end_time, k.start_time, k.end_time)
            if iou > max_iou:
                overlap = True
                break
        if not overlap:
            kept.append(clip)

    return kept


SPONSOR_TERMS = [
    "presents", "partner", "delivery partner", "protein partner", "fragrance partner",
    "exclusive partner", "powered by", "brought to you by", "sponsor", "coupon code",
    "discount code", "link in description", "download the app", "subscribe to",
    "welcome to episode", "india's got latent", "presented by"
]


DANGLING_CONNECTORS = {
    "and", "or", "but", "so", "because", "then", "with", "from", "to", "for",
    "that", "if", "when", "while", "as", "is", "was", "are", "were", "this",
    "which", "who", "whom", "where", "like", "the", "a", "an", "has", "have"
}


def is_clean_sentence_end(text: str) -> bool:
    """Checks if a subtitle line represents a natural, complete sentence or thought conclusion."""
    t = text.strip()
    if not t:
        return False
    # Supports Western punctuation and Devanagari danda / double danda (U+0964, U+0965)
    if t.endswith((".", "!", "?", "\u0964", "\u0965")):
        clean_no_punc = t.rstrip(".!? \u0964\u0965")
        last_word = clean_no_punc.split()[-1].lower() if clean_no_punc.split() else ""
        if last_word in DANGLING_CONNECTORS:
            return False
        return True
    if t.endswith((",", "-", "--", "…", "...", ":", ";")):
        return False
    last_word = t.split()[-1].lower() if t.split() else ""
    if last_word in DANGLING_CONNECTORS:
        return False
    return False


def detect_candidate_moments(
    transcript: TranscriptResult,
    audio_analysis: AudioAnalysisResult,
    target_duration: str = "30 sec",
    min_clip_duration: float = 12.0,
    max_clip_duration: float = 60.0
) -> List[CandidateClip]:
    """
    Scans transcript and acoustic signal across the entire video to detect genuine
    viral comedy candidate moments based on sustained laughter clusters, pre-punchline
    comedic pauses, vocal burst inflection, and clean sentence boundaries.
    Strictly eliminates sponsor reads, prevents premature punchline cuts, and guarantees
    full setup and reaction resolution.
    """
    from src.clip_scorer import calculate_grounded_virality_components, calibrate_viral_scores

    preferred_duration = 32.0
    if "15" in target_duration:
        preferred_duration = 20.0
    elif "30" in target_duration:
        preferred_duration = 32.0
    elif "45" in target_duration:
        preferred_duration = 44.0
    elif "60" in target_duration:
        preferred_duration = 55.0

    total_duration = max(transcript.duration, audio_analysis.duration)
    raw_candidates: List[CandidateClip] = []

    # 1. Cluster contiguous laughter events (laughter bursts within 3.5s of each other)
    laughter_events = [e for e in audio_analysis.events if e.event_type == "laughter"]
    laughter_clusters = []
    current_cluster = []

    for ev in laughter_events:
        if not current_cluster:
            current_cluster.append(ev)
        else:
            if ev.start_time - current_cluster[-1].end_time <= 3.5:
                current_cluster.append(ev)
            else:
                if len(current_cluster) >= 1:
                    laughter_clusters.append(current_cluster)
                current_cluster = [ev]
    if current_cluster:
        laughter_clusters.append(current_cluster)

    # 2. Build Candidate Anchors from Laughter Clusters
    candidate_anchors = []
    for c in laughter_clusters:
        cl_start = c[0].start_time
        cl_end = c[-1].end_time
        cl_dur = cl_end - cl_start
        burst_count = len(c)
        mean_int = float(np.mean([e.intensity for e in c])) if burst_count > 0 else 0.5

        # Find acoustic punchline peak in [cl_start - 3.0, cl_start + 0.5]
        peaks_before = [p for p in audio_analysis.peak_timestamps if cl_start - 3.0 <= p <= cl_start + 0.5]
        punch_t = peaks_before[-1] if peaks_before else cl_start

        # Detect comedic pause right before punchline [punch_t - 2.5, punch_t]
        pauses_before = [p for p in audio_analysis.pause_timestamps if punch_t - 2.5 <= p <= punch_t]
        has_pause = len(pauses_before) > 0

        candidate_anchors.append({
            "punchline": punch_t,
            "laughter_start": cl_start,
            "reaction_end": cl_end,
            "laughter_dur": cl_dur,
            "burst_count": burst_count,
            "mean_intensity": mean_int,
            "has_pause": has_pause,
            "has_peak": len(peaks_before) > 0
        })

    # If few or no laughter clusters detected (e.g. synthetic demo media or speech only), add acoustic peaks
    if len(candidate_anchors) < 5:
        for p in audio_analysis.peak_timestamps:
            if 3.0 <= p <= total_duration - 5.0:
                candidate_anchors.append({
                    "punchline": p,
                    "laughter_start": p + 0.5,
                    "reaction_end": min(total_duration, p + 5.0),
                    "laughter_dur": 3.5,
                    "burst_count": 2,
                    "mean_intensity": 0.65,
                    "has_pause": False,
                    "has_peak": True
                })
        for seg in transcript.segments:
            t_lower = seg.text.lower()
            if any(w in t_lower for w in ["gym", "workout", "bhai", "joke", "funny", "laugh", "what"]):
                candidate_anchors.append({
                    "punchline": seg.end,
                    "laughter_start": seg.end,
                    "reaction_end": min(total_duration, seg.end + 5.0),
                    "laughter_dur": 3.0,
                    "burst_count": 2,
                    "mean_intensity": 0.60,
                    "has_pause": False,
                    "has_peak": False
                })

    clip_index = 1
    for anc in candidate_anchors:
        punch_t = anc["punchline"]
        cl_dur = anc["laughter_dur"]
        cl_end = anc["reaction_end"]
        burst_count = anc["burst_count"]
        mean_int = anc["mean_intensity"]
        has_pause = anc["has_pause"]
        has_peak = anc["has_peak"]

        # Setup duration target: 50-60% of preferred duration
        setup_target = preferred_duration * 0.55
        # Reaction target: MUST encompass full laughter cluster + generous post-laughter comedic resolution
        react_target = max(9.0, min(38.0, (cl_end - punch_t) + 6.0))

        ideal_start = max(0.0, punch_t - setup_target)
        ideal_end = min(total_duration, punch_t + react_target)

        # Snap start time cleanly to sentence boundary
        valid_start_segs = [
            s for s in transcript.segments
            if max(0.0, punch_t - (setup_target * 1.6)) <= s.start <= punch_t - 5.0
        ]
        if valid_start_segs:
            best_start_seg = min(valid_start_segs, key=lambda s: abs(s.start - ideal_start))
            clip_start = best_start_seg.start
        else:
            clip_start = ideal_start

        # Snap end time cleanly to sentence boundary AFTER laughter reaction has subsided
        min_end_t = max(punch_t + 5.0, cl_end + 1.2)
        max_end_t = min(total_duration, punch_t + 38.0)

        valid_end_segs = [
            s for s in transcript.segments
            if min_end_t <= s.end <= max_end_t
        ]
        clean_end_segs = [s for s in valid_end_segs if is_clean_sentence_end(s.text)]
        candidate_end_pool = clean_end_segs if clean_end_segs else valid_end_segs

        if candidate_end_pool:
            best_end_seg = min(candidate_end_pool, key=lambda s: abs(s.end - ideal_end))
            clip_end = best_end_seg.end
            # Walk forward through contiguous thought segments until clean sentence / bit conclusion
            try:
                s_idx = transcript.segments.index(best_end_seg)
                for next_s in transcript.segments[s_idx + 1: s_idx + 8]:
                    if (next_s.end - clip_start) > max_clip_duration - 2.0:
                        break
                    # If current segment has a dangling ending or next segment is an immediate exclamation/punchline tag
                    clip_end = next_s.end
                    if is_clean_sentence_end(next_s.text):
                        break
            except (ValueError, IndexError):
                pass
        else:
            clip_end = ideal_end

        # Strictly enforce punchline bracketing inside the clip
        clip_start = min(clip_start, max(0.0, punch_t - 5.0))
        clip_end = max(clip_end, min(total_duration, punch_t + 5.0))

        duration = clip_end - clip_start
        if duration < min_clip_duration or duration > max_clip_duration:
            continue

        # Gather dialogue in clip
        window_segs = [s for s in transcript.segments if s.end >= clip_start and s.start <= clip_end]
        clip_text = " ".join(s.text for s in window_segs).strip()
        text_lower = clip_text.lower()

        # Strict Sponsor & Intro Ad Filtering
        is_sponsor = any(term in text_lower for term in SPONSOR_TERMS)
        if is_sponsor and clip_start < 120.0 and total_duration > 180.0:
            continue  # Completely drop intro sponsor reads

        # Gather audio events
        ev_summary = []
        for ev in audio_analysis.events:
            if ev.end_time >= clip_start and ev.start_time <= clip_end:
                ev_summary.append(f"{ev.event_type}@{round(ev.start_time, 1)}s")

        # Grounded 8-Component Virality Scoring
        score_breakdown = calculate_grounded_virality_components(
            clip_text=clip_text if clip_text else "High energy comedy clip",
            clip_duration=duration,
            punchline_time=punch_t,
            start_time=clip_start,
            end_time=clip_end,
            laughter_duration=cl_dur,
            laughter_burst_count=burst_count,
            laughter_intensity=mean_int,
            has_pre_punchline_pause=has_pause,
            has_vocal_peak=has_peak,
            visual_energy=0.75,
            is_sponsor=is_sponsor
        )

        # 3-Act Structure
        act1_end = round(min(clip_end, clip_start + 3.0), 2)
        act2_end = round(max(act1_end, punch_t - 0.5), 2)

        candidate = CandidateClip(
            clip_id=f"cand_{clip_index:02d}",
            start_time=round(clip_start, 2),
            end_time=round(clip_end, 2),
            duration=round(duration, 2),
            hook_start=round(clip_start, 2),
            setup_start=round(clip_start + 1.5, 2),
            punchline_time=round(punch_t, 2),
            reaction_end=round(clip_end, 2),
            act1_hook_end=act1_end,
            act2_setup_end=act2_end,
            act3_punchline_time=round(punch_t, 2),
            text=clip_text if clip_text else f"High energy comedy moment from {clip_start:.1f}s to {clip_end:.1f}s",
            audio_events=ev_summary[:10],
            visual_energy=0.75,
            estimated_score=float(score_breakdown.viral_potential_score),
            hook_score=score_breakdown.hook_score,
            flow_score=score_breakdown.flow_score,
            value_score=score_breakdown.value_score,
            trend_score=score_breakdown.trend_score,
            opus_virality_score=score_breakdown.opus_virality_score,
            hook_insight=score_breakdown.hook_insight,
            flow_insight=score_breakdown.flow_insight,
            value_insight=score_breakdown.value_insight,
            trend_insight=score_breakdown.trend_insight,
            humor_score=score_breakdown.humor_score,
            punchline_score=score_breakdown.punchline_score,
            reaction_score=score_breakdown.reaction_score,
            standalone_score=score_breakdown.standalone_score,
            rewatch_score=score_breakdown.rewatch_score,
            shareability_score=score_breakdown.shareability_score,
            is_sponsor=is_sponsor
        )
        raw_candidates.append(candidate)
        clip_index += 1

    # Apply NMS Deduplication
    deduped = deduplicate_candidates(raw_candidates, max_iou=0.35)

    # Calibrate final scores across candidates for realistic spread
    if deduped:
        raw_scs = [c.estimated_score for c in deduped]
        calibrated = calibrate_viral_scores(raw_scs)
        for i, c in enumerate(deduped):
            c.estimated_score = float(calibrated[i])

    return deduped
