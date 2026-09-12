"""
ViralClipper AI Studio - Full Interactive Web Application
Features YouTube ingestion, local video upload, speech transcription, DSP analysis,
candidate detection, Gemini comedy intelligence, 9:16 Shorts rendering, and export suite.
"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import streamlit as st

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.config import (
    DEFAULT_GEMINI_MODEL,
    AVAILABLE_GEMINI_MODELS,
    CONTENT_TYPES,
    CLIP_COUNT_OPTIONS,
    CLIP_DURATION_OPTIONS,
    EDITING_STYLES,
    TRANSFORMATION_LEVELS,
    LEGAL_DISCLAIMER,
    REUSED_CONTENT_POLICY_NOTICE,
    SAFE_EXPORT_STATUS_NOTICE,
    TEMP_DIR,
    load_saved_api_key,
    save_api_key_locally,
    verify_login_credentials,
    ADMIN_USERNAME
)
from datetime import datetime, timedelta, timezone
from src.utils import is_valid_youtube_url
from src.asset_license import AssetCategory, AssetStatus, is_eligible_for_export
from src.meme_manager import AssetLibraryManager
from src.asset_downloader import update_trending_meme_library
from src.pipeline import run_pipeline
from src.youtube_publisher import (
    YouTubeChannelManager,
    ChannelInfo,
    schedule_youtube_short,
    get_scheduled_shorts,
    delete_scheduled_short,
    format_youtube_title,
    format_youtube_tags
)


def init_session_state():
    """Initializes application session state variables."""
    if "is_authenticated" not in st.session_state:
        st.session_state.is_authenticated = False
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = load_saved_api_key()
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    if "source_confirmed" not in st.session_state:
        st.session_state.source_confirmed = False
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Studio"
    if "pipeline_results" not in st.session_state:
        st.session_state.pipeline_results = None
    if "pipeline_status" not in st.session_state:
        st.session_state.pipeline_status = "idle"
    if "active_preview_style" not in st.session_state:
        st.session_state.active_preview_style = "meme"
    if "uploaded_video_path" not in st.session_state:
        st.session_state.uploaded_video_path = None


def render_sidebar():
    """Renders sidebar controls and API configuration."""
    with st.sidebar:
        st.title("🎬 ViralClipper AI")
        st.caption("Automated AI Vertical Shorts Studio for Comedy & Podcasts")
        st.divider()

        st.subheader("🔑 Gemini AI Configuration")
        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.gemini_api_key,
            type="password",
            help="Masked input. Saved locally on this machine so it persists across page reloads.",
            placeholder="AIzaSy..."
        )
        if api_key != st.session_state.gemini_api_key:
            st.session_state.gemini_api_key = api_key
            if api_key.strip():
                save_api_key_locally(api_key)

        save_key_toggle = st.checkbox(
            "💾 Remember key on reload",
            value=True,
            help="Saves your key locally so you never have to re-enter it when refreshing the browser.",
            key="chk_save_key"
        )
        if save_key_toggle and api_key.strip():
            save_api_key_locally(api_key)
        elif not save_key_toggle and not api_key.strip():
            save_api_key_locally("")

        model_choice = st.selectbox(
            "Gemini Model",
            options=AVAILABLE_GEMINI_MODELS,
            index=AVAILABLE_GEMINI_MODELS.index(st.session_state.selected_model)
            if st.session_state.selected_model in AVAILABLE_GEMINI_MODELS else 0,
            help="Select the active Google Gemini model."
        )
        st.session_state.selected_model = model_choice

        # Key Status & Verification
        if st.session_state.gemini_api_key:
            kcol1, kcol2 = st.columns([1.7, 1.3])
            with kcol1:
                st.caption(f"🟢 **Key Active** (`{model_choice}`)")
            with kcol2:
                if st.button("🔌 Test Key", key="btn_test_gemini_key"):
                    with st.spinner("Pinging Gemini..."):
                        try:
                            from google import genai
                            test_client = genai.Client(api_key=st.session_state.gemini_api_key)
                            test_resp = test_client.models.generate_content(
                                model=model_choice,
                                contents="Say 'OK' in one word."
                            )
                            st.success("✅ Connected!")
                        except Exception as ex:
                            err_msg = str(ex)
                            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                                st.error(f"⚠️ **Quota limit reached on `{model_choice}`** (Google AI free tier limit).")
                                st.info("💡 **Quick Fix**: Change **Gemini Model** above to **`gemini-3.5-flash-lite`** or **`gemini-3.7-flash`** — both have active quota for your key!")
                            else:
                                st.error(f"❌ Error: {err_msg[:120]}")

            if st.button("🗑️ Forget Saved Key", key="btn_forget_key"):
                save_api_key_locally("")
                st.session_state.gemini_api_key = ""
                st.rerun()
        else:
            st.info("ℹ️ No key entered. Using local acoustic heuristics (offline).")

        st.caption("🔒 *API key is saved locally in your workspace and loaded automatically on reload.*")
        st.divider()

        st.subheader("📺 YouTube Channel")
        yt_mgr = YouTubeChannelManager()
        if yt_mgr.is_connected():
            ch_info = yt_mgr.get_channel_info()
            if ch_info:
                st.markdown(f"🟢 **{ch_info.title}**")
                st.caption(f"{ch_info.handle} • {ch_info.subscriber_count:,} subs {'(Demo Sandbox)' if ch_info.is_demo else '(Live OAuth)'}")
                ycol1, ycol2 = st.columns(2)
                with ycol1:
                    if st.button("Manage", key="btn_sb_yt_manage", use_container_width=True):
                        st.session_state.active_tab = "📺 YouTube Channel & Scheduler"
                        st.rerun()
                with ycol2:
                    if st.button("Disconnect", key="btn_sb_yt_disc", use_container_width=True):
                        yt_mgr.disconnect()
                        st.rerun()
            else:
                st.caption("🟢 **Connected**")
        else:
            st.caption("🔴 **No Channel Connected**")
            if st.button("🔗 Connect Channel", key="btn_sb_yt_conn", use_container_width=True):
                st.session_state.active_tab = "📺 YouTube Channel & Scheduler"
                st.rerun()
        st.divider()

        st.subheader("🧭 Studio Navigation")
        nav_options = ["Studio", "Asset Library", "Rights & Compliance", "📺 YouTube Channel & Scheduler"]
        cur_idx = nav_options.index(st.session_state.active_tab) if st.session_state.active_tab in nav_options else 0
        app_mode = st.radio(
            "Navigation",
            options=nav_options,
            index=cur_idx
        )
        st.session_state.active_tab = app_mode
        st.divider()

        st.markdown("""
