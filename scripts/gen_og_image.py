"""Generate the static Open Graph share-card image for social link previews."""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = "#0c0a08"
ACCENT = "#e8892b"
TEXT_1 = "#f5efe4"
TEXT_2 = "#a99a84"

FONT_DIR = Path("/System/Library/Fonts/Supplemental")
title_font = ImageFont.truetype(str(FONT_DIR / "Georgia Bold.ttf"), 92)
sub_font   = ImageFont.truetype(str(FONT_DIR / "Georgia.ttf"), 30)
tag_font   = ImageFont.truetype(str(FONT_DIR / "Georgia.ttf"), 22)

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

# Chakra mark
cx, cy, r = 150, 150, 62
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT, width=6)
d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=ACCENT)
for i in range(8):
    angle = i * (2 * math.pi / 8)
    x1, y1 = cx + 26 * math.cos(angle), cy + 26 * math.sin(angle)
    x2, y2 = cx + 78 * math.cos(angle), cy + 78 * math.sin(angle)
    d.line([x1, y1, x2, y2], fill=ACCENT, width=5)

# Wordmark + tagline next to mark
d.text((240, 108), "PRAMAANA", font=sub_font, fill=TEXT_1)
d.text((240, 148), "CREDIBILITY INTELLIGENCE", font=tag_font, fill=TEXT_2)

# Headline
d.text((90, 280), "Know what you're", font=title_font, fill=TEXT_1)
d.text((90, 390), "actually reading.", font=title_font, fill=ACCENT)

# Footer line
d.text((90, 552), "pramaana.fyi  ·  Structural credibility analysis for news articles", font=sub_font, fill=TEXT_2)

out = Path(__file__).parent.parent / "og-image.png"
img.save(out, "PNG")
print(f"Saved {out} ({out.stat().st_size // 1024} KB)")
