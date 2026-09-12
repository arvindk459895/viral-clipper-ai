"""
ViralClipper AI Studio - Acceptance Tests for Context Expansion & Event Reconstruction
Verifies the 8 core acceptance criteria:
1. Complete Comedy (Setup + Buildup + Micro-pause + Burst + Punchline + Laughter)
2. Pause Inside Setup (Setup pauses rejected from being punchline anchors)
3. Long Setup (Preserves essential setup context within duration ceiling)
4. Short Joke (Naturally ~30s joke is NOT padded with unrelated content)
5. Long Laughter (Full 10s eruption preserved throughout natural decay)
6. No Laughter (Strong punchline without laughter still detected)
7. Multiple Peaks (Merged into single coherent event)
8. Unrelated Following Content (Reaction concludes cleanly before next topic)
"""
import pytest
from typing import List

from src.transcription import TranscriptResult, TranscriptSegment, TranscriptWord
from src.audio_analysis import AudioAnalysisResult, AudioEvent
from src.context_expander import (
    validate_micro_pause,
    find_narrative_start_candidates,
    find_reaction_end,
    merge_contiguous_event_peaks,
    reconstruct_narrative_event,
    calculate_momentum_envelope,
    ReconstructedEvent
)


# Helper to build test transcripts
def make_segment(seg_id: int, start: float, end: float, text: str) -> TranscriptSegment:
    words = []
    w_list = text.split()
    dur = max(0.1, end - start)
    step = dur / max(1, len(w_list))
    for i, w in enumerate(w_list):
        words.append(TranscriptWord(word=w, start=start + (i * step), end=start + ((i + 1) * step)))
    return TranscriptSegment(id=seg_id, start=start, end=end, text=text, language="hi", words=words)


# ==============================================================================
# TEST 1 — COMPLETE COMEDY
# Setup -> buildup -> micro-pause -> vocal burst -> punchline -> laughter.
# Expected: Setup + buildup + punchline + meaningful laughter (not punchline + laughter only).
# ==============================================================================
def test_1_complete_comedy():
    segments = [
        make_segment(0, 10.0, 15.0, "So yesterday I went to the gym for the very first time."),
        make_segment(1, 15.2, 21.0, "The trainer looked at me and asked what is your primary fitness goal?"),
        make_segment(2, 21.5, 27.0, "I paused and looked him dead in the eye and said bhai mera ek hi goal hai zinda rehna!"),
        make_segment(3, 27.5, 34.0, "Sab log hasne lage aur trainer shock ho gaya!")
    ]
    transcript = TranscriptResult(language="hi", duration=50.0, segments=segments, full_text=" ".join(s.text for s in segments))

    audio_events = [
        AudioEvent(event_type="silence", start_time=24.0, end_time=24.8, intensity=0.9, description="Pre-punchline pause"),
        AudioEvent(event_type="peak", start_time=25.2, end_time=25.8, intensity=0.95, description="Vocal burst"),
        AudioEvent(event_type="laughter", start_time=27.2, end_time=33.5, intensity=0.9, description="Audience laughter eruption")
    ]
    analysis = AudioAnalysisResult(
        duration=50.0,
        events=audio_events,
        average_rms=0.2,
        peak_rms=0.95,
        peak_timestamps=[25.2],
        pause_timestamps=[24.0],
        laughter_timestamps=[27.2, 29.0, 31.5]
    )

    t_peak = 25.2
    recon = reconstruct_narrative_event(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=analysis,
        total_video_duration=50.0,
        target_duration=55.0
    )

    # Assert that the clip does NOT start only at the punchline (25.2s)
    # It must start at the beginning of the setup (10.0s)
    assert recon.t_final_start <= 11.0, f"Expected start near 10.0s setup opener, got {recon.t_final_start}"
    # It must capture the audience laughter and reaction beyond 30.0s
    assert recon.t_final_end >= 33.0, f"Expected end beyond 33.0s laughter, got {recon.t_final_end}"
    assert recon.context_completeness_score >= 85.0
    assert "Premise opener" in recon.boundary_start_reason or "setup" in recon.boundary_start_reason.lower()