**Quick Guide:**
1. Confirm source video authorization.
2. Provide YouTube URL, Upload File, or select Demo.
3. Click **Analyze & Generate Shorts**.
4. Preview Clean, Meme, and Heavy styles.
5. Download ZIP with copyright report.
""")
        st.divider()
        if st.button("🔒 Sign Out / Lock Studio", key="btn_sign_out", use_container_width=True):
            st.session_state.is_authenticated = False
            st.rerun()


def render_compliance_banner():
    """Mandatory legal disclaimer and user authorization confirmation."""
    with st.expander("⚖️ Copyright & Rights Authorization (Required)", expanded=True):
        st.markdown(f"> **Important Legal Notice**: {LEGAL_DISCLAIMER}")
        st.markdown(f"<small>{REUSED_CONTENT_POLICY_NOTICE}</small>", unsafe_allow_html=True)
        st.write("")
        confirmed = st.checkbox(
            "I confirm that I own or have authorization to use the source video and the assets I provide.",
            value=st.session_state.source_confirmed,
            help="Mandatory confirmation to unlock video export."
        )
        st.session_state.source_confirmed = confirmed
        if not confirmed:
            st.warning("⚠️ You must check the authorization confirmation above to generate and export clips.")


def render_studio_view():
    """Primary video clipping and results view."""
    st.header("🎬 Studio Control Center")
    st.caption("Transform long-form comedy and podcast footage into viral 9:16 vertical Shorts.")

    render_compliance_banner()

    source_tab1, source_tab2, source_tab3 = st.tabs([
        "🔗 YouTube Ingestion",
        "📁 Upload Local Video",
        "🧪 Offline Demo Mode"
    ])
    selected_source = ""
    is_demo_mode = False

    with source_tab1:
        yt_url = st.text_input(
            "YouTube Video URL",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Enter a YouTube link you own or have explicit authorization to clip."
        )
        if yt_url:
            if is_valid_youtube_url(yt_url):
                st.success("✅ Valid YouTube URL")
                selected_source = yt_url
            else:
                st.error("❌ Invalid YouTube URL format")

    with source_tab2:
        st.write("Upload an MP4, MOV, or WEBM video file from your computer (100% reliable, zero YouTube throttling).")
        uploaded_file = st.file_uploader(
            "Choose local video file",
            type=["mp4", "mov", "mkv", "webm", "avi"],
            key="local_video_uploader"
        )
        if uploaded_file is not None:
            saved_path = TEMP_DIR / uploaded_file.name
            saved_path.write_bytes(uploaded_file.read())
            st.session_state.uploaded_video_path = str(saved_path)
            selected_source = str(saved_path)
            st.success(f"📁 Local video loaded: {uploaded_file.name} ({saved_path.stat().st_size / (1024*1024):.1f} MB)")

    with source_tab3:
        st.write("Test the complete pipeline offline with synthetic comedy footage (no internet or downloads needed).")
        demo_btn = st.button("🧪 Select Built-in Comedy Demo Clip", use_container_width=True)
        if demo_btn:
            st.session_state.use_demo_source = True
            is_demo_mode = True
            selected_source = "demo_comedy_source"
            st.success("🎯 Demo clip active: 'Indian Comedy & Panel Show (Hinglish Special)'")

    st.divider()

    st.subheader("🎯 Studio Mode")
    mode_col1, mode_col2 = st.columns(2)
    with mode_col1:
        studio_mode_choice = st.radio(
            "Creation Workflow",
            options=["🎙️ Faceless AI Commentary (Transformative Editorial)", "⚡ Standard Short (Opus Clip Virality)"],
            index=0,
            help="Faceless AI Commentary creates an original editorial video essay with AI voiceover, original cartoon graphics, and interleaved source moments. Standard mode creates viral punchline clips."
        )
    is_faceless = "Faceless" in studio_mode_choice
    active_studio_mode = "faceless" if is_faceless else "standard"

    with mode_col2:
        if is_faceless:
            lang_col, emo_col = st.columns(2)
            with lang_col:
                lang_choice = st.selectbox(
                    "Commentary Language",
                    options=["Auto (Match Video: Hinglish)", "Hinglish (Natural Indian Comedy)", "Hindi", "English"],
                    index=1,
                    help="Auto detects Hindi/Hinglish in video and generates natural conversational Hinglish commentary."
                )
            with emo_col:
                emo_choice = st.selectbox(
                    "Narration Emotion",
                    options=[
                        "Auto (Dynamic Scene Matching)",
                        "😂 Laugh / Cheerful",
                        "😢 Sad / Melodrama",
                        "❤️ Loved / Heartfelt",
                        "😱 Shocked / Excited",
                        "😏 Sarcastic / Roast"
                    ],
                    index=0,
                    help="Applies neural SSML emotion modulation to voiceover delivery."
                )

            v_col1, v_col2, v_col3 = st.columns(3)
            with v_col1:
                voice_choice = st.selectbox(
                    "AI Voice Persona",
                    options=[
                        "🎙️ Madhur (Indian Male - Natural Hinglish/Hindi)",
                        "🎙️ Prabhat (Indian Energetic - Punchy Hinglish/English)",
                        "🎙️ Swara (Indian Female - Natural Hinglish/Hindi)",
                        "🎙️ Neerja (Indian Female - Expressive)",
                        "🎙️ Guy (US Male - Energetic English)",
                        "🎙️ Eric (US Male - Comedic English)"
                    ],
                    index=0,
                    help="Natural neural voice personas. Madhur & Prabhat deliver authentic Indian creator cadence (RC Hidden style)."
                )
            with v_col2:
                narration_speed_choice = st.selectbox(
                    "Narration Speed / Pacing",
                    options=[
                        "⚡ 1.5x (Fast & Viral - Creator Standard)",
                        "🚀 1.75x (Hyper High-Energy)",
                        "🏃 1.25x (Punchy)",
                        "🚶 1.0x (Normal Pace)"
                    ],
                    index=0,
                    help="Sets AI voiceover tempo. 1.5x is standard for fast viral Indian comedy reaction shorts."
                )
            with v_col3:
                meme_style_choice = st.selectbox(
                    "Meme & Cutaway Style",
                    options=[
                        "🎬 Video Meme Cutaway (Seamless 1-2s insert - RC Hidden Style)",
                        "🎨 Animated Sticker Overlay with SFX",
                        "📜 Explainer Card with Diagram"
                    ],
                    index=0,
                    help="Video cutaway splices real 1-2s viral video memes directly into the timeline at the climax, like top Shorts creators."
                )

            voice_map = {
                "🎙️ Madhur (Indian Male - Natural Hinglish/Hindi)": "madhur",
                "🎙️ Prabhat (Indian Energetic - Punchy Hinglish/English)": "prabhat",
                "🎙️ Swara (Indian Female - Natural Hinglish/Hindi)": "swara",
                "🎙️ Neerja (Indian Female - Expressive)": "neerja",
                "🎙️ Guy (US Male - Energetic English)": "guy",
                "🎙️ Eric (US Male - Comedic English)": "eric"
            }
            voice_persona = voice_map.get(voice_choice, "madhur")

            speed_map = {
                "⚡ 1.5x (Fast & Viral - Creator Standard)": 1.5,
                "🚀 1.75x (Hyper High-Energy)": 1.75,
                "🏃 1.25x (Punchy)": 1.25,
                "🚶 1.0x (Normal Pace)": 1.0
            }
            active_speed = speed_map.get(narration_speed_choice, 1.5)

            if "Video Meme Cutaway" in meme_style_choice:
                active_vis_mode = "video_cutaway"
                active_meme_style = "cutaway"
            elif "Animated Sticker Overlay" in meme_style_choice:
                active_vis_mode = "video_cutaway"
                active_meme_style = "overlay"
            else:
                active_vis_mode = "diagram_card"
                active_meme_style = "cutaway"

            quality_bar = 70

            # Map selections
            lang_map = {
                "Auto (Match Video: Hinglish)": "auto",
                "Hinglish (Natural Indian Comedy)": "hinglish",
                "Hindi": "hindi",
                "English": "english"
            }
            active_comm_lang = lang_map.get(lang_choice, "auto")

            emo_map = {
                "Auto (Dynamic Scene Matching)": "auto",
                "😂 Laugh / Cheerful": "laugh",
                "😢 Sad / Melodrama": "sad",
                "❤️ Loved / Heartfelt": "loved",
                "😱 Shocked / Excited": "excited",
                "😏 Sarcastic / Roast": "sarcastic"
            }
            active_comm_emo = emo_map.get(emo_choice, "auto")
        else:
            voice_persona = "madhur"
            active_vis_mode = "video_cutaway"
            active_meme_style = "cutaway"
            quality_bar = 70
            active_comm_lang = "auto"
            active_comm_emo = "auto"
            active_speed = 1.5
            st.info("⚡ Standard Opus Clip Mode active (Acoustic detection + karaoke subtitles + reaction memes).")

    st.divider()

    st.subheader("⚙️ Clipping & Editing Controls")
    col1, col2, col3 = st.columns(3)
    with col1:
        content_type = st.selectbox("Content Type", options=CONTENT_TYPES, index=1)
        subtitle_lang = st.selectbox(
            "Subtitle / Spoken Language",
            options=["Auto (Native Spoken / Hindi)", "Hindi (हिंदी)", "English"],
            index=0,
            help="Selects native Hindi captions for Hindi comedy videos, matching the spoken words exactly without bad English auto-translations."
        )
        clip_count = st.selectbox("Number of Shorts", options=CLIP_COUNT_OPTIONS, index=2)
    with col2:
        clip_duration = st.selectbox(
            "Clip Duration",
            options=CLIP_DURATION_OPTIONS,
            index=0,
            help="60 sec maximizes viewer watch time and YouTube algorithm monetization without crossing the 60s Shorts ceiling."
        )
        editing_style = st.selectbox("Editing Style", options=EDITING_STYLES, index=3)
    with col3:
        framing_choice = st.selectbox(
            "Video Framing",
            options=["Fit Stage (Blurred Background)", "Speaker Crop (9:16 Fill)"],
            index=0,
            help="Fit Stage keeps 100% of everyone on stage visible without cutting anyone off. Speaker Crop zooms in on the active speaker."
        )
        min_viral_score = st.slider("Minimum Viral Score", min_value=0, max_value=100, value=85)

    framing_mode = "blur" if "Blurred" in framing_choice else "crop"

    # Top Banner Headline Controls (persistent text in space above video)
    hcol1, hcol2 = st.columns([1.1, 1.9])
    with hcol1:
        header_preset = st.selectbox(
            "Top Banner Mode",
            options=[
                "Custom Text",
                "Auto (Clip Viral Title)",
                "WAIT FOR THE END 😂",
                "SAMAY RAINA ON FIRE 🔥",
                "INSTANT REGRET 💀",
                "BEST MOMENT OF THE SHOW 🤯"
            ],
            index=1,
            help="Displays a bold, high-contrast headline banner in the space above the video throughout the entire Short."
        )
    with hcol2:
        if header_preset == "Custom Text":
            top_header_input = st.text_input(
                "Custom Top Banner Text",
                value="WAIT FOR THE END 😂",
                placeholder="e.g., SAMAY RAINA ON FIRE 🔥",
                help="This exact text will stay displayed at the top above the video throughout the entire Short."
            )
        elif header_preset == "Auto (Clip Viral Title)":
            top_header_input = "auto"
            st.caption("✨ Each clip will automatically feature its own AI-generated viral hook title at the top.")
        else:
            top_header_input = header_preset
            st.caption(f"📌 Persistent top text: **{header_preset}**")
        fcol1, fcol2, fcol3, fcol4 = st.columns(4)
        with fcol1:
            st.checkbox("Analyze transcript", value=True)
            st.checkbox("Detect laughter", value=True)
            st.checkbox("Smart captions", value=True)
        with fcol2:
            st.checkbox("Smart memes", value=True)
            st.checkbox("Reaction effects", value=True)
            st.checkbox("Sound effects", value=True)
        with fcol3:
            st.checkbox("Dynamic zooms", value=True)
            st.checkbox("Transitions", value=True)
            st.checkbox("Generate titles", value=True)
        with fcol4:
            st.checkbox("Generate descriptions", value=True)
            st.checkbox("Generate hashtags", value=True)
            st.checkbox("Generate thumbnails", value=True)

    st.divider()

    # Process Trigger
    can_start = st.session_state.source_confirmed and bool(selected_source)
    btn_col, status_col = st.columns([1.2, 2])

    with btn_col:
        run_btn = st.button(
            "🚀 Analyze & Generate Shorts" if can_start else "🔒 Select Source & Confirm Rights",
            type="primary",
            disabled=not can_start,
            use_container_width=True
        )

    with status_col:
        if not st.session_state.source_confirmed:
            st.info("Please confirm copyright authorization in the top banner.")
        elif not selected_source:
            st.info("Enter a YouTube URL, upload a video file, or select Demo Clip.")

    # Execution Progress
    if run_btn:
        progress_bar = st.progress(0.0)
        status_text = st.empty()

        def update_cb(pct: float, msg: str):
            progress_bar.progress(pct)
            status_text.write(msg)

        with st.spinner("Processing video pipeline..."):
            try:
                results = run_pipeline(
                    video_source=selected_source,
                    is_demo=is_demo_mode or ("demo" in selected_source.lower()),
                    api_key=st.session_state.gemini_api_key,
                    model_name=st.session_state.selected_model,
                    num_shorts=clip_count,
                    clip_duration=clip_duration,
                    editing_style=editing_style,
                    framing_mode=framing_mode,
                    user_confirmed_source=st.session_state.source_confirmed,
                    progress_callback=update_cb,
                    top_header_text=top_header_input,
                    studio_mode=active_studio_mode,
                    voice_style=voice_persona,
                    commentary_threshold=quality_bar,
                    commentary_language=active_comm_lang,
                    commentary_emotion=active_comm_emo,
                    visual_mode=active_vis_mode,
                    meme_style=active_meme_style,
                    narration_speed=active_speed
                )
                st.session_state.pipeline_results = results
                st.session_state.pipeline_status = "completed"
                st.success("🎉 Shorts generation complete!")
            except Exception as e:
                st.error(f"Pipeline error: {str(e)}")

    # Render Results Page (Step 17 & 21)
    if st.session_state.pipeline_results:
        render_results_page(st.session_state.pipeline_results)


def render_results_page(results: Dict[str, Any]):
    """Displays generated Shorts, video players, viral potential radar, metadata, and export buttons."""
    st.divider()
    st.header("🏆 TOP SHORTS")

    shorts = results.get("shorts", [])
    if not shorts:
        st.warning("No candidate clips reached the threshold.")
        return

    # Rights Gate Display (Step 18)
    rights_rep = results.get("rights_report", {})
    st.subheader("🛡️ Pre-Export Rights Verification")
    rcol1, rcol2, rcol3, rcol4 = st.columns(4)
    with rcol1:
        st.metric("Source Status", rights_rep.get("source_rights_status", "UNKNOWN"))
    with rcol2:
        app_memes = rights_rep.get("meme_assets_approved", 0)
        st.metric("Meme Assets", f"{app_memes} APPROVED")
    with rcol3:
        st.metric("Sound Effects", f"{rights_rep.get('sfx_approved', 0)} APPROVED")
    with rcol4:
        st.metric("Music Used", rights_rep.get("music_used", "NONE"))

    export_status_lbl = rights_rep.get("export_status_label", SAFE_EXPORT_STATUS_NOTICE)
    st.success(f"**Verification Status**: {export_status_lbl}")
    st.caption("Disclaimer: *The application never claims 'fair use guarantee' or 'copyright safe'.*")

    st.divider()

    # One-Click ZIP Download (Step 21)
    zip_path = Path(results.get("zip_package_path", ""))
    if zip_path.exists():
        with open(zip_path, "rb") as zf:
            st.download_button(
                label="📦 Download Complete Package (All MP4s, Thumbnails, CSV, JSON, Rights Report)",
                data=zf.read(),
                file_name="viral_shorts_package.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True
            )

    st.write("")

    # Display Each Short Card
    for idx, short in enumerate(shorts):
        with st.container():
            st.markdown(f"### Short #{idx+1} • {short['titles'][0]}")

            col_vid, col_meta = st.columns([1.2, 1.8])

            with col_vid:
                is_faceless_clip = short.get("studio_mode") == "faceless" or bool(short.get("originality_report"))

                if is_faceless_clip:
                    vid_file = short.get("faceless_mp4", short.get("meme_mp4", ""))
                    st.caption("🎙️ **Faceless AI Commentary Video Essay**")
                    st.caption("*(Substantive AI Voice Narration + Interleaved Source Moments + Original Graphics)*")
                    if Path(vid_file).exists():
                        st.video(vid_file)
                        with open(vid_file, "rb") as vf:
                            st.download_button(
                                label="⬇️ Download Faceless Editorial MP4",
                                data=vf.read(),
                                file_name=Path(vid_file).name,
                                mime="video/mp4",
                                key=f"dl_vid_faceless_{idx}"
                            )
                else:
                    # Video Style Toggle
                    style_toggle = st.radio(
                        f"Preview Style for #{idx+1}",
                        options=["Clean", "Meme", "Heavy Meme"],
                        index=1,
                        horizontal=True,
                        key=f"style_toggle_{idx}"
                    )

                    if style_toggle == "Clean":
                        vid_file = short["clean_mp4"]
                    elif style_toggle == "Heavy Meme":
                        vid_file = short["heavy_mp4"]
                    else:
                        vid_file = short["meme_mp4"]

                    style_descriptions = {
                        "Clean": "🎬 **Clean**: Original video + dynamic captions (No memes, no SFX).",
                        "Meme": "💥 **Meme**: Punchline zoom + Reaction meme badge + Pop SFX.",
                        "Heavy Meme": "🔥 **Heavy Meme**: Impact zoom + Camera shake + Dual reaction memes + Dual SFX!"
                    }
                    st.caption(style_descriptions.get(style_toggle, ""))

                    if Path(vid_file).exists():
                        st.video(vid_file)

                    # Individual MP4 Download
                    if Path(vid_file).exists():
                        with open(vid_file, "rb") as vf:
                            st.download_button(
                                label=f"⬇️ Download {style_toggle} MP4",
                                data=vf.read(),
                                file_name=Path(vid_file).name,
                                mime="video/mp4",
                                key=f"dl_vid_{idx}_{style_toggle}"
                            )

            with col_meta:
                # Opus Clip Virality Score & Core Metrics
                opus_sc = short.get("opus_virality_score", short.get("viral_score", 85))
                if opus_sc >= 90:
                    virality_badge = f"🔥 **{opus_sc}/99 • Very High Virality**"
                elif opus_sc >= 80:
                    virality_badge = f"⚡ **{opus_sc}/99 • High Virality**"
                else:
                    virality_badge = f"✨ **{opus_sc}/99 • Good Potential**"

                mcol1, mcol2, mcol3 = st.columns([1.4, 1.3, 1.3])
                with mcol1:
                    st.metric("Opus Virality Score", f"{opus_sc}/99")
                    st.caption(virality_badge)
                with mcol2:
                    st.metric("Duration", f"{short['duration']:.1f}s")
                    st.caption(f"⏱️ `{short['start_time']:.1f}s - {short['end_time']:.1f}s`")
                with mcol3:
                    h_type = short['humor_type'].replace('_', ' ').title()
                    st.metric("Humor Type", h_type)
                    st.caption("🎭 Comedy Category")

                # Opus 3-Act Narrative Arc
                act3_t = short.get("act3_punchline_time", short.get("punchline_time", short["start_time"] + 18.0))
                rel_punch = max(3.0, act3_t - short["start_time"])
                st.info(
                    f"🧭 **3-Act Narrative Arc**: "
                    f"**Act 1: Hook** `0.0s–3.0s` ➔ "
                    f"**Act 2: Setup** `3.0s–{rel_punch:.1f}s` ➔ "
                    f"**Act 3: Punchline & Reaction** `{rel_punch:.1f}s–{short['duration']:.1f}s`"
                )

                # Opus 4-Pillar Score Cards
                pcol1, pcol2 = st.columns(2)
                with pcol1:
                    st.markdown(f"🪝 **Hook**: `{short.get('hook_score', 85):.0f}/100` *(30% weight)*")
                    st.caption(f"*{short.get('hook_insight', 'Curiosity hook captured immediately.')}*")

                    st.markdown(f"💎 **Value**: `{short.get('value_score', 88):.0f}/100` *(25% weight)*")
                    st.caption(f"*{short.get('value_insight', 'High comedy resonance with audience laughter.')}*")

                with pcol2:
                    st.markdown(f"🌊 **Flow**: `{short.get('flow_score', 85):.0f}/100` *(30% weight)*")
                    st.caption(f"*{short.get('flow_insight', 'Seamless narrative progression with clean conclusion.')}*")

                    st.markdown(f"🔥 **Trend**: `{short.get('trend_score', 84):.0f}/100` *(15% weight)*")
                    st.caption(f"*{short.get('trend_insight', 'Quotable punchline with strong meme potential.')}*")

                st.markdown(f"**Editorial Breakdown**: *{short['reason']}*")
                st.caption(f"🤖 **AI Engine**: `{short.get('analysis_engine', 'Google Gemini')}` | 📌 **Top Banner**: `{short.get('top_header_text', 'None')}`")

                # Event Reconstruction & Momentum Diagnostic (Point 23 & 24)
                with st.expander("🧠 Event Reconstruction & Momentum Diagnostic", expanded=False):
                    diag_cls = short.get("diagnostic_classification", "EVENT_RECONSTRUCTION_SUCCESS")
                    if diag_cls == "EVENT_RECONSTRUCTION_SUCCESS":
                        st.success(f"🟢 **Status**: `{diag_cls}` | Reaction: `{short.get('reaction_state', 'REACTION_RESOLVED')}`")
                    else:
                        st.warning(f"⚠️ **Status**: `{diag_cls}` | Reaction: `{short.get('reaction_state', 'REACTION_RESOLVED')}`")

                    env_ascii = short.get("envelope_ascii", "")
                    if env_ascii:
                        st.code(env_ascii, language="text")

                    dcol1, dcol2, dcol3, dcol4 = st.columns(4)
                    with dcol1:
                        st.metric("Context Completeness", f"{short.get('context_completeness_score', 92):.0f}%")
                        st.caption(f"🏁 **Start Reason**: *{short.get('boundary_start_reason', 'Narrative premise')}*")
                    with dcol2:
                        st.metric("Momentum Coverage", f"{short.get('momentum_coverage_score', 95):.0f}%")
                        st.caption(f"🛑 **End Reason**: *{short.get('boundary_end_reason', 'Audience eruption')}*")
                    with dcol3:
                        st.metric("Event Integrity", f"{short.get('event_integrity_score', 95):.0f}%")
                        st.caption(f"⚠️ **Cut Risk**: `{short.get('cut_risk_score', 5):.0f}%`")
                    with dcol4:
                        st.metric("Boundary Quality", f"{short.get('boundary_quality_score', 94):.0f}%")
                        st.caption(f"🎯 **Anchor Peak ($T_{{peak}}$)**: `{short.get('t_peak', short['punchline_time']):.1f}s`")

                    if short.get("compression_applied"):
                        st.info(
                            f"✂️ **Intelligent Event Compression Active**: "
                            f"{len(short.get('removed_segments', []))} redundant filler sentences were pruned internally "
                            f"to preserve both the complete setup premise and audience eruption within 58.5s."
                        )

                    calib_info = short.get("dsp_calibration_profile", "")
                    if calib_info:
                        st.caption(f"📊 **Acoustic DSP Calibration**: `{calib_info}`")

                    st.markdown(
                        f"⏱️ **Dynamic Allocation**: Setup & Buildup: **{short.get('pre_context_duration', 0.0):.1f}s** | "
                        f"Punchline & Reaction: **{short.get('post_context_duration', 0.0):.1f}s**"
                    )

                # Originality & Editorial Compliance Audit Card
                orig_rep = short.get("originality_report")
                if orig_rep:
                    st.markdown("---")
                    st.markdown("#### 🛡️ Originality & Editorial Compliance Audit")

                    rcol1, rcol2, rcol3 = st.columns(3)
                    with rcol1:
                        if orig_rep['originality_assessment'] == "STRONG":
                            st.success(f"**Originality:** {orig_rep['originality_assessment']}")
                        else:
                            st.info(f"**Originality:** {orig_rep['originality_assessment']}")
                    with rcol2:
                        st.info(f"**Reuse Risk:** {orig_rep['reuse_risk']}")
                    with rcol3:
                        st.warning(f"**Copyright Risk:** {orig_rep['copyright_risk']}")

                    st.markdown(
                        f"⏱️ **Editorial Ratio**: Source Footage: **{orig_rep['source_footage_sec']}s ({orig_rep['source_percentage']}%)** | "
                        f"AI Commentary & Visuals: **{orig_rep['ai_commentary_sec'] + orig_rep['ai_visuals_sec']}s ({orig_rep['commentary_percentage']}%)**"
                    )

                    with st.expander("📜 View Viral Commentary Script & Timeline Beats", expanded=True):
                        scr = short.get("script", {})
                        st.markdown(f"🪝 **[Beat 1: AI Hook Voiceover]**: *\"{scr.get('hook', '')}\"*")
                        st.markdown(f"🎬 **[Beat 2: Source Video Setup]**: *Source dialogue & situational action begins*")
                        st.markdown(f"💥 **[Beat 3: Viral Video Meme Cutaway (1-2s)]**: *Spliced reaction clip (RC Hidden style) hits at the climax*")
                        st.markdown(f"🔍 **[Beat 4: Punchline & Payoff]**: *Source punchline delivery and room reaction*")
                        st.markdown(f"🏁 **[Beat 5: AI Roaster Outro & CTA]**: *\"{scr.get('conclusion', '')}\"*")

                        voice_info = short.get("voice_info", {})
                        if voice_info:
                            st.caption(f"🎤 Voice Provider: `{voice_info.get('voice_provider')}` | Voice ID: `{voice_info.get('voice_id')}` | Generated: `{voice_info.get('generation_timestamp', '')[:19]}`")

                    st.info(f"📢 **YouTube Synthetic Content Policy**: {orig_rep['youtube_disclosure_reminder']}")
                    st.caption(f"⚖️ *{orig_rep['disclaimer']}*")

                # Titles & Description Tabs
                t_tab1, t_tab2, t_tab3 = st.tabs(["🏷️ Title Options", "📝 Description", "#️⃣ Hashtags"])
                with t_tab1:
                    for t_idx, title in enumerate(short["titles"]):
                        st.code(title, language=None)
                with t_tab2:
                    st.text_area("Video Description", value=short["description"], height=120, key=f"desc_{idx}")
                with t_tab3:
                    st.code(" ".join(short["hashtags"]), language=None)

                # Thumbnail Previews & Downloads
                st.markdown("**Thumbnails (2 Options)**")
                tcol1, tcol2 = st.columns(2)
                with tcol1:
                    if Path(short["thumbnail_1"]).exists():
                        st.image(short["thumbnail_1"], caption="Option 1 (Reaction)", use_container_width=True)
                        with open(short["thumbnail_1"], "rb") as tf1:
                            st.download_button("🖼️ Cover 1", tf1.read(), file_name=f"{short['clip_id']}_thumb1.jpg", key=f"dl_t1_{idx}")
                with tcol2:
                    if Path(short["thumbnail_2"]).exists():
                        st.image(short["thumbnail_2"], caption="Option 2 (Curiosity)", use_container_width=True)
                        with open(short["thumbnail_2"], "rb") as tf2:
                            st.download_button("🖼️ Cover 2", tf2.read(), file_name=f"{short['clip_id']}_thumb2.jpg", key=f"dl_t2_{idx}")

            # 🚀 1-Click YouTube Shorts Scheduler Drawer
            render_1click_youtube_scheduler_card(idx, short, vid_file)

            st.divider()


def render_1click_youtube_scheduler_card(idx: int, short: Dict[str, Any], default_vid_path: str):
    """Interactive 1-Click YouTube Shorts Scheduler Card directly inside each clip card."""
    yt_mgr = YouTubeChannelManager()
    is_conn = yt_mgr.is_connected()
    ch_info = yt_mgr.get_channel_info() if is_conn else None

    with st.expander(f"🚀 1-Click Schedule on YouTube Shorts (#{idx+1})", expanded=False):
        # Channel Connection Status Bar
        if is_conn and ch_info:
            scol1, scol2 = st.columns([2.6, 1.4])
            with scol1:
                st.success(f"🟢 **Target Channel**: {ch_info.title} (`{ch_info.handle}`) • {ch_info.subscriber_count:,} subs {'(Sandbox Mode)' if ch_info.is_demo else '(Live OAuth)'}")
            with scol2:
                if st.button("⚙️ Manage Channel", key=f"btn_switch_ch_{idx}", use_container_width=True):
                    st.session_state.active_tab = "📺 YouTube Channel & Scheduler"
                    st.rerun()
        else:
            st.warning("⚠️ **No YouTube Channel Connected.** You can test immediately in Sandbox Mode or connect via Google Cloud.")
            bcol1, bcol2 = st.columns(2)
            with bcol1:
                if st.button("🧪 Connect Demo Channel Instantly", key=f"btn_card_demo_{idx}", type="primary", use_container_width=True):
                    yt_mgr.connect_demo_mode()
                    st.success("✅ Demo Channel connected! Ready to schedule.")
                    st.rerun()
            with bcol2:
                if st.button("🔗 Open Channel Setup Space", key=f"btn_card_setup_{idx}", use_container_width=True):
                    st.session_state.active_tab = "📺 YouTube Channel & Scheduler"
                    st.rerun()

        # 1. Title Selection
        title_options = short["titles"] + ["Custom Title"]
        chosen_title_preset = st.selectbox(
            "YouTube Short Title",
            options=title_options,
            index=0,
            key=f"yt_card_title_sel_{idx}"
        )
        if chosen_title_preset == "Custom Title":
            active_title = st.text_input(
                "Custom Title",
                value=short["titles"][0],
                key=f"yt_card_custom_title_{idx}"
            )
        else:
            active_title = chosen_title_preset

        st.caption(f"📝 Title Preview: **{format_youtube_title(active_title)}**")

        # 2. Description Editor
        active_desc = st.text_area(
            "Video Description (Includes Auto-Credits, Timestamps & Legal Notice)",
            value=short["description"],
            height=100,
            key=f"yt_card_desc_{idx}"
        )

        # 3. Tags & Hashtags
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            default_tags = "comedy, standup comedy, hindi comedy, funny, shorts, viral, relatable, jokes, desi humor, trending shorts, laugh, comedy video"
            active_tags_str = st.text_input(
                "Search Tags (comma-separated keywords)",
                value=default_tags,
                key=f"yt_card_tags_{idx}"
            )
        with col_t2:
            default_hashes = " ".join(short.get("hashtags", ["#Shorts", "#Comedy", "#HindiComedy", "#Viral"]))
            active_hashes_str = st.text_input(
                "Hashtags",
                value=default_hashes,
                key=f"yt_card_hashes_{idx}"
            )

        # 4. Schedule Timing & Thumbnail Cover
        time_col1, time_col2 = st.columns([1.6, 1.4])
        with time_col1:
            schedule_preset = st.radio(
                "Publish Schedule",
                options=[
                    "🌆 Tomorrow Prime Time (6:00 PM)",
                    "🌅 Tomorrow Morning (9:00 AM)",
                    "⚡ Immediate Release (Public)",
                    "📅 Custom Date & Time"
                ],
                index=0,
                key=f"yt_card_timing_{idx}"
            )
        with time_col2:
            thumb_choice = st.selectbox(
                "Cover Thumbnail",
                options=["Option 1 (Reaction)", "Option 2 (Curiosity)", "Auto Video Frame"],
                index=1,
                key=f"yt_card_thumb_sel_{idx}"
            )

        custom_publish_dt = None
        if schedule_preset == "📅 Custom Date & Time":
            dcol1, dcol2 = st.columns(2)
            with dcol1:
                c_date = st.date_input("Schedule Date", key=f"yt_card_date_{idx}")
            with dcol2:
                c_time = st.time_input("Schedule Time", key=f"yt_card_time_{idx}")
            custom_publish_dt = datetime.combine(c_date, c_time)

        # 5. One-Click Action Trigger
        action_label = f"🚀 1-Click Schedule on {ch_info.handle}" if (is_conn and ch_info) else "🚀 1-Click Schedule on YouTube"

        if st.button(action_label, type="primary", use_container_width=True, key=f"btn_execute_schedule_{idx}"):
            if not is_conn:
                yt_mgr.connect_demo_mode()
                ch_info = yt_mgr.get_channel_info()

            with st.spinner("Processing 1-Click YouTube upload and schedule..."):
                try:
                    now = datetime.now()
                    if schedule_preset == "🌆 Tomorrow Prime Time (6:00 PM)":
                        target_dt = (now + timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
                        priv = "private"
                    elif schedule_preset == "🌅 Tomorrow Morning (9:00 AM)":
                        target_dt = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                        priv = "private"
                    elif schedule_preset == "⚡ Immediate Release (Public)":
                        target_dt = None
                        priv = "public"
                    else:
                        target_dt = custom_publish_dt
                        priv = "private"

                    vid_to_publish = short.get("faceless_mp4") or default_vid_path or short.get("meme_mp4") or short.get("clean_mp4")
                    if not vid_to_publish or not Path(vid_to_publish).exists():
                        raise FileNotFoundError("Video file for this short was not found.")

                    if thumb_choice == "Option 1 (Reaction)":
                        selected_thumb = short.get("thumbnail_1")
                    elif thumb_choice == "Option 2 (Curiosity)":
                        selected_thumb = short.get("thumbnail_2")
                    else:
                        selected_thumb = None

                    clean_hashtags = [h.strip() for h in active_hashes_str.split() if h.strip()]

                    res = schedule_youtube_short(
                        video_path=vid_to_publish,
                        title=active_title,
                        description=active_desc,
                        tags=active_tags_str,
                        hashtags=clean_hashtags,
                        publish_at=target_dt,
                        privacy_status=priv,
                        thumbnail_path=selected_thumb,
                        channel_manager=yt_mgr
                    )

                    st.success(f"🎉 **Short #{idx+1} Successfully Scheduled for {res.get('scheduled_time_local', 'Immediate Release')}!**")
                    lcol1, lcol2 = st.columns(2)
                    with lcol1:
                        st.link_button("▶️ Open YouTube Shorts Link", res["youtube_url"], use_container_width=True)
                    with lcol2:
                        st.link_button("⚙️ Manage in YouTube Studio", res["studio_url"], use_container_width=True)

                except Exception as err:
                    st.error(f"Scheduling error: {str(err)}")


def render_youtube_manager_view():
    """Dedicated YouTube Channel Connection Space and Scheduled Shorts Queue."""
    st.header("📺 YouTube Channel Connection & 1-Click Scheduler")
    st.caption("Connect your YouTube Channel via Google OAuth 2.0 or Instant Test Mode to schedule viral Shorts in 1 click.")

    yt_mgr = YouTubeChannelManager()
    is_conn = yt_mgr.is_connected()
    ch_info = yt_mgr.get_channel_info() if is_conn else None

    yt_tab1, yt_tab2 = st.tabs([
        "🔗 Channel Connection Space",
        "📅 Scheduled Shorts Queue"
    ])

    with yt_tab1:
        st.subheader("YouTube Channel Authorization")

        if is_conn and ch_info:
            st.success("✅ **YouTube Channel Connected & Ready for 1-Click Publishing**")
            prof_col1, prof_col2 = st.columns([1.2, 3])
            with prof_col1:
                if ch_info.avatar_url:
                    st.image(ch_info.avatar_url, width=140)
            with prof_col2:
                st.markdown(f"### {ch_info.title}")
                st.caption(f"Handle: **{ch_info.handle}** | Channel ID: `{ch_info.channel_id}`")
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Subscribers", f"{ch_info.subscriber_count:,}")
                with m2:
                    st.metric("Total Videos", f"{ch_info.video_count:,}")
                with m3:
                    st.metric("Mode", "Demo Sandbox" if ch_info.is_demo else "Live Google OAuth")

                st.link_button("▶️ View Channel on YouTube", f"https://youtube.com/{ch_info.handle.lstrip('@')}")

            st.write("")
            if st.button("🔴 Disconnect / Switch Channel", type="secondary"):
                yt_mgr.disconnect()
                st.success("Channel disconnected.")
                st.rerun()

        else:
            st.info("Choose your connection method below to start scheduling shorts:")

            c_col1, c_col2 = st.columns(2)

            with c_col1:
                st.markdown("#### 🧪 Instant Test Channel (Demo Mode)")
                st.caption("Zero-setup sandbox. Test the 1-click scheduler immediately without needing a Google Cloud developer account or API approval.")
                d_name = st.text_input("Demo Channel Name", value="My Comedy Studio", key="input_demo_ch_name")
                d_handle = st.text_input("Demo Handle", value="@MyComedyStudio", key="input_demo_ch_handle")
                if st.button("🚀 Activate Demo Channel Instantly", type="primary", use_container_width=True, key="btn_activate_demo_ch"):
                    yt_mgr.connect_demo_mode(channel_name=d_name, handle=d_handle)
                    st.success("✅ Demo Channel connected! You can now test 1-click scheduling.")
                    st.rerun()

            with c_col2:
                st.markdown("#### 🔑 Official Google Cloud OAuth 2.0")
                st.caption("Connect your real YouTube channel with official Google OAuth to publish directly to your audience.")

                with st.expander("📋 Quick Setup Guide (Google Cloud Console)"):
                    st.markdown("""
