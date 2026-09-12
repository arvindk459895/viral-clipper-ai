"""
ViralClipper AI Studio - Metadata Generation Module
Generates 3 engaging title options, 1 informative description with rights disclaimer,
and 5-10 targeted hashtags avoiding keyword stuffing.
"""
import json
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.config import LEGAL_DISCLAIMER, DEFAULT_GEMINI_MODEL
from src.candidate_detector import CandidateClip
from src.gemini_analyzer import GeminiClipAnalysis, clean_json_response


class ClipMetadata(BaseModel):
    clip_id: str
    titles: List[str] = Field(..., min_length=3, max_length=3)
    description: str
    hashtags: List[str] = Field(..., min_length=5, max_length=15)


def generate_clip_metadata(
    candidate: CandidateClip,
    analysis: GeminiClipAnalysis,
    channel_name: str = "Creator Channel",
    api_key: Optional[str] = None,
    model_name: str = DEFAULT_GEMINI_MODEL
) -> ClipMetadata:
    """
    Constructs high-engagement titles, description, and hashtags tailored for
    YouTube Shorts, Instagram Reels, and TikTok. Uses Gemini when an API key is available.
    """
    key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)

            prompt = f"""You are a viral YouTube Shorts and Instagram Reels strategist.
Generate metadata for this comedy clip:
- Dialogue: "{candidate.text}"
- Setup: "{analysis.setup}"
- Punchline: "{analysis.punchline}"
- Humor Type: {analysis.humor_type}
- Channel/Creator: {channel_name}

Return STRICT JSON with these exact fields:
{{
  "titles": [
    "<Title 1: High curiosity hook title, 60-85 characters, irresistible curiosity gap with 1-2 emojis and #Shorts>",
    "<Title 2: Detailed relatable POV or reaction title, 60-85 characters with emojis and #Shorts>",
    "<Title 3: Engaging punchline quote or dramatic question title, 60-85 characters with emoji and #Shorts>"
  ],
  "description": "<2-3 sentence engaging description including credit to {channel_name}>",
  "hashtags": ["#Shorts", "#<humor_tag>", "#<topic_tag>", "#Comedy", "#Funny", "#Viral", "#Relatable", "#Reels", "#DesiComedy", "#TrendingShorts", "#IndianComedy"]
}}
"""
            resp = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            data = json.loads(clean_json_response(resp.text))
            titles = data.get("titles", [])
            if len(titles) == 3 and all(isinstance(t, str) and len(t) > 0 for t in titles):
                # Ensure titles respect the 100 char limit
                titles = [t[:95] if len(t) > 95 else t for t in titles]
                desc = data.get("description", "")
                full_desc = f"{desc}\n\nOriginal Source: {channel_name}\nClip: {candidate.start_time:.1f}s - {candidate.end_time:.1f}s\n\n---\nRights Notice: {LEGAL_DISCLAIMER}"
                tags = data.get("hashtags", [])
                if 5 <= len(tags) <= 15:
                    return ClipMetadata(
                        clip_id=candidate.clip_id,
                        titles=titles,
                        description=full_desc,
                        hashtags=tags
                    )
        except Exception as e:
            print(f"[Metadata Warning] Gemini metadata call failed: {e}. Using heuristic templates.")

    # 1. 3 Distinct Title Options (Fallback: 60-85 chars YouTube Shorts sweet spot)
    humor_label = analysis.humor_type.replace('_', ' ').title()
    punchline_snip = candidate.text.split("?")[-1].split("!")[-1].strip()
    if len(punchline_snip) > 40:
        punchline_snip = punchline_snip[:37] + "..."

    title_1 = f"Wait For What He Said At The End! 🤯 ({humor_label}) #Shorts"
    title_2 = f"When The Punchline Hits Way Too Hard In The Middle Of The Show 😂 #Shorts"
    title_3 = f"He Really Thought Nobody Would Notice This Unscripted Moment! 💀 #Shorts"

    if "zinda" in candidate.text.lower() or "gym" in candidate.text.lower():
        title_1 = "Gym Trainer Ne Pucha Fitness Goal Kya Hai? Epic Reply 😂 #Shorts"
        title_2 = "When You Join The Gym For The First Time And Immediate Regret Hits! 💀 #Shorts"
        title_3 = "First Day Gym Routine Gone Completely Wrong | Wait For It! 🏋️ #Shorts"
    elif len(candidate.text) > 0:
        clean_text_sample = " ".join(candidate.text.split()[:7])
        title_1 = f"When He Said '{clean_text_sample}...' And Chaos Happened! 😂 #Shorts"
        title_2 = f"You Won't Believe How Fast This Joke Escalate To Next Level! 💀 #Shorts"
        title_3 = f"Nobody In The Audience Was Ready For This Brutal Punchline! 🤯 #Shorts"

    # Enforce YouTube Shorts title character limit <= 95 characters
    title_1 = title_1[:95].strip()
    title_2 = title_2[:95].strip()
    title_3 = title_3[:95].strip()

    # 2. Informative Description
    desc_lines = [
        f"🔥 Best comedic moment: {title_1}",
        "",
        f"Segment Summary: {analysis.reason}",
        f"Original Source: {channel_name}",
        f"Clip Timestamp: {candidate.start_time:.1f}s - {candidate.end_time:.1f}s",
        "",
        "---",
        f"⚖️ Rights Notice: {LEGAL_DISCLAIMER}",
        "Edited using ViralClipper AI Studio."
    ]
    description = "\n".join(desc_lines)

    # 3. 10-15 Targeted Hashtags
    hashtags = [
        "#Shorts",
        "#Comedy",
        "#HindiComedy",
        "#StandupComedy",
        "#DesiHumor",
        "#Relatable",
        "#FunnyMoments",
        "#IndianComedy",
        "#DesiComedy",
        "#LaughOutLoud",
        "#TrendingShorts",
        "#ViralReels"
    ]

    return ClipMetadata(
        clip_id=candidate.clip_id,
        titles=[title_1, title_2, title_3],
        description=description,
        hashtags=hashtags
    )
