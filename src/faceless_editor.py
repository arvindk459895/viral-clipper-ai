"""
ViralClipper AI Studio - Faceless Video Assembly & Multi-Track Audio Mixing Engine
Interleaves source footage with AI voice commentary, original cartoon/comic visuals,
and diagrams according to the 7-beat editorial structure:
[AI Hook] -> [Source Setup] -> [AI Context] -> [Source Punchline] -> [AI Reaction/Analysis] -> [Source Laughter] -> [AI Conclusion]
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable

import wave
import numpy as np
from src.config import OUTPUTS_DIR, TEMP_DIR, TARGET_WIDTH, TARGET_HEIGHT, TARGET_FPS
from src.utils import run_ffmpeg, sanitize_filename
from src.candidate_detector import CandidateClip, is_clean_sentence_end
from src.transcription import TranscriptSegment, TranscriptWord
from src.commentary_engine import CommentaryScript
from src.ai_voice import generate_ai_voice, clean_spoken_text
from src.visual_generator import generate_faceless_visual_package
from src.captions import generate_ass_subtitles
from src.originality_report import generate_originality_report, OriginalityReport
from src.meme_selector import select_video_meme_cutaway


def _render_source_video_with_voiceover(
    video_path: str,
    audio_path: str,
    start_t: float,
    duration_t: float,
    voiceover_audio_path: str,
    output_path: Path
) -> str:
    """
    Renders 9:16 blurred background source video while ducking source audio
    and mixing in the AI voiceover narration cleanly.
    """
    dur_str = f"{duration_t:.3f}"
    ss_str = f"{start_t:.3f}"

    filter_str = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=25:5[blurred];"
        f"[fg]scale={TARGET_WIDTH}:608[scaled];"
        f"[blurred][scaled]overlay=0:656[v];"
        f"[1:a]volume=0.20[bg_aud];"
        f"[2:a]volume=1.20[voice_aud];"
        f"[bg_aud][voice_aud]amix=inputs=2:duration=longest[a]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", ss_str, "-t", dur_str, "-i", video_path,
        "-ss", ss_str, "-t", dur_str, "-i", audio_path,
        "-i", str(voiceover_audio_path),
        "-filter_complex", filter_str,
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-r", str(TARGET_FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-t", dur_str,
        str(output_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(output_path)


def _render_paused_frame_with_voiceover(
    video_path: str,
    frame_t: float,
    duration_t: float,
    voiceover_audio_path: str,
    output_path: Path
) -> str:
    """
    Extracts a snapshot frame at frame_t and renders a 9:16 blurred vertical segment
    with the video PAUSED (frozen on that exact moment) while playing the AI voiceover.
    Eliminates lip-sync mismatch and focuses audience attention entirely on the commentary.
    """
    dur_str = f"{duration_t:.3f}"
    ss_str = f"{frame_t:.3f}"
    temp_frame = output_path.parent / f"{output_path.stem}_frame.jpg"

    # 1. Extract high quality snapshot frame
    cmd_extract = [
        "ffmpeg", "-y",
        "-ss", ss_str, "-i", video_path,
        "-frames:v", "1", "-q:v", "2",
        str(temp_frame)
    ]
    subprocess.run(cmd_extract, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 2. Render paused 9:16 blurred vertical video holding that exact frame with Cinematic Dark & Cyan atmosphere glow
    filter_str = (
        f"[0:v]split=2[bg][fg];"
        f"[bg]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=28:6,colorchannelmixer=rr=0.60:gg=1.12:bb=1.45,vignette=PI/3.5:aspect=9/16[blurred];"
        f"[fg]scale={TARGET_WIDTH}:608,eq=contrast=1.22:brightness=-0.04:saturation=1.15,unsharp=5:5:0.8:5:5:0.0[scaled];"
        f"[blurred][scaled]overlay=0:656[v]"
    )
    cmd_render = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(temp_frame),
        "-i", str(voiceover_audio_path),
        "-filter_complex", filter_str,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-r", str(TARGET_FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-t", dur_str,
        "-shortest",
        str(output_path)
    ]
    subprocess.run(cmd_render, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(output_path)


def _render_video_meme_segment(
    meme_path: str,
    output_path: Path
) -> str:
    """
    Normalizes a video meme cutaway to the target 1080x1920 30fps with stereo 44.1k AAC audio.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(meme_path),
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-r", str(TARGET_FPS),
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(output_path)


