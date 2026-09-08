"""
ViralClipper AI Studio - Rights Checker & Compliance Module
Performs pre-export rights audits across source video, meme overlays, sound effects,
and music. Generates rights_report.json and enforces strict copyright clearance.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.config import LEGAL_DISCLAIMER, SAFE_EXPORT_STATUS_NOTICE
from src.asset_license import AssetItem, AssetStatus, is_eligible_for_export
from src.meme_manager import AssetLibraryManager


class AssetUsageReport(BaseModel):
    name: str
    asset_id: str
    category: str
    source_name: str
    license: str
    commercial_use_allowed: bool
    attribution_required: bool
    status: str
    rights_status: str


class RightsAuditReport(BaseModel):
    source_video_title: str
    source_rights_status: str  # USER_CONFIRMED_AUTHORIZED, DEMO_AUTHORIZED, UNKNOWN
    is_eligible_for_export: bool
    export_status_label: str
    meme_assets_approved: int = 0
    meme_assets_review: int = 0
    meme_assets_blocked: int = 0
    sfx_approved: int = 0
    sfx_review: int = 0
    music_used: str = "NONE"
    assets_used: List[AssetUsageReport] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    legal_notice: str = LEGAL_DISCLAIMER


def audit_clip_rights(
    source_title: str,
    user_confirmed_source: bool,
    assets_used: List[AssetItem],
    is_demo_mode: bool = False
) -> RightsAuditReport:
    """
    Performs a pre-export rights audit.
    Only allows export if source is confirmed and 100% of assets are APPROVED.
    """
    source_status = "UNKNOWN"
    if is_demo_mode:
        source_status = "DEMO_SYNTHETIC_AUTHORIZED"
    elif user_confirmed_source:
        source_status = "USER_CONFIRMED_AUTHORIZED"

    warnings = []
    if source_status == "UNKNOWN":
        warnings.append("Source video rights have not been confirmed by the user.")

    meme_app = 0
    meme_rev = 0
    meme_blk = 0
    sfx_app = 0
    sfx_rev = 0

    asset_reports = []
    for asset in assets_used:
        report = AssetUsageReport(
            name=asset.name,
            asset_id=asset.asset_id,
            category=asset.asset_category.value,
            source_name=asset.source_name,
            license=asset.license,
            commercial_use_allowed=asset.commercial_use_allowed,
            attribution_required=asset.attribution_required,
            status=asset.status.value,
            rights_status=asset.rights_status.value
        )
        asset_reports.append(report)

        if asset.asset_category.value in ["memes", "gifs", "generated"]:
            if asset.status == AssetStatus.APPROVED and is_eligible_for_export(asset):
                meme_app += 1
            elif asset.status == AssetStatus.REVIEW:
                meme_rev += 1
                warnings.append(f"Meme asset '{asset.name}' requires license review.")
            else:
                meme_blk += 1
                warnings.append(f"Meme asset '{asset.name}' is blocked from export.")
        elif asset.asset_category.value == "sfx":
            if asset.status == AssetStatus.APPROVED and is_eligible_for_export(asset):
                sfx_app += 1
            else:
                sfx_rev += 1
                warnings.append(f"Sound effect '{asset.name}' is not approved.")

    is_eligible = (
        source_status in ["USER_CONFIRMED_AUTHORIZED", "DEMO_SYNTHETIC_AUTHORIZED"] and
        meme_rev == 0 and meme_blk == 0 and sfx_rev == 0
    )

    export_status_label = SAFE_EXPORT_STATUS_NOTICE if is_eligible else "HELD FOR REVIEW - UNVERIFIED ASSETS DETECTED"

    return RightsAuditReport(
        source_video_title=source_title,
        source_rights_status=source_status,
        is_eligible_for_export=is_eligible,
        export_status_label=export_status_label,
        meme_assets_approved=meme_app,
        meme_assets_review=meme_rev,
        meme_assets_blocked=meme_blk,
        sfx_approved=sfx_app,
        sfx_review=sfx_rev,
        music_used="NONE",
        assets_used=asset_reports,
        warnings=warnings
    )


def save_rights_report(report: RightsAuditReport, output_path: Path) -> Path:
    """Saves rights audit report to rights_report.json."""
    output_path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    return output_path
