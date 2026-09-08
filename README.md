# ? ViralClipper AI Studio

> **Production-Quality Automated Short-Form Video Studio for Comedy, Podcasts & Hinglish Content**

ViralClipper AI Studio transforms long-form authorized video content into highly edited, high-engagement 9:16 vertical Shorts. Powered by the official Google Gemini SDK (`google-genai`), `faster-whisper`, OpenCV, and FFmpeg, the studio features comedy structure analysis, active speaker tracking, word-highlighted bilingual captions, dynamic punchline zooms, and a copyright-aware asset management pipeline.

---

## 1. File Structure

```
viral_clipper_ai_studio/
??? app.py                     # Main Streamlit web application & interactive UI
??? src/
?   ??? config.py              # Configuration, model choices, scoring weights, constants
?   ??? youtube.py             # yt-dlp metadata extraction & audio/video ingestion
?   ??? transcription.py       # faster-whisper transcription (Hindi, Hinglish, English)
?   ??? audio_analysis.py      # Audio DSP: laughter, applause, shouting, dramatic pauses, RMS
?   ??? video_analysis.py      # OpenCV shot changes, face detection, 9:16 reframing center
?   ??? candidate_detector.py  # Hook-Setup-Punchline moment detector & overlap NMS
?   ??? gemini_analyzer.py     # Gemini SDK analysis, strict JSON schema, timeline generator
?   ??? clip_scorer.py         # 8-component Viral Potential Score calculator
?   ??? asset_license.py       # Rights/license data models & export clearance gates
?   ??? asset_downloader.py    # Trending asset discovery & CC0/license classifier
?   ??? meme_manager.py        # Asset library manager & procedural sticker/SFX synthesizer
?   ??? meme_selector.py       # Contextual joke-to-meme matcher & safe placement allocator
?   ??? effects.py             # Punch zooms, freeze frames, camera shake, white flashes
?   ??? editor.py              # 9:16 vertical video renderer & audio loudnorm engine
?   ??? captions.py            # ASS subtitle generator with keyword and punchline highlights
?   ??? thumbnail.py           # Reaction frame extractor & bold cover typography generator
?   ??? metadata.py            # 3 title options, description with disclaimer, 5-10 hashtags
?   ??? rights_checker.py      # Pre-export rights audit & rights_report.json
?   ??? pipeline.py            # Master end-to-end workflow orchestrator
?   ??? utils.py               # Timestamps, FFmpeg runner, file helpers
??? assets/
?   ??? memes/                 # Cleared reaction images and stickers
?   ??? gifs/                  # Cleared reaction animations
?   ??? sfx/                   # Cleared sound effects (pop, whoosh, scratch)
?   ??? music/                 # Cleared background music tracks
?   ??? transitions/           # Transitions and video masks
??? metadata/
?   ??? asset_library.json     # Full asset catalog with licensing metadata
??? outputs/                   # Exported Shorts (clean, meme, heavy), thumbnails, ZIPs
??? temp/                      # Ephemeral working directory
??? tests/                     # 33 comprehensive automated tests
??? requirements.txt           # Pinned Python package dependencies
??? .env.example               # Environment variables template
??? README.md                  # Comprehensive studio documentation
```

---

## 2. Installation Commands

Ensure Python 3.10+ is installed on your system.

```bash
# Clone or navigate to the project directory
cd viral_clipper_ai_studio

# Create a virtual environment (recommended)
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux / macOS:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

---

## 3. FFmpeg Setup

FFmpeg is required for video slicing, dynamic 9:16 cropping, subtitle burn-in, and audio normalization.

### Windows:
1. Download an official build (e.g. from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)).
2. Extract the archive and add the `bin/` folder to your system `PATH`.
3. Verify in command prompt or PowerShell:
   ```cmd
   ffmpeg -version
   ```

### macOS:
```bash
brew install ffmpeg
```

### Linux (Ubuntu/Debian):
```bash
sudo apt update && sudo apt install -y ffmpeg
```

---

## 4. Gemini Setup

ViralClipper AI Studio uses the official Google Gemini SDK (`google-genai`).

1. Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/).
2. You can set it in an environment variable or enter it directly in the app sidebar:
   ```bash
   cp .env.example .env
   # Edit .env and set GEMINI_API_KEY=your_key_here
   ```
3. **Privacy & Security**:
   - The API key input in the Streamlit UI is masked (`type="password"`).
   - The key is stored strictly in volatile session state.
   - It is never written to logs, never committed to source control, and never exposed in output files.
4. **Configurable Models**:
   - Easily switch between `gemini-2.5-flash` (default, fast), `gemini-3.7-flash`, `gemini-3.5-flash-lite`, and `gemini-2.5-pro`.

---

## 5. Run Command

Launch the Streamlit web application:

```bash
streamlit run app.py
```

The web interface will open automatically in your browser at `http://localhost:8501`.

