"""
ViralClipper AI Studio - Meme & Rights-Aware Asset Manager
Manages asset_library.json, seeds original generated graphics/SFX,
handles user uploads, and enforces approval statuses.
"""
import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import soundfile as sf

from src.config import (
    ASSET_LIBRARY_PATH,
    MEMES_DIR,
    GIFS_DIR,
    SFX_DIR,
    MUSIC_DIR,
    TRANSITIONS_DIR,
    METADATA_DIR
)
from src.asset_license import (
    AssetItem,
    AssetCategory,
    AssetStatus,
    RightsStatus,
    is_eligible_for_export
)


class AssetLibraryManager:
    def __init__(self, library_path: Path = ASSET_LIBRARY_PATH):
        self.library_path = library_path
        self.library_path.parent.mkdir(parents=True, exist_ok=True)
        self.assets: Dict[str, AssetItem] = {}
        self.load()
        if not self.assets:
            self.seed_original_assets()

    def load(self):
        """Loads asset catalog from JSON and normalizes paths for the current machine."""
        if self.library_path.exists():
            try:
                data = json.loads(self.library_path.read_text(encoding="utf-8"))
                self.assets = {}
                for k, v in data.items():
                    fname = v.get("filename", "")
                    cat = v.get("asset_category", "")
                    if cat == "sfx":
                        v["file_path"] = str(SFX_DIR / fname)
                    elif cat == "music":
                        v["file_path"] = str(MUSIC_DIR / fname)
                    else:
                        v["file_path"] = str(MEMES_DIR / fname)
                    self.assets[k] = AssetItem(**v)
            except Exception:
                self.assets = {}

        # Re-seed if catalog is empty or any generated file is physically missing
        missing_files = any(not Path(a.file_path).exists() for a in self.assets.values())
        if not self.assets or missing_files:
            self.seed_original_assets()
            self.save()

    def save(self):
        """Saves asset catalog to JSON."""
        data = {k: v.model_dump() for k, v in self.assets.items()}
        self.library_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def get_all_assets(self) -> List[AssetItem]:
        return list(self.assets.values())

    def get_approved_assets(self, category: Optional[AssetCategory] = None) -> List[AssetItem]:
        res = [a for a in self.assets.values() if a.status == AssetStatus.APPROVED and is_eligible_for_export(a)]
        if category:
            res = [a for a in res if a.asset_category == category]
        return res

    def get_by_tag(self, tag: str, category: Optional[AssetCategory] = None) -> List[AssetItem]:
        approved = self.get_approved_assets(category)
        tag_lower = tag.lower()
        matching = [a for a in approved if any(tag_lower in t.lower() for t in a.tags)]
        return matching or approved

    def update_status(self, asset_id: str, new_status: AssetStatus) -> bool:
        if asset_id in self.assets:
            self.assets[asset_id].status = new_status
            self.save()
            return True
        return False

    def add_user_asset(
        self,
        source_path: Path,
        asset_category: AssetCategory,
        tags: List[str]
    ) -> AssetItem:
        """Imports a user-provided asset and marks rights_status=user_supplied."""
        dest_dir = {
            AssetCategory.MEME: MEMES_DIR,
            AssetCategory.GIF: GIFS_DIR,
            AssetCategory.SFX: SFX_DIR,
            AssetCategory.MUSIC: MUSIC_DIR,
            AssetCategory.TRANSITION: TRANSITIONS_DIR,
            AssetCategory.GENERATED: MEMES_DIR
        }[asset_category]

        dest_file = dest_dir / source_path.name
        shutil.copy2(source_path, dest_file)

        asset_id = f"user_{source_path.stem}_{len(self.assets) + 1}"
        item = AssetItem(
            asset_id=asset_id,
            name=source_path.stem.replace("_", " ").title(),
            asset_category=asset_category,
            filename=source_path.name,
            file_path=str(dest_file),
            rights_status=RightsStatus.USER_SUPPLIED,
            source_name="User Upload",
            license="User Authorized / Owned",
            creator="User",
            attribution_required=False,
            commercial_use_allowed=True,
            status=AssetStatus.APPROVED,
            tags=tags
        )
        self.assets[asset_id] = item
        self.save()
        return item

    def seed_original_assets(self):
        """
        Generates original reaction stickers and sound effects procedurally.
        Guarantees 100% legal clearance with rights_status=generated.
        """
        # 1. Original Graphic Badges
        badges = [
            ("laugh_badge", "LOL! ", ["funny", "laugh", "rofl"], (255, 204, 0)),
            ("dead_skull_badge", "DEAD! ", ["shock", "funny", "disbelief"], (230, 230, 230)),
            ("what_badge", "WHAT?!", ["surprise", "shock", "confused"], (255, 60, 60)),
            ("mindblown_badge", "WOAH! ", ["shock", "surprise", "chaos"], (255, 100, 200)),
            ("fire_roast_badge", "ROASTED ", ["roast", "sarcasm", "funny"], (255, 120, 0)),
            ("awkward_pause_badge", "AWKWARD ", ["awkward", "deadpan", "fail"], (120, 180, 255)),
        ]

        for file_key, text, tags, bg_color in badges:
            img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Circular badge with shadow
            draw.ellipse([20, 20, 380, 380], fill=bg_color, outline=(0, 0, 0, 255), width=8)
            draw.text((200, 190), text, fill=(0, 0, 0, 255), anchor="mm")

            dest_path = MEMES_DIR / f"{file_key}.png"
            img.save(dest_path)

            asset_id = f"gen_{file_key}"
            self.assets[asset_id] = AssetItem(
                asset_id=asset_id,
                name=f"Reaction: {text}",
                asset_category=AssetCategory.GENERATED,
                filename=f"{file_key}.png",
                file_path=str(dest_path),
                rights_status=RightsStatus.GENERATED,
                source_name="Procedurally Generated by Studio",
                license="Original / CC0 Equivalent",
                creator="ViralClipper Studio Engine",
                attribution_required=False,
                commercial_use_allowed=True,
                status=AssetStatus.APPROVED,
                tags=tags
            )

        # 2. Original Cleared Sound Effects
        sr = 44100
        # A. Pop effect (sine frequency sweep from 400Hz to 800Hz with exponential decay)
        dur_pop = 0.25
        t_pop = np.linspace(0, dur_pop, int(sr * dur_pop))
        freq_pop = np.linspace(350, 900, len(t_pop))
        wave_pop = 0.6 * np.sin(2 * np.pi * freq_pop * t_pop) * np.exp(-12 * t_pop)
        pop_file = SFX_DIR / "pop.wav"
        sf.write(str(pop_file), wave_pop.astype(np.float32), sr)

        self.assets["gen_sfx_pop"] = AssetItem(
            asset_id="gen_sfx_pop",
            name="Comedic Pop Accent",
            asset_category=AssetCategory.SFX,
            filename="pop.wav",
            file_path=str(pop_file),
            rights_status=RightsStatus.GENERATED,
            source_name="Procedurally Synthesized",
            license="Original Sound Design",
            creator="ViralClipper Studio",
            attribution_required=False,
            commercial_use_allowed=True,
            status=AssetStatus.APPROVED,
            tags=["pop", "accent", "funny", "punchline"]
        )

        # B. Whoosh transition effect (modulated white noise sweep)
        dur_whoosh = 0.5
        t_whoosh = np.linspace(0, dur_whoosh, int(sr * dur_whoosh))
        noise = np.random.uniform(-1, 1, len(t_whoosh))
        envelope = np.sin(np.pi * (t_whoosh / dur_whoosh)) ** 2
        wave_whoosh = 0.5 * noise * envelope
        whoosh_file = SFX_DIR / "whoosh.wav"
        sf.write(str(whoosh_file), wave_whoosh.astype(np.float32), sr)

        self.assets["gen_sfx_whoosh"] = AssetItem(
            asset_id="gen_sfx_whoosh",
            name="Subtle Whoosh Sweep",
            asset_category=AssetCategory.SFX,
            filename="whoosh.wav",
            file_path=str(whoosh_file),
            rights_status=RightsStatus.GENERATED,
            source_name="Procedurally Synthesized",
            license="Original Sound Design",
            creator="ViralClipper Studio",
            attribution_required=False,
            commercial_use_allowed=True,
            status=AssetStatus.APPROVED,
            tags=["whoosh", "transition", "impact"]
        )

        # C. Record scratch accent
        dur_scratch = 0.4
        t_scratch = np.linspace(0, dur_scratch, int(sr * dur_scratch))
        f_scratch = np.linspace(1500, 200, len(t_scratch))
        wave_scratch = 0.4 * np.sin(2 * np.pi * f_scratch * t_scratch) * np.exp(-4 * t_scratch)
        scratch_file = SFX_DIR / "record_scratch.wav"
        sf.write(str(scratch_file), wave_scratch.astype(np.float32), sr)

        self.assets["gen_sfx_scratch"] = AssetItem(
            asset_id="gen_sfx_scratch",
            name="Comedic Record Scratch",
            asset_category=AssetCategory.SFX,
            filename="record_scratch.wav",
            file_path=str(scratch_file),
            rights_status=RightsStatus.GENERATED,
            source_name="Procedurally Synthesized",
            license="Original Sound Design",
            creator="ViralClipper Studio",
            attribution_required=False,
            commercial_use_allowed=True,
            status=AssetStatus.APPROVED,
            tags=["scratch", "awkward", "pause", "fail"]
        )

        self.save()
