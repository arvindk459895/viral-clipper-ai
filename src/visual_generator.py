"""
ViralClipper AI Studio - Original AI Visuals & Reaction Graphic Synthesizer
Generates 100% original, copyright-free reaction illustrations, comic burst cards,
and visual breakdown diagrams. Eliminates the need for copyrighted movie/TV reaction clips.
"""
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont

from src.config import TEMP_DIR
from src.utils import sanitize_filename

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920


def _get_font(size: int = 40):
    """Safely retrieves a PIL font with fallback."""
    for font_name in ["arialbd.ttf", "arial.ttf", "seguiemj.ttf", "DejaVuSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    start_pos: tuple,
    max_width: int,
    fill_color: tuple,
    line_spacing: int = 14,
    max_lines: int = 5
) -> int:
    """
    Renders text cleanly wrapped across multiple lines within max_width using actual pixel bounding box.
    Guarantees text never overflows horizontally outside containers.
    Returns the y-coordinate after the last line rendered.
    """
    words = text.strip().split()
    lines = []
    curr_line = []

    for word in words:
        test_line = " ".join(curr_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width:
            curr_line.append(word)
        else:
            if curr_line:
                lines.append(" ".join(curr_line))
            curr_line = [word]
    if curr_line:
        lines.append(" ".join(curr_line))

    # Clamp to max_lines if needed
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if not lines[-1].endswith("..."):
            lines[-1] = lines[-1].rstrip(".,!? ") + "..."

    x, y = start_pos
    for line in lines:
        draw.text((x, y), line, fill=fill_color, font=font)
        bbox = draw.textbbox((0, 0), line, font=font)
        line_h = bbox[3] - bbox[1]
        y += line_h + line_spacing

    return y


def generate_editorial_title_card(
    title: str,
    subtitle: str,
    output_path: Path,
    tag: str = "EDITORIAL COMEDY DECONSTRUCTION"
) -> str:
    """
    Generates a full-screen (1080x1920) sleek modern title card for the AI Hook with zero text overflow.
    """
    img = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (16, 18, 27, 255))
    draw = ImageDraw.Draw(img)

    # Background gradient / tech grid accents
    for y in range(0, TARGET_HEIGHT, 60):
        draw.line([(0, y), (TARGET_WIDTH, y)], fill=(25, 30, 45, 120), width=1)
    for x in range(0, TARGET_WIDTH, 60):
        draw.line([(x, 0), (x, TARGET_HEIGHT)], fill=(25, 30, 45, 120), width=1)

    # Center glowing container
    margin_x = 80
    container_y1 = 520
    container_y2 = 1420
    container_w = TARGET_WIDTH - (2 * margin_x)
    draw.rounded_rectangle(
        [(margin_x, container_y1), (TARGET_WIDTH - margin_x, container_y2)],
        radius=30,
        fill=(24, 28, 42, 240),
        outline=(0, 212, 255, 255),
        width=4
    )

    # Header Tag Pill
    pill_w = min(680, container_w - 40)
    pill_h = 56
    pill_x1 = (TARGET_WIDTH - pill_w) // 2
    pill_y1 = container_y1 - (pill_h // 2)
    draw.rounded_rectangle(
        [(pill_x1, pill_y1), (pill_x1 + pill_w, pill_y1 + pill_h)],
        radius=28,
        fill=(255, 60, 110, 255),
        outline=(255, 255, 255, 220),
        width=2
    )
    font_tag = _get_font(24)
    draw.text((pill_x1 + 32, pill_y1 + 14), tag, fill=(255, 255, 255, 255), font=font_tag)

    # Title Text wrapped with pixel measurement
    font_title = _get_font(52)
    text_pad_x = margin_x + 50
    usable_w = container_w - 100

    curr_y = draw_wrapped_text(
        draw=draw,
        text=title,
        font=font_title,
        start_pos=(text_pad_x, container_y1 + 100),
        max_width=usable_w,
        fill_color=(255, 255, 255, 255),
        line_spacing=16,
        max_lines=4
    )

    # Accent divider line
    draw.line([(text_pad_x, curr_y + 15), (TARGET_WIDTH - text_pad_x, curr_y + 15)], fill=(0, 212, 255, 180), width=2)
    curr_y += 35

    # Subtitle / Hook framing with text wrapping
    font_sub = _get_font(32)
    draw_wrapped_text(
        draw=draw,
        text=f"ANALYSIS: {subtitle}",
        font=font_sub,
        start_pos=(text_pad_x, curr_y),
        max_width=usable_w,
        fill_color=(255, 215, 0, 255),
        line_spacing=12,
        max_lines=3
    )

    # Bottom watermark badge
    font_wm = _get_font(22)
    draw.text((margin_x + 50, container_y2 - 60), "ORIGINAL EDITORIAL ESSAY • FACELESS COMMENTARY", fill=(160, 175, 200, 255), font=font_wm)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")
    return str(output_path)


def generate_cartoon_reaction(
    reaction_type: str,
    caption: str,
    output_path: Path
) -> str:
    """
    Generates a high-contrast, transparent (600x600) original comic/cartoon reaction sticker.
    Types: 'laugh', 'confused', 'shock', 'disbelief', 'plot_twist'.
    """
    size = 600
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, (size // 2) - 30

    if reaction_type in ["laugh", "joy"]:
        # Comic starburst in background
        draw.ellipse([(cx - 220, cy - 220), (cx + 220, cy + 220)], fill=(255, 214, 10, 255), outline=(0, 0, 0, 255), width=8)
        # Laughing curved eyes
        draw.arc([(cx - 130, cy - 80), (cx - 30, cy + 20)], start=190, end=350, fill=(0, 0, 0, 255), width=10)
        draw.arc([(cx + 30, cy - 80), (cx + 130, cy + 20)], start=190, end=350, fill=(0, 0, 0, 255), width=10)
        # Giant open laughing mouth
        draw.chord([(cx - 120, cy - 10), (cx + 120, cy + 140)], start=0, end=180, fill=(180, 20, 40, 255), outline=(0, 0, 0, 255), width=8)
        # Tongue
        draw.chord([(cx - 60, cy + 60), (cx + 60, cy + 140)], start=0, end=180, fill=(255, 120, 150, 255))
        # Tears of laughter
        draw.polygon([(cx - 180, cy - 30), (cx - 150, cy - 70), (cx - 150, cy + 10)], fill=(0, 180, 255, 255), outline=(0, 0, 0, 255))
        draw.polygon([(cx + 180, cy - 30), (cx + 150, cy - 70), (cx + 150, cy + 10)], fill=(0, 180, 255, 255), outline=(0, 0, 0, 255))

    elif reaction_type in ["shock", "disbelief"]:
        # Blue gradient shocked face
        draw.ellipse([(cx - 220, cy - 220), (cx + 220, cy + 220)], fill=(120, 180, 255, 255), outline=(0, 0, 0, 255), width=8)
        # Wide blank eyes
        draw.ellipse([(cx - 130, cy - 100), (cx - 30, cy)], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=8)
        draw.ellipse([(cx + 30, cy - 100), (cx + 130, cy)], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=8)
        # Tiny shock pupils
        draw.ellipse([(cx - 85, cy - 55), (cx - 75, cy - 45)], fill=(0, 0, 0, 255))
        draw.ellipse([(cx + 75, cy - 55), (cx + 85, cy - 45)], fill=(0, 0, 0, 255))
        # Dropped jaw mouth
        draw.ellipse([(cx - 60, cy + 40), (cx + 60, cy + 160)], fill=(0, 0, 0, 255), outline=(0, 0, 0, 255), width=6)

    else:
        # Confused / Plot Twist Face
        draw.ellipse([(cx - 220, cy - 220), (cx + 220, cy + 220)], fill=(255, 170, 0, 255), outline=(0, 0, 0, 255), width=8)
        # One high eyebrow, one low
        draw.arc([(cx - 130, cy - 120), (cx - 30, cy - 40)], start=200, end=340, fill=(0, 0, 0, 255), width=10)
        draw.arc([(cx + 30, cy - 70), (cx + 130, cy + 10)], start=200, end=340, fill=(0, 0, 0, 255), width=10)
        # Question marks around head
        font_q = _get_font(60)
        draw.text((cx - 200, cy - 220), "?", fill=(255, 40, 80, 255), font=font_q)
        draw.text((cx + 160, cy - 200), "?", fill=(0, 200, 255, 255), font=font_q)
        # Squiggly mouth
        draw.line([(cx - 70, cy + 80), (cx - 20, cy + 60), (cx + 30, cy + 90), (cx + 80, cy + 70)], fill=(0, 0, 0, 255), width=8)

    # Caption banner at bottom
    pill_y = size - 85
    draw.rounded_rectangle([(30, pill_y), (size - 30, pill_y + 70)], radius=20, fill=(0, 0, 0, 230), outline=(255, 255, 255, 255), width=3)
    font_cap = _get_font(28)
    draw.text((60, pill_y + 16), caption.upper()[:28], fill=(255, 255, 255, 255), font=font_cap)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")
    return str(output_path)


def generate_diagram_card(
    premise_text: str,
    subversion_text: str,
    output_path: Path
) -> str:
    """
    Generates a full-screen 1080x1920 diagram card contrasting the setup vs. the comedic subversion.
    Strictly wraps all text inside bounded containers with zero horizontal overflow.
    """
    img = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (12, 14, 24, 255))
    draw = ImageDraw.Draw(img)

    # Background framing
    margin = 80
    container_w = TARGET_WIDTH - (2 * margin)
    usable_text_w = container_w - 70

    font_head = _get_font(46)
    draw_wrapped_text(
        draw=draw,
        text="COMEDIC MECHANICS DECONSTRUCTED",
        font=font_head,
        start_pos=(margin, 180),
        max_width=container_w,
        fill_color=(0, 212, 255, 255),
        line_spacing=10,
        max_lines=2
    )

    # Box 1: The Setup / Expectation
    b1_y1 = 340
    b1_y2 = 800
    draw.rounded_rectangle([(margin, b1_y1), (TARGET_WIDTH - margin, b1_y2)], radius=25, fill=(26, 32, 48, 255), outline=(100, 150, 255, 255), width=3)
    draw.rectangle([(margin, b1_y1), (TARGET_WIDTH - margin, b1_y1 + 65)], fill=(40, 60, 110, 255))
    font_sub = _get_font(30)
    draw.text((margin + 30, b1_y1 + 16), "ACT 1: THE ASSUMED PREMISE", fill=(255, 255, 255, 255), font=font_sub)

    # Wrapped premise text
    font_body = _get_font(32)
    draw_wrapped_text(
        draw=draw,
        text=f'"{premise_text}"',
        font=font_body,
        start_pos=(margin + 35, b1_y1 + 95),
        max_width=usable_text_w,
        fill_color=(220, 230, 250, 255),
        line_spacing=14,
        max_lines=5
    )

    # Downward Arrow / Transition Icon
    arrow_y = 860
    cx = TARGET_WIDTH // 2
    draw.polygon([(cx, arrow_y + 55), (cx - 35, arrow_y), (cx + 35, arrow_y)], fill=(255, 60, 110, 255))

    # Box 2: The Subversion / Reality
    b2_y1 = 980
    b2_y2 = 1440
    draw.rounded_rectangle([(margin, b2_y1), (TARGET_WIDTH - margin, b2_y2)], radius=25, fill=(36, 24, 38, 255), outline=(255, 60, 110, 255), width=4)
    draw.rectangle([(margin, b2_y1), (TARGET_WIDTH - margin, b2_y1 + 65)], fill=(130, 25, 60, 255))
    draw.text((margin + 30, b2_y1 + 16), "ACT 2: THE BRUTAL SUBVERSION", fill=(255, 255, 255, 255), font=font_sub)

    # Wrapped subversion text
    draw_wrapped_text(
        draw=draw,
        text=f'"{subversion_text}"',
        font=font_body,
        start_pos=(margin + 35, b2_y1 + 95),
        max_width=usable_text_w,
        fill_color=(255, 220, 180, 255),
        line_spacing=14,
        max_lines=5
    )

    # Footer note wrapped
    font_ft = _get_font(26)
    draw_wrapped_text(
        draw=draw,
        text="WHY IT WORKS: The shock gap between expectation & punchline delivery.",
        font=font_ft,
        start_pos=(margin, 1540),
        max_width=container_w,
        fill_color=(255, 215, 0, 255),
        line_spacing=10,
        max_lines=2
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), format="PNG")
    return str(output_path)