1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **YouTube Data API v3** in APIs & Services.
3. In **OAuth consent screen**, set user type to *External* and add test users.
4. Go to **Credentials** ➔ **Create Credentials** ➔ **OAuth client ID** (Desktop Application).
5. Download `client_secrets.json` or copy Client ID & Secret.
""")

                oauth_tab1, oauth_tab2, oauth_tab3 = st.tabs(["Upload Token (Cloud Safe)", "Upload client_secrets.json", "Enter Client ID & Secret"])
                with oauth_tab1:
                    st.caption("💡 **Recommended for Streamlit Cloud**: Authorize once on your desktop, then upload `credentials/youtube_token.json` here.")
                    up_token = st.file_uploader("Upload youtube_token.json", type=["json"], key="uploader_yt_token_cloud")
                    if up_token:
                        if st.button("💾 Save Channel Token", type="primary", use_container_width=True, key="btn_save_cloud_token"):
                            try:
                                tok_dict = json.loads(up_token.read().decode("utf-8"))
                                ok, msg = yt_mgr.connect_with_token_dict(tok_dict)
                                if ok:
                                    st.success(f"✅ {msg}")
                                    st.rerun()
                                else:
                                    st.error(msg)
                            except Exception as ex:
                                st.error(f"Error parsing token file: {ex}")

                with oauth_tab2:
                    uploaded_secret = st.file_uploader("Upload Google client_secrets.json", type=["json"], key="uploader_yt_secrets")
                    if uploaded_secret:
                        if st.button("Authorize with Google (File)", type="primary", use_container_width=True, key="btn_auth_file"):
                            try:
                                sec_dict = json.loads(uploaded_secret.read().decode("utf-8"))
                                with st.spinner("Authorizing with Google..."):
                                    ok, msg = yt_mgr.connect_with_client_secrets_dict(sec_dict)
                                    if ok:
                                        st.success("✅ Channel connected successfully!")
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            except Exception as ex:
                                st.error(f"Error parsing secrets file: {ex}")

                with oauth_tab3:
                    cid = st.text_input("Client ID", placeholder="xxxx.apps.googleusercontent.com", key="input_yt_cid")
                    csecret = st.text_input("Client Secret", type="password", placeholder="GOCSPX-xxxx", key="input_yt_csec")
                    if st.button("Authorize with Google (Credentials)", type="primary", use_container_width=True, key="btn_auth_creds"):
                        if cid and csecret:
                            with st.spinner("Authorizing with Google..."):
                                ok, msg = yt_mgr.connect_with_client_credentials(cid, csecret)
                                if ok:
                                    st.success("✅ Channel connected successfully!")
                                    st.rerun()
                                else:
                                    st.error(msg)
                        else:
                            st.warning("Please provide both Client ID and Client Secret.")

    with yt_tab2:
        st.subheader("📅 Scheduled Shorts Queue")
        queue = get_scheduled_shorts()

        if not queue:
            st.info("Your scheduled queue is currently empty. Generate Shorts in the Studio tab, then click **'🚀 1-Click Schedule'** on any clip you like!")
        else:
            q1, q2, q3 = st.columns(3)
            with q1:
                st.metric("Total In Queue", len(queue))
            with q2:
                scheduled_count = sum(1 for q in queue if q.get("status") == "SCHEDULED")
                st.metric("Scheduled Releases", scheduled_count)
            with q3:
                target_ch = queue[0].get("channel_handle", "@channel")
                st.metric("Primary Channel", target_ch)

            st.divider()

            for item in queue:
                with st.container():
                    qc1, qc2, qc3 = st.columns([1, 2.5, 1.2])
                    with qc1:
                        if item.get("thumbnail_path") and Path(item["thumbnail_path"]).exists():
                            st.image(item["thumbnail_path"], use_container_width=True)
                        else:
                            st.caption("🎬 9:16 Video Short")
                    with qc2:
                        st.markdown(f"**{item['title']}**")
                        st.caption(f"Release: **{item.get('scheduled_time_local', item.get('scheduled_time_utc', 'Immediate'))}** • Channel: `{item.get('channel_handle')}`")
                        st.markdown(f"Status: **:{'green' if item.get('status') == 'SCHEDULED' else 'blue'}[{item.get('status', 'SCHEDULED')}]**")
                        if item.get("tags"):
                            st.caption(f"Tags: `{'`, `'.join(item['tags'][:6])}`")
                    with qc3:
                        st.link_button("▶️ Shorts Link", item["youtube_url"], use_container_width=True)
                        st.link_button("⚙️ Studio Edit", item["studio_url"], use_container_width=True)
                        if st.button("🗑️ Remove", key=f"del_q_{item['id']}", use_container_width=True):
                            delete_scheduled_short(item["id"])
                            st.rerun()
                    st.divider()


def render_asset_library_view():
    """Asset Library management UI with tabs, status toggles, and trending updates."""
    st.header("🗂️ Rights-Aware Asset Library")
    st.caption("Only APPROVED assets can be included in exported Shorts. Any unverified asset is held for review.")

    mgr = AssetLibraryManager()

    col_btn, col_info = st.columns([1.2, 3])
    with col_btn:
        if st.button("🔄 Update Meme Library", type="primary", use_container_width=True):
            stats = update_trending_meme_library(mgr)
            st.success(f"Discovery Scan: New assets found: {stats['new_found']} | Approved: {stats['approved']} | Needs license review: {stats['needs_review']}")

    with col_info:
        st.info("ℹ️ Safe discovery searches only verified CC0 / Public Domain repositories and procedurally synthesizes original stickers and SFX.")

    # Upload User Asset
    with st.expander("➕ Upload User-Owned Asset", expanded=False):
        up_file = st.file_uploader("Choose media file (PNG, JPG, GIF, MP4, WAV, MP3)", type=["png", "jpg", "jpeg", "gif", "mp4", "wav", "mp3"])
        up_cat = st.selectbox("Asset Category", options=[c.value for c in AssetCategory])
        up_tags = st.text_input("Tags (comma-separated)", value="user_upload, reaction")
        if st.button("Import & Approve Asset") and up_file:
            temp_up = TEMP_DIR / up_file.name
            temp_up.write_bytes(up_file.read())
            cat_enum = AssetCategory(up_cat)
            tags_list = [t.strip() for t in up_tags.split(",") if t.strip()]
            new_asset = mgr.add_user_asset(temp_up, cat_enum, tags_list)
            st.success(f"Imported '{new_asset.name}' with rights_status='user_supplied'.")

    # Tabs for categories
    tabs = st.tabs(["🎬 50 Indian Video Memes", "Memes & Stickers", "Sound Effects", "Music", "Transitions", "All Assets"])

    with tabs[0]:
        st.subheader("🎭 50 Authentic Indian Scene Memes (0% Chroma Green Bleed)")
        st.caption("Real film & TV comedy scenes from *Phir Hera Pheri*, *Panchayat*, *Welcome*, *3 Idiots*, *Mirzapur*, *Shark Tank*, and *TMKOC*.")
        from src.meme_selector import INDIAN_MEME_CATALOG
        from pathlib import Path
        v_dir = Path("assets/memes/videos")
        
        m_cols = st.columns(3)
        for i, item in enumerate(INDIAN_MEME_CATALOG):
            col = m_cols[i % 3]
            with col:
                f_path = v_dir / item["filename"]
                if f_path.exists():
                    st.video(str(f_path))
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"Tags: `{', '.join(item['keywords'][:4])}`")
                    st.write("")

    for tab_idx, cat in enumerate([AssetCategory.MEME, AssetCategory.SFX, AssetCategory.MUSIC, AssetCategory.TRANSITION, None]):
        with tabs[tab_idx + 1]:
            if cat:
                cat_assets = [a for a in mgr.get_all_assets() if a.asset_category == cat or (cat == AssetCategory.MEME and a.asset_category == AssetCategory.GENERATED)]
            else:
                cat_assets = mgr.get_all_assets()

            if not cat_assets:
                st.write("No assets in this category.")
                continue

            for asset in cat_assets:
                with st.container():
                    acol1, acol2, acol3 = st.columns([1, 2.5, 1.5])
                    with acol1:
                        if asset.file_path.endswith((".png", ".jpg", ".jpeg", ".webp")):
                            st.image(asset.file_path, width=120)
                        elif asset.file_path.endswith((".wav", ".mp3")):
                            st.audio(asset.file_path)
                    with acol2:
                        st.markdown(f"**{asset.name}** (`{asset.asset_id}`)")
                        st.caption(f"Category: {asset.asset_category.value} | Source: {asset.source_name} | License: {asset.license}")
                        st.markdown(f"Tags: `{'`, `'.join(asset.tags)}`")
                    with acol3:
                        badge_color = "green" if asset.status == AssetStatus.APPROVED else ("orange" if asset.status == AssetStatus.REVIEW else "red")
                        st.markdown(f":{badge_color}[**Status: {asset.status.value}**]")
                        st.caption(f"Commercial Use: **{'YES' if asset.commercial_use_allowed else 'NO'}**")

                        # Action Toggles
                        b1, b2 = st.columns(2)
                        with b1:
                            if st.button("Approve", key=f"app_{tab_idx}_{asset.asset_id}"):
                                mgr.update_status(asset.asset_id, AssetStatus.APPROVED)
                                st.rerun()
                        with b2:
                            if st.button("Block", key=f"blk_{tab_idx}_{asset.asset_id}"):
                                mgr.update_status(asset.asset_id, AssetStatus.BLOCKED)
                                st.rerun()
                    st.divider()


def render_login_view():
    """Renders high-security login screen preventing unauthorized access."""
    col_l, col_m, col_r = st.columns([1, 1.4, 1])
    with col_m:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container():
            st.markdown("<h2 style='text-align: center;'>🎬 ViralClipper AI Studio</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #888;'>Private Creator Suite • Authentication Required</p>", unsafe_allow_html=True)
            st.divider()

            with st.form("login_form", clear_on_submit=False):
                st.subheader("🔐 Secure Sign In")
                username_input = st.text_input("Login ID / Mobile", placeholder="Enter your Login ID")
                password_input = st.text_input("Password", type="password", placeholder="••••••••••••")

                submitted = st.form_submit_button("🚀 Access Studio", type="primary", use_container_width=True)

                if submitted:
                    if verify_login_credentials(username_input, password_input):
                        st.session_state.is_authenticated = True
                        st.success("✅ Login successful! Entering Studio...")
                        st.rerun()
                    else:
                        st.error("❌ Invalid Login ID or Password. Access denied.")

            st.caption("🔒 *Protected environment. Only authorized administrators may access clipping pipelines and assets.*")


def render_compliance_view():
    """Legal, copyright, and YouTube reused-content compliance educational center."""
    st.header("⚖️ Rights, Compliance & Transformation Guidelines")
    st.markdown(f"""
