#!/usr/bin/env python3
"""Etsy listing photos for the Budget Guide + Life & Budget Planner bundle.

    python3 pdf-products/build_bundle.py

Needs the guide and planner PDFs (and their listing photos) built first.
"""

import os
import shutil

import pymupdf
from PIL import Image, ImageDraw, ImageFont

from build_planner import HERE, OUT, SHOP, THEMES

THEME = "sage"
GUIDE = os.path.join(OUT, "Beginners-Budget-Guide_sage_LETTER.pdf")
PLANNER = os.path.join(OUT, "Life-Budget-Planner_sage_LETTER.pdf")
DEST = os.path.join(OUT, "listing-photos", "Budget-Bundle-sage")
W, H = 2700, 2025


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def page_img(doc, i, height):
    pix = doc[i].get_pixmap(dpi=200)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)


def paste(bg, im, x, y, t):
    bg.paste(Image.new("RGB", im.size, t["line"]), (x + 12, y + 12))
    bg.paste(im, (x, y))


def main():
    t = THEMES[THEME]
    guide, planner = pymupdf.open(GUIDE), pymupdf.open(PLANNER)
    os.makedirs(DEST, exist_ok=True)

    # 1. hero: both covers side by side under a banner
    bg = Image.new("RGB", (W, H), t["soft"])
    d = ImageDraw.Draw(bg)
    d.text((W / 2, 150), "The Budget Starter Bundle", font=font("PlayfairDisplay-VF.ttf", 130),
           fill=t["ink"], anchor="mm")
    d.text((W / 2, 280), "GUIDE + PLANNER  ·  SAVE 15%", font=font("Lato-Bold.ttf", 62),
           fill=t["accent"], anchor="mm")
    paste(bg, page_img(guide, 0, 1450), 170, 400, t)
    paste(bg, page_img(planner, 0, 1450), 1520, 400, t)
    d.ellipse((1325, 1040, 1495, 1210), fill=t["accent"])
    d.text((1410, 1125), "+", font=font("Lato-Bold.ttf", 140), fill="white", anchor="mm")
    bg.save(os.path.join(DEST, "01-hero.jpg"), quality=92)

    # 2. what's included
    bg = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(bg)
    d.text((W / 2, 140), "What's Included", font=font("PlayfairDisplay-VF.ttf", 120), fill=t["ink"], anchor="mm")
    cols = [("The Beginner's Budget Guide", f"{len(guide)} pages  ·  8 steps  ·  10 worksheets", guide, [0, 7, 18]),
            ("Life & Budget Planner", f"{len(planner)} printable planner pages", planner, [0, 8, 6])]
    for k, (title, sub, doc, pages) in enumerate(cols):
        cx = 690 + k * 1320
        for j, i in enumerate(reversed(pages)):
            im = page_img(doc, i, 1150 - (2 - j) * 40)
            paste(bg, im, cx - im.width // 2 + (2 - j) * 190 - 190, 330 + (2 - j) * 20, t)
        d.text((cx, 1640), title, font=font("PlayfairDisplay-VF.ttf", 72), fill=t["ink"], anchor="mm")
        d.text((cx, 1740), sub.upper(), font=font("Lato-Bold.ttf", 44), fill=t["accent"], anchor="mm")
    d.rectangle((0, H - 150, W, H), fill=t["accent"])
    d.text((W / 2, H - 75), f"US LETTER + A4  ·  INSTANT DOWNLOAD  ·  {SHOP.upper()}",
           font=font("Lato-Bold.ttf", 56), fill="white", anchor="mm")
    bg.save(os.path.join(DEST, "02-whats-included.jpg"), quality=92)

    # 3-7. best existing photos from each product
    reuse = [("Beginners-Budget-Guide-sage/02-eight-steps.jpg", "03-guide-steps.jpg"),
             ("Beginners-Budget-Guide-sage/04-real-examples.jpg", "04-guide-example.jpg"),
             ("sage/02-whats-inside.jpg", "05-planner-pages.jpg"),
             ("Beginners-Budget-Guide-sage/03-worksheets.jpg", "06-worksheets.jpg"),
             ("sage/03-monthly-budget.jpg", "07-monthly-budget.jpg")]
    for src, name in reuse:
        shutil.copy(os.path.join(OUT, "listing-photos", src), os.path.join(DEST, name))
    print("photos:", DEST, sorted(os.listdir(DEST)))


if __name__ == "__main__":
    main()