# ==============================================================================
# TEST 2 — PAUSE INSIDE SETUP
# Setup contains several natural pauses. Only the final pause is followed by
# vocal burst + semantic punchline + reaction.
# Expected: Setup pauses are rejected from being punchline anchors.
# ==============================================================================
def test_2_pause_inside_setup():
    segments = [
        make_segment(0, 5.0, 9.0, "So I went to the shop..."),
        make_segment(1, 10.0, 14.0, "...and then I saw..."),
        make_segment(2, 15.0, 18.0, "...the craziest thing in my entire life..."),
        make_segment(3, 19.0, 24.0, "The cashier told me sir credit card is blocked!")
    ]
    transcript = TranscriptResult(language="en", duration=40.0, segments=segments, full_text=" ".join(s.text for s in segments))

    # Multiple pauses: at 9.2s (setup pause), at 14.2s (setup pause), and at 18.2s (punchline pause)
    audio_events = [
        AudioEvent(event_type="silence", start_time=9.2, end_time=9.8, intensity=0.7),
        AudioEvent(event_type="silence", start_time=14.2, end_time=14.8, intensity=0.7),
        AudioEvent(event_type="silence", start_time=18.2, end_time=18.8, intensity=0.9),
        AudioEvent(event_type="peak", start_time=19.5, end_time=20.0, intensity=0.95),  # only after final pause
        AudioEvent(event_type="laughter", start_time=22.0, end_time=26.0, intensity=0.85)
    ]
    analysis = AudioAnalysisResult(
        duration=40.0,
        events=audio_events,
        average_rms=0.2,
        peak_rms=0.95,
        peak_timestamps=[19.5],
        pause_timestamps=[9.2, 14.2, 18.2],
        laughter_timestamps=[22.0]
    )

    # Validate the setup pauses (9.2s and 14.2s)
    is_valid_1, conf_1, _ = validate_micro_pause(9.2, analysis, transcript)
    is_valid_2, conf_2, _ = validate_micro_pause(14.2, analysis, transcript)
    is_valid_3, conf_3, _ = validate_micro_pause(18.2, analysis, transcript)

    # Setup pauses must be rejected (no vocal burst or reaction follows)
    assert not is_valid_1, f"Setup pause at 9.2s should be rejected, got conf={conf_1}"
    assert not is_valid_2, f"Setup pause at 14.2s should be rejected, got conf={conf_2}"
    # Punchline pause must be accepted
    assert is_valid_3, f"True punchline pause at 18.2s should be accepted, got conf={conf_3}"
    assert conf_3 >= 0.70


# ==============================================================================
# TEST 3 — LONG SETUP
# 45-second setup + 5-second punchline + 5-second reaction.
# Expected: Preserves enough setup to understand the joke without cutting to < 10s.
# ==============================================================================
def test_3_long_setup():
    segments = [
        make_segment(0, 0.0, 12.0, "Let me tell you about my childhood in Delhi."),
        make_segment(1, 12.5, 24.0, "My father was extremely strict and always demanded full marks in mathematics."),
        make_segment(2, 24.5, 36.0, "Whenever report card came home the entire family would sit in silence waiting for his judgment."),
        make_segment(3, 36.5, 45.0, "So this one time I failed and told him papa mathematics has changed now."),
        make_segment(4, 45.5, 51.0, "He took off his slipper and said beta mathematics is same, physics is about to hit you!"),
        make_segment(5, 51.5, 58.0, "Everyone in the hall burst into tears laughing!")
    ]
    transcript = TranscriptResult(language="en", duration=70.0, segments=segments, full_text=" ".join(s.text for s in segments))

    audio_events = [
        AudioEvent(event_type="peak", start_time=47.5, end_time=48.2, intensity=0.9),
        AudioEvent(event_type="laughter", start_time=51.0, end_time=57.0, intensity=0.95)
    ]
    analysis = AudioAnalysisResult(
        duration=70.0,
        events=audio_events,
        average_rms=0.2,
        peak_rms=0.95,
        peak_timestamps=[47.5],
        pause_timestamps=[45.0],
        laughter_timestamps=[51.0, 53.0]
    )

    t_peak = 47.5
    recon = reconstruct_narrative_event(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=analysis,
        total_video_duration=70.0,
        target_duration=55.0,
        max_clip_duration=58.5
    )

    # Ensure clip duration stays within Shorts ceiling
    assert recon.total_duration <= 58.5
    # Ensure setup is substantial (at least 20s of setup context preserved, not cut to a 10s snippet)
    assert recon.pre_context_duration >= 25.0
    assert recon.context_completeness_score >= 80.0


