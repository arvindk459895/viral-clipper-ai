"""
Tests for Phase 9 & 10: Rights Verification, Compliance Audit, and ZIP Export.
"""
import json
import zipfile
from pathlib import Path
from src.asset_license import AssetItem, AssetCategory, AssetStatus, RightsStatus
from src.rights_checker import audit_clip_rights, save_rights_report, RightsAuditReport
from src.pipeline import run_pipeline


def test_rights_audit_approved_assets():
    approved_asset = AssetItem(
        asset_id="a1",
        name="Laugh Badge",
        asset_category=AssetCategory.MEME,
        filename="laugh.png",
        file_path="assets/memes/laugh.png",
        rights_status=RightsStatus.GENERATED,
        status=AssetStatus.APPROVED,
        commercial_use_allowed=True
    )
    report = audit_clip_rights(
        source_title="Authorized Comedy Video",
        user_confirmed_source=True,
        assets_used=[approved_asset],
        is_demo_mode=False
    )
    assert report.is_eligible_for_export is True
    assert report.source_rights_status == "USER_CONFIRMED_AUTHORIZED"
    assert report.export_status_label == "No unverified assets detected."
    assert report.meme_assets_approved == 1
    assert report.meme_assets_review == 0


def test_rights_audit_unverified_assets():
    unverified_asset = AssetItem(
        asset_id="a2",
        name="Unverified Meme",
        asset_category=AssetCategory.MEME,
        filename="unverified.png",
        file_path="assets/memes/unverified.png",
        rights_status=RightsStatus.UNKNOWN,
        status=AssetStatus.REVIEW,
        commercial_use_allowed=False
    )
    report = audit_clip_rights(
        source_title="Sample Video",
        user_confirmed_source=True,
        assets_used=[unverified_asset],
        is_demo_mode=False
    )
    assert report.is_eligible_for_export is False
    assert "HELD FOR REVIEW" in report.export_status_label
    assert report.meme_assets_review == 1
    assert len(report.warnings) > 0


def test_save_rights_report(tmp_path):
    report = RightsAuditReport(
        source_video_title="Test Video",
        source_rights_status="USER_CONFIRMED_AUTHORIZED",
        is_eligible_for_export=True,
        export_status_label="No unverified assets detected."
    )
    out_json = tmp_path / "rights_report.json"
    save_rights_report(report, out_json)
    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["source_rights_status"] == "USER_CONFIRMED_AUTHORIZED"


def test_full_pipeline_demo_run():
    # Run pipeline with 1 short in demo mode
    result = run_pipeline(
        video_source="demo_sample",
        is_demo=True,
        num_shorts=1,
        clip_duration="15 sec",
        editing_style="Meme",
        user_confirmed_source=True
    )

    assert "shorts" in result
    assert len(result["shorts"]) == 1
    short = result["shorts"][0]

    # Verify all 3 video variations
    clean_p = Path(short["clean_mp4"])
    meme_p = Path(short["meme_mp4"])
    heavy_p = Path(short["heavy_mp4"])
    assert clean_p.exists() and clean_p.stat().st_size > 0
    assert meme_p.exists() and meme_p.stat().st_size > 0
    assert heavy_p.exists() and heavy_p.stat().st_size > 0

    # Verify 2 thumbnails
    t1_p = Path(short["thumbnail_1"])
    t2_p = Path(short["thumbnail_2"])
    assert t1_p.exists() and t1_p.stat().st_size > 0
    assert t2_p.exists() and t2_p.stat().st_size > 0

    # Verify CSV, JSON, and ZIP bundle
    csv_p = Path(result["clips_csv_path"])
    json_p = Path(result["analysis_json_path"])
    rights_p = Path(result["rights_report_path"])
    zip_p = Path(result["zip_package_path"])

    assert csv_p.exists() and csv_p.stat().st_size > 0
    assert json_p.exists() and json_p.stat().st_size > 0
    assert rights_p.exists() and rights_p.stat().st_size > 0
    assert zip_p.exists() and zip_p.stat().st_size > 0

    # Inspect contents of the exported ZIP bundle
    with zipfile.ZipFile(zip_p, "r") as zf:
        namelist = zf.namelist()
        assert any("clean.mp4" in name for name in namelist)
        assert any("meme.mp4" in name for name in namelist)
        assert any("heavy.mp4" in name for name in namelist)
        assert any("thumbnail" in name for name in namelist)
        assert "rights_report.json" in namelist
        assert "clips.csv" in namelist
        assert "analysis.json" in namelist
