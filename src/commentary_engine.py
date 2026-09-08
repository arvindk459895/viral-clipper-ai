"""
ViralClipper AI Studio - Faceless Originality & Commentary Engine
Generates independent, substantive editorial commentary analyzing comedy structure,
performer timing, crowd psychology, and contextual nuances.
Bans generic fluff phrases (e.g. "That was crazy", "LOL") in favor of genuine editorial perspective.
"""
import json
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional

from src.candidate_detector import CandidateClip

BANNED_GENERIC_PHRASES = [
    "that was crazy",
    "that was funny",
    "lol",
    "wow",
    "so funny",
    "hilarious",
    "lmao",
    "omg",
    "insane moment",
    "you won't believe",
    "wait till you see this",
    "this is wild"
]


@dataclass
class CommentaryScript:
    hook: str
    context_commentary: str
    analysis_reaction: str
    conclusion: str
    editorial_angle: str
    humor_breakdown: str
    language: str = "hinglish"
    hook_emotion: str = "excited"
    context_emotion: str = "sarcastic"
    analysis_emotion: str = "cheerful"
    conclusion_emotion: str = "cheerful"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hook": self.hook,
            "context_commentary": self.context_commentary,
            "analysis_reaction": self.analysis_reaction,
            "conclusion": self.conclusion,
            "editorial_angle": self.editorial_angle,
            "humor_breakdown": self.humor_breakdown,
            "language": self.language,
            "hook_emotion": self.hook_emotion,
            "context_emotion": self.context_emotion,
            "analysis_emotion": self.analysis_emotion,
            "conclusion_emotion": self.conclusion_emotion
        }


def clean_banned_phrases(text: str) -> str:
    """Removes or replaces low-effort generic filler phrases."""
    cleaned = text
    for phrase in BANNED_GENERIC_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        cleaned = pattern.sub("", cleaned).strip()
    return cleaned


def is_hindi_or_hinglish(text: str, detected_lang: str = "en") -> bool:
    """Detects if text contains Hindi (Devanagari), Urdu, or Hinglish vocabulary."""
    if detected_lang and detected_lang.lower().strip() in ["hi", "hindi", "ur", "urdu", "pa", "mr", "gu", "bn"]:
        return True
    # Check for Devanagari script (actual Hindi characters)
    if re.search(r"[\u0900-\u097F]", text):
        return True
    indic_markers = [
        "bhai", "kya", "nahi", "nahin", "shadi", "crore", "hai", "hain", "yeh", "ye", "woh", "wo",
        "toh", "mera", "meri", "mere", "tera", "teri", "tere", "zinda", "bol", "bola", "boli", "pucha",
        "samay", "roast", "dekh", "dekho", "dekha", "kaise", "karte", "karta", "karti", "hoga", "hogi",
        "apne", "apna", "apni", "wale", "wala", "wali", "kuch", "baat", "aur", "ek", "do", "teen",
        "bhi", "sirf", "matlab", "trainer", "gym", "paisa", "paise", "aaya", "aayi", "gaya", "gayi",
        "chal", "chalu", "yaar", "abey", "oye", "kaun", "kahan", "kab", "kyun", "kyu", "aise", "waisa",
        "sab", "log", "banda", "bande", "ladka", "ladki", "bolte", "bolti", "achha", "theek"
    ]
    text_lower = text.lower()
    return bool(re.search(r"\b(" + "|".join(indic_markers) + r")\b", text_lower))


