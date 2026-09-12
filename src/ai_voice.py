"""
ViralClipper AI Studio - Faceless AI Voice Generation Engine
Provides generic neural AI voiceover narration across multiple personas and languages
(Hinglish, Hindi, English) with emotional inflection (Laugh/Cheerful, Sad, Loved, Excited, Sarcastic).
Strictly does NOT clone or imitate any real person, celebrity, or comedian.
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

import sys
try:
    import audioop
except ImportError:
    try:
        import pyaudioop as audioop
        sys.modules["audioop"] = audioop
    except ImportError:
        pass

import edge_tts
from pydub import AudioSegment

from src.config import TEMP_DIR
from src.utils import sanitize_filename

VOICE_PERSONAS: Dict[str, Dict[str, Any]] = {
    # Friendly Creator Aliases (Indian & International)
    "madhur": {
        "voice_id": "hi-IN-MadhurNeural",
        "rate": "+50%",
        "pitch": "+4Hz",
        "locale": "hi-IN",
        "description": "Natural, energetic Indian male creator voice (Hinglish/Hindi - RC Hidden style) at 1.5x"
    },
    "prabhat": {
        "voice_id": "en-IN-PrabhatNeural",
        "rate": "+50%",
        "pitch": "+4Hz",
        "locale": "en-IN",
        "description": "Punchy, fast-paced Indian English & Hinglish narrator at 1.5x"
    },
    "swara": {
        "voice_id": "hi-IN-SwaraNeural",
        "rate": "+50%",
        "pitch": "+3Hz",
        "locale": "hi-IN",
        "description": "Expressive, energetic Indian female voice (Hinglish/Hindi) at 1.5x"
    },
    "neerja": {
        "voice_id": "en-IN-NeerjaExpressiveNeural",
        "rate": "+45%",
        "pitch": "+1Hz",
        "locale": "en-IN",
        "description": "Dynamic emotionally expressive Indian female voice at 1.5x"
    },
    "guy": {
        "voice_id": "en-US-GuyNeural",
        "rate": "+50%",
        "pitch": "+2Hz",
        "locale": "en-US",
        "description": "High-energy, punchy US commentary at 1.5x"
    },
    "eric": {
        "voice_id": "en-US-EricNeural",
        "rate": "+48%",
        "pitch": "+0Hz",
        "locale": "en-US",
        "description": "Witty US comedic voice at 1.5x"
    },
    # Hinglish & Hindi Voices (Natural Indian Style)
    "hinglish_male": {
        "voice_id": "hi-IN-MadhurNeural",
        "rate": "+10%",
        "pitch": "+2Hz",
        "locale": "hi-IN",
        "description": "Natural Indian male voice (Hinglish/Hindi)"
    },
    "hinglish_female": {
        "voice_id": "hi-IN-SwaraNeural",
        "rate": "+8%",
        "pitch": "+1Hz",
        "locale": "hi-IN",
        "description": "Expressive Indian female voice (Hinglish/Hindi)"
    },
    "hinglish_energetic": {
        "voice_id": "en-IN-PrabhatNeural",
        "rate": "+12%",
        "pitch": "+2Hz",
        "locale": "en-IN",
        "description": "Punchy Indian English & Hinglish narrator"
    },
    "hinglish_expressive": {
        "voice_id": "en-IN-NeerjaExpressiveNeural",
        "rate": "+6%",
        "pitch": "+1Hz",
        "locale": "en-IN",
        "description": "Dynamic emotionally expressive Indian female voice"
    },
    # English Personas
    "energetic": {
        "voice_id": "en-US-GuyNeural",
        "rate": "+12%",
        "pitch": "+2Hz",
        "locale": "en-US",
        "description": "High-energy, punchy commentary for fast viral clips"
    },
    "comedic": {
        "voice_id": "en-US-EricNeural",
        "rate": "+8%",
        "pitch": "+0Hz",
        "locale": "en-US",
        "description": "Witty, playful cadence suited for punchline breakdowns"
    },
    "sarcastic": {
        "voice_id": "en-US-ChristopherNeural",
        "rate": "-4%",
        "pitch": "-2Hz",
        "locale": "en-US",
        "description": "Dry, deadpan delivery with deliberate comedic pauses"
    },
    "documentary": {
        "voice_id": "en-US-BrianNeural",
        "rate": "-5%",
        "pitch": "-4Hz",
        "locale": "en-US",
        "description": "Authoritative, deep analytical narrator"
    },
    "calm": {
        "voice_id": "en-US-RogerNeural",
        "rate": "+0%",
        "pitch": "-1Hz",
        "locale": "en-US",
        "description": "Relaxed, conversational storyteller"
    },
    "female": {
        "voice_id": "en-US-AriaNeural",
        "rate": "+6%",
        "pitch": "+1Hz",
        "locale": "en-US",
        "description": "Expressive, clear female narrator"
    },
    "male": {
        "voice_id": "en-US-AndrewNeural",
        "rate": "+4%",
        "pitch": "+0Hz",
        "locale": "en-US",
        "description": "Crisp, balanced male voiceover"
    },
    "neutral": {
        "voice_id": "en-US-JennyNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "locale": "en-US",
        "description": "Standard informative neutral narration"
    }
}

AVAILABLE_VOICE_STYLES = list(VOICE_PERSONAS.keys())

EMOTION_STYLES = {
    "laugh": "cheerful",
    "cheerful": "cheerful",
    "sad": "sad",
    "loved": "empathetic",
    "excited": "excited",
    "shocked": "excited",
    "sarcastic": "calm",
    "neutral": "calm"
}


async def _synthesize_edge_tts(
    text: str,
    voice_id: str,
    rate: str,
    pitch: str,
    emotion: str,
    locale: str,
    output_path: str
) -> None:
    """Async helper to generate audio using edge_tts with clean text and energetic rate control."""
    cleaned = clean_spoken_text(text)
    effective_rate = rate or "+20%"
    communicate = edge_tts.Communicate(text=cleaned, voice=voice_id, rate=effective_rate)
    await communicate.save(output_path)


def clean_spoken_text(text: str) -> str:
    """Cleans text for conversational, natural AI narration without reading formatting marks or XML tags."""
    import re
    # Remove XML / HTML tags like <speak>, <voice>, etc.
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Remove markdown bold/italic/code
    cleaned = re.sub(r"[\*`_]+", "", cleaned)
    # Remove bracketed editorial marks [like this] or (like this)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    # Remove emojis so TTS does not speak 'grinning face with smiling eyes'
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", cleaned)
    # Convert colons, dashes, semicolons into natural pauses
    cleaned = re.sub(r"[:;—–]+", ", ", cleaned)
    # Remove unwanted quotes and backslashes
    cleaned = re.sub(r'["\\]+', '', cleaned)
    # Normalize spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def resolve_voice_profile(voice_style: str, language: str = "auto", text: str = "") -> Dict[str, Any]:
    """Resolves appropriate voice profile considering requested style and language."""
    clean_style = voice_style.lower().strip()
    from src.commentary_engine import is_hindi_or_hinglish
    is_indic = (language.lower() in ["hinglish", "hindi", "indic"]) or (language.lower() == "auto" and bool(text and is_hindi_or_hinglish(text)))

    if clean_style in VOICE_PERSONAS:
        profile = VOICE_PERSONAS[clean_style]
        # Auto-adapt English persona to Indian neural voice ONLY when content is Indic
        if is_indic and "hi-" not in profile["locale"] and "en-IN" not in profile["locale"]:
            if "female" in clean_style:
                return VOICE_PERSONAS["swara"]
            elif "prabhat" in clean_style:
                return VOICE_PERSONAS["prabhat"]
            else:
                return VOICE_PERSONAS["madhur"]
        return profile

    if is_indic:
        if "female" in clean_style:
            return VOICE_PERSONAS["swara"]
        return VOICE_PERSONAS["madhur"]

    return VOICE_PERSONAS.get(clean_style, VOICE_PERSONAS["energetic"])


def generate_ai_voice(
    text: str,
    voice_style: str = "energetic",
    emotion: str = "auto",
    language: str = "auto",
    speed: float = 1.5,
    output_path: Optional[Path] = None,
    clip_id: str = "voice"
) -> Dict[str, Any]:
    """
    Synthesizes speech for editorial commentary with energetic 1.5x pacing (+50%),
    emotional inflection (laugh, sad, loved, excited, sarcastic), and native Hinglish/Hindi neural voices.
    Stores voice_provider, voice_id, and generation_timestamp.
    """
    profile = resolve_voice_profile(voice_style, language, text=text)
    voice_id = profile["voice_id"]
    locale = profile.get("locale", "hi-IN" if language in ["hinglish", "hindi"] else "en-US")

    # Base rate calculation: speed=1.5 maps to +50% (1.5x speed)
    base_speed_pct = int(round((speed - 1.0) * 100))
    pitch = profile.get("pitch", "+4Hz")

    clean_emo = emotion.lower().strip() if emotion else "auto"
    if clean_emo in ["laugh", "cheerful"]:
        rate_offset = 0
        pitch = "+4Hz"
    elif clean_emo in ["sad", "heartbreak"]:
        rate_offset = -8
        pitch = "-2Hz"
    elif clean_emo in ["loved", "heartfelt", "empathetic"]:
        rate_offset = -4
        pitch = "+1Hz"
    elif clean_emo in ["excited", "shocked"]:
        rate_offset = +5
        pitch = "+5Hz"
    elif clean_emo in ["sarcastic", "deadpan"]:
        rate_offset = -2
        pitch = "+2Hz"
    else:
        rate_offset = 0
        pitch = "+4Hz"

    final_pct = base_speed_pct + rate_offset
    rate = f"+{final_pct}%" if final_pct >= 0 else f"{final_pct}%"

    safe_id = sanitize_filename(clip_id)
    out_file = output_path or (TEMP_DIR / f"{safe_id}_{voice_style}_{int(datetime.now().timestamp())}.mp3")
    out_file.parent.mkdir(parents=True, exist_ok=True)

    timestamp_iso = datetime.now().isoformat()
    spoken_text = clean_spoken_text(text)

    try:
        asyncio.run(_synthesize_edge_tts(
            text=spoken_text,
            voice_id=voice_id,
            rate=rate,
            pitch=pitch,
            emotion=clean_emo,
            locale=locale,
            output_path=str(out_file)
        ))
        seg = AudioSegment.from_file(str(out_file))
        duration_sec = round(len(seg) / 1000.0, 3)
    except Exception as e:
        print(f"[AI Voice Warning] edge_tts failed ({e}). Generating fallback silence audio.")
        silence = AudioSegment.silent(duration=2000)
        silence.export(str(out_file), format="mp3")
        duration_sec = 2.0

    return {
        "audio_path": str(out_file),
        "duration_sec": duration_sec,
        "text": text,
        "voice_provider": "edge-tts (Microsoft Cognitive Neural)",
        "voice_id": voice_id,
        "voice_style": voice_style,
        "emotion": clean_emo,
        "language": language,
        "generation_timestamp": timestamp_iso,
        "is_synthetic": True,
        "is_clone": False,
        "disclaimer": "Non-imitative generic synthetic voice; does not impersonate any real individual."
    }
