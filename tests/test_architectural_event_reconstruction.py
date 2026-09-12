"""
ViralClipper AI Studio - Architectural Event Reconstruction & Moment Capture Tests
Verifies the 5 Critical Acceptance Scenarios:
1. False Boundary Trap in Narrative Setup (Micro-payoff override preserving T-50s premise)
2. Acoustic Decay Protection vs Hard Stop (Reaction decay state machine deferring 'Acha suno...')
3. 58.5-Second Limit Collision & Intelligent Event Compression (75s event compressed <= 58.5s)
4. Dynamic Per-Video DSP Calibration on Compressed Audio (Adaptive thresholds)
5. Deadpan & Low-Energy Punchline Detection (Multi-signal compensation without 1.8x burst)
"""
import numpy as np
import pytest
from pathlib import Path

from src.transcription import TranscriptResult, TranscriptSegment
from src.audio_analysis import (
    AudioAnalysisResult,
    AudioEvent,
    AudioCalibrationProfile,
    calibrate_audio_dsp
)
from src.context_expander import (
    evaluate_narrative_depth,
    find_narrative_start_candidates,
    find_reaction_end,
    intelligently_compress_event,
    calculate_event_integrity,
    reconstruct_narrative_event,
    validate_micro_pause,
    DiagnosticCategory,
    ReactionState,
    ReconstructedEvent
)
from src.candidate_detector import detect_candidate_moments, CandidateClip


def test_critical_1_long_form_story_with_mini_payoffs():
    """
    Critical Test 1: Long-Form Story with Mini-Payoffs
    Scenario:
      T=10.0: "Maine gym join kiya tha doston" (True Premise opener)
      T=25.0: "Trainer bola weight lift karo" (Escalation)
      T=38.0: "Maine bola dumbbell nahi uthta" (Micro-payoff)
      T=40.0 - 43.0: Audience laughs at micro-payoff
      T=44.0: "Toh fir trainer ne pucha tera goal kya hai life mein?" (Story continues)
      T=56.0: Micro-pause
      T=57.0: "Maine bola goal bas ek hi hai bhai zinda rehna!" (Punchline / T_peak)
      T=58.0 - 66.0: Full audience eruption

    Verification:
      Prior bug: backward search saw laughter at 40-43s and cut at 43.5s, losing the premise.
      Fix: Override Rule identifies 38-44s as micro-payoff; T_event_start must be ~10.0s!
    """
    t_peak = 57.0

    segments = [
        TranscriptSegment(id=0, start=10.0, end=15.0, text="Maine gym join kiya tha doston.", words=[]),
        TranscriptSegment(id=1, start=16.0, end=24.0, text="Pehle din gaya main gym mein full enthusiasm ke sath.", words=[]),
        TranscriptSegment(id=2, start=25.0, end=32.0, text="Trainer bola chal pehle bench press karte hain.", words=[]),
        TranscriptSegment(id=3, start=33.0, end=39.0, text="Maine bola bhai dumbbell nahi uthta mujhse.", words=[]),
        TranscriptSegment(id=4, start=44.0, end=50.0, text="Toh fir trainer ne pucha tera goal kya hai life mein?", words=[]),
        TranscriptSegment(id=5, start=51.0, end=55.0, text="Maine do second socha aur dekh ke bola,", words=[]),
        TranscriptSegment(id=6, start=56.5, end=61.0, text="Goal bas ek hi hai bhai zinda rehna!", words=[]),
        TranscriptSegment(id=7, start=68.0, end=74.0, text="Agla topic hai shaadi ka, chalo suno.", words=[])
    ]
    transcript = TranscriptResult(text="", segments=segments, language="hi", duration=80.0)

    events = [
        # Intermediate laughter at micro-payoff (40.0s to 43.5s)
        AudioEvent(event_type="laughter", start_time=40.0, end_time=43.5, intensity=0.75),
        # Climax laughter after main punchline (57.5s to 66.5s)
        AudioEvent(event_type="laughter", start_time=57.5, end_time=66.5, intensity=0.95),
        # Dramatic micro-pause before punchline
        AudioEvent(event_type="silence", start_time=55.2, end_time=56.4, intensity=0.8)
    ]
    audio_analysis = AudioAnalysisResult(
        duration=80.0,
        events=events,
        average_rms=0.04,
        peak_rms=0.18,
        peak_timestamps=[38.5, 57.0],
        pause_timestamps=[55.5],
        laughter_timestamps=[40.5, 58.0]
    )

    # 1. Verify Narrative Depth evaluation classifies 44.0s as a micro-payoff
    depth_res = evaluate_narrative_depth(
        candidate_t=44.0,
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=audio_analysis
    )
    assert depth_res.is_micro_payoff is True
    assert depth_res.narrative_dependency_score >= 60.0
    assert depth_res.premise_origin_timestamp == 10.0

    # 2. Reconstruct narrative event
    recon = reconstruct_narrative_event(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=audio_analysis,
        total_video_duration=80.0,
        target_duration=55.0,
        max_clip_duration=58.5
    )

    # Crucial Assertion: Event start MUST capture the original premise at 10.0s, NOT cut at 43.5s!
    assert recon.t_event_start <= 11.0, f"Expected T_event_start ~10.0s, got {recon.t_event_start}s"
    assert recon.t_final_start <= 11.0, f"Expected T_final_start ~10.0s, got {recon.t_final_start}s"
    assert "Maine gym join kiya" in recon.event_text
    assert recon.event_integrity_score >= 85.0
    assert recon.cut_risk_score <= 15.0