def generate_heuristic_commentary(
    candidate: CandidateClip,
    humor_type: str = "unexpected_answer",
    language: str = "auto",
    emotion: str = "auto",
    detected_lang: str = "en"
) -> CommentaryScript:
    """
    Generates substantive editorial commentary using grounded linguistic and comedic heuristics.
    Supports Hinglish (natural Indian comedy style) and English with emotional inflection.
    """
    text_lower = candidate.text.lower()
    has_indic = is_hindi_or_hinglish(candidate.text, detected_lang=detected_lang)
    if language in ["hinglish", "hindi"]:
        effective_lang = language
    elif language == "english":
        effective_lang = "english"
    else:
        # Default Auto to Hinglish for Indian reaction creators
        effective_lang = "hinglish" if (has_indic or language == "auto") else "english"

    has_question = "?" in candidate.text or any(q in text_lower for q in ["kya", "why", "how", "what", "kaun"])
    has_pause = "silence" in " ".join(candidate.audio_events)

    if effective_lang in ["hinglish", "hindi"]:
        if "gym" in text_lower or "workout" in text_lower:
            hook = "Bhai ye banda itne confidence me gym gaya tha, par dekho aage kya hua!"
            context = "Trainer ne socha tha bodybuilder banayega, par iska pehla hi jawab sunke dimaag ghoom gaya!"
            analysis = "Matlab agle hi din ghutno ne resign kar diya! Bhai zinda bach gaya wahi badi baat hai! 😂"
            conclusion = "Aapka gym me pehla din kaisa tha, comments me batao aur subscribe karna mat bhoolna!"
            angle = "First day gym expectation vs reality"
            breakdown = "Classic relatable lazy humor"
            h_emo = "excited"
            c_emo = "sarcastic"
            a_emo = "cheerful"
            con_emo = "cheerful"
        elif "roast" in text_lower or "average" in text_lower or "score" in text_lower or "shadi" in text_lower or "crore" in text_lower:
            hook = "Arre bhai bhai bhai, Samay ne aate hi iski aisi le li na, ki pura panel hil gaya!"
            context = "Banda socha tha stage pe hero banega, par agle hi second aisi beizzati hui ki bas dekhte jao!"
            analysis = "Matlab aisi roasting to dushman ki bhi na ho! Panel ka shock dekho zara! 🤣"
            conclusion = "Aapko konsa roast sabse khatarnak laga, comments me batao aur subscribe thoko!"
            angle = "Brutal unexpected comedy roast"
            breakdown = "Deadpan delivery with hilarious panel eruption"
            h_emo = "excited"
            c_emo = "sarcastic"
            a_emo = "cheerful"
            con_emo = "cheerful"
        elif has_question:
            hook = "Bhai ye video dekh ke aapki hansi nahi rukegi, dekho aage kya hone wala hai!"
            context = "Setup dekh ke bilkul normal lag raha tha, par aage jo twist aaya na, alag hi level tha!"
            analysis = "Ye reaction dekho bhai, banda sach me confuse ho gaya ki achanak hua kya! 😂"
            conclusion = "Aapka ispe kya reaction hai, comments me batao aur channel ko subscribe karlo!"
            angle = "Innocent question leading to hilarious twist"
            breakdown = "Sharp comedic punchline and confusion"
            h_emo = "excited"
            c_emo = "sarcastic"
            a_emo = "cheerful"
            con_emo = "cheerful"
        else:
            hook = "Bhai ye clip dekho zara, aage jo hone wala hai aap soch bhi nahi sakte!"
            context = "Pehle to sab shanti se chal raha tha, par agle hi second aisi comedy hui ki sab dang reh gaye!"
            analysis = "Hansi ke maare bura haal ho gaya! Matlab timing dekho bande ki, kya dialogue maara hai! 🤣"
            conclusion = "Video pasand aayi toh like karo aur niche batao sabse best part konsa tha!"
            angle = "Priceless comedic timing and crowd eruption"
            breakdown = "Fast setup followed by laugh riot payoff"
            h_emo = "excited"
            c_emo = "sarcastic"
            a_emo = "cheerful"
            con_emo = "cheerful"
    else:
        if "gym" in text_lower or "workout" in text_lower:
            hook = "Watch how this guy's gym confidence completely crumbles in three seconds flat!"
            context = "The trainer expected pure dedication, but got hit with the most brutally honest goal ever!"
            analysis = "His knees literally handed in their resignation letter right then and there! 😂"
            conclusion = "What was your most painful first day at the gym? Tell us in the comments and subscribe!"
            angle = "Gym expectation vs brutal survival reality"
            breakdown = "Relatable fitness struggle humor"
            h_emo = "excited"
            c_emo = "sarcastic"
            a_emo = "cheerful"
            con_emo = "cheerful"
        elif "roast" in text_lower or "average" in text_lower or "score" in text_lower or "shadi" in text_lower:
            hook = "Bro thought he was going to own the stage, but got dismantled instantly!"
            context = "Everything seemed calm until this savage one-liner completely flipped the room upside down!"
            analysis = "Look at the panel's face — absolute stunned disbelief followed by pure chaos! 🤣"
            conclusion = "Rate this roast from one to ten in the comments and smash that subscribe button!"
            angle = "Instant comedic obliteration"
            breakdown = "Deadpan setup and explosive shock payoff"
            h_emo = "excited"
            c_emo = "sarcastic"
            a_emo = "cheerful"
            con_emo = "cheerful"
        else:
            hook = "Watch closely because what happens next is about to catch you completely off guard!"
            context = "The conversation seemed totally harmless, but nobody saw this punchline coming!"
            analysis = "The sheer shock on their faces says it all — comedy gold delivered at lightning speed! 😂"
            conclusion = "Did you see that coming? Let us know in the comments and follow for more daily laughs!"
            angle = "Unexpected comedic twist"
            breakdown = "Rapid misdirection with high-energy payoff"
            h_emo = "excited"
            c_emo = "sarcastic"
            a_emo = "cheerful"
            con_emo = "cheerful"

    # User emotion override if not auto
    if emotion and emotion.lower() != "auto":
        override_emo = emotion.lower()
        h_emo = override_emo
        c_emo = override_emo
        a_emo = override_emo
        con_emo = override_emo

    return CommentaryScript(
        hook=hook,
        context_commentary=context,
        analysis_reaction=analysis,
        conclusion=conclusion,
        editorial_angle=angle,
        humor_breakdown=breakdown,
        language=effective_lang,
        hook_emotion=h_emo,
        context_emotion=c_emo,
        analysis_emotion=a_emo,
        conclusion_emotion=con_emo
    )


