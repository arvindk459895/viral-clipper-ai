"""
ViralClipper AI Studio - Configuration Module
"""
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
ASSETS_DIR = BASE_DIR / "assets"
MEMES_DIR = ASSETS_DIR / "memes"
GIFS_DIR = ASSETS_DIR / "gifs"
SFX_DIR = ASSETS_DIR / "sfx"
MUSIC_DIR = ASSETS_DIR / "music"
TRANSITIONS_DIR = ASSETS_DIR / "transitions"
METADATA_DIR = BASE_DIR / "metadata"
ASSET_LIBRARY_PATH = METADATA_DIR / "asset_library.json"
OUTPUTS_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"
CREDENTIALS_DIR = BASE_DIR / "credentials"
YOUTUBE_TOKEN_FILE = CREDENTIALS_DIR / "youtube_token.json"
YOUTUBE_CLIENT_SECRETS_FILE = CREDENTIALS_DIR / "client_secrets.json"
SCHEDULED_SHORTS_FILE = OUTPUTS_DIR / "scheduled_shorts.json"

for d in [MEMES_DIR, GIFS_DIR, SFX_DIR, MUSIC_DIR, TRANSITIONS_DIR, METADATA_DIR, OUTPUTS_DIR, TEMP_DIR, CREDENTIALS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
AVAILABLE_GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.7-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro"
]

VIRAL_WEIGHTS: Dict[str, float] = {
    "hook": 0.15,
    "humor": 0.20,
    "punchline": 0.15,
    "reaction": 0.15,
    "standalone": 0.10,
    "rewatch": 0.10,
    "shareability": 0.10,
    "visual": 0.05
}

OPUS_VIRAL_WEIGHTS: Dict[str, float] = {
    "hook": 0.30,   # First 2-3s curiosity & opening velocity
    "flow": 0.30,   # Narrative pacing, continuity, standalone clarity
    "value": 0.25,  # Humor roar, punchline contrast, emotional arousal
    "trend": 0.15   # Quotability, shareability, meme potential
}

CONTENT_TYPES: List[str] = [
    "Auto",
    "Comedy",
    "Podcast",
    "Interview",
    "Reaction",
    "Gaming",
    "Educational",
    "News",
    "Other"
]

CLIP_COUNT_OPTIONS: List[int] = [3, 5, 10, 20]
CLIP_DURATION_OPTIONS: List[str] = ["15 sec", "30 sec", "45 sec", "60 sec", "Auto"]
EDITING_STYLES: List[str] = ["Clean", "Modern", "Meme", "Heavy Meme"]
TRANSFORMATION_LEVELS: List[str] = ["1. Clean", "2. Enhanced", "3. Commentary", "4. Meme-heavy"]

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_FPS = 30

LEGAL_DISCLAIMER = (
    "Copyright and monetization decisions depend on the underlying material, rights, jurisdiction, "
    "and platform review. Editing effects do not guarantee protection from claims, takedowns, or strikes."
)

REUSED_CONTENT_POLICY_NOTICE = (
    "YouTube's reused-content policy is separate from copyright. Meaningful commentary, storytelling, "
    "reaction, or substantive editing can help with reused-content eligibility, but does NOT automatically eliminate copyright obligations."
)

SAFE_EXPORT_STATUS_NOTICE = "No unverified assets detected."

KEY_STORE_PATH = BASE_DIR / ".gemini_api_key"


def load_saved_api_key() -> str:
    """Loads saved Gemini API key from environment variable or local persistence file."""
    import os
    env_k = os.getenv("GEMINI_API_KEY", "").strip()
    if env_k:
        return env_k
    if KEY_STORE_PATH.exists():
        try:
            saved = KEY_STORE_PATH.read_text(encoding="utf-8").strip()
            if saved:
                return saved
        except Exception:
            pass
    return ""


def save_api_key_locally(key: str) -> bool:
    """Persists Gemini API key locally so it survives browser reloads."""
    try:
        clean_key = key.strip()
        if clean_key:
            KEY_STORE_PATH.write_text(clean_key, encoding="utf-8")
        elif KEY_STORE_PATH.exists():
            KEY_STORE_PATH.unlink()
        return True
    except Exception:
        return False