def test_critical_2_punchline_active_laughter_immediate_transition():
    """
    Critical Test 2: Punchline + Active Laughter + Immediate Transition
    Scenario:
      T=30.0: Comedian delivers punchline
      T=30.5 - 40.0: Huge audience laughter ongoing
      T=34.0: Comedian starts speaking next topic: "Acha suno agla joke..."
      
    Verification:
      Prior bug: Topic shift hard cut fired at 34.0 - 0.3 = 33.7s, abruptly cutting laughter.
      Fix: Reaction Decay State Machine detects REACTION_ACTIVE (laughter extends to 40.0s).
           Topic cut is DEFERRED, keeping laughter through at least 41.0s!
    """
    t_peak = 30.0

    segments = [
        TranscriptSegment(id=0, start=15.0, end=22.0, text="Ek baar kya hua flight mein,", words=[]),
        TranscriptSegment(id=1, start=23.0, end=29.0, text="Pilot ne bola engine band ho gaya hai.", words=[]),
        TranscriptSegment(id=2, start=29.5, end=32.0, text="Maine bola ticket ke paise wapas milenge?", words=[]),
        # Comedian interrupts active laughter with topic shift at 34.0s!
        TranscriptSegment(id=3, start=34.0, end=38.0, text="Acha suno ab agla topic shuru karte hain.", words=[]),
        TranscriptSegment(id=4, start=39.0, end=45.0, text="By the way dusri baat suno sab log.", words=[])
    ]
    transcript = TranscriptResult(text="", segments=segments, language="hi", duration=50.0)

    events = [
        # Sustained audience eruption from 30.5s to 40.0s
        AudioEvent(event_type="laughter", start_time=30.5, end_time=40.0, intensity=0.95)
    ]
    audio_analysis = AudioAnalysisResult(
        duration=50.0,
        events=events,
        average_rms=0.05,
        peak_rms=0.20,
        peak_timestamps=[30.0],
        pause_timestamps=[],
        laughter_timestamps=[31.0]
    )

    laugh_start, reaction_end, reason = find_reaction_end(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=audio_analysis,
        total_video_duration=50.0,
        post_roll_sec=3.5
    )

    # Crucial Assertion: reaction_end MUST NOT be chopped at 33.7s!
    # Laughter continues to 40.0s, so reaction_end must extend to >= 41.0s.
    assert reaction_end >= 41.0, f"Expected reaction_end >= 41.0s, but got {reaction_end}s (chopped early!)"
    assert "deferred" in reason.lower(), f"Expected 'deferred' in reason, got: {reason}"


