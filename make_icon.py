#!/usr/bin/env python3
"""Make a simple placeholder app icon (icon-source.png, 1024x1024).

  python3 make_icon.py                     # plain placeholder: colored square + "RB"
  python3 make_icon.py --text "SF"         # your own initials
  python3 make_icon.py --photo my.jpg      # use your own photo (center-cropped to a square)

Then run `python3 build.py`; it resizes icon-source.png into icons/ (180, 192, 512 + maskable versions).
You can also just replace icon-source.png with any square PNG (1024x1024 recommended) and rebuild.
"""
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageOps

ap = argparse.ArgumentParser()
ap.add_argument("--text", default="RB")
ap.add_argument("--photo")
ap.add_argument("--bg", default="#b5542d")
ap.add_argument("--fg", default="#fbf5ec")
a = ap.parse_args()
S = 1024
if a.photo:
    img = ImageOps.fit(Image.open(a.photo).convert("RGB"), (S, S), Image.LANCZOS)
else:
    img = Image.new("RGB", (S, S), a.bg)
    d = ImageDraw.Draw(img)
    font = None
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"):
        try: font = ImageFont.truetype(f, 420); break
        except OSError: pass
    font = font or ImageFont.load_default()
    d.rounded_rectangle((150, 150, S - 150, S - 150), radius=90, outline=a.fg, width=24)
    d.text((S / 2, S / 2 + 10), a.text[:3], fill=a.fg, font=font, anchor="mm")
img.save("icon-source.png")
print("Wrote icon-source.png (run python3 build.py to regenerate icons/)")