def generate_faceless_visual_package(
    clip_id: str,
    script_dict: Dict[str, str]
) -> Dict[str, str]:
    """
    Generates all necessary original visuals for a faceless commentary Short.
    Returns dictionary of generated asset paths.
    """
    safe_id = sanitize_filename(clip_id)
    pkg_dir = TEMP_DIR / f"{safe_id}_faceless_assets"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    hook_card = pkg_dir / "hook_card.png"
    generate_editorial_title_card(
        title=script_dict.get("hook", "Why This Joke Broke the Internet"),
        subtitle=script_dict.get("editorial_angle", "Comedic Subversion Analysis"),
        output_path=hook_card
    )

    reaction_badge = pkg_dir / "reaction_badge.png"
    generate_cartoon_reaction(
        reaction_type="laugh",
        caption="Pure Timing",
        output_path=reaction_badge
    )

    diagram_card = pkg_dir / "diagram_card.png"
    generate_diagram_card(
        premise_text=script_dict.get("context_commentary", "The normal setup"),
        subversion_text=script_dict.get("analysis_reaction", "The unexpected punchline"),
        output_path=diagram_card
    )

    return {
        "hook_card": str(hook_card),
        "reaction_badge": str(reaction_badge),
        "diagram_card": str(diagram_card)
    }