def generate_commentary_script(
    candidate: CandidateClip,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.5-flash-lite",
    humor_type: str = "unexpected_answer",
    language: str = "auto",
    emotion: str = "auto",
    detected_lang: str = "en"
) -> CommentaryScript:
    """
    Generates an original viral reaction/roaster commentary script (RC Hidden style).
    Supports Hinglish, Hindi, and English with emotional inflection.
    Calls Gemini API if available, falling back smoothly to heuristic engine.
    """
    has_indic = is_hindi_or_hinglish(candidate.text, detected_lang=detected_lang)
    if language in ["hinglish", "hindi"]:
        effective_lang = language
    elif language == "english":
        effective_lang = "english"
    else:
        # Default Auto to Hinglish whenever Indic elements or Auto is requested
        effective_lang = "hinglish" if (has_indic or language == "auto") else "english"

    if not api_key or not api_key.strip():
        return generate_heuristic_commentary(candidate, humor_type, language=effective_lang, emotion=emotion, detected_lang=detected_lang)

    if effective_lang == "hinglish":
        lang_instruction = (
            "CRITICAL LANGUAGE RULE (MANDATORY):\n"
            "You MUST write the entire commentary script in energetic, witty, conversational HINGLISH (Hindi words written in Latin/English letters, like top Indian creators on YouTube Shorts, e.g., 'Bhai is bande ka confidence dekho! Gym aate hi aisa bola ki sab hil gaye!').\n"
            "STRICT PROHIBITION: DO NOT write in pure English. If you write in pure English, the response will be discarded. The commentary MUST be in Hindi/Hinglish."
        )
    elif effective_lang == "hindi":
        lang_instruction = "LANGUAGE REQUIREMENT:\nWrite the entire script in natural, energetic conversational Hindi."
    else:
        lang_instruction = "LANGUAGE REQUIREMENT:\nWrite the entire script in punchy, witty YouTube Shorts creator English."

    prompt = f"""You are a top viral YouTube Shorts creator and reaction roaster (like popular YouTube Shorts reaction channels, witty, energetic, hilarious, and relatable).
Analyze this short comedic clip and write an ORIGINAL, HILARIOUS creator reaction & commentary voiceover.

{lang_instruction}

CREATOR STYLE RULES (CRITICAL):
1. Talk directly to the audience like a witty, fun-loving creator reacting to a viral video (NOT an academic professor or literature critic).
2. STRICTLY FORBIDDEN: DO NOT talk about "structural mechanics", "comedic subversion", "subversion of aspirational fitness culture", "hesitation analysis", "tension release", or "psychological contrast". Speak in real human words!
3. Keep it punchy, high-energy, funny, and conversational with exclamation marks:
   - hook (1 sentence, 8-14 words): Energetic tease pulling the viewer in (e.g. "Bhai is bande ka confidence dekho! Gym aate hi jo bola sunke dimaag hil gaya!").
   - context_commentary (1 sentence, 10-18 words): Funny setup line describing the situation or building anticipation.
   - analysis_reaction (1-2 sentences, 12-25 words): Hilarious roast or laugh reaction reacting directly to the punchline!
   - conclusion (1 sentence, 8-15 words): Snappy outro question driving viewer comments and channel subscription!
4. EMOTION TAGS:
   Assign an emotional style from: "cheerful" (laugh/funny), "excited" (shocked), "sarcastic" (roast/deadpan), "sad" (moye moye defeat).

CLIP DATA:
- Transcript: "{candidate.text}"
- Duration: {candidate.duration:.1f}s
- Humor Type: {humor_type}
- Audio Events: {', '.join(candidate.audio_events)}

Return ONLY a valid JSON object matching this schema:
{{
  "hook": "...",
  "context_commentary": "...",
  "analysis_reaction": "...",
  "conclusion": "...",
  "editorial_angle": "...",
  "humor_breakdown": "...",
  "hook_emotion": "excited",
  "context_emotion": "sarcastic",
  "analysis_emotion": "cheerful",
  "conclusion_emotion": "cheerful"
}}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        raw_text = resp.text.strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```[a-zA-Z]*\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)
        data = json.loads(raw_text)

        hook = clean_banned_phrases(str(data.get("hook", "")))
        context = clean_banned_phrases(str(data.get("context_commentary", "")))
        analysis = clean_banned_phrases(str(data.get("analysis_reaction", "")))
        conclusion = clean_banned_phrases(str(data.get("conclusion", "")))

        fallback = generate_heuristic_commentary(candidate, humor_type, language=effective_lang, emotion=emotion)
        return CommentaryScript(
            hook=hook if len(hook) > 10 else fallback.hook,
            context_commentary=context if len(context) > 10 else fallback.context_commentary,
            analysis_reaction=analysis if len(analysis) > 10 else fallback.analysis_reaction,
            conclusion=conclusion if len(conclusion) > 10 else fallback.conclusion,
            editorial_angle=str(data.get("editorial_angle", fallback.editorial_angle)),
            humor_breakdown=str(data.get("humor_breakdown", fallback.humor_breakdown)),
            language=effective_lang,
            hook_emotion=str(data.get("hook_emotion", fallback.hook_emotion)),
            context_emotion=str(data.get("context_emotion", fallback.context_emotion)),
            analysis_emotion=str(data.get("analysis_emotion", fallback.analysis_emotion)),
            conclusion_emotion=str(data.get("conclusion_emotion", fallback.conclusion_emotion))
        )
    except Exception as ex:
        print(f"[Commentary Engine Info] API generation falling back to heuristics: {ex}")
        return generate_heuristic_commentary(candidate, humor_type, language=effective_lang, emotion=emotion)