# ==============================================================================
# TEST 4 — SHORT JOKE
# 20-second setup + 5-second punchline + 5-second reaction = 30 sec.
# Expected: approximately 30 seconds. Do NOT add 25 seconds of unrelated content.
# ==============================================================================
def test_4_short_joke():
    segments = [
        make_segment(0, 0.0, 9.5, "Unrelated sports news discussing cricket match."),
        make_segment(1, 10.0, 20.0, "So yesterday I asked my dog why he was staring at the blank wall."),
        make_segment(2, 20.5, 25.0, "He gave me a side eye and said at least I am not staring at Excel sheets!"),
        make_segment(3, 25.5, 30.0, "The whole room was laughing so hard!"),
        make_segment(4, 31.0, 45.0, "Next topic let's discuss inflation in housing sector.")
    ]
    transcript = TranscriptResult(language="en", duration=60.0, segments=segments, full_text=" ".join(s.text for s in segments))

    audio_events = [
        AudioEvent(event_type="peak", start_time=23.0, end_time=23.5, intensity=0.9),
        AudioEvent(event_type="laughter", start_time=25.0, end_time=29.5, intensity=0.85)
    ]
    analysis = AudioAnalysisResult(
        duration=60.0,
        events=audio_events,
        average_rms=0.2,
        peak_rms=0.9,
        peak_timestamps=[23.0],
        pause_timestamps=[20.2],
        laughter_timestamps=[25.0]
    )

    t_peak = 23.0
    recon = reconstruct_narrative_event(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=analysis,
        total_video_duration=60.0,
        target_duration=55.0  # target is 55s, but natural joke is ~23s!
    )

    # Crucial assertion: Natural duration should be around 20-30 seconds!
    # It must NOT force padding with the cricket news (0.0-9.5s) or inflation (31.0-45.0s)
    assert 18.0 <= recon.total_duration <= 32.0, f"Expected ~20-30s natural joke, got {recon.total_duration}s"
    assert recon.t_final_start >= 9.8, "Should not include preceding cricket talk"
    assert recon.t_final_end <= 33.5, "Should not spill into inflation topic"


# ==============================================================================
# TEST 5 — LONG LAUGHTER
# Punchline + 10-second audience eruption.
# Expected: Meaningful laughter should be preserved throughout decay, not cut prematurely.
# ==============================================================================
def test_5_long_laughter():
    segments = [
        make_segment(0, 5.0, 15.0, "Toh maine bola bhai shaadi ke baad aadmi saint ban jata hai."),
        make_segment(1, 15.5, 20.0, "Kyunki sab kuch chhod ke bas shanti dhundta hai!"),
        make_segment(2, 20.5, 33.0, "Audience goes wild and erupts in nonstop roaring laughter!")
    ]
    transcript = TranscriptResult(language="hi", duration=50.0, segments=segments, full_text=" ".join(s.text for s in segments))

    # 10 full seconds of laughter from 19.5s to 29.5s
    audio_events = [
        AudioEvent(event_type="peak", start_time=18.5, end_time=19.0, intensity=0.95),
        AudioEvent(event_type="laughter", start_time=19.5, end_time=29.5, intensity=0.92)
    ]
    analysis = AudioAnalysisResult(
        duration=50.0,
        events=audio_events,
        average_rms=0.2,
        peak_rms=0.95,
        peak_timestamps=[18.5],
        pause_timestamps=[15.2],
        laughter_timestamps=[19.5, 23.0, 27.0, 29.0]
    )

    t_peak = 18.5
    recon = reconstruct_narrative_event(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=analysis,
        total_video_duration=50.0,
        target_duration=55.0
    )

    # It must preserve the full 10 seconds of laughter (+ breathing room)
    # Laughter ends at 29.5s, so t_final_end must reach >= 32.0s
    assert recon.t_final_end >= 32.0, f"Expected reaction end >= 32.0s, got {recon.t_final_end}"
    assert recon.post_context_duration >= 12.0


