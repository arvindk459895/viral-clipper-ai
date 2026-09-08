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
    hashtags: List[str] = Field(..., min_length=5, max_length=10)


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
    "<Title 1: High curiosity hook under 50 chars with 1 emoji and #Shorts>",
    "<Title 2: Relatable POV or reaction title with emoji>",
    "<Title 3: Direct punchline quote title>"
  ],
  "description": "<2-3 sentence engaging description including credit to {channel_name}>",
  "hashtags": ["#Shorts", "#<humor_tag>", "#<topic_tag>", "#Comedy", "#Funny", "#Viral", "#Relatable", "#Reels"]
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
                desc = data.get("description", "")
                full_desc = f"{desc}\n\nOriginal Source: {channel_name}\nClip: {candidate.start_time:.1f}s - {candidate.end_time:.1f}s\n\n---\nRights Notice: {LEGAL_DISCLAIMER}"
                tags = data.get("hashtags", [])
                if 5 <= len(tags) <= 10:
                    return ClipMetadata(
                        clip_id=candidate.clip_id,
                        titles=titles,
                        description=full_desc,
                        hashtags=tags
                    )
        except Exception as e:
            print(f"[Metadata Warning] Gemini metadata call failed: {e}. Using heuristic templates.")

    # 1. 3 Distinct Title Options (Fallback)
    punchline_snip = candidate.text.split("?")[-1].split("!")[-1].strip()
    if len(punchline_snip) > 35:
        punchline_snip = punchline_snip[:32] + "..."

    title_1 = f"He Said WHAT?!  ({analysis.humor_type.replace('_', ' ').title()})"
    title_2 = f"When the punchline hits too hard  #{candidate.clip_id}"
    title_3 = f"Gym Trainer Asked Him What?!  | Viral Moments"

    if "zinda" in candidate.text.lower() or "gym" in candidate.text.lower():
        title_1 = "Gym Trainer Ne Pucha Goal Kya Hai?  #Shorts"
        title_2 = "When You Go To The Gym For The First Time "
        title_3 = "Leg Day Pe Ghutne Resign Kar Gaye! "
    elif len(candidate.text) > 0:
        words = candidate.text.split()
        lead = " ".join(words[:4])
        title_1 = f"{lead}...  #Shorts"
        title_2 = f"Wait for the punchline at the end! "
        title_3 = f"That reaction was totally unscripted! "

    # 2. Informative Description
    desc_lines = [
        f" Best comedic moment: {title_1}",
        "",
        f"Segment Summary: {analysis.reason}",
        f"Original Source: {channel_name}",
        f"Clip Timestamp: {candidate.start_time:.1f}s - {candidate.end_time:.1f}s",
        "",
        "---",
        f" Rights Notice: {LEGAL_DISCLAIMER}",
        "Edited using ViralClipper AI Studio."
    ]
    description = "\n".join(desc_lines)

    # 3. 5-10 Targeted Hashtags
    hashtags = [
        "#Shorts",
        "#Comedy",
        "#HindiComedy",
        "#StandupComedy",
        "#DesiHumor",
        "#Relatable",
        "#FunnyMoments",
        "#IndianComedy"
    ]

    return ClipMetadata(
        clip_id=candidate.clip_id,
        titles=[title_1, title_2, title_3],
        description=description,
        hashtags=hashtags
    )