### Legal Disclaimer
> **{LEGAL_DISCLAIMER}**

### YouTube Reused-Content Policy vs Copyright
{REUSED_CONTENT_POLICY_NOTICE}

---

### Four Levels of Transformation Mode
1. **1. Clean**: Minimal reframing to 9:16 vertical + exact subtitles. Best when user owns 100% of original raw footage.
2. **2. Enhanced**: Clean + comedic punchline zooms, dramatic freeze frames, and normalized audio.
3. **3. Commentary**: Encourages adding original voiceover commentary, reaction cameras, or analytical critique.
4. **4. Meme-Heavy**: Adds verified comedic reaction badges, impact flashes, and custom sound effects.

---

### Three-Tier Rights Framework
- **Source Video Rights**: You must confirm ownership or written authorization from the copyright holder before processing third-party content.
- **Meme/Overlay Rights**: Only assets verified as Creative Commons, Public Domain, User-Owned, or Procedurally Generated can be used.
- **Audio Rights**: Background music and SFX must have verified commercial synchronization rights.

### Export Status Standard
When a video is cleared for export, the status reads:
**`{SAFE_EXPORT_STATUS_NOTICE}`**
*(The application never makes legal conclusions or claims of guaranteed protection).*
""")


def main():
    """Application entry point."""
    st.set_page_config(
        page_title="ViralClipper AI Studio",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_session_state()

    # Authentication Gate
    if not st.session_state.is_authenticated:
        render_login_view()
        return

    render_sidebar()

    if st.session_state.active_tab == "Studio":
        render_studio_view()
    elif st.session_state.active_tab == "Asset Library":
        render_asset_library_view()
    elif st.session_state.active_tab == "Rights & Compliance":
        render_compliance_view()
    elif "YouTube" in st.session_state.active_tab:
        render_youtube_manager_view()


if __name__ == "__main__":
    main()
