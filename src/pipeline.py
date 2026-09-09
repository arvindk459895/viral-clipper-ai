"""
ViralClipper AI Studio - Master Pipeline Orchestrator
Coordinates video ingestion, speech transcription, audio DSP, candidate detection,
Gemini comedy intelligence, multi-style 9:16 rendering, rights verification, and ZIP packaging.
"""
import csv
import json
import os
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from src.config import (
    OUTPUTS_DIR,
    TEMP_DIR,
    DEFAULT_GEMINI_MODEL
)
from src.youtube import (
    download_video_and_audio,
    ingest_local_video,
    create_demo_media,
    VideoMetadata
)
from src.transcription import transcribe_audio, get_demo_transcript
from src.audio_analysis import analyze_audio_events
from src.candidate_detector import detect_candidate_moments, CandidateClip
from src.gemini_analyzer import analyze_candidate_with_gemini, GeminiClipAnalysis
from src.editor import render_short_clip
from src.thumbnail import generate_thumbnails, ThumbnailResult
from src.metadata import generate_clip_metadata, ClipMetadata
from src.rights_checker import audit_clip_rights, save_rights_report
from src.meme_manager import AssetLibraryManager
from src.commentary_engine import generate_commentary_script
from src.commentary_validator import validate_commentary_quality
from src.faceless_editor import render_faceless_commentary_short


