# 🎬 ViralClipper AI Studio

> **Automated AI Vertical Shorts Studio for Comedy, Podcasts & Standup with 1-Click YouTube Publishing**

ViralClipper AI Studio transforms long-form comedy and podcast footage into viral 9:16 vertical Shorts. Powered by the official Google Gemini SDK (`google-genai`), `faster-whisper`, OpenCV, and FFmpeg, the studio features:
- **🎙️ Transformative Faceless AI Commentary**: Slices source video into discrete setup and punchline beats, interleaved with AI voiceover commentary and roaster verdicts.
- **🎨 Visual & Color Grading**: High-contrast "Cinematic Dark" grade with ambient Cyan/Teal vignette glow and reaction badge stickers.
- **🎵 Dynamic Sound Design**: Low-tempo Phonk/Trap beat layering with an energetic +10dB beat drop on punchlines.
- **😂 Real-Scene Meme Cutaways**: Spliced genuine live-action video meme reactions right at the climax.
- **📺 1-Click YouTube Shorts Scheduler**: Connect your YouTube channel via Google OAuth 2.0 or Instant Demo Mode, and schedule any Short in 1 click with AI titles, descriptions, search tags, and hashtags.

---

## 🚀 What to Do After Entering the Project Folder (How to Run It)

Once you clone or open the `viral_clipper_ai_studio` folder on any computer:

### Step 1: Launch the Studio (1-Click)
- **On Windows**: Simply **double-click `run.bat`** (or open Command Prompt in the folder and type `run.bat`).
- **On macOS / Linux**: Open Terminal in the folder and run:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```
> **What this does automatically:**
> - Detects Python on your computer.
> - Creates an isolated virtual environment (`.venv`).
> - Installs all dependencies from `requirements.txt`.
> - Checks if FFmpeg is installed (with 1-click install instructions if missing).
> - Opens the studio interface in your web browser at **`http://localhost:8501`**.

---

