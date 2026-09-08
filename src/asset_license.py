"""
ViralClipper AI Studio - Asset License & Rights Models
Defines licensing schemes, commercial use verification, and approval statuses.
"""
from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class RightsStatus(str, Enum):
    USER_SUPPLIED = "user_supplied"
    PUBLIC_DOMAIN = "public_domain"
    CREATIVE_COMMONS = "creative_commons"
    LICENSED = "licensed"
    GENERATED = "generated"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class AssetStatus(str, Enum):
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


class AssetCategory(str, Enum):
    MEME = "memes"
    GIF = "gifs"
    SFX = "sfx"
    MUSIC = "music"
    TRANSITION = "transitions"
    GENERATED = "generated"


class AssetItem(BaseModel):
    asset_id: str
    name: str
    asset_category: AssetCategory
    filename: str
    file_path: str
    rights_status: RightsStatus
    source_name: str = "Local / Generated"
    source_url: Optional[str] = None
    license: str = "Original Generated / Cleared"
    license_url: Optional[str] = None
    creator: str = "ViralClipper Studio"
    attribution_required: bool = False
    commercial_use_allowed: bool = True
    modification_allowed: bool = True
    status: AssetStatus = AssetStatus.APPROVED
    tags: List[str] = Field(default_factory=list)
    download_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    preview_path: Optional[str] = None


def is_eligible_for_export(asset: AssetItem) -> bool:
    """Strict gate: Only APPROVED assets with verified commercial rights can be exported."""
    if asset.status != AssetStatus.APPROVED:
        return False
    if asset.rights_status in [RightsStatus.BLOCKED, RightsStatus.UNKNOWN]:
        return False
    if not asset.commercial_use_allowed and asset.rights_status != RightsStatus.USER_SUPPLIED:
        return False
    return True