def test_critical_3_intelligent_event_compression_for_75s_event():
    """
    Critical Test 3: 75-Second Complete Event
    Scenario:
      A standup routine is naturally 75 seconds:
      T=0.0 - 10.0: Premise opener ("Maine gym join kiya...")
      T=11.0 - 45.0: Long descriptive middle setup with filler and tangents
      T=46.0 - 62.0: Escalation, tension building
      T=63.0: Punchline delivery
      T=64.0 - 74.0: Audience eruption

    Verification:
      Prior behavior: either blindly chop premise (T_start = 74 - 58.5 = 15.5s)
      or blindly chop reaction.
      Fix: Intelligent Event Compression activates!
           Keeps Premise (0-10s) and Climax/Reaction (55-74s).
           Prunes middle filler, yielding a compressed Short <= 58.5s.
    """
    t_peak = 63.0

    segments = [
        # Premise (0-10s) - ESSENTIAL
        TranscriptSegment(id=0, start=0.0, end=6.0, text="Maine gym join kiya tha ek baar doston.", words=[]),
        TranscriptSegment(id=1, start=6.5, end=11.0, text="Bahut hi ajeeb experience tha mera wahan par.", words=[]),
        # Middle filler / redundant details (12-45s) - PRUNABLE
        TranscriptSegment(id=2, start=12.0, end=19.0, text="Matlab pehle din main subah subah utha tha paanch baje.", words=[]),
        TranscriptSegment(id=3, start=20.0, end=28.0, text="Ghar se nikalte waqt socha ki aaj toh body bana ke hi aaunga.", words=[]),
        TranscriptSegment(id=4, start=29.0, end=38.0, text="Wahan jaake dekha toh sab log protein shake pi rahe the aur mirror dekh rahe the.", words=[]),
        TranscriptSegment(id=5, start=39.0, end=47.0, text="Toh basically main aage badha aur trainer se milne gaya.", words=[]),
        # Escalation (48-62s) - ESSENTIAL
        TranscriptSegment(id=6, start=48.0, end=55.0, text="Trainer bola bench press pe so jao aur 50 kilo uthao.", words=[]),
        TranscriptSegment(id=7, start=56.0, end=62.0, text="Maine bola bhai 50 kilo mein meri aatma nikal jayegi!", words=[]),
        # Punchline & Reaction (63-74s) - ESSENTIAL
        TranscriptSegment(id=8, start=63.0, end=67.0, text="Usne pucha goal kya hai? Maine bola bas kal subah uth jana!", words=[]),
        TranscriptSegment(id=9, start=68.0, end=74.0, text="Sab log zor zor se hasne lage!", words=[])
    ]
    transcript = TranscriptResult(text="", segments=segments, language="hi", duration=80.0)

    events = [
        AudioEvent(event_type="laughter", start_time=64.0, end_time=73.0, intensity=0.95)
    ]
    audio_analysis = AudioAnalysisResult(
        duration=80.0,
        events=events,
        average_rms=0.04,
        peak_rms=0.19,
        peak_timestamps=[63.0],
        pause_timestamps=[62.2],
        laughter_timestamps=[64.5]
    )

    recon = reconstruct_narrative_event(
        t_peak=t_peak,
        transcript=transcript,
        audio_analysis=audio_analysis,
        total_video_duration=80.0,
        target_duration=55.0,
        max_clip_duration=58.5
    )

    # Assertions
    assert recon.natural_event_duration >= 70.0, f"Expected natural duration >= 70s, got {recon.natural_event_duration}"
    assert recon.compression_applied is True
    assert recon.total_duration <= 58.5, f"Compressed duration {recon.total_duration}s exceeds 58.5s ceiling!"
    assert len(recon.compressed_segments) >= 2
    # Verify Premise is preserved in first interval
    first_interval = recon.compressed_segments[0]
    assert first_interval[0] == 0.0, "Premise start was destroyed!"
    # Verify Climax & Reaction are preserved in last interval
    last_interval = recon.compressed_segments[-1]
    assert last_interval[1] >= 72.0, "Audience reaction was truncated!"
    assert recon.diagnostic_classification == DiagnosticCategory.SUCCESS


