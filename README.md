# 🎬 ViralClipper AI Studio

> **Automated AI Vertical Shorts Studio for Comedy, Podcasts & Standup with 1-Click YouTube Publishing**

ViralClipper AI Studio transforms long-form comedy and podcast footage into viral 9:16 vertical Shorts. Powered by the official Google Gemini SDK (`google-genai`), `faster-whisper`, OpenCV, and FFmpeg, the studio features:
- **🎙️ Transformative Faceless AI Commentary**: Slices source video into discrete setup and punchline beats, interleaved with AI voiceover commentary and roaster verdicts.
- **🎨 Visual & Color Grading**: High-contrast "Cinematic Dark" grade with ambient Cyan/Teal vignette glow and reaction badge stickers.
- **🎵 Dynamic Sound Design**: Low-tempo Phonk/Trap beat layering with an energetic +10dB beat drop on punchlines.
- **😂 Real-Scene Meme Cutaways**: Spliced genuine live-action video meme reactions right at the climax.
- **📺 1-Click YouTube Shorts Scheduler**: Connect your YouTube channel via Google OAuth 2.0 or Instant Demo Mode, and schedule any Short in 1 click with AI titles, descriptions, search tags, and hashtags.

---

## ⚡ Super-Easy Quickstart (Another PC)

We have made running this project on another computer require **zero manual work**:

### On Windows:
1. Clone or download the repository to the new PC.
2. **Double-click `run.bat`**!
   - It automatically checks Python.
   - It automatically creates the virtual environment (`.venv`).
   - It automatically installs all dependencies from `requirements.txt`.
   - It automatically checks if FFmpeg is installed.
   - It automatically launches the studio in your browser at `http://localhost:8501`!

### On macOS / Linux:
1. Clone or download the repository.
2. Open terminal and run:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

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

## 🚀 How to Upload to GitHub (For arvindk459895@gmail.com)

Follow these 3 simple steps to upload this project to your GitHub profile:

### Step 1: Create a Repository on GitHub
1. Sign in to your GitHub account ([github.com](https://github.com/)) with **arvindk459895@gmail.com**.
2. Click the **`+`** icon at the top right ➔ click **New repository** (or go to [github.com/new](https://github.com/new)).
3. Repository name: `viral-clipper-ai-studio` (or your preferred name).
4. Select **Public** or **Private**.
5. **Important**: Do **NOT** check "Add a README file", "Add .gitignore", or "Choose a license" (we already created all of these for you).
6. Click **Create repository**.

### Step 2: Push from your Computer
Open PowerShell or Terminal in this project folder (`viral_clipper_ai_studio`) and run:

```bash
git add .
git commit -m "Initial commit: ViralClipper AI Studio with 1-Click YouTube Scheduler"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/viral-clipper-ai-studio.git
git push -u origin main
```
*(Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username).*

---

## 📥 How to Run on Another PC (Step-by-Step)

Once uploaded to GitHub, running it on any other PC takes less than 2 minutes:

1. Open Terminal or PowerShell on the new PC and clone the repo:
   ```bash
   git clone https://github.com/YOUR_GITHUB_USERNAME/viral-clipper-ai-studio.git
   cd viral-clipper-ai-studio
   ```
2. **Double-click `run.bat`** (or run `./run.sh` on Mac/Linux).
3. The app opens at `http://localhost:8501`. Enter your Gemini API key in the sidebar, and you're ready to create viral Shorts!

---

## 📁 Repository Structure

```
viral_clipper_ai_studio/
├── app.py                     # Streamlit Studio Web Application
├── run.bat                    # 1-Click Automated Launcher for Windows
├── run.sh                     # 1-Click Automated Launcher for macOS/Linux
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
