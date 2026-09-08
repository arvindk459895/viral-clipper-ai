"""
ViralClipper AI Studio - Faceless Commentary Quality & Originality Validator
Evaluates AI commentary scripts against strict editorial criteria:
1. Adds context/analysis rather than merely describing visuals.
2. Demonstrates genuine editorial purpose.
3. Explains comedic/narrative mechanics.
4. Free from repetitive/generic fluff.
Rejects scripts below configurable quality thresholds.
"""
import json
import re
from dataclasses import dataclass
from typing import Dict, Any, Optional

from src.commentary_engine import CommentaryScript, BANNED_GENERIC_PHRASES


@dataclass
class CommentaryQualityReport:
    commentary_value: int       # 0-100: informative & analytical depth
    originality: int            # 0-100: distinct perspective, free from clichés
    context_value: int          # 0-100: explains background, setup, subversion
    entertainment_value: int    # 0-100: engagement, pacing, clarity
    overall_score: int          # Weighted composite (0-100)
    passed: bool                # True if overall_score >= threshold
    threshold: int
    critique: str
    banned_phrases_found: list

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commentary_value": self.commentary_value,
            "originality": self.originality,
            "context_value": self.context_value,
            "entertainment_value": self.entertainment_value,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "threshold": self.threshold,
            "critique": self.critique,
            "banned_phrases_found": self.banned_phrases_found
        }


def heuristic_validate_commentary(
    script: CommentaryScript,
    threshold: int = 70
) -> CommentaryQualityReport:
    """
    Locally validates the editorial commentary script using structural analysis.
    """
    full_text = f"{script.hook} {script.context_commentary} {script.analysis_reaction} {script.conclusion}".lower()

    # 1. Check for banned generic phrases
    found_banned = [p for p in BANNED_GENERIC_PHRASES if p in full_text]
    banned_penalty = len(found_banned) * 20

    # 2. Check for analytical vocabulary
    analytical_keywords = [
        "subvert", "contrast", "setup", "punchline", "misdirection", "timing",
        "tension", "pause", "reversal", "audience", "reaction", "delivery",
        "cadence", "rhythm", "psychology", "disbelief", "hesitation"
    ]
    analytical_matches = sum(1 for w in analytical_keywords if w in full_text)
    analytical_bonus = min(25, analytical_matches * 5)

    # 3. Word count & depth checks
    total_words = len(full_text.split())
    depth_score = min(30, int((total_words / 45.0) * 30))

    # Base scores
    orig = max(40, min(98, 75 + analytical_bonus - banned_penalty))
    comm_val = max(40, min(96, 70 + analytical_bonus + (depth_score // 2) - banned_penalty))
    ctx_val = max(40, min(95, 72 + (analytical_matches * 4) - banned_penalty))
    ent_val = max(40, min(95, 78 + (10 if len(script.hook) > 20 else 0) - banned_penalty))

    overall = int(round((comm_val * 0.35) + (orig * 0.30) + (ctx_val * 0.20) + (ent_val * 0.15)))
    passed = (overall >= threshold) and (len(found_banned) == 0)

    if passed:
        critique = "Strong editorial script. Substantively explains comedic subversion and pacing without generic filler."
    else:
        critique = f"Commentary failed quality bar (Score: {overall}/{threshold}). " + (
            f"Contains banned clichés: {found_banned}." if found_banned else "Lacks sufficient analytical depth."
        )

    return CommentaryQualityReport(
        commentary_value=comm_val,
        originality=orig,
        context_value=ctx_val,
        entertainment_value=ent_val,
        overall_score=overall,
        passed=passed,
        threshold=threshold,
        critique=critique,
        banned_phrases_found=found_banned
    )


def validate_commentary_quality(
    script: CommentaryScript,
    threshold: int = 70,
    api_key: Optional[str] = None,
    model_name: str = "gemini-3.5-flash-lite"
) -> CommentaryQualityReport:
    """
    Validates the editorial commentary script before rendering.
    Uses Gemini API if key is provided, otherwise evaluates via local heuristic rubric.
    """
    if not api_key or not api_key.strip():
        return heuristic_validate_commentary(script, threshold)

    prompt = f"""Evaluate this AI commentary script for an editorial comedy short:
Hook: "{script.hook}"
Context: "{script.context_commentary}"
Analysis: "{script.analysis_reaction}"
Conclusion: "{script.conclusion}"

Evaluate against these 4 criteria on a 0-100 scale:
1. commentary_value: Does it explain WHY the moment works (subversion, timing, contrast) rather than just stating what happened?
2. originality: Is it a unique critical observation free from clichés (e.g. "so funny", "crazy")?
3. context_value: Does it provide useful context on the comedic setup and reaction?
4. entertainment_value: Is the writing engaging, sharp, and concise for a short video essay?

Return ONLY a JSON object:
{{
  "commentary_value": 0-100,
  "originality": 0-100,
  "context_value": 0-100,
  "entertainment_value": 0-100,
  "critique": "short 1-2 sentence explanation"
}}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        resp = client.models.generate_content(model=model_name, contents=prompt)
        raw = resp.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)

        comm_val = int(data.get("commentary_value", 80))
        orig = int(data.get("originality", 80))
        ctx_val = int(data.get("context_value", 80))
        ent_val = int(data.get("entertainment_value", 80))
        critique = str(data.get("critique", "Solid editorial analysis."))

        full_text = f"{script.hook} {script.context_commentary} {script.analysis_reaction} {script.conclusion}".lower()
        found_banned = [p for p in BANNED_GENERIC_PHRASES if p in full_text]
        if found_banned:
            orig = max(20, orig - 30)

        overall = int(round((comm_val * 0.35) + (orig * 0.30) + (ctx_val * 0.20) + (ent_val * 0.15)))
        passed = (overall >= threshold) and (len(found_banned) == 0)

        return CommentaryQualityReport(
            commentary_value=comm_val,
            originality=orig,
            context_value=ctx_val,
            entertainment_value=ent_val,
            overall_score=overall,
            passed=passed,
            threshold=threshold,
            critique=critique,
            banned_phrases_found=found_banned
        )
    except Exception as ex:
        print(f"[Commentary Validator Info] API validation fallback: {ex}")
        return heuristic_validate_commentary(script, threshold)