def test_critical_4_compressed_podcast_audio_dynamic_calibration(tmp_path):
    """
    Critical Test 4: Dynamic Per-Video DSP Calibration on Compressed Audio
    Scenario:
      A heavily dynamic-compressed podcast recording (e.g. broadcast compressor applied).
      Noise floor is high, RMS variance is low, dynamic range < 12 dB.
    Verification:
      calibrate_audio_dsp detects is_compressed_audio = True, adjusts adaptive_pause_threshold
      and adaptive_burst_multiplier dynamically instead of failing on rigid hardcoded thresholds.
    """
    import soundfile as sf

    sr = 16000
    dur = 5.0
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    
    # Generate compressed audio signal: speech with elevated noise floor
    # Amplitude stays consistently between 0.15 and 0.35 (narrow dynamic range)
    noise = np.random.normal(0, 0.08, len(t))
    speech = 0.25 * np.sin(2 * np.pi * 300 * t) * (1.0 + 0.3 * np.sin(2 * np.pi * 2 * t))
    compressed_signal = np.clip(speech + noise, -0.4, 0.4).astype(np.float32)

    wav_path = tmp_path / "compressed_podcast.wav"
    sf.write(str(wav_path), compressed_signal, sr)

    profile = calibrate_audio_dsp(str(wav_path))

    # Assertions
    assert profile.median_rms > 0.0
    assert profile.dynamic_range_db < 20.0
    assert profile.is_compressed_audio is True
    # Adaptive thresholds must adapt:
    assert profile.adaptive_burst_multiplier < 1.8  # Adapted from standard 1.8x down to ~1.4x
    assert profile.adaptive_pause_threshold > 0.0
    assert "DR:" in profile.description or "Dynamic Range" in profile.description


def test_critical_5_deadpan_low_energy_punchline_detection():
    """
    Critical Test 5: Deadpan / Low-Energy Punchline Detection
    Scenario:
      Deadpan comedian delivers a killer punchline in a flat, quiet voice (no 1.8x vocal burst).
      Preceded by a micro-pause and followed immediately by huge audience laughter.
    Verification:
      validate_micro_pause and subtle_peak detection identify this beat as a valid punchline
      via multi-signal compensation (pause + semantic question/answer + audience laughter).
    """
    pause_time = 14.0
    burst_time = 14.8

    segments = [
        TranscriptSegment(id=0, start=10.0, end=13.8, text="Trainer ne pucha goal kya hai?", words=[]),
        TranscriptSegment(id=1, start=14.8, end=17.0, text="Maine bola zinda rehna.", words=[])  # Deadpan punchline
    ]
    transcript = TranscriptResult(text="", segments=segments, language="hi", duration=30.0)

    # Audio analysis has subtle peak and laughter, but no massive 1.8x vocal burst
    events = [
        AudioEvent(event_type="silence", start_time=13.8, end_time=14.5, intensity=0.8),
        AudioEvent(event_type="subtle_peak", start_time=14.8, end_time=15.5, intensity=0.75),
        AudioEvent(event_type="laughter", start_time=16.0, end_time=22.0, intensity=0.90)
    ]
    audio_analysis = AudioAnalysisResult(
        duration=30.0,
        events=events,
        average_rms=0.06,
        peak_rms=0.10,  # Only 1.6x average (below old 1.8x threshold)
        peak_timestamps=[14.8],
        pause_timestamps=[14.0],
        laughter_timestamps=[16.5]
    )

    # 1. Micro-pause validation with multi-signal evidence
    is_valid, conf, details = validate_micro_pause(
        pause_time=14.0,
        audio_analysis=audio_analysis,
        transcript=transcript
    )
    assert is_valid is True
    assert conf >= 0.70
    assert details["has_laughter"] is True
    assert details["has_semantic_climax"] is True

    # 2. Reconstructed event captures deadpan bit cleanly
    recon = reconstruct_narrative_event(
        t_peak=14.8,
        transcript=transcript,
        audio_analysis=audio_analysis,
        total_video_duration=30.0,
        target_duration=20.0,
        max_clip_duration=30.0
    )
    assert recon.t_final_start <= 10.5
    assert recon.t_final_end >= 20.0
    assert recon.event_integrity_score >= 85.0
