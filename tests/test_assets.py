"""
Tests for Phase 6: Rights-Aware Asset System, Manager, and Trending Discovery.
"""
from pathlib import Path
from src.asset_license import (
    AssetItem,
    AssetCategory,
    AssetStatus,
    RightsStatus,
    is_eligible_for_export
)
from src.meme_manager import AssetLibraryManager
from src.asset_downloader import update_trending_meme_library


def test_asset_export_eligibility():
    # Approved CC0 asset -> eligible
    approved_item = AssetItem(
        asset_id="a1",
        name="Laugh Sticker",
        asset_category=AssetCategory.MEME,
        filename="laugh.png",
        file_path="assets/memes/laugh.png",
        rights_status=RightsStatus.GENERATED,
        status=AssetStatus.APPROVED,
        commercial_use_allowed=True
    )
    assert is_eligible_for_export(approved_item) is True

    # Asset in REVIEW -> ineligible
    review_item = AssetItem(
        asset_id="a2",
        name="Movie Clip",
        asset_category=AssetCategory.MEME,
        filename="clip.gif",
        file_path="assets/gifs/clip.gif",
        rights_status=RightsStatus.UNKNOWN,
        status=AssetStatus.REVIEW,
        commercial_use_allowed=False
    )
    assert is_eligible_for_export(review_item) is False

    # Blocked asset -> ineligible
    blocked_item = AssetItem(
        asset_id="a3",
        name="Copyrighted Song",
        asset_category=AssetCategory.MUSIC,
        filename="song.mp3",
        file_path="assets/music/song.mp3",
        rights_status=RightsStatus.BLOCKED,
        status=AssetStatus.BLOCKED,
        commercial_use_allowed=False
    )
    assert is_eligible_for_export(blocked_item) is False


def test_asset_manager_seeding(tmp_path):
    mgr = AssetLibraryManager(library_path=tmp_path / "asset_lib.json")
    all_assets = mgr.get_all_assets()
    assert len(all_assets) >= 6

    # Verify procedural sound effects and graphics were generated
    approved = mgr.get_approved_assets()
    assert len(approved) == len(all_assets)

    sfx_assets = mgr.get_approved_assets(AssetCategory.SFX)
    assert len(sfx_assets) >= 2
    assert any("pop" in a.name.lower() for a in sfx_assets)

    # Check that generated files actually exist on disk
    for a in all_assets:
        assert Path(a.file_path).exists()


def test_trending_meme_discovery(tmp_path):
    mgr = AssetLibraryManager(library_path=tmp_path / "asset_lib.json")
    initial_count = len(mgr.get_all_assets())

    stats = update_trending_meme_library(mgr)
    assert stats["new_found"] > 0
    assert stats["approved"] > 0
    assert stats["needs_review"] > 0
    assert len(mgr.get_all_assets()) == initial_count + stats["new_found"]

    # Verify unverified assets are marked REVIEW and NOT eligible for export
    review_items = [a for a in mgr.get_all_assets() if a.status == AssetStatus.REVIEW]
    assert len(review_items) == stats["needs_review"]
    for r in review_items:
        assert is_eligible_for_export(r) is False