# ==============================================================================
# TEST 6 — NO LAUGHTER
# Strong semantic punchline + vocal emphasis + visual reaction + little/no audible laughter.
# Expected: The system still successfully detects and reconstructs the event.
# ==============================================================================
def test_6_no_laughter():
    segments = [
        make_segment(0, 10.0, 18.0, "You know what the biggest paradox in corporate life is?"),
        make_segment(1, 18.5, 24.0, "They give you unlimited sick leave, but getting sick requires 4 approvals in Jira!"),
        make_segment(2, 24.5, 28.0, "Dead silence in the meeting room while everyone agrees.")
    ]
    transcript = TranscriptResult(language="en", duration=45.0, segments=segments, full_text=" ".join(s.text for s in segments))

    # No laughter event recorded
    audio_events = [
        AudioEvent(event_type="silence", start_time=18.0, end_time=18.4, intensity=0.8),
        AudioEvent(event_type="peak", start_time=21.0, end_time=21.5, intensity=0.92)
    ]
    analysis = AudioAnalysisResult(
        duration=45.0,
        events=audio_events,
        average_rms=0.2,
        peak_rms=0.92,
        peak_timestamps=[21.0],
        pause_timestamps=[18.0],
        laughter_timestamps=[]  # No laughter recorded
    )

    t_peak = 21.0
    recon = reconstruct_narrative_event(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=analysis,
        total_video_duration=45.0,
        target_duration=55.0
    )

    # Event must still be reconstructed properly
    assert recon.t_final_start <= 11.0, "Setup must still be identified"
    assert recon.t_final_end >= 25.0, "Resolution must be captured"
    assert recon.total_duration >= 14.0


# ==============================================================================
# TEST 7 — MULTIPLE PEAKS
# Setup -> punchline -> laughter -> second punchline -> larger laughter.
# Expected: ONE coherent event when the peaks belong to the same joke/story.
# ==============================================================================
def test_7_multiple_peaks():
    # Peak 1 at 20.0s (first laugh ends 24.0s)
    # Peak 2 at 26.5s (second laugh ends 33.0s)
    # Gap between 24.0s and 26.5s is 2.5s (<= 8.0s) -> belongs to same bit!
    peak_anchors = [
        {"t_peak": 20.0, "reaction_end": 24.0, "name": "Joke part 1"},
        {"t_peak": 26.5, "reaction_end": 33.0, "name": "Joke tagline part 2"},
        {"t_peak": 65.0, "reaction_end": 72.0, "name": "Completely separate joke later"}
    ]

    merged = merge_contiguous_event_peaks(peak_anchors, max_gap_sec=8.0)

    # The first two peaks must be merged into 1 event, leaving 2 events in total
    assert len(merged) == 2, f"Expected 2 merged events, got {len(merged)}"
    first_event = merged[0]
    assert first_event["is_merged_story"] is True
    assert first_event["t_peak"] == 26.5  # Climax peak
    assert first_event["reaction_end"] == 33.0  # Full resolution


# ==============================================================================
# TEST 8 — UNRELATED FOLLOWING CONTENT
# Punchline -> laughter -> new unrelated topic.
# Expected: Clip ends after meaningful reaction and does not include the unrelated topic.
# ==============================================================================
def test_8_unrelated_following_content():
    segments = [
        make_segment(0, 10.0, 18.0, "Ek baar kya hua main train mein baitha tha bina ticket."),
        make_segment(1, 18.5, 24.0, "TC ne bola ticket dikhao, maine bola sir mera aadhar card dekh lo shakl se garib lag raha hoon!"),
        make_segment(2, 24.5, 30.0, "Puri train zor zor se hasne lagi!"),
        # Next topic starts at 31.0s with explicit starter phrase:
        make_segment(3, 31.0, 42.0, "Anyway speaking of which yesterday I was checking stock market prices.")
    ]
    transcript = TranscriptResult(language="hi", duration=55.0, segments=segments, full_text=" ".join(s.text for s in segments))

    audio_events = [
        AudioEvent(event_type="peak", start_time=21.0, end_time=21.5, intensity=0.9),
        AudioEvent(event_type="laughter", start_time=24.5, end_time=28.5, intensity=0.9)
    ]
    analysis = AudioAnalysisResult(
        duration=55.0,
        events=audio_events,
        average_rms=0.2,
        peak_rms=0.9,
        peak_timestamps=[21.0],
        pause_timestamps=[18.2],
        laughter_timestamps=[24.5, 27.0]
    )

    t_peak = 21.0
    laugh_start, reaction_end, reason = find_reaction_end(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=analysis,
        total_video_duration=55.0,
        post_roll_sec=3.5
    )

    # Must truncate BEFORE 31.0s where "Anyway speaking of which..." begins
    assert reaction_end <= 31.0, f"Expected reaction_end <= 31.0s, got {reaction_end}"
    assert "truncated before next joke topic" in reason.lower()
