"""
ViralClipper AI Studio - Audio Analysis Module
Performs digital signal processing to detect laughter, applause, shouting,
dramatic pauses, and audio energy peaks. Also provides audio normalization.
"""
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
from pydantic import BaseModel, Field
import soundfile as sf
from scipy.signal import find_peaks


class AudioEvent(BaseModel):
    event_type: str = Field(..., description="laughter, applause, shouting, silence, or peak")
    start_time: float
    end_time: float
    intensity: float = 1.0  # 0.0 to 1.0
    description: str = ""


class AudioCalibrationProfile(BaseModel):
    median_rms: float = 0.0
    p10_noise_floor: float = 0.0
    p25_rms: float = 0.0
    p50_rms: float = 0.0
    p75_rms: float = 0.0
    p90_speech_ref: float = 0.0
    p99_burst_ref: float = 0.0
    dynamic_range_db: float = 0.0
    is_compressed_audio: bool = False
    adaptive_pause_threshold: float = 0.0
    adaptive_burst_threshold: float = 0.0
    adaptive_burst_multiplier: float = 1.8
    adaptive_laughter_threshold: float = 0.0
    description: str = ""


class AudioAnalysisResult(BaseModel):
    duration: float
    events: List[AudioEvent] = Field(default_factory=list)
    average_rms: float = 0.0
    peak_rms: float = 0.0
    peak_timestamps: List[float] = Field(default_factory=list)
    laughter_timestamps: List[float] = Field(default_factory=list)
    pause_timestamps: List[float] = Field(default_factory=list)
    calibration: Optional[AudioCalibrationProfile] = None


