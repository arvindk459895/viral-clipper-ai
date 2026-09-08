"""
ViralClipper AI Studio - Audio Analysis Module
Performs digital signal processing to detect laughter, applause, shouting,
dramatic pauses, and audio energy peaks. Also provides audio normalization.
"""
import math
from pathlib import Path
from typing import List, Dict, Any, Tuple
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


class AudioAnalysisResult(BaseModel):
    duration: float
    events: List[AudioEvent] = Field(default_factory=list)
    average_rms: float = 0.0
    peak_rms: float = 0.0
    peak_timestamps: List[float] = Field(default_factory=list)
    laughter_timestamps: List[float] = Field(default_factory=list)
    pause_timestamps: List[float] = Field(default_factory=list)


def analyze_audio_events(
    audio_path: str,
    hop_length_sec: float = 0.05
) -> AudioAnalysisResult:
    """
    Reads an audio file and detects acoustic events:
    - Audio energy peaks / shouting
    - Laughter bursts
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

    # 1. Detect Peaks & Shouting
    peak_indices, properties = find_peaks(
        rms_values,
        height=avg_rms * 1.8,
        distance=int(0.5 / hop_length_sec),
        prominence=avg_rms * 0.5
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

    # 2. Detect Dramatic Pauses / Awkward Silence (>0.35s below 25% avg RMS)
    pause_threshold = avg_rms * 0.25
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

    # 3. Detect Laughter & Applause
    # Laughter has rhythmic bursts: high variance of local RMS in 1.5s windows
    win_len = int(1.2 / hop_length_sec)
    for i in range(0, num_frames - win_len, win_len // 2):
        window = rms_values[i:i + win_len]
        w_mean = np.mean(window)
        w_std = np.std(window)
        t_center = round((i + win_len // 2) * hop_length_sec, 2)

        # Laughter bursts: moderate mean, high rhythmic variation
        if w_mean > avg_rms * 1.1 and (w_std / (w_mean + 1e-6)) > 0.4:
            laughter_timestamps.append(t_center)
            events.append(AudioEvent(
                event_type="laughter",
                start_time=round(i * hop_length_sec, 2),
                end_time=round((i + win_len) * hop_length_sec, 2),
                intensity=min(1.0, float(w_mean / max_rms)),
                description="Audience / presenter laughter burst"
            ))
        # Applause: sustained high energy with low variance
        elif w_mean > avg_rms * 1.5 and (w_std / (w_mean + 1e-6)) <= 0.3:
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
        pause_timestamps=pause_timestamps
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
