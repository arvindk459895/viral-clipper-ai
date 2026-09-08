"""
Tests for Phase 3: Transcription, Audio DSP, Video Analysis, and Candidate Moment Detection.
"""
import numpy as np
from pathlib import Path
from src.transcription import get_demo_transcript, TranscriptResult
from src.audio_analysis import AudioAnalysisResult, AudioEvent, compute_normalization_gain, analyze_audio_events
from src.video_analysis import get_video_properties, detect_faces_in_frame, calculate_optimal_crop_center, extract_keyframe
from src.candidate_detector import (
    CandidateClip,
    calculate_overlap_ratio,
    deduplicate_candidates,
    detect_candidate_moments
)
from src.youtube import create_demo_media


def test_demo_transcript_structure():
    transcript = get_demo_transcript(25.0)
    assert transcript.language == "hi"
    assert len(transcript.segments) >= 4
    assert "workout" in transcript.full_text.lower()
    assert transcript.segments[0].words[0].word == "Toh"


def test_overlap_ratio_iou():
    # Identical intervals
    assert calculate_overlap_ratio(10.0, 30.0, 10.0, 30.0) == 1.0
    # No overlap
    assert calculate_overlap_ratio(0.0, 10.0, 20.0, 30.0) == 0.0
    # Partial overlap (10s overlap, 30s union = 1/3)
    iou = calculate_overlap_ratio(10.0, 30.0, 20.0, 40.0)
    assert round(iou, 2) == 0.33


def test_deduplicate_candidates():
    c1 = CandidateClip(
        clip_id="c1", start_time=10.0, end_time=30.0, duration=20.0,
        hook_start=10.0, setup_start=12.0, punchline_time=25.0, reaction_end=30.0,
        text="Joke 1", estimated_score=90.0
    )
    # Heavy overlap with c1 (11.0 to 30.0)
    c2 = CandidateClip(
        clip_id="c2", start_time=11.0, end_time=30.0, duration=19.0,
        hook_start=11.0, setup_start=13.0, punchline_time=25.0, reaction_end=30.0,
        text="Joke 1 slightly shifted", estimated_score=75.0
    )
    # Distinct non-overlapping clip (40.0 to 60.0)
    c3 = CandidateClip(
        clip_id="c3", start_time=40.0, end_time=60.0, duration=20.0,
        hook_start=40.0, setup_start=42.0, punchline_time=55.0, reaction_end=60.0,
        text="Joke 2", estimated_score=85.0
    )

    deduped = deduplicate_candidates([c1, c2, c3], max_iou=0.45)
    assert len(deduped) == 2
    assert deduped[0].clip_id == "c1"
    assert deduped[1].clip_id == "c3"


def test_candidate_detection_on_transcript():
    transcript = get_demo_transcript(25.0)
    audio_analysis = AudioAnalysisResult(
        duration=25.0,
        events=[
            AudioEvent(event_type="laughter", start_time=9.2, end_time=11.0, intensity=0.9),
            AudioEvent(event_type="peak", start_time=14.5, end_time=15.2, intensity=0.85)
        ],
        laughter_timestamps=[9.5, 14.8],
        peak_timestamps=[14.5]
    )

    candidates = detect_candidate_moments(transcript, audio_analysis, target_duration="30 sec")
    assert len(candidates) >= 1
    best = candidates[0]
    # Check that candidate starts before the punchline (does NOT start on punchline)
    assert best.start_time < best.punchline_time
    # Check that candidate extends past punchline to include reaction
    assert best.end_time >= best.punchline_time


def test_video_and_audio_analysis_on_demo_media(tmp_path):
    media = create_demo_media(output_dir=tmp_path, duration=6)
    v_props = get_video_properties(media["video_path"])
    assert v_props.width == 1280
    assert v_props.height == 720
    assert v_props.duration >= 5.5

    crop_center = calculate_optimal_crop_center(media["video_path"], 0.0, 5.0, num_samples=3)
    assert 0.25 <= crop_center <= 0.75

    keyframe_p = extract_keyframe(media["video_path"], 2.0, str(tmp_path / "test_kf.jpg"))
    assert Path(keyframe_p).exists()

    a_analysis = analyze_audio_events(media["audio_path"])
    assert a_analysis.duration >= 5.5
    gain = compute_normalization_gain(media["audio_path"])
    assert 0.2 <= gain <= 5.0


def test_sponsor_filtering_and_punchline_bracketing():
    from src.transcription import TranscriptSegment, TranscriptResult

    # Mock long video transcript (300s) where intro (0-30s) is sponsor ad
    segs = [
        TranscriptSegment(id=0, start=5.0, end=25.0, text="Ai+ phone presents the show with delivery partner Flipkart Minutes.", words=[]),
        TranscriptSegment(id=1, start=90.0, end=100.0, text="Why did you do that? That was completely crazy.", words=[]),
        TranscriptSegment(id=2, start=100.0, end=115.0, text="Because he told me it would work! Wow that is hilarious.", words=[])
    ]
    transcript = TranscriptResult(
        segments=segs,
        full_text="Ai+ phone presents the show with delivery partner Flipkart Minutes. Why did you do that? That was completely crazy. Because he told me it would work! Wow that is hilarious.",
        language="en",
        duration=300.0
    )

    audio_res = AudioAnalysisResult(
        duration=300.0,
        events=[
            AudioEvent(event_type="laughter", start_time=10.0, end_time=18.0, intensity=0.9),  # Canned intro laugh
            AudioEvent(event_type="laughter", start_time=105.0, end_time=114.0, intensity=0.95), # Real joke laugh
            AudioEvent(event_type="silence", start_time=99.0, end_time=100.2, intensity=0.8),   # Comedic pause
            AudioEvent(event_type="peak", start_time=103.5, end_time=104.2, intensity=0.9)     # Vocal punch
        ],
        peak_timestamps=[103.5],
        laughter_timestamps=[12.0, 108.0],
        pause_timestamps=[99.5]
    )

    candidates = detect_candidate_moments(transcript, audio_res, target_duration="30 sec")
    assert len(candidates) >= 1

    # Guarantee: NO candidate starts in the 0-30s sponsor ad window!
    for cand in candidates:
        assert not (cand.start_time < 30.0 and "presents" in cand.text.lower())
        # Guarantee: Punchline is strictly inside clip
        assert cand.start_time + 3.0 <= cand.punchline_time <= cand.end_time - 2.5
        # Guarantee: Virality sub-scores are populated
        assert cand.hook_score > 0
        assert cand.humor_score > 0
        assert cand.punchline_score > 0


def test_dangling_connector_and_clean_sentence_end():
    from src.candidate_detector import is_clean_sentence_end
    # Complete sentences
    assert is_clean_sentence_end("This was hilarious.") is True
    assert is_clean_sentence_end("What an amazing moment!") is True
    assert is_clean_sentence_end("Are you serious?") is True
    # Incomplete or dangling sentences
    assert is_clean_sentence_end("And from District,") is False
    assert is_clean_sentence_end("Way to ruin it, Ai+ and") is False
    assert is_clean_sentence_end("This has--") is False
    assert is_clean_sentence_end("Because...") is False
    assert is_clean_sentence_end("with") is False
    assert is_clean_sentence_end("") is False