def _render_image_audio_segment(
    image_path: str,
    audio_path: str,
    duration_sec: float,
    output_path: Path
) -> str:
    """Renders a static 1080x1920 card with voiceover audio into a normalized MP4 segment."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-t", f"{duration_sec:.3f}",
        "-pix_fmt", "yuv420p",
        "-r", str(TARGET_FPS),
        "-vf", f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-ac", "2",
        str(output_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(output_path)


def _render_source_video_segment(
    video_path: str,
    audio_path: str,
    start_t: float,
    end_t: float,
    output_path: Path,
    overlay_badge: Optional[str] = None
) -> str:
    """
    Renders an excerpt of the source video in 9:16 blurred background format,
    optionally overlaying an original cartoon reaction badge.
    """
    dur = max(0.5, end_t - start_t)
    ss_str = f"{start_t:.3f}"
    t_str = f"{dur:.3f}"

    if overlay_badge and Path(overlay_badge).exists():
        filter_str = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=28:6,colorchannelmixer=rr=0.60:gg=1.12:bb=1.45,vignette=PI/3.5:aspect=9/16[blurred];"
            f"[fg]scale={TARGET_WIDTH}:608,eq=contrast=1.22:brightness=-0.04:saturation=1.15,unsharp=5:5:0.8:5:5:0.0[scaled];"
            f"[blurred][scaled]overlay=0:656[staged];"
            f"[2:v]scale=220:220[badge];"
            f"[staged][badge]overlay=W-w-60:680:shortest=1[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", ss_str, "-t", t_str, "-i", video_path,
            "-ss", ss_str, "-t", t_str, "-i", audio_path,
            "-i", str(overlay_badge),
            "-filter_complex", filter_str,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-r", str(TARGET_FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-t", t_str,
            "-shortest",
            str(output_path)
        ]
    else:
        filter_str = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,crop={TARGET_WIDTH}:{TARGET_HEIGHT},boxblur=28:6,colorchannelmixer=rr=0.60:gg=1.12:bb=1.45,vignette=PI/3.5:aspect=9/16[blurred];"
            f"[fg]scale={TARGET_WIDTH}:608,eq=contrast=1.22:brightness=-0.04:saturation=1.15,unsharp=5:5:0.8:5:5:0.0[scaled];"
            f"[blurred][scaled]overlay=0:656[v]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", ss_str, "-t", t_str, "-i", video_path,
            "-ss", ss_str, "-t", t_str, "-i", audio_path,
            "-filter_complex", filter_str,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast", "-r", str(TARGET_FPS),
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-t", t_str,
            "-shortest",
            str(output_path)
        ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return str(output_path)


def _generate_dynamic_phonk_bgm(
    total_short_dur: float,
    hook_dur: float,
    setup_dur: float,
    punch_dur: float,
    meme_dur: float,
    outro_dur: float,
    output_wav_path: Path
) -> Optional[str]:
    """
    Constructs an automated volume envelope for the Phonk / Trap beat:
    - Beat 1 & 2 (Hook & Setup): Low-tempo beat playing softly at -22dB (0.08) under dialogue.
    - Beat 3 (Punchline / Climax): Beats swell smoothly from -20dB to -12dB (0.28, +10dB boost) for the beat drop!
    - Beat 4 (Meme Cutaway): Muted (0.00) so the meme clip audio lands at 100% full volume.
    - Beat 5 (Outro): Resumes softly at -22dB (0.08) and fades to 0 over the final 0.8s.
    """
    bgm_source = Path("assets/music/phonk_beat.wav")
    if not bgm_source.exists():
        return None

    sample_rate = 44100
    num_samples = int(total_short_dur * sample_rate)
    env = np.zeros(num_samples, dtype=np.float32)

    t1 = hook_dur
    t2 = t1 + setup_dur
    t3 = t2 + punch_dur
    t4 = t3 + meme_dur
    t5 = t4 + outro_dur

    # Beat 1 (Hook): 0.08
    s1 = int(t1 * sample_rate)
    env[:s1] = 0.08

    # Beat 2 (Setup Dialogue): 0.08
    s2 = int(t2 * sample_rate)
    env[s1:s2] = 0.08

    # Beat 3 (Punchline & Climax):
    # First 60% is 0.09, last 40% (or last 3.5s) swells smoothly to 0.28 (Beat Drop!)
    s3 = int(t3 * sample_rate)
    swell_dur = min(3.5, max(1.5, punch_dur * 0.45))
    swell_start_t = t3 - swell_dur
    s_swell = int(swell_start_t * sample_rate)
    env[s2:s_swell] = 0.09
    if s3 > s_swell:
        env[s_swell:s3] = np.linspace(0.09, 0.28, s3 - s_swell)

    # Beat 4 (Meme Cutaway): Muted (0.0)
    s4 = int(t4 * sample_rate)
    env[s3:s4] = 0.0

    # Beat 5 (Outro): 0.08 with smooth 0.8s fade out at the end
    s5 = min(num_samples, int(t5 * sample_rate))
    fade_samples = int(0.8 * sample_rate)
    if s5 > s4:
        env[s4:s5] = 0.08
        if (s5 - s4) > fade_samples:
            env[s5 - fade_samples:s5] = np.linspace(0.08, 0.0, fade_samples)
        else:
            env[s4:s5] = np.linspace(0.08, 0.0, s5 - s4)

    # Read source phonk audio
    with wave.open(str(bgm_source), 'rb') as wf:
        n_ch = wf.getnchannels()
        s_width = wf.getsampwidth()
        fr = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    raw_audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
    if n_ch == 2:
        raw_audio = raw_audio.reshape(-1, 2)
    else:
        raw_audio = np.column_stack((raw_audio, raw_audio))

    # Loop phonk beat if total_short_dur > source duration
    if len(raw_audio) < num_samples:
        repeats = (num_samples // len(raw_audio)) + 1
        raw_audio = np.tile(raw_audio, (repeats, 1))
    raw_audio = raw_audio[:num_samples]

    # Apply envelope
    shaped_audio = raw_audio * env[:, np.newaxis]
    int16_out = np.clip(shaped_audio, -32768, 32767).astype(np.int16)

    output_wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_wav_path), 'wb') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int16_out.tobytes())

    return str(output_wav_path)



def render_faceless_commentary_short(
    video_path: str,
    audio_path: str,
    candidate: CandidateClip,
    script: CommentaryScript,
    transcript_segments: List[TranscriptSegment],
    voice_style: str = "madhur",
    narration_speed: float = 1.5,
    output_path: Optional[Path] = None,
    top_header_text: Optional[str] = None,
    editorial_purpose: str = "Viral comedy reaction, creator commentary & timing analysis",
    visual_mode: str = "video_cutaway",
    meme_style: str = "cutaway",
    humor_type: Optional[str] = None,
    clip_index: int = 0,
    dialogue_text: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None
) -> Dict[str, Any]:
    """
    Renders a complete Faceless AI Commentary Short (RC Hidden Style):
    - Generates AI voiceover audio across hook and outro segments at energetic 1.5x pacing.
    - Slices source video into discrete setup and punchline/reaction beats.
    - Splices a seamless 1-2s viral video meme cutaway clip at the climax.
    - Plays AI voiceover over source video with ducked background audio (no static text cards).
    - Burns persistent top header banner and subtitles.
    - Audits originality and returns an OriginalityReport.
    """
    if progress_callback:
        progress_callback(0.05, "Synthesizing AI voiceover narration & dialogue analysis...")

    safe_id = sanitize_filename(candidate.clip_id)
    out_file = output_path or (OUTPUTS_DIR / f"{safe_id}_faceless_{voice_style}.mp4")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Synthesize AI Voices with Native Language & Emotion at 1.5x speed
    lang = getattr(script, "language", "hinglish")
    hook_emo = getattr(script, "hook_emotion", "excited")
    ctx_emo = getattr(script, "context_emotion", "sarcastic")
    ana_emo = getattr(script, "analysis_emotion", "cheerful")
    concl_emo = getattr(script, "conclusion_emotion", "cheerful")

    hook_v = generate_ai_voice(
        text=script.hook,
        voice_style=voice_style,
        emotion=hook_emo,
        language=lang,
        speed=narration_speed,
        clip_id=f"{safe_id}_v1_hook"
    )
    context_v = generate_ai_voice(
        text=script.context_commentary,
        voice_style=voice_style,
        emotion=ctx_emo,
        language=lang,
        speed=narration_speed,
        clip_id=f"{safe_id}_v2_ctx"
    )
    analysis_v = generate_ai_voice(
        text=script.analysis_reaction,
        voice_style=voice_style,
        emotion=ana_emo,
        language=lang,
        speed=narration_speed,
        clip_id=f"{safe_id}_v3_ana"
    )
    conclusion_v = generate_ai_voice(
        text=script.conclusion,
        voice_style=voice_style,
        emotion=concl_emo,
        language=lang,
        speed=narration_speed,
        clip_id=f"{safe_id}_v4_concl"
    )

    # 2. Synthesize Original Visual Assets (fallback or badges)
    visuals = generate_faceless_visual_package(safe_id, script.to_dict())

    # 3. Define Source Excerpts & Dynamic Pacing
    setup_start = candidate.start_time
    punch_t = candidate.punchline_time
    clip_end = candidate.end_time

    seg_dir = TEMP_DIR / f"{safe_id}_segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    if visual_mode == "video_cutaway":
        # === RC HIDDEN / VIRAL SHORTS MODE: Engaging 6-Beat Reaction Short ===
        # Beat 1 Duration (Hook)
        hook_dur = max(2.2, round(hook_v["duration_sec"] + 0.2, 2))

        # Beat 5 Audio & Duration (Outro Roaster Verdict & CTA)
        outro_text = clean_spoken_text(f"{script.analysis_reaction} {script.conclusion}")
        outro_v = generate_ai_voice(
            text=outro_text,
            voice_style=voice_style,
            emotion=ana_emo,
            language=lang,
            speed=narration_speed,
            clip_id=f"{safe_id}_v_outro"
        )
        # Ensure outro duration ALWAYS covers the full generated voiceover audio + comfortable padding
        outro_dur = max(2.5, round(outro_v["duration_sec"] + 0.3, 2))

        # Beat 4 Meme Selection & Duration
        resolved_humor = humor_type or getattr(candidate, "humor_type", "unexpected_answer")
        resolved_dialogue = dialogue_text or getattr(candidate, "text", "")
        meme_file = select_video_meme_cutaway(
            humor_type=resolved_humor,
            emotion=ana_emo,
            dialogue_text=resolved_dialogue,
            clip_index=clip_index
        )
        if meme_file and Path(meme_file).exists():
            probe_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(meme_file)]
            try:
                raw_meme_dur = float(subprocess.check_output(probe_cmd, text=True).strip())
                meme_dur = round(min(2.5, max(1.2, raw_meme_dur)), 2)
            except Exception:
                meme_dur = 1.8
        else:
            meme_dur = round(context_v["duration_sec"], 2)

        # Probe source video duration to prevent any out-of-bounds frame extraction
        total_vid_dur = None
        try:
            probe_vid = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)]
            total_vid_dur = float(subprocess.check_output(probe_vid, text=True).strip())
        except Exception:
            pass

        # Dynamic YouTube Shorts Duration Budget (Max 58.0s to strictly stay within 60s limit)
        MAX_TOTAL_SHORT_DUR = 58.0
        ai_overhead = round(hook_dur + meme_dur + outro_dur, 2)
        max_source_budget = max(20.0, round(MAX_TOTAL_SHORT_DUR - ai_overhead, 2))

        # Calculate Scene Boundaries: Guarantee complete story setup through punchline and clean resolution
        cand_start = candidate.start_time
        punch_t = candidate.punchline_time
        cand_end = candidate.end_time

        if punch_t <= cand_start + 1.0:
            punch_t = cand_start + 3.5
        if cand_end <= punch_t + 1.0:
            cand_end = punch_t + 5.0

        # Look for the natural conclusion of the joke/scene
        # The punchline climax & audience reaction extends through and beyond punch_t
        # Find all sentence endings or speech pauses after punch_t
        post_punch_segs = [
            s for s in transcript_segments
            if s.end >= punch_t + 1.5 and s.start <= cand_end + 10.0
        ]

        # Prioritize clean thought ends after punch_t that fit within the Shorts budget
        clean_ends = [
            s.end for s in post_punch_segs
            if (is_clean_sentence_end(s.text) or s.text.strip().endswith(("?", "!", ".", "।", "॥")))
            and s.end >= punch_t + 2.0
        ]

        if clean_ends:
            # Pick the furthest clean sentence end that fits within our source duration budget
            budgeted_ends = [e for e in clean_ends if (e - cand_start) <= max_source_budget]
            target_resolution = budgeted_ends[-1] if budgeted_ends else clean_ends[0]
        else:
            # If no explicit punctuation, use the latest transcript segment within budget
            budgeted_segs = [s.end for s in post_punch_segs if (s.end - cand_start) <= max_source_budget]
            target_resolution = budgeted_segs[-1] if budgeted_segs else max(cand_end, punch_t + 5.0)

        scene_end = round(target_resolution, 2)
        if total_vid_dur and total_vid_dur > 2.0:
            scene_end = min(scene_end, round(total_vid_dur - 0.1, 2))

        # Budget source duration: Start from cand_start, or if the scene is long, ensure setup has at least 8-12s
        req_dur = round(scene_end - cand_start, 2)
        if req_dur <= max_source_budget:
            scene_start = cand_start
        else:
            # If the entire story exceeds budget, back up from punch_t to give ample setup
            raw_start = max(cand_start, round(scene_end - max_source_budget, 2))
            valid_starts = [
                s.start for s in transcript_segments
                if raw_start - 2.0 <= s.start <= punch_t - 5.0
            ]
            scene_start = round(valid_starts[0], 2) if valid_starts else raw_start

        # Snap scene_start and scene_end cleanly to speech boundaries so words/sentences are never sliced mid-syllable
        for idx, s in enumerate(transcript_segments):
            if s.start < scene_start < s.end:
                scene_start = round(s.start, 2)
                break

        for idx, s in enumerate(transcript_segments):
            if s.start < scene_end < s.end:
                scene_end = round(s.end, 2)
                break

        # Split into Beat 2 (Setup Dialogue) and Beat 3 (Punchline & Reaction Payoff)
        # Find natural transcript segment boundary right before punchline
        pre_punch_segs = [
            s.end for s in transcript_segments
            if scene_start + 2.0 <= s.end <= punch_t - 0.2 and s.end <= scene_end - 2.0
        ]
        if pre_punch_segs:
            split_t = round(pre_punch_segs[-1], 2)
        else:
            split_t = round(max(scene_start + 2.0, min(punch_t - 0.4, scene_end - 2.0)), 2)

        # Beat 1: Hook (AI Voiceover with video PAUSED on opening moment)
        if progress_callback:
            progress_callback(0.20, "Rendering Beat 1: Dynamic hook narration...")
        seg1_path = seg_dir / "seg1_hook.mp4"
        _render_paused_frame_with_voiceover(
            video_path=video_path,
            frame_t=scene_start,
            duration_t=hook_dur,
            voiceover_audio_path=hook_v["audio_path"],
            output_path=seg1_path
        )

        # Beat 2: Source Setup Dialogue (Video UNPAUSES and plays live dialogue at 100% volume)
        if progress_callback:
            progress_callback(0.38, "Rendering Beat 2: Setup dialogue with Cinematic Dark grade...")
        seg2_start = scene_start
        setup_end = split_t
        seg2_dur = round(setup_end - seg2_start, 2)
        seg2_path = seg_dir / "seg2_setup.mp4"
        _render_source_video_segment(video_path, audio_path, seg2_start, setup_end, seg2_path)

        # Beat 3: Source Punchline & Climax (Original punchline dialogue lands live at 100% volume with reaction sticker)
        if progress_callback:
            progress_callback(0.56, "Rendering Beat 3: Punchline climax with reaction badge & cyan glow...")
        punch_start = setup_end
        punch_end = scene_end
        seg3_dur = round(punch_end - punch_start, 2)
        seg3_path = seg_dir / "seg3_punchline.mp4"

        sticker_path = Path("assets/stickers/dizzy_blue_emoji.png")
        overlay_sticker = str(sticker_path) if sticker_path.exists() else visuals["reaction_badge"]
        _render_source_video_segment(video_path, audio_path, punch_start, punch_end, seg3_path, overlay_badge=overlay_sticker)

        # Beat 4: Clean Viral Meme Cutaway (RIGHT AFTER punchline, 1.2 to 2.0s)
        if progress_callback:
            progress_callback(0.72, "Rendering Beat 4: Live-action meme cutaway...")
        seg4_path = seg_dir / "seg4_meme.mp4"
        if meme_file and Path(meme_file).exists():
            _render_video_meme_segment(str(meme_file), seg4_path)
        else:
            _render_image_audio_segment(visuals["hook_card"], context_v["audio_path"], context_v["duration_sec"], seg4_path)

        # Beat 5: Roaster Verdict & Outro (Video PAUSES on reaction face while creator roasts + CTA)
        if progress_callback:
            progress_callback(0.82, "Rendering Beat 5: Outro commentary & Like/Subscribe CTA...")
        max_frame_t = (total_vid_dur - 0.2) if total_vid_dur else (scene_end - 0.2)
        target_frame_t = max(punch_start + 0.5, scene_end - 0.2)
        outro_frame_t = round(max(0.5, min(max_frame_t, target_frame_t)), 2)
        seg5_path = seg_dir / "seg5_outro.mp4"
        _render_paused_frame_with_voiceover(
            video_path=video_path,
            frame_t=outro_frame_t,
            duration_t=outro_dur,
            voiceover_audio_path=outro_v["audio_path"],
            output_path=seg5_path
        )

        total_source_dur = round(seg2_dur + seg3_dur, 2)
        total_ai_comm_dur = round(hook_dur + outro_dur, 2)
        total_ai_vis_dur = round(meme_dur, 2)
        total_short_dur = round(hook_dur + seg2_dur + seg3_dur + meme_dur + outro_dur, 2)

        # Build word-level subtitle segments for the complete flow
        sub_segments: List[TranscriptSegment] = []
        cur_t = 0.0

        # Hook words
        hook_words_raw = clean_spoken_text(script.hook).split()
        if hook_words_raw:
            w_step = (hook_dur - 0.4) / max(1, len(hook_words_raw))
            w_list = [
                TranscriptWord(word=w, start=round(cur_t + 0.2 + i * w_step, 2), end=round(cur_t + 0.2 + (i + 1) * w_step, 2))
                for i, w in enumerate(hook_words_raw)
            ]
            sub_segments.append(TranscriptSegment(
                id=1,
                start=round(cur_t + 0.2, 2),
                end=round(cur_t + hook_dur - 0.2, 2),
                text=script.hook,
                words=w_list
            ))
        cur_t += hook_dur

        # Setup words from source transcript
        for s in transcript_segments:
            s_mid = (s.start + s.end) / 2.0
            if s.end >= seg2_start and s_mid < setup_end:
                shift = cur_t - seg2_start
                s_words = [
                    TranscriptWord(word=w.word, start=round(w.start + shift, 2), end=round(w.end + shift, 2))
                    for w in s.words
                ]
                sub_segments.append(TranscriptSegment(
                    id=len(sub_segments) + 1,
                    start=round(max(cur_t, s.start + shift), 2),
                    end=round(min(cur_t + seg2_dur, s.end + shift), 2),
                    text=s.text,
                    words=s_words
                ))
        cur_t += seg2_dur

        # Punchline words from source transcript
        for s in transcript_segments:
            s_mid = (s.start + s.end) / 2.0
            if s_mid >= punch_start and s.start <= punch_end:
                shift = cur_t - punch_start
                s_words = [
                    TranscriptWord(word=w.word, start=round(w.start + shift, 2), end=round(w.end + shift, 2))
                    for w in s.words
                ]
                sub_segments.append(TranscriptSegment(
                    id=len(sub_segments) + 1,
                    start=round(max(cur_t, s.start + shift), 2),
                    end=round(min(cur_t + seg3_dur, s.end + shift), 2),
                    text=s.text,
                    words=s_words
                ))
        cur_t += seg3_dur

        # Meme pause in subtitles
        cur_t += meme_dur

        # Outro roast words
        outro_words_raw = outro_text.split()
        if outro_words_raw:
            w_step = (outro_dur - 0.4) / max(1, len(outro_words_raw))
            w_list = [
                TranscriptWord(word=w, start=round(cur_t + 0.2 + i * w_step, 2), end=round(cur_t + 0.2 + (i + 1) * w_step, 2))
                for i, w in enumerate(outro_words_raw)
            ]
            sub_segments.append(TranscriptSegment(
                id=len(sub_segments) + 1,
                start=round(cur_t + 0.2, 2),
                end=round(cur_t + outro_dur - 0.2, 2),
                text=outro_text,
                words=w_list
            ))

    else:
        # === DIAGRAM CARD FALLBACK ===
        cand_start = candidate.start_time
        punch_t = candidate.punchline_time
        cand_end = candidate.end_time
        if punch_t <= cand_start + 1.0:
            punch_t = cand_start + 3.5
        if cand_end <= punch_t + 1.0:
            cand_end = punch_t + 3.0

        pre_punch_segs = [
            s.end for s in transcript_segments
            if cand_start + 2.0 <= s.end <= punch_t - 0.2 and s.end <= cand_end - 2.0
        ]
        split_t = pre_punch_segs[-1] if pre_punch_segs else max(cand_start + 2.5, min(punch_t - 0.5, cand_end - 2.5))

        setup_start = cand_start
        setup_end = round(split_t, 2)
        punch_start = setup_end
        clip_end = round(cand_end, 2)

        source_setup_dur = round(setup_end - setup_start, 2)
        source_payoff_dur = round(clip_end - punch_start, 2)
        total_source_dur = round(source_setup_dur + source_payoff_dur, 2)

        seg1_path = seg_dir / "seg1_hook.mp4"
        _render_image_audio_segment(visuals["hook_card"], hook_v["audio_path"], hook_v["duration_sec"], seg1_path)

        seg2_path = seg_dir / "seg2_setup.mp4"
        _render_source_video_segment(video_path, audio_path, setup_start, setup_end, seg2_path)

        seg3_path = seg_dir / "seg3_context.mp4"
        _render_image_audio_segment(visuals["diagram_card"], context_v["audio_path"], context_v["duration_sec"], seg3_path)

        seg4_path = seg_dir / "seg4_payoff.mp4"
        _render_source_video_segment(video_path, audio_path, punch_start, clip_end, seg4_path, overlay_badge=visuals["reaction_badge"])

        seg5_path = seg_dir / "seg5_conclusion.mp4"
        _render_image_audio_segment(visuals["hook_card"], conclusion_v["audio_path"], conclusion_v["duration_sec"], seg5_path)

        total_ai_comm_dur = round(hook_v["duration_sec"] + context_v["duration_sec"] + analysis_v["duration_sec"] + conclusion_v["duration_sec"], 2)
        total_ai_vis_dur = round(hook_v["duration_sec"] + context_v["duration_sec"] + conclusion_v["duration_sec"], 2)
        total_short_dur = round(total_source_dur + total_ai_comm_dur, 2)
        sub_segments = []

    # 4. Concatenate Segments
    if progress_callback:
        progress_callback(0.88, "Concatenating 5-beat short structure...")
    concat_list_file = seg_dir / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        f.write(f"file '{str(seg1_path).replace(chr(92), '/')}'\n")
        f.write(f"file '{str(seg2_path).replace(chr(92), '/')}'\n")
        f.write(f"file '{str(seg3_path).replace(chr(92), '/')}'\n")
        f.write(f"file '{str(seg4_path).replace(chr(92), '/')}'\n")
        f.write(f"file '{str(seg5_path).replace(chr(92), '/')}'\n")

    unsubbed_path = seg_dir / "unsubbed_joined.mp4"
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(unsubbed_path)
    ]
    subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 5. Burn Persistent Top Header Banner & Synchronized Word Subtitles
    final_banner_text = top_header_text or "WAIT FOR THE END! 😂"
    ass_path = seg_dir / "top_header.ass"

    generate_ass_subtitles(
        segments=sub_segments,
        clip_start=0.0,
        clip_end=total_short_dur,
        output_path=ass_path,
        top_header_text=final_banner_text
    )

    # 5b. Generate Dynamic Phonk/Trap BGM Layer with Punchline Beat Drop
    if progress_callback:
        progress_callback(0.92, "Synthesizing Phonk beat drop & layering dynamic BGM...")
    bgm_wav = seg_dir / "phonk_bgm_track.wav"
    bgm_res = _generate_dynamic_phonk_bgm(
        total_short_dur=total_short_dur,
        hook_dur=hook_dur,
        setup_dur=seg2_dur,
        punch_dur=seg3_dur,
        meme_dur=meme_dur,
        outro_dur=outro_dur,
        output_wav_path=bgm_wav
    )

    if progress_callback:
        progress_callback(0.96, "Burning word-by-word karaoke subtitles & header banner...")
    clean_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
    if bgm_res and Path(bgm_res).exists():
        cmd_burn = [
            "ffmpeg", "-y",
            "-i", str(unsubbed_path),
            "-i", str(bgm_res),
            "-filter_complex", f"[0:v]subtitles='{clean_ass}'[vout];[0:a][1:a]amix=inputs=2:duration=first:dropout_transition=0[aout]",
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-crf", "22", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            str(out_file)
        ]
    else:
        cmd_burn = [
            "ffmpeg", "-y",
            "-i", str(unsubbed_path),
            "-vf", f"subtitles='{clean_ass}'",
            "-c:v", "libx264", "-crf", "22", "-preset", "ultrafast",
            "-c:a", "copy",
            str(out_file)
        ]
    subprocess.run(cmd_burn, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if progress_callback:
        progress_callback(1.00, "Short rendered successfully!")

    # 6. Audit Originality & Compliance
    originality_report = generate_originality_report(
        source_duration_sec=total_source_dur,
        ai_commentary_sec=total_ai_comm_dur,
        ai_visuals_sec=total_ai_vis_dur,
        editorial_purpose=editorial_purpose,
        licensed_assets_count=1,
        ai_assets_count=3,
        has_source_cuts=True
    )

    return {
        "output_path": str(out_file),
        "video_filename": out_file.name,
        "total_duration": total_short_dur,
        "mode": "faceless_commentary",
        "script": script.to_dict(),
        "voice_info": hook_v,
        "visual_assets": visuals,
        "originality_report": originality_report.to_dict(),
        "editorial_purpose": editorial_purpose
    }