---

## 6. How to Add Memes

### Method A: Via the Web UI
1. Open the **Asset Library** view from the sidebar.
2. Expand **Upload User-Owned Asset**.
3. Select your file (`.png`, `.jpg`, `.gif`, `.mp4`).
4. Select category: `memes` or `gifs`.
5. Enter tags (e.g. `funny, disbelief, roast`).
6. Click **Import & Approve Asset**. The asset is automatically cataloged with `rights_status="user_supplied"`.

### Method B: Manual File Placement
1. Place your cleared image in `assets/memes/` or `assets/gifs/`.
2. Add an entry to `metadata/asset_library.json` with `status: "APPROVED"` and `commercial_use_allowed: true`.

---

## 7. How to Add Sound Effects (SFX)

1. Place your licensed or user-owned `.wav` or `.mp3` audio files into `assets/sfx/`.
2. In the UI, use the **Upload User-Owned Asset** panel and set Category to `sfx`.
3. The system will automatically tag and normalize the sound effect for ducked audio mixing (-14dB to -18dB relative to spoken dialogue).

---

## 8. How the Trending Asset Updater Works

Clicking **?? Update Meme Library** initiates the safe discovery module (`src/asset_downloader.py`):
1. It queries approved, verified Creative Commons repositories (such as CC0 / Public Domain repositories) for trending reaction concepts.
2. It explicitly checks licensing terms:
   - Permissive CC0 / Public Domain $ightarrow$ Automatically classified as **`APPROVED`**.
   - Ambiguous, non-commercial (CC-BY-NC), or unverified sources $ightarrow$ Categorized as **`REVIEW`**.
3. It displays real discovery metrics:
   ```
   New assets found: 8 | Approved: 6 | Needs license review: 2
   ```
4. **Safety Guarantee**: Unverified assets are never silently injected into video exports.

---

## 9. How the Rights Checker Works

Before exporting any final Short or ZIP package, the pre-export rights gate (`src/rights_checker.py`) performs a 4-tier audit:

1. **Source Video Check**: Verifies that the user checked the mandatory confirmation box confirming ownership or authorization (`USER_CONFIRMED_AUTHORIZED`).
2. **Meme Rights Check**: Ensures 100% of graphic overlays have `status == "APPROVED"`. Any asset marked `REVIEW` or `BLOCKED` halts export.
3. **SFX Rights Check**: Verifies sound effect licensing.
4. **Music Rights Check**: Ensures music tracks are cleared or marked NONE.
5. **Output**:
   - Status: **`No unverified assets detected.`** (The system never claims "fair use guarantee" or "copyright safe").
   - Generates a permanent compliance record: `rights_report.json`.

---

## 10. Known Limitations

1. **Offline Mode vs Live YouTube**:
   - If downloading long YouTube videos, download speeds and video resolutions depend on your local network and YouTube's bandwidth.
   - For rapid testing and air-gapped systems, use the built-in **?? Offline Demo Mode**.
2. **Whisper Transcription on CPU**:
   - On systems without an NVIDIA GPU, `faster-whisper` runs using CPU INT8 quantization. On very long videos (1 hour+), transcription may take several minutes.
3. **Complex Multi-Speaker Overlap**:
   - In scenes where multiple speakers talk simultaneously with rapid cross-talk, active speaker tracking centers on the highest-confidence face contour.
4. **Legal & Monetization Policies**:
   - YouTube's reused-content policy is distinct from copyright law. Even heavily edited and transformed videos remain subject to platform policy review and human creator rights.

---

## Testing & Quality Assurance

Run the automated test suite covering all 10 architectural phases:

```bash
python -m pytest tests/ -v
```

**33 unit and integration tests** verify:
- Configuration, paths, and legal disclaimers
- YouTube URL and metadata validation
- Transcription parsing and Hindi/Hinglish cue handling
- Audio DSP (laughter detection, dramatic pauses, loudness normalization)
- Video geometry, face detection, and 9:16 cropping
- Gemini Pydantic validation and Viral Potential Score formula
- Video effects, ASS subtitle formatting, and real MP4 rendering
- Asset licensing triage and safe discovery
- Contextual joke-to-meme matching
- Metadata and thumbnail cover typography
- Pre-export rights auditing and ZIP packaging
