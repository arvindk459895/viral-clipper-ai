"""
ViralClipper AI Studio - Smart Meme Selector & Safe Placement Engine
Selects contextually appropriate approved memes based on joke analysis (humor_type, reaction_type)
and assigns collision-free safe coordinates avoiding speaker faces and subtitles.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.asset_license import AssetItem, AssetCategory, AssetStatus
from src.meme_manager import AssetLibraryManager
from src.gemini_analyzer import GeminiClipAnalysis


class MemePlacement(BaseModel):
    asset_id: str
    asset_name: str
    file_path: str
    start_time: float
    end_time: float
    duration: float
    position: str = "bottom_right"  # bottom_right, top_right, top_left
    scale: float = 0.28  # fraction of 1080 width (~300px)
    opacity: float = 0.95
    reason: str = ""


# Contextual Joke-to-Meme Tag Map (Step 7)
HUMOR_TO_TAGS_MAP: Dict[str, List[str]] = {
    "unexpected_answer": ["disbelief", "shock", "surprise"],
    "sarcasm": ["deadpan", "funny", "roast"],
    "roast": ["roast", "funny", "laugh"],
    "reaction": ["disbelief", "laugh", "shock"],
    "awkward": ["awkward", "deadpan", "fail"],
    "shock": ["shock", "what", "surprise"],
    "fail": ["fail", "dead", "awkward"],
    "confusion": ["confused", "what", "disbelief"],
    "dark_humor": ["dead", "shock"],
    "self_deprecating": ["laugh", "funny", "dead"],
    "embarrassment": ["awkward", "facepalm"],
    "emotional": ["subtle", "sad"],
    "absurd": ["chaos", "what", "mindblown"],
    "deadpan": ["awkward", "subtle"],
    "chaos": ["chaos", "mindblown", "fire"]
}


def select_contextual_meme(
    analysis: GeminiClipAnalysis,
    manager: AssetLibraryManager,
    editing_style: str = "Meme"
) -> Optional[MemePlacement]:
    """
    Selects a single, high-affinity APPROVED asset matching the joke's comedic intention.
    Prevents over-editing: exactly 0 memes for Clean style, max 1 tasteful meme for Modern/Meme.
    """
    if editing_style.lower() == "clean":
        return None

    approved_memes = manager.get_approved_assets(AssetCategory.GENERATED) + manager.get_approved_assets(AssetCategory.MEME)
    if not approved_memes:
        return None

    # Determine priority tags
    target_tags = HUMOR_TO_TAGS_MAP.get(analysis.humor_type, ["funny", "laugh"])
    if analysis.recommended_asset_tags:
        target_tags = analysis.recommended_asset_tags + target_tags

    chosen_asset: Optional[AssetItem] = None
    for tag in target_tags:
        matching = [a for a in approved_memes if any(tag.lower() in t.lower() for t in a.tags)]
        if matching:
            chosen_asset = matching[0]
            break

    if not chosen_asset:
        chosen_asset = approved_memes[0]

    # Calculate safe timing around punchline
    # Display for 1.2 to 1.6 seconds during the reaction beat
    clip_len = analysis.end_time - analysis.start_time
    # Default reaction point: ~75% into the clip or right after punchline
    rel_punch = clip_len * 0.70
    # Search edit timeline for punchline zoom or reaction_asset
    for act in analysis.edit_timeline:
        if act.action in ["punch_zoom", "reaction_asset", "freeze_frame"]:
            rel_punch = max(0.5, act.time - analysis.start_time)
            break

    start_rel = min(clip_len - 1.5, rel_punch + 0.2)
    end_rel = min(clip_len, start_rel + 1.4)
    duration = round(end_rel - start_rel, 2)

    # Position: bottom_right in safe zone (above navigation, right of subtitles)
    return MemePlacement(
        asset_id=chosen_asset.asset_id,
        asset_name=chosen_asset.name,
        file_path=chosen_asset.file_path,
        start_time=round(start_rel, 2),
        end_time=round(end_rel, 2),
        duration=duration,
        position="bottom_right",
        scale=0.28,
        opacity=0.95,
        reason=f"Comedic emphasis for {analysis.humor_type} joke reaction"
    )


def select_video_meme_cutaway(
    humor_type: str = "unexpected_answer",
    emotion: str = "auto",
    dialogue_text: str = "",
    clip_index: int = 0
) -> Optional[Any]:
    """
    Selects a clean, watermark-free 1-2 second viral video meme cutaway clip
    matching the dialogue punchline, scene emotion, and comedy style.
    Rotates across multiple candidate memes using clip_index so shorts in a batch
    feature diverse trending memes.
    """
    from pathlib import Path
    videos_dir = Path("assets/memes/videos")
    if not videos_dir.exists():
        return None

    clean_emo = (emotion or "auto").lower().strip()
    clean_humor = (humor_type or "unexpected_answer").lower().strip()
    dialogue_lower = (dialogue_text or "").lower()

    # 1. Semantic Dialogue Match (Dialogue-driven selection)
    if any(k in dialogue_lower for k in ["paisa", "crore", "crorepati", "lakh", "ameer", "dhan", "rich", "bussiness", "business", "kamana", "daulat", "kharcha"]):
        cand = videos_dir / "paisa_hi_paisa.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["chup", "shant", "bakwas band", "shut up", "chupchap", "chup kar", "awaz mat kar"]):
        cand = videos_dir / "chup_kar_bilkul_chup.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["control", "gussa mat ho", "relax", "uday", "santulan"]):
        cand = videos_dir / "control_uday.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["kehna kya", "samajh nahi", "kya bol", "kya keh", "explain", "clear bol"]):
        cand = videos_dir / "kehna_kya_chahte_ho.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["bawasir", "kachra", "bekar", "ghatiya", "disaster", "kharab", "tatti"]):
        cand = videos_dir / "bawasir_bana_diye.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["jalwa", "swag", "bhaukal", "king", "bhaiya", "bhaigiri", "attitude", "power"]):
        cand = videos_dir / "jalwa_hai_hamara.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["beizzati", "insult", "sharam", "roast", "izzat"]):
        cand = videos_dir / "gajab_beizzati.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["khatam", "tata", "bye", "chala gaya", "finish", "over", "end", "khel khatam"]):
        cand = videos_dir / "khatam_tata.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["kaun hai ye", "kahan se aate", "kaha se aate", "ajeeb", "namoona", "mental"]):
        cand = videos_dir / "kaha_se_aate_hai.mp4"
        if cand.exists():
            return cand

    if any(k in dialogue_lower for k in ["joke", "has re", "hasi", "rofl", "lol", "laugh", "mazak"]):
        cand = videos_dir / "mast_joke_mara.mp4"
        if cand.exists():
            return cand

    # 2. Contextual Humor & Emotion Matching with Pool Rotation
    # Roast / Savage
    if any(k in clean_humor for k in ["roast", "insult", "beizzati", "savage"]):
        roast_pool = ["gajab_beizzati.mp4", "bawasir_bana_diye.mp4", "chup_kar_bilkul_chup.mp4"]
        for name in roast_pool[clip_index % len(roast_pool):] + roast_pool[:clip_index % len(roast_pool)]:
            f = videos_dir / name
            if f.exists():
                return f

    # Disbelief / Confusion / Shock
    if clean_emo in ["sarcastic", "shocked"] or any(k in clean_humor for k in ["disbelief", "shock", "confusion", "what"]):
        shock_pool = ["kehna_kya_chahte_ho.mp4", "kaha_se_aate_hai.mp4", "control_uday.mp4"]
        for name in shock_pool[clip_index % len(shock_pool):] + shock_pool[:clip_index % len(shock_pool)]:
            f = videos_dir / name
            if f.exists():
                return f

    # Silence / Irritation
    if any(k in clean_humor for k in ["silence", "chup", "shut", "irritat", "angry"]):
        irrit_pool = ["chup_kar_bilkul_chup.mp4", "control_uday.mp4"]
        for name in irrit_pool[clip_index % len(irrit_pool):] + irrit_pool[:clip_index % len(irrit_pool)]:
            f = videos_dir / name
            if f.exists():
                return f

    # Fail / Deadpan
    if any(k in clean_humor for k in ["fail", "dead", "khatam", "tata", "resign", "finish"]):
        fail_pool = ["khatam_tata.mp4", "bawasir_bana_diye.mp4", "moye_moye.mp4"]
        for name in fail_pool[clip_index % len(fail_pool):] + fail_pool[:clip_index % len(fail_pool)]:
            f = videos_dir / name
            if f.exists():
                return f

    # Sad / Defeat / Melodrama
    if clean_emo in ["sad", "melodrama", "defeat"] or any(k in clean_humor for k in ["sad", "defeat", "moye", "crying"]):
        f = videos_dir / "moye_moye.mp4"
        if f.exists():
            return f

    # General Comedy / Laugh / Unexpected Answer: Rotate across all top clean comedy memes!
    comedy_pool = [
        "mast_joke_mara.mp4",
        "jalwa_hai_hamara.mp4",
        "kehna_kya_chahte_ho.mp4",
        "control_uday.mp4",
        "paisa_hi_paisa.mp4",
        "kaha_se_aate_hai.mp4",
        "gajab_beizzati.mp4"
    ]
    # Rotate pool by clip_index so Short 1, Short 2, Short 3 get different memes
    rotated = comedy_pool[clip_index % len(comedy_pool):] + comedy_pool[:clip_index % len(comedy_pool)]
    for name in rotated:
        cand = videos_dir / name
        if cand.exists():
            return cand

    all_videos = sorted(list(videos_dir.glob("*.mp4")))
    if all_videos:
        return all_videos[clip_index % len(all_videos)]
    return None

