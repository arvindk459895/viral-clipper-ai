"""
ViralClipper AI Studio - Originality & Editorial Compliance Auditor
Computes quantitative editorial ratios (source vs commentary vs visuals), evaluates
internal reuse and copyright risk indicators, and tracks YouTube AI synthetic media disclosure requirements.
Strictly disclaims legal determinations and fair use guarantees.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class OriginalityReport:
    source_footage_sec: float
    ai_commentary_sec: float
    ai_visuals_sec: float
    original_editing_sec: float
    total_duration_sec: float
    source_percentage: float
    commentary_percentage: float
    licensed_assets_count: int
    ai_assets_count: int
    editorial_purpose: str
    originality_assessment: str     # STRONG / MODERATE / WEAK
    reuse_risk: str                 # LOW / MEDIUM / HIGH
    copyright_risk: str             # LOW / MEDIUM / HIGH
    has_ai_voice: bool
    has_ai_visuals: bool
    has_altered_real_content: bool
    youtube_disclosure_required: bool
    youtube_disclosure_reminder: str
    disclaimer: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_footage_sec": round(self.source_footage_sec, 1),
            "ai_commentary_sec": round(self.ai_commentary_sec, 1),
            "ai_visuals_sec": round(self.ai_visuals_sec, 1),
            "original_editing_sec": round(self.original_editing_sec, 1),
            "total_duration_sec": round(self.total_duration_sec, 1),
            "source_percentage": round(self.source_percentage, 1),
            "commentary_percentage": round(self.commentary_percentage, 1),
            "licensed_assets_count": self.licensed_assets_count,
            "ai_assets_count": self.ai_assets_count,
            "editorial_purpose": self.editorial_purpose,
            "originality_assessment": self.originality_assessment,
            "reuse_risk": self.reuse_risk,
            "copyright_risk": self.copyright_risk,
            "has_ai_voice": self.has_ai_voice,
            "has_ai_visuals": self.has_ai_visuals,
            "has_altered_real_content": self.has_altered_real_content,
            "youtube_disclosure_required": self.youtube_disclosure_required,
            "youtube_disclosure_reminder": self.youtube_disclosure_reminder,
            "disclaimer": self.disclaimer
        }


def generate_originality_report(
    source_duration_sec: float,
    ai_commentary_sec: float,
    ai_visuals_sec: float,
    editorial_purpose: str,
    licensed_assets_count: int = 1,
    ai_assets_count: int = 3,
    has_source_cuts: bool = True
) -> OriginalityReport:
    """
    Computes an objective editorial breakdown and evaluates internal risk indicators.
    """
    total_dur = max(1.0, source_duration_sec + ai_commentary_sec + ai_visuals_sec)
    source_pct = (source_duration_sec / total_dur) * 100.0
    commentary_pct = ((ai_commentary_sec + ai_visuals_sec) / total_dur) * 100.0
    original_editing_sec = ai_commentary_sec + ai_visuals_sec + (source_duration_sec * 0.3)

    # Assess Originality
    if commentary_pct >= 40.0 and has_source_cuts:
        originality_assessment = "STRONG"
        reuse_risk = "LOW"
        copyright_risk = "LOW"
    elif commentary_pct >= 25.0:
        originality_assessment = "MODERATE"
        reuse_risk = "MEDIUM"
        copyright_risk = "MEDIUM"
    else:
        originality_assessment = "WEAK"
        reuse_risk = "HIGH"
        copyright_risk = "HIGH"

    youtube_disclosure_reminder = (
        "YouTube Policy Notice: This video contains AI-generated voiceover narration and synthetic editorial visuals. "
        "When uploading to YouTube Studio, you must select 'Yes' under the 'Altered or synthetic content' disclosure setting "
        "if realistic representations of real individuals or events have been modified."
    )

    disclaimer = (
        "CRITICAL DISCLAIMER: These metrics are internal editorial-risk indicators and do NOT constitute legal advice or "
        "legal determinations. Transformative commentary and AI disclosure do not guarantee immunity from copyright claims, "
        "Content ID matches, or strikes. Always ensure you possess the appropriate licenses or permissions for third-party source footage."
    )

    return OriginalityReport(
        source_footage_sec=source_duration_sec,
        ai_commentary_sec=ai_commentary_sec,
        ai_visuals_sec=ai_visuals_sec,
        original_editing_sec=original_editing_sec,
        total_duration_sec=total_dur,
        source_percentage=source_pct,
        commentary_percentage=commentary_pct,
        licensed_assets_count=licensed_assets_count,
        ai_assets_count=ai_assets_count,
        editorial_purpose=editorial_purpose,
        originality_assessment=originality_assessment,
        reuse_risk=reuse_risk,
        copyright_risk=copyright_risk,
        has_ai_voice=True,
        has_ai_visuals=True,
        has_altered_real_content=True,
        youtube_disclosure_required=True,
        youtube_disclosure_reminder=youtube_disclosure_reminder,
        disclaimer=disclaimer
    )
