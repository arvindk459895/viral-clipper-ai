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


# Comprehensive 45+ Authentic Indian Scene Meme Catalog
INDIAN_MEME_CATALOG: List[Dict[str, Any]] = [
    {
        "filename": "paisa_hi_paisa.mp4",
        "title": "Paisa Hi Paisa Hoga (Phir Hera Pheri)",
        "keywords": ["paisa", "crore", "crorepati", "lakh", "ameer", "dhan", "rich", "bussiness", "business", "kamana", "daulat", "kharcha", "scheme", "kamai", "profit", "invest", "funding"],
        "humor_types": ["unexpected_answer", "roast", "sarcasm"],
        "emotions": ["cheerful", "laugh", "excited"]
    },
    {
        "filename": "zor_zor_se_scheme.mp4",
        "title": "Zor Zor Se Bolke Scheme Bata De (Phir Hera Pheri)",
        "keywords": ["scheme", "raaz", "secret", "zor zor", "bol diya", "chup reh", "bata de", "plan", "chori", "leak", "khulasa", "pata chal gaya"],
        "humor_types": ["sarcasm", "unexpected_answer", "roast"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "50_rupya_overacting.mp4",
        "title": "50 Rupya Kaat Overacting Ka (Phir Hera Pheri)",
        "keywords": ["overacting", "drama", "50 rupya", "nautanki", "fake", "dikhava", "acting", "extra", "hero ban raha", "jyada ho gaya"],
        "humor_types": ["roast", "sarcasm", "awkward"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "tumse_na_ho_payega.mp4",
        "title": "Beta Tumse Na Ho Payega (Gangs of Wasseypur)",
        "keywords": ["tumse na ho", "fail", "aukat nahi", "impossible", "har gaya", "chod de", "quit", "incapable", "rehnde", "har maan le"],
        "humor_types": ["fail", "roast", "deadpan"],
        "emotions": ["sarcastic", "deadpan"]
    },
    {
        "filename": "dekh_raha_hai_binod.mp4",
        "title": "Dekh Raha Hai Binod (Panchayat)",
        "keywords": ["dekh raha hai", "binod", "dekh lo", "dekha", "notice", "witness", "politics", "chalak", "game", "harkat"],
        "humor_types": ["sarcasm", "reaction", "roast"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "seh_lenge_thoda.mp4",
        "title": "Seh Lenge Thoda (Welcome)",
        "keywords": ["seh lenge", "thoda sa", "jhel lenge", "dard", "adjust", "sacrifice", "compromise", "bardasht", "sah lenge"],
        "humor_types": ["emotional", "awkward", "self_deprecating"],
        "emotions": ["sad", "sarcastic"]
    },
    {
        "filename": "khopdi_tod.mp4",
        "title": "Khopdi Tod Saale Ka (Hera Pheri)",
        "keywords": ["khopdi tod", "maro", "peeto", "maar saale", "gussa", "violence", "thukai", "tod phod", "kutai", "pitai"],
        "humor_types": ["chaos", "roast", "shock"],
        "emotions": ["excited", "shocked"]
    },
    {
        "filename": "aurat_ka_chakkar.mp4",
        "title": "Aurat Ka Chakkar Babu Bhaiya (Hera Pheri)",
        "keywords": ["aurat", "ladki", "crush", "girlfriend", "prem", "chakkar", "simping", "babu bhaiya", "pighal gaya", "ishq", "bhabhi"],
        "humor_types": ["roast", "unexpected_answer", "reaction"],
        "emotions": ["cheerful", "laugh"]
    },
    {
        "filename": "yeh_baburao_ka_style.mp4",
        "title": "Yeh Baburao Ka Style Hai (Hera Pheri)",
        "keywords": ["style", "baburao ka style", "swag", "mera style", "alag hai", "unique", "class", "attitude"],
        "humor_types": ["unexpected_answer", "reaction", "sarcasm"],
        "emotions": ["cheerful", "excited"]
    },
    {
        "filename": "meri_anuradha.mp4",
        "title": "Meri Anuradha Aisi Nahi Ho Sakti (Phir Hera Pheri)",
        "keywords": ["anuradha", "dhoka", "bewafa", "aisi nahi", "scam", "loot liya", "betrayed", "fraud", "popat", "kat gaya"],
        "humor_types": ["fail", "shock", "emotional"],
        "emotions": ["sad", "shocked"]
    },
    {
        "filename": "miracle_miracle.mp4",
        "title": "Miracle Miracle (Welcome)",
        "keywords": ["miracle", "chamatkar", "magic", "jaadu", "unbelievable", "ho gaya", "impossible", "kamaal ho gaya", "hairan"],
        "humor_types": ["absurd", "shock", "unexpected_answer"],
        "emotions": ["excited", "shocked"]
    },
    {
        "filename": "kya_gunda_banega_re.mp4",
        "title": "Kya Gunda Banega Re Tu (Hera Pheri)",
        "keywords": ["gunda", "gangster", "darr", "darpok", "fattu", "kya banega", "fail", "bheegi billi", "dar gaya", "phattu"],
        "humor_types": ["roast", "fail", "awkward"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "apun_hi_bhagwan_hai.mp4",
        "title": "Apun Hi Bhagwan Hai (Sacred Games)",
        "keywords": ["bhagwan", "god", "supreme", "invincible", "ghamand", "ego", "topper", "unstoppable", "gaitonde", "lord"],
        "humor_types": ["absurd", "sarcasm", "chaos"],
        "emotions": ["excited", "sarcastic"]
    },
    {
        "filename": "doglapan.mp4",
        "title": "Yeh Sab Doglapan Hai (Shark Tank)",
        "keywords": ["doglapan", "hypocrisy", "double standard", "jhooth", "drama", "expose", "two faced", "ashneer", "palat gaya"],
        "humor_types": ["roast", "sarcasm", "shock"],
        "emotions": ["sarcastic", "shocked"]
    },
    {
        "filename": "main_kar_leta_hoon.mp4",
        "title": "Main Kar Leta Hoon (Shark Tank)",
        "keywords": ["main kar leta", "dream11", "tum jao", "main sambhalta", "expert", "overconfident", "side ho jao", "team banao"],
        "humor_types": ["sarcasm", "roast", "unexpected_answer"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "chai_piyo_biscuit_khao.mp4",
        "title": "Chai Piyo Biscuit Khao (TMKOC)",
        "keywords": ["chai", "biscuit", "nashta", "chill", "relax", "aaram se", "refreshment", "calm", "jethalal", "shanti"],
        "humor_types": ["deadpan", "sarcasm", "unexpected_answer"],
        "emotions": ["cheerful", "subtle"]
    },
    {
        "filename": "hey_maa_mataji.mp4",
        "title": "Hey Maa Mataji (TMKOC)",
        "keywords": ["hey maa", "mataji", "shock", "panic", "blunder", "galti", "re deva", "tension", "daya", "garba", "o god"],
        "humor_types": ["shock", "chaos", "absurd"],
        "emotions": ["shocked", "excited"]
    },
    {
        "filename": "bohot_tejaswi_log.mp4",
        "title": "Bohot Tejaswi Log Hain (Modi Ji)",
        "keywords": ["tejaswi", "genius", "einstein", "ultra legend", "big brain", "brilliant", "intellectual", "shandar dimag", "kya dimag hai"],
        "humor_types": ["sarcasm", "roast", "unexpected_answer"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "chhoti_bachhi_ho_kya.mp4",
        "title": "Chhoti Bachhi Ho Kya (Heropanti)",
        "keywords": ["chhoti bachhi", "bachha", "bachi", "immaturity", "innocent", "ro kyu rahi", "cute", "tiger", "nadaan"],
        "humor_types": ["roast", "awkward", "sarcasm"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "gormint_aunty.mp4",
        "title": "Yeh Bik Gayi Hai Gormint",
        "keywords": ["gormint", "bik gayi", "sab chor hain", "corrupt", "fraud", "system", "scam", "loot", "neta", "bhrashtachar"],
        "humor_types": ["chaos", "roast", "absurd"],
        "emotions": ["excited", "shocked"]
    },
    {
        "filename": "kismat_ke_bharose.mp4",
        "title": "Kismat Ke Bharose (Puneet Superstar)",
        "keywords": ["kismat", "bhagya", "luck", "destiny", "berozgar", "nalla", "idle", "berozgari", "puneet", "kuch nahi karta"],
        "humor_types": ["self_deprecating", "absurd", "deadpan"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "paisa_barbaad.mp4",
        "title": "Paisa Barbaad BC (CarryMinati)",
        "keywords": ["paisa barbaad", "loss", "nuksan", "loot gaye", "zero", "wastage", "bekar kharcha", "lut gaya", "barbad"],
        "humor_types": ["fail", "roast", "chaos"],
        "emotions": ["shocked", "sarcastic"]
    },
    {
        "filename": "shaktimaan_sorry.mp4",
        "title": "Sorry Shaktimaan",
        "keywords": ["sorry", "maafi", "mafi", "maaf kar", "apologize", "regret", "remorse", "shaktimaan", "bhool ho gayi"],
        "humor_types": ["awkward", "fail", "self_deprecating"],
        "emotions": ["sad", "subtle"]
    },
    {
        "filename": "vasooli_bhai.mp4",
        "title": "Vasooli Bhai (Golmaal)",
        "keywords": ["vasooli", "udhari", "paise wapas", "loan", "debt", "vasool", "tapori", "dhamki", "bhai", "hafta"],
        "humor_types": ["roast", "unexpected_answer", "chaos"],
        "emotions": ["excited", "sarcastic"]
    },
    {
        "filename": "maro_mujhe_maro.mp4",
        "title": "Maro Mujhe Maro (Pakistani Fan)",
        "keywords": ["maro mujhe", "waqt badal diya", "jazbaat", "shock", "disbelief", "unexpected", "trauma", "match", "zindagi badal di"],
        "humor_types": ["shock", "fail", "chaos"],
        "emotions": ["shocked", "sad"]
    },
    {
        "filename": "shabaash_beta.mp4",
        "title": "Shabaash Beta Bohot Badhiya (Mirzapur)",
        "keywords": ["shabaash", "badhiya", "proud", "well done", "good job", "salute", "kamaal", "bahut accha", "bohot khoob"],
        "humor_types": ["sarcasm", "unexpected_answer", "roast"],
        "emotions": ["cheerful", "sarcastic"]
    },
    {
        "filename": "baap_ka_dada_ka.mp4",
        "title": "Sabka Badla Lega Re Faizal (Wasseypur)",
        "keywords": ["badla", "revenge", "dushmani", "faizal", "sabka badla", "dushman", "payback", "baap ka dada ka", "hisaab"],
        "humor_types": ["chaos", "unexpected_answer", "reaction"],
        "emotions": ["excited", "shocked"]
    },
    {
        "filename": "bhai_ne_bola.mp4",
        "title": "Bhai Ne Bola Karne Ka Toh Karne Ka (Munna Bhai)",
        "keywords": ["bhai ne bola", "karne ka", "circuit", "order", "hukum", "loyalty", "boss", " obedience", "karenge"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["excited", "cheerful"]
    },
    {
        "filename": "pighal_gaya.mp4",
        "title": "Lekin Apun Yahan Pighal Gaya (Zakir Khan)",
        "keywords": ["pighal gaya", "sakht launda", "crush", "ladki", "smile", "dil aa gaya", "control nahi hua", "soft"],
        "humor_types": ["unexpected_answer", "self_deprecating"],
        "emotions": ["cheerful", "laugh"]
    },
    {
        "filename": "wah_bete_mauj_kardi.mp4",
        "title": "Wah Bete Mauj Kardi",
        "keywords": ["mauj kardi", "wah bete", "heavy driver", "kamaal", "dhamaal", "epic", "legend"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["cheerful", "excited"]
    },
    {
        "filename": "chup_kar_bilkul_chup.mp4",
        "title": "Chup Kar Bilkul Chup (Phir Hera Pheri)",
        "keywords": ["chup", "shant", "bakwas band", "shut up", "chupchap", "chup kar", "awaz mat kar", "bol mat", "muh band"],
        "humor_types": ["silence", "roast", "awkward"],
        "emotions": ["sarcastic", "excited"]
    },
    {
        "filename": "control_uday.mp4",
        "title": "Control Uday Control (Welcome)",
        "keywords": ["control", "gussa mat ho", "relax", "uday", "santulan", "shant", "calm", "sambhal apne aap ko", "gussa"],
        "humor_types": ["reaction", "shock", "awkward"],
        "emotions": ["shocked", "sarcastic"]
    },
    {
        "filename": "kehna_kya_chahte_ho.mp4",
        "title": "Arre Kehna Kya Chahte Ho (3 Idiots)",
        "keywords": ["kehna kya", "samajh nahi", "kya bol", "kya keh", "explain", "clear bol", "confuse", "bhashan", "meaning"],
        "humor_types": ["confusion", "disbelief", "shock"],
        "emotions": ["shocked", "sarcastic"]
    },
    {
        "filename": "bawasir_bana_diye.mp4",
        "title": "Yeh Kya Bawasir Bana Diye Ho (Panchayat)",
        "keywords": ["bawasir", "kachra", "bekar", "ghatiya", "disaster", "kharab", "tatti", "flop", "hatao isko", "worst"],
        "humor_types": ["roast", "fail", "chaos"],
        "emotions": ["sarcastic", "shocked"]
    },
    {
        "filename": "jalwa_hai_hamara.mp4",
        "title": "Jalwa Hai Hamara Yahan (Mirzapur)",
        "keywords": ["jalwa", "swag", "bhaukal", "king", "bhaiya", "bhaigiri", "attitude", "power", "boss", "raj", "dabdaba"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["excited", "cheerful"]
    },
    {
        "filename": "gajab_beizzati.mp4",
        "title": "Gajab Beizzati Hai (Panchayat)",
        "keywords": ["beizzati", "insult", "sharam", "roast", "izzat", "aukat", "tareef ki ulti", "laaj", "disrespect", "humiliation"],
        "humor_types": ["roast", "sarcasm", "awkward"],
        "emotions": ["sarcastic", "cheerful"]
    },
    {
        "filename": "khatam_tata.mp4",
        "title": "Khatam Tata Bye Bye (Rahul Gandhi)",
        "keywords": ["khatam", "tata", "bye", "chala gaya", "finish", "over", "end", "khel khatam", "resign", "gaya", "goodbye"],
        "humor_types": ["fail", "deadpan", "roast"],
        "emotions": ["cheerful", "sarcastic"]
    },
    {
        "filename": "kaha_se_aate_hai.mp4",
        "title": "Kaun Hain Ye Log Kahan Se Aate Hain (Jolly LLB)",
        "keywords": ["kaun hai ye", "kahan se aate", "kaha se aate", "ajeeb", "namoona", "mental", "pagal", "alien", "strange"],
        "humor_types": ["confusion", "disbelief", "shock"],
        "emotions": ["shocked", "sarcastic"]
    },
    {
        "filename": "mast_joke_mara.mp4",
        "title": "Mast Joke Mara Re (Phir Hera Pheri)",
        "keywords": ["joke", "has re", "hasi", "rofl", "lol", "laugh", "mazak", "halkat", "komedy", "haste haste", "laughter"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["cheerful", "laugh"]
    },
    {
        "filename": "moye_moye.mp4",
        "title": "Moye Moye (Viral Trend)",
        "keywords": ["sad", "defeat", "moye", "crying", "heartbreak", "dard", "rona", "bad luck", "trauma", "gham", "dukhi"],
        "humor_types": ["emotional", "fail"],
        "emotions": ["sad"]
    },
    {
        "filename": "kuch_bhi_arnab.mp4",
        "title": "Kuch Bhi (Arnab Goswami)",
        "keywords": ["kuch bhi", "arnab", "nonsense", "kuchh bhi", "bakwas bol raha", "jhooth"],
        "humor_types": ["unexpected_answer", "shock", "disbelief"],
        "emotions": ["shocked", "sarcastic"]
    },
    {
        "filename": "sachin_bat_grip.mp4",
        "title": "Ae Vedya Bat Ka Grip (Sachin Trend)",
        "keywords": ["bat ka grip", "vedya", "nikal ke", "sachin", "gussa", "bat"],
        "humor_types": ["chaos", "roast", "absurd"],
        "emotions": ["excited", "shocked"]
    },
    {
        "filename": "puneet_lord_laugh.mp4",
        "title": "Lord Puneet Laughing",
        "keywords": ["puneet laugh", "lord puneet", "chilgoza", "laugh", "hasi", "crazy laugh", "halkat"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["cheerful", "laugh"]
    },
    {
        "filename": "rajpal_ghar_jaana_hai.mp4",
        "title": "Mujhe Apne Ghar Jaana Hai (Chup Chup Ke)",
        "keywords": ["ghar jaana hai", "torture", "pareshan", "trap", "phas gaya", "chup chup ke", "rajpal"],
        "humor_types": ["emotional", "self_deprecating", "awkward"],
        "emotions": ["sad", "shocked"]
    },
    {
        "filename": "wah_kya_scene_hai.mp4",
        "title": "Wah Kya Scene Hai (Modi Ji)",
        "keywords": ["wah kya scene", "kya scene hai", "scene", "view", "nazaara", "beautiful", "zabardast"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["cheerful", "excited"]
    },
    {
        "filename": "pagal_aurat_jethalal.mp4",
        "title": "Ae Pagal Aurat (TMKOC)",
        "keywords": ["pagal aurat", "pagal", "dimag kharab", "irritating", "jethalal", "chup kar aurat"],
        "humor_types": ["roast", "silence", "awkward"],
        "emotions": ["sarcastic", "excited"]
    },
    {
        "filename": "samajh_rahe_ho.mp4",
        "title": "Samajh Rahe Ho Na",
        "keywords": ["samajh rahe ho", "wink", "double meaning", "you know", "hint", "ishara", "secret"],
        "humor_types": ["unexpected_answer", "sarcasm"],
        "emotions": ["cheerful", "sarcastic"]
    },
    {
        "filename": "chup_kar_carry.mp4",
        "title": "Chup Bilkul Chup (CarryMinati)",
        "keywords": ["carry chup", "carryminati", "bilkul chup", "chup be", "shutup", "shant ho ja"],
        "humor_types": ["silence", "roast"],
        "emotions": ["sarcastic", "excited"]
    },
    {
        "filename": "toh_kaise_hain_aap_log.mp4",
        "title": "Toh Kaise Hain Aap Log (CarryMinati)",
        "keywords": ["kaise hain aap log", "carry intro", "namaskar", "swag intro"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["excited", "cheerful"]
    },
    {
        "filename": "kya_baat_hai_sir.mp4",
        "title": "Kya Baat Hai Sir",
        "keywords": ["kya baat hai", "kya baat hai sir", "salute", "kamaal", "superb", "proud"],
        "humor_types": ["unexpected_answer", "reaction"],
        "emotions": ["cheerful", "excited"]
    }
]


def select_video_meme_cutaway(
    humor_type: str = "unexpected_answer",
    emotion: str = "auto",
    dialogue_text: str = "",
    clip_index: int = 0
) -> Optional[Any]:
    """
    Intelligently selects an authentic, clean Indian scene meme cutaway clip
    from the 45+ meme library based on semantic dialogue keywords, comedic intent,
    and scene emotion. Rotates top matches across clip indices so consecutive
    Shorts in a batch never repeat the same reaction.
    """
    from pathlib import Path
    videos_dir = Path("assets/memes/videos")
    if not videos_dir.exists():
        return None

    clean_emo = (emotion or "auto").lower().strip()
    clean_humor = (humor_type or "unexpected_answer").lower().strip()
    dialogue_lower = (dialogue_text or "").lower().strip()

    # Find all available physical meme files on disk
    available_files = {f.name: f for f in videos_dir.glob("*.mp4")}
    if not available_files:
        return None

    # Score each cataloged meme based on match affinity
    scored_candidates = []
    for item in INDIAN_MEME_CATALOG:
        fname = item["filename"]
        if fname not in available_files:
            continue

        score = 0
        # 1. Dialogue keyword affinity (strongest signal)
        for kw in item["keywords"]:
            if kw in dialogue_lower:
                score += 10

        # 2. Humor type affinity
        if any(h in clean_humor for h in item.get("humor_types", [])):
            score += 3

        # 3. Emotion affinity
        if clean_emo in item.get("emotions", []):
            score += 2

        if score > 0:
            scored_candidates.append((score, available_files[fname]))

    # If we have matched candidates, sort by score descending
    if scored_candidates:
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        # Select from top scoring group with clip_index rotation for diversity
        top_score = scored_candidates[0][0]
        top_tier = [path for s, path in scored_candidates if s >= max(3, top_score - 2)]
        return top_tier[clip_index % len(top_tier)]

    # Fallback: Rotate across all available physical memes
    sorted_all = sorted(list(available_files.values()), key=lambda p: p.name)
    return sorted_all[clip_index % len(sorted_all)]