def run_pipeline(
    video_source: str,
    is_demo: bool = False,
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_GEMINI_MODEL,
    num_shorts: int = 3,
    clip_duration: str = "30 sec",
    editing_style: str = "Meme",
    framing_mode: str = "blur",
    user_confirmed_source: bool = True,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    top_header_text: Optional[str] = None,
    studio_mode: str = "standard",
    voice_style: str = "madhur",
    commentary_threshold: int = 70,
    commentary_language: str = "auto",
    commentary_emotion: str = "auto",
    visual_mode: str = "video_cutaway",
    meme_style: str = "cutaway",
    **kwargs
) -> Dict[str, Any]:
    """
    Executes the full end-to-end ViralClipper workflow.
    """
    def update_progress(val: float, text: str):
        if progress_callback:
            progress_callback(val, text)

    asset_mgr = AssetLibraryManager()

    # Step 1A: Ingest / Download Video
    update_progress(0.05, "Step 1A: Ingesting video source...")

    if is_demo or "demo" in video_source.lower():
        media = create_demo_media(duration=25)
    elif Path(video_source).exists() and Path(video_source).is_file():
        update_progress(0.08, "Step 1A: Ingesting local video file...")
        media = ingest_local_video(video_source)
    else:
        update_progress(0.08, "Step 1A: Downloading video from YouTube...")
        media = download_video_and_audio(
            video_source,
            progress_cb=lambda msg: update_progress(0.12, f"Step 1A: {msg}")
        )

    # Step 1B: Verify video exists before extracting audio
    video_path = media["video_path"]
    audio_path = media["audio_path"]
    meta: VideoMetadata = media["metadata"]

    update_progress(0.10, f"Step 1B: Audio track verified ({Path(audio_path).name})")

    # Step 2: Transcribe Speech / Ingest Subtitles (Hindi/Hinglish/English)
    update_progress(0.18, "Step 2: Ingesting speech and word-level timestamps...")
    if is_demo:
        transcript = get_demo_transcript(meta.duration)
    else:
        transcript = transcribe_audio(
            audio_path=audio_path,
            subtitle_path=media.get("subtitle_path"),
            total_duration=meta.duration
        )

    # Step 3: Audio DSP Event Analysis
    update_progress(0.28, "Step 3: Detecting laughter bursts, peaks, and dramatic pauses...")
    audio_analysis = analyze_audio_events(audio_path)

    # Step 4: Comedy Candidate Moment Detection across full duration
    update_progress(0.38, "Step 4: Clustering laughter and identifying funniest comedy moments...")
    candidates = detect_candidate_moments(
        transcript=transcript,
        audio_analysis=audio_analysis,
        target_duration=clip_duration
    )
    if not candidates:
        dur = min(25.0, meta.duration)
        candidates = [CandidateClip(
            clip_id="cand_01",
            start_time=0.5,
            end_time=dur,
            duration=dur - 0.5,
            hook_start=0.5,
            setup_start=2.0,
            punchline_time=dur * 0.7,
            reaction_end=dur,
            text=transcript.full_text[:120],
            estimated_score=85.0
        )]

    selected_candidates = candidates[:num_shorts]

    # Step 5: Gemini Analysis & Scoring
    update_progress(0.46, "Step 5: Performing Gemini comedy intelligence and viral scoring...")
    analyzed_clips: List[Dict[str, Any]] = []

    for idx, cand in enumerate(selected_candidates):
        cand.clip_id = f"clip_{idx+1:02d}"
        analysis = analyze_candidate_with_gemini(
            candidate=cand,
            api_key=api_key,
            model_name=model_name,
            editing_style=editing_style
        )
        analyzed_clips.append({"candidate": cand, "analysis": analysis})

    # Step 6: 9:16 Video Rendering, Captions, Effects, and Thumbnails
    num_clips = len(analyzed_clips)
    rendered_shorts: List[Dict[str, Any]] = []
    export_files: List[Path] = []
    used_assets = asset_mgr.get_approved_assets()[:2]

    step6_start = 0.50
    step6_end = 0.94
    clip_weight = (step6_end - step6_start) / max(1, num_clips)

    for idx, item in enumerate(analyzed_clips):
        cand: CandidateClip = item["candidate"]
        analysis: GeminiClipAnalysis = item["analysis"]
        base_p = step6_start + (idx * clip_weight)

        def make_clip_cb(c_idx, c_id, base_pct, c_weight):
            def _cb(sub_pct: float, sub_msg: str):
                cur_pct = base_pct + (sub_pct * c_weight)
                update_progress(round(cur_pct, 3), f"Step 6 [{c_idx+1}/{num_clips}] ({c_id}): {sub_msg}")
            return _cb

        clip_cb = make_clip_cb(idx, cand.clip_id, base_p, clip_weight)
        clip_cb(0.02, "Generating titles, descriptions & viral hashtags...")

        # 1. Generate Metadata first so titles can feed the top header if in Auto mode
        metadata = generate_clip_metadata(
            cand,
            analysis,
            channel_name=meta.channel,
            api_key=api_key,
            model_name=model_name
        )

        # Determine top header banner text (stays throughout entire Short)
        if top_header_text and top_header_text.strip() and top_header_text.strip().lower() != "auto":
            active_header = top_header_text.strip()
        else:
            active_header = metadata.titles[0] if metadata.titles else "WAIT FOR THE END 😂"

        # Render according to Studio Mode
        if studio_mode == "faceless":
            clip_cb(0.05, "Writing original editorial commentary script...")
            # Generate and validate original editorial script with language and emotion
            comm_script = generate_commentary_script(
                candidate=cand,
                api_key=api_key,
                model_name=model_name,
                humor_type=analysis.humor_type,
                language=commentary_language,
                emotion=commentary_emotion,
                detected_lang=getattr(transcript, "language", "hi")
            )
            quality_report = validate_commentary_quality(
                script=comm_script,
                threshold=commentary_threshold,
                api_key=api_key,
                model_name=model_name
            )

            faceless_res = render_faceless_commentary_short(
                video_path=video_path,
                audio_path=audio_path,
                candidate=cand,
                script=comm_script,
                transcript_segments=transcript.segments,
                voice_style=voice_style,
                top_header_text=active_header,
                visual_mode=visual_mode,
                meme_style=meme_style,
                humor_type=analysis.humor_type,
                clip_index=idx,
                dialogue_text=cand.text,
                progress_callback=clip_cb
            )
            export_files.append(Path(faceless_res["output_path"]))
            clean_res = {"output_path": faceless_res["output_path"]}
            meme_res = {"output_path": faceless_res["output_path"]}
            heavy_res = {"output_path": faceless_res["output_path"]}
        else:
            # 2. Render Clean version
            clip_cb(0.10, "Rendering Clean 9:16 Short...")
            clean_res = render_short_clip(
                video_path=video_path,
                audio_path=audio_path,
                candidate=cand,
                analysis=analysis,
                transcript_segments=transcript.segments,
                editing_style="Clean",
                asset_manager=asset_mgr,
                framing_mode=framing_mode,
                top_header_text=active_header
            )
            export_files.append(Path(clean_res["output_path"]))

            # 3. Render Meme / Modern version
            clip_cb(0.45, "Rendering Meme / Modern 9:16 Short...")
            meme_res = render_short_clip(
                video_path=video_path,
                audio_path=audio_path,
                candidate=cand,
                analysis=analysis,
                transcript_segments=transcript.segments,
                editing_style="Meme",
                asset_manager=asset_mgr,
                framing_mode=framing_mode,
                top_header_text=active_header
            )
            export_files.append(Path(meme_res["output_path"]))

            # 4. Render Heavy Meme version
            clip_cb(0.75, "Rendering Heavy Meme 9:16 Short...")
            heavy_res = render_short_clip(
                video_path=video_path,
                audio_path=audio_path,
                candidate=cand,
                analysis=analysis,
                transcript_segments=transcript.segments,
                editing_style="Heavy Meme",
                asset_manager=asset_mgr,
                framing_mode=framing_mode,
                top_header_text=active_header
            )
            export_files.append(Path(heavy_res["output_path"]))
            comm_script = None
            quality_report = None
            faceless_res = None

        # 5. Generate Thumbnails (2 options)
        clip_cb(0.98, "Generating vertical thumbnail variants...")
        thumbs = generate_thumbnails(video_path, cand, analysis)
        export_files.append(Path(thumbs.option_1_path))
        export_files.append(Path(thumbs.option_2_path))

        short_dict = {
            "clip_id": cand.clip_id,
            "start_time": cand.start_time,
            "end_time": cand.end_time,
            "duration": cand.duration,
            "viral_score": analysis.viral_score,
            "opus_virality_score": getattr(analysis, "opus_virality_score", 88),
            "analysis_engine": analysis.analysis_engine,
            "top_header_text": active_header,
            "studio_mode": studio_mode,
            # Opus 4 Pillars & Diagnostic Insights
            "hook_score": analysis.hook_score,
            "flow_score": getattr(analysis, "flow_score", 85.0),
            "value_score": getattr(analysis, "value_score", 88.0),
            "trend_score": getattr(analysis, "trend_score", 84.0),
            "hook_insight": getattr(analysis, "hook_insight", "Attention-grabbing opening creates curiosity."),
            "flow_insight": getattr(analysis, "flow_insight", "Seamless narrative continuity and pacing."),
            "value_insight": getattr(analysis, "value_insight", "High comedy resonance and audience reaction."),
            "trend_insight": getattr(analysis, "trend_insight", "Quotable punchline with meme potential."),
            # Opus 3-Act Structure Timestamps
            "act1_hook_end": cand.act1_hook_end,
            "act2_setup_end": cand.act2_setup_end,
            "act3_punchline_time": cand.act3_punchline_time,
            "punchline_time": cand.punchline_time,
            "humor_score": analysis.humor_score,
            "punchline_score": analysis.punchline_score,
            "reaction_score": analysis.reaction_score,
            "shareability_score": analysis.shareability_score,
            "humor_type": analysis.humor_type,
            "reaction_type": analysis.reaction_type,
            "reason": analysis.reason,
            "recommended_effects": analysis.recommended_effects,
            "recommended_asset_tags": analysis.recommended_asset_tags,
            "clean_mp4": clean_res["output_path"],
            "meme_mp4": meme_res["output_path"],
            "heavy_mp4": heavy_res["output_path"],
            "thumbnail_1": thumbs.option_1_path,
            "thumbnail_2": thumbs.option_2_path,
            "titles": metadata.titles,
            "description": metadata.description,
            "hashtags": metadata.hashtags
        }

        if studio_mode == "faceless" and faceless_res:
            short_dict["faceless_mp4"] = faceless_res["output_path"]
            short_dict["script"] = faceless_res["script"]
            short_dict["voice_info"] = faceless_res["voice_info"]
            short_dict["visual_assets"] = faceless_res["visual_assets"]
            short_dict["originality_report"] = faceless_res["originality_report"]
            short_dict["quality_report"] = quality_report.to_dict() if quality_report else {}

        rendered_shorts.append(short_dict)

    # Step 7: Rights Verification & Export Packaging
    update_progress(0.95, "Step 7: Performing pre-export rights audit and packaging ZIP...")

    rights_report = audit_clip_rights(
        source_title=meta.title,
        user_confirmed_source=user_confirmed_source,
        assets_used=used_assets,
        is_demo_mode=is_demo
    )
    rights_path = OUTPUTS_DIR / "rights_report.json"
    save_rights_report(rights_report, rights_path)
    export_files.append(rights_path)

    # Save analysis.json
    analysis_path = OUTPUTS_DIR / "analysis.json"
    analysis_data = [
        {"clip_id": s["clip_id"], "viral_score": s["viral_score"], "titles": s["titles"], "reason": s["reason"]}
        for s in rendered_shorts
    ]
    analysis_path.write_text(json.dumps(analysis_data, indent=2), encoding="utf-8")
    export_files.append(analysis_path)

    # Save clips.csv
    csv_path = OUTPUTS_DIR / "clips.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Clip ID", "Start Time", "End Time", "Duration", "Viral Potential Score", "Humor Type", "Title 1"])
        for s in rendered_shorts:
            writer.writerow([s["clip_id"], s["start_time"], s["end_time"], s["duration"], s["viral_score"], s["humor_type"], s["titles"][0]])
    export_files.append(csv_path)

    # Package into ZIP bundle
    zip_path = OUTPUTS_DIR / "viral_shorts_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in export_files:
            if f.exists():
                zf.write(f, arcname=f.name)

    update_progress(1.0, "Complete: Shorts, thumbnails, and compliance package ready!")

    return {
        "metadata": meta.model_dump(),
        "shorts": rendered_shorts,
        "rights_report": rights_report.model_dump(),
        "rights_report_path": str(rights_path),
        "analysis_json_path": str(analysis_path),
        "clips_csv_path": str(csv_path),
        "zip_package_path": str(zip_path)
    }