### Step 2: Set Your Gemini API Key
1. Get a free API key from [Google AI Studio](https://aistudio.google.com/).
2. In the left sidebar of the studio under **🔑 Gemini AI Configuration**, paste your API key.
3. Keep **"💾 Remember key on reload"** checked (it securely saves your key locally so you never have to re-enter it).

---

### Step 3: Select Video Source & Confirm Rights
1. Check the mandatory authorization checkbox in the top **⚖️ Copyright & Rights Authorization** banner.
2. Select your input video:
   - **🔗 YouTube Ingestion**: Paste any authorized YouTube video URL.
   - **📁 Upload Local Video**: Drag & drop any MP4, MOV, MKV, or WEBM file from your computer.
   - **🧪 Offline Demo Mode**: Test immediately with built-in comedy footage without needing downloads.

---

### Step 4: Choose Studio Mode & Settings
- **🎙️ Faceless AI Commentary (Recommended)**: Builds a complete 5-beat viral Short with energetic AI voiceover (Hinglish/Hindi/English), Cinematic Dark color grading, ambient cyan glow, phonk beat drops, and live-action meme cutaways.
- **⚡ Standard Short**: High-energy Opus Clip virality with speaker tracking and karaoke subtitles.
- Choose your preferred top headline banner mode, video duration, and framing.

---

### Step 5: Generate & Schedule in 1 Click!
1. Click **`🚀 Analyze & Generate Shorts`**.
2. Watch the live progress bar update beat-by-beat in real time.
3. Review your rendered 9:16 Shorts in the video player, download individual MP4s or the full package ZIP, or schedule directly to YouTube!

---

## 📺 How to Connect Your YouTube Account for Uploading

The studio gives you **two easy ways** to connect a YouTube channel for 1-click scheduling:

### Option A: Instant Demo Mode (Zero-Setup Sandbox — 10 Seconds)
*Use this if you want to test the 1-click scheduler immediately without setting up Google developer credentials:*
1. In the studio sidebar under **🧭 Studio Navigation**, select **`📺 YouTube Channel & Scheduler`**.
2. Under **"🧪 Instant Test Channel (Demo Mode)"**:
   - Enter your channel name (e.g. `My Comedy Channel`) and handle (e.g. `@MyComedyChannel`).
   - Click **`🚀 Activate Demo Channel Instantly`**.
3. Done! The channel card turns green, and you can immediately schedule any generated Short in 1 click.

---

### Option B: Connect a Real YouTube Channel (Official Google OAuth 2.0)
*Use this to automatically upload and schedule real videos directly to your live YouTube channel:*

Google requires a free developer credential (`client_secrets.json`) to authorize uploads:

#### 1. Enable YouTube API in Google Cloud
1. Go to **[Google Cloud Console](https://console.cloud.google.com/)** and sign in with your Google account.
2. Click **Select a project** (top-left) ➔ Click **NEW PROJECT** ➔ Name it `ViralClipper` ➔ Click **Create**.
3. In the top search bar, search for **`YouTube Data API v3`** ➔ Click on it ➔ Click **Enable**.

#### 2. Configure OAuth Consent Screen
1. Go to **APIs & Services** ➔ **OAuth consent screen**.
2. Select **External** ➔ Click **Create**.
3. Enter:
   - **App name**: `ViralClipper Studio`
   - **User support email**: Your email address
   - **Developer contact email**: Your email address
   - Click **Save and Continue**.
4. In the **Test users** step:
   - Click **+ ADD USERS** ➔ Enter the email address of the YouTube account you want to upload to ➔ Click **Save and Continue**.
   > **Note for Different / Brand Accounts**: If you want to upload to a different account (not your primary developer email) or a brand channel, simply add that specific email here as a Test User!

#### 3. Download `client_secrets.json`
1. Go to **APIs & Services** ➔ **Credentials**.
2. Click **+ CREATE CREDENTIALS** (top) ➔ select **OAuth client ID**.
3. Under **Application type**, select **Desktop app**.
4. Name it `ViralClipper Desktop` ➔ Click **Create**.
5. Click **Download JSON** on the popup (this downloads your `client_secrets.json`).

#### 4. Connect in the Web Studio
1. In the studio web app, navigate to **`📺 YouTube Channel & Scheduler`**.
2. Under **"🔑 Official Google Cloud OAuth 2.0"**, drag and drop your `client_secrets.json` file.
3. Click **`Authorize with Google (File)`**.
4. A Google sign-in window will open in your browser:
   - Select your target YouTube account (or click *"Use another account"* to log into a different channel).
   - If managing a Brand Channel, select the exact channel name.
   - Click **Continue** / **Allow** to grant YouTube upload permissions.
5. 🎉 **Connected!** Your live YouTube channel name, avatar, and subscriber count will now appear in the studio.

---

### 🚀 How to Schedule a Video Once Connected

1. Go to the **Studio** tab.
2. Scroll down to any Short you like in the results.
3. Open the **`🚀 1-Click Schedule on YouTube Shorts`** drawer:
   - **Title**: Select from the 3 AI-generated curiosity/POV titles or type your own (includes `#Shorts` format).
   - **Description**: Pre-filled with viral summary, timestamps, creator credit, and fair use disclaimer.
   - **Search Tags**: Pre-filled with search keywords (`comedy, standup comedy, hindi comedy, funny, shorts, viral`).
   - **Hashtags**: Pre-filled with `#Shorts`, `#Comedy`, etc.
   - **Publish Timing**: Select **🌆 Tomorrow Prime Time (6:00 PM)** (recommended for peak comedy viewing), **🌅 Tomorrow Morning (9:00 AM)**, **⚡ Immediate Release (Public)**, or **📅 Custom Date & Time**.
   - **Cover Thumbnail**: Pick Cover Option 1 (Reaction Face) or Option 2 (Curiosity Zoom).
   - Click **`🚀 1-Click Schedule on @YourChannel`**!
4. Direct clickable links will appear:
   - `▶️ Open YouTube Shorts Link`
   - `⚙️ Manage in YouTube Studio`
5. You can view, track, and manage all your scheduled videos anytime in the **`📅 Scheduled Shorts Queue`** tab!

---

## 🛠️ Prerequisites (If Setting Up Manually)

1. **Python 3.10, 3.11, 3.12, or 3.13**
   - Download from [python.org](https://www.python.org/downloads/).
   - *Windows note*: Check **"Add python.exe to PATH"** during installation.

2. **FFmpeg** (Required for video encoding & subtitles):
   - **Windows (1-click via Terminal)**:
     ```powershell
     winget install Gyan.FFmpeg
     ```
     *(Or download from [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) and add `bin/` to your PATH).*
   - **macOS**:
     ```bash
     brew install ffmpeg
     ```
   - **Linux (Ubuntu/Debian)**:
     ```bash
     sudo apt update && sudo apt install -y ffmpeg
     ```

3. **Google Gemini API Key (Free)**:
   - Get a free API key at [Google AI Studio](https://aistudio.google.com/).
   - Enter it directly into the web app sidebar (saved securely and loaded automatically).

---

## 📁 Repository Structure

```
viral_clipper_ai_studio/
├── app.py                     # Streamlit Studio Web Application
├── run.bat                    # 1-Click Automated Launcher for Windows
├── run.sh                     # 1-Click Automated Launcher for macOS/Linux
├── push_to_github.bat         # 1-Click GitHub Repository Uploader
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Excludes heavy video outputs and API keys
├── src/
│   ├── pipeline.py            # Master end-to-end clipping and rendering pipeline
│   ├── faceless_editor.py     # 5-beat faceless short editor with phonk BGM & subtitles
│   ├── youtube_publisher.py   # 1-Click YouTube Shorts Scheduler & OAuth channel manager
│   ├── candidate_detector.py  # Hook-Setup-Punchline detection with scene resolution
│   ├── commentary_engine.py   # AI Hinglish commentary & creative CTA generation
│   ├── captions.py            # Word-by-word karaoke ASS subtitles
│   ├── meme_selector.py       # Contextual meme matching engine
│   └── ...
├── assets/
│   ├── memes/videos/          # Genuine live-action reaction memes
│   ├── music/                 # 130 BPM Phonk beats with beat drop
│   ├── stickers/              # Transparent reaction overlay badges
│   └── sfx/                   # Pop, whoosh, record scratch sound effects
├── outputs/                   # Exported Shorts & thumbnails (git-ignored)
└── tests/                     # Comprehensive automated test suite
```

---

## 🧪 Testing

To verify all components and publishing systems locally:
```bash
pytest tests/
```