def calibrate_audio_dsp(
    rms_values: Union[np.ndarray, str, Path],
    avg_rms: Optional[float] = None,
    max_rms: Optional[float] = None
) -> AudioCalibrationProfile:
    """
    Analyzes the complete audio distribution to calibrate per-video thresholds.
    Handles highly compressed podcasts, noisy audio, music beds, and normal dynamic range.
    Can accept precomputed rms_values array or audio file path.
    """
    if isinstance(rms_values, (str, Path)):
        data, sample_rate = sf.read(str(rms_values))
        if data.ndim > 1:
            data = np.mean(data, axis=1)
        hop_samples = int(0.1 * sample_rate)
        num_frames = max(1, len(data) // hop_samples)
        rms_arr = np.zeros(num_frames)
        for i in range(num_frames):
            frame = data[i * hop_samples : (i + 1) * hop_samples]
            rms_arr[i] = np.sqrt(np.mean(frame ** 2)) if len(frame) > 0 else 0.0
        rms_values = rms_arr
        avg_rms = float(np.mean(rms_values))
        max_rms = float(np.max(rms_values))

    if len(rms_values) == 0 or (max_rms is not None and max_rms <= 1e-6):
        return AudioCalibrationProfile(description="Silent or empty audio")

    avg_rms = float(np.mean(rms_values)) if avg_rms is None else avg_rms

    p10, p25, p50, p75, p90, p99 = np.percentile(rms_values, [10, 25, 50, 75, 90, 99])
    
    # Calculate robust dynamic range in dB
    dr_db = float(20.0 * np.log10(max(1e-5, p90) / max(1e-5, p10)))
    is_compressed = dr_db < 14.0 or (p10 > avg_rms * 0.45)

    if is_compressed:
        # Compressed podcast / studio audio: noise floor is raised, dynamic range is squashed
        # Pause threshold must move up (e.g. 35-40% of median) to detect conversational beats
        adaptive_pause = float(p10 + (p50 - p10) * 0.40)
        # Burst threshold adapts down toward ~1.35x-1.45x
        adaptive_burst = float(max(p75 * 1.15, p50 * 1.35))
        adaptive_multiplier = 1.40
        adaptive_laughter = float(max(p75 * 1.05, avg_rms * 1.05))
        desc = f"Compressed Podcast Profile (DR: {dr_db:.1f}dB, PauseThresh: {adaptive_pause:.4f}, BurstMult: 1.4x)"
    else:
        # Normal dynamic range (live stage comedy, wide dynamic range)
        adaptive_pause = float(max(p10 * 1.5, avg_rms * 0.25))
        adaptive_burst = float(max(avg_rms * 1.8, p90 * 0.95))
        adaptive_multiplier = 1.80
        adaptive_laughter = float(avg_rms * 1.10)
        desc = f"Dynamic Stage Profile (DR: {dr_db:.1f}dB, PauseThresh: {adaptive_pause:.4f}, BurstMult: 1.8x)"

    return AudioCalibrationProfile(
        median_rms=float(p50),
        p10_noise_floor=float(p10),
        p25_rms=float(p25),
        p50_rms=float(p50),
        p75_rms=float(p75),
        p90_speech_ref=float(p90),
        p99_burst_ref=float(p99),
        dynamic_range_db=round(dr_db, 2),
        is_compressed_audio=is_compressed,
        adaptive_pause_threshold=round(adaptive_pause, 5),
        adaptive_burst_threshold=round(adaptive_burst, 5),
        adaptive_burst_multiplier=adaptive_multiplier,
        adaptive_laughter_threshold=round(adaptive_laughter, 5),
        description=desc
    )


def analyze_audio_events(
    audio_path: str,
    hop_length_sec: float = 0.05
) -> AudioAnalysisResult:
    """
    Reads an audio file, performs per-video dynamic DSP calibration, and detects acoustic events:
    - Audio energy peaks / vocal punchlines
    - Subtle / deadpan punchline climaxes
    - Laughter bursts & audience eruption
    - Applause / crowd cheer
    - Dramatic pauses / awkward silences
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    data, sample_rate = sf.read(str(path))
    # Convert stereo to mono if needed
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    total_samples = len(data)
    duration = total_samples / float(sample_rate)
    if duration == 0:
        return AudioAnalysisResult(duration=0.0)

    # Compute short-time energy (RMS)
    hop_samples = int(hop_length_sec * sample_rate)
    num_frames = max(1, total_samples // hop_samples)
    rms_values = np.zeros(num_frames)

    for i in range(num_frames):
        start_idx = i * hop_samples
        end_idx = min(total_samples, start_idx + hop_samples)
        frame = data[start_idx:end_idx]
        rms_values[i] = np.sqrt(np.mean(frame ** 2)) if len(frame) > 0 else 0.0

    avg_rms = float(np.mean(rms_values))
    max_rms = float(np.max(rms_values)) if len(rms_values) > 0 else 0.0

    events: List[AudioEvent] = []
    peak_timestamps: List[float] = []
    laughter_timestamps: List[float] = []
    pause_timestamps: List[float] = []

    if max_rms == 0 or avg_rms == 0:
        return AudioAnalysisResult(duration=duration, average_rms=0.0, peak_rms=0.0)

    # 1. Per-Video Dynamic DSP Calibration
    calibration = calibrate_audio_dsp(rms_values, avg_rms, max_rms)

    # 2. Detect Vocal Burst Peaks & Shouting using Calibrated Threshold
    burst_threshold = calibration.adaptive_burst_threshold
    burst_prominence = max(0.001, calibration.p50_rms * 0.25)
    
    peak_indices, _ = find_peaks(
        rms_values,
        height=burst_threshold,
        distance=int(0.5 / hop_length_sec),
        prominence=burst_prominence
    )
    for idx in peak_indices:
        t = round(idx * hop_length_sec, 2)
        intensity = min(1.0, float(rms_values[idx] / (max_rms + 1e-6)))
        peak_timestamps.append(t)
        events.append(AudioEvent(
            event_type="shouting" if intensity > 0.8 else "peak",
            start_time=max(0.0, t - 0.2),
            end_time=min(duration, t + 0.4),
            intensity=intensity,
            description="High vocal energy / punchline delivery"
        ))

    # Deadpan / low-energy comedy support:
    # If peak count is low (< 3) or audio is compressed, detect subtle speech peaks
    if len(peak_indices) < 5:
        subtle_threshold = max(calibration.p50_rms * 1.1, calibration.p25_rms * 1.3)
        subtle_indices, _ = find_peaks(
            rms_values,
            height=subtle_threshold,
            distance=int(1.0 / hop_length_sec),
            prominence=max(0.0005, calibration.p50_rms * 0.15)
        )
        for idx in subtle_indices:
            t = round(idx * hop_length_sec, 2)
            if not any(abs(t - p) <= 0.8 for p in peak_timestamps):
                intensity = min(0.85, max(0.4, float(rms_values[idx] / (calibration.p90_speech_ref + 1e-6))))
                peak_timestamps.append(t)
                events.append(AudioEvent(
                    event_type="peak",
                    start_time=max(0.0, t - 0.2),
                    end_time=min(duration, t + 0.4),
                    intensity=intensity,
                    description="Subtle / deadpan comedic delivery"
                ))

    # 3. Detect Dramatic Pauses using Adaptive Pause Threshold
    pause_threshold = calibration.adaptive_pause_threshold
    in_pause = False
    pause_start = 0.0

    for i, rms in enumerate(rms_values):
        t = i * hop_length_sec
        if rms < pause_threshold:
            if not in_pause:
                in_pause = True
                pause_start = t
        else:
            if in_pause:
                in_pause = False
                pause_duration = t - pause_start
                if pause_duration >= 0.35 and pause_start > 1.0 and t < duration - 1.0:
                    pause_timestamps.append(round(pause_start, 2))
                    events.append(AudioEvent(
                        event_type="silence",
                        start_time=round(pause_start, 2),
                        end_time=round(t, 2),
                        intensity=0.8,
                        description="Dramatic pause / awkward comedic beat"
                    ))
    if in_pause and (duration - pause_start) >= 0.35:
        pause_timestamps.append(round(pause_start, 2))
        events.append(AudioEvent(
            event_type="silence",
            start_time=round(pause_start, 2),
            end_time=round(duration, 2),
            intensity=0.8,
            description="Ending pause"
        ))

    # 4. Detect Laughter & Applause using Adaptive Laughter Threshold
    win_len = int(1.2 / hop_length_sec)
    laugh_thresh = calibration.adaptive_laughter_threshold

    for i in range(0, num_frames - win_len, win_len // 2):
        window = rms_values[i:i + win_len]
        w_mean = np.mean(window)
        w_std = np.std(window)
        t_center = round((i + win_len // 2) * hop_length_sec, 2)

        # Laughter bursts: moderate mean, high rhythmic variation
        if w_mean > laugh_thresh and (w_std / (w_mean + 1e-6)) > 0.35:
            laughter_timestamps.append(t_center)
            events.append(AudioEvent(
                event_type="laughter",
                start_time=round(i * hop_length_sec, 2),
                end_time=round((i + win_len) * hop_length_sec, 2),
                intensity=min(1.0, float(w_mean / max_rms)),
                description="Audience / presenter laughter burst"
            ))
        # Applause: sustained high energy with low variance
        elif w_mean > avg_rms * 1.4 and (w_std / (w_mean + 1e-6)) <= 0.3:
            events.append(AudioEvent(
                event_type="applause",
                start_time=round(i * hop_length_sec, 2),
                end_time=round((i + win_len) * hop_length_sec, 2),
                intensity=min(1.0, float(w_mean / max_rms)),
                description="Crowd applause / cheer"
            ))

    # Deduplicate timestamps
    peak_timestamps = sorted(list(set(peak_timestamps)))
    laughter_timestamps = sorted(list(set(laughter_timestamps)))
    pause_timestamps = sorted(list(set(pause_timestamps)))

    return AudioAnalysisResult(
        duration=duration,
        events=events,
        average_rms=avg_rms,
        peak_rms=max_rms,
        peak_timestamps=peak_timestamps,
        laughter_timestamps=laughter_timestamps,
        pause_timestamps=pause_timestamps,
        calibration=calibration
    )


def compute_normalization_gain(audio_path: str, target_peak_db: float = -1.0) -> float:
    """
    Calculates linear gain factor to normalize audio to target peak dBFS.
    Avoids clipping and sudden volume changes.
    """
    data, _ = sf.read(str(audio_path))
    max_val = np.max(np.abs(data)) if len(data) > 0 else 0.0
    if max_val <= 1e-6:
        return 1.0

    target_linear = 10.0 ** (target_peak_db / 20.0)
    gain = target_linear / max_val
    return float(np.clip(gain, 0.2, 5.0))
