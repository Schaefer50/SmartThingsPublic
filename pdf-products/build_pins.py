#!/usr/bin/env python3
"""Make Pinterest pins (1000x1500) for live Etsy listings, plus a bulk-upload CSV.

    python3 pdf-products/build_pins.py

Pins land in output/pins/. The CSV points at the pin images on GitHub
(public raw URLs), so push the branch before uploading the CSV to Pinterest
(Create > Bulk create Pins).
"""

import csv
import os

import pymupdf
from PIL import Image, ImageDraw, ImageFont

from build_planner import HERE, OUT, SHOP, THEMES

RAW = ("https://raw.githubusercontent.com/Schaefer50/SmartThingsPublic/"
       "claude/pdf-documents-sale-tizxmz/pdf-products/output/pins/")
W, H = 1000, 1500

PLANNER_DESC = ("Undated printable life & budget planner: monthly budget, habit tracker, "
                "$5,050 savings challenge, meal planner, debt payoff tracker and more. "
                "17 pages, US Letter + A4, instant download. Print at home or use in GoodNotes.")
GUIDE_DESC = ("New to budgeting? This 27-page beginner's guide walks you through 8 simple steps, "
              "from knowing your numbers to paying off debt, with a real worked example and "
              "10 printable worksheets. Instant PDF download, US Letter + A4.")

# (slug, pdf, theme, etsy listing id, board, [(headline, subline, pages)], description, keywords)
PRODUCTS = [
    ("planner-sage", "Life-Budget-Planner_sage_LETTER.pdf", "sage", 4584031029, "Printable Planners",
     [("Life & Budget Planner", "17 printable pages · undated", [0, 8, 6]),
      ("Get Your Money Organized", "Budget · savings · debt trackers", [8, 11, 12])],
     PLANNER_DESC, "budget planner, printable planner, undated planner, habit tracker, savings challenge"),
    ("planner-blush", "Life-Budget-Planner_blush_LETTER.pdf", "blush", 4584689836, "Printable Planners",
     [("Blush Pink Life Planner", "17 printable pages · undated", [0, 6, 4]),
      ("Plan · Save · Grow", "Habit tracker, budget & more", [6, 8, 13])],
     PLANNER_DESC, "pink planner, budget planner, printable planner, habit tracker, aesthetic planner"),
    ("planner-neutral", "Life-Budget-Planner_neutral_LETTER.pdf", "neutral", 4584690230, "Printable Planners",
     [("Neutral Life & Budget Planner", "17 printable pages · undated", [0, 5, 8]),
      ("Your Whole Life, Organized", "Daily, weekly & monthly pages", [3, 4, 5])],
     PLANNER_DESC, "neutral planner, minimalist planner, budget planner, printable planner, life planner"),
    ("budget-guide", "Beginners-Budget-Guide_sage_LETTER.pdf", "sage", 4585066275, "Budgeting Tips",
     [("How to Budget for Beginners", "8 simple steps + 10 worksheets", [0, 7, 18]),
      ("Build Your First Budget", "A step-by-step guide with real numbers", [7, 15, 19])],
     GUIDE_DESC, "budgeting for beginners, how to budget, budget guide, 50 30 20 budget, money tips"),
]


def font(name, size):
    return ImageFont.truetype(os.path.join(HERE, "fonts", name), size)


def page_img(doc, i, height):
    pix = doc[i].get_pixmap(dpi=150)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    return lines + [cur]


def make_pin(doc, theme, headline, subline, pages, path):
    t = THEMES[theme]
    bg = Image.new("RGB", (W, H), t["soft"])
    d = ImageDraw.Draw(bg)
    # headline block
    d.rectangle((0, 0, W, 430), fill=t["accent"])
    serif = font("PlayfairDisplay-VF.ttf", 86)
    lines = wrap(d, headline, serif, W - 120)
    y = 215 - len(lines) * 50 - 25
    for ln in lines:
        d.text((W / 2, y), ln, font=serif, fill="white", anchor="ma")
        y += 100
    d.text((W / 2, y + 15), subline.upper(), font=font("Lato-Bold.ttf", 34), fill=t["soft"], anchor="ma")
    # fanned pages
    front, mid, back = pages
    for i, x, top, h in ((back, 390, 520, 740), (mid, 240, 560, 780), (front, 60, 600, 820)):
        im = page_img(doc, i, h)
        bg.paste(Image.new("RGB", im.size, t["line"]), (x + 10, top + 10))
        bg.paste(im, (x, top))
    # footer
    d.rectangle((0, H - 90, W, H), fill="white")
    d.text((W / 2, H - 45), f"INSTANT DOWNLOAD  ·  {SHOP.upper()}", font=font("Lato-Bold.ttf", 30),
           fill=t["ink"], anchor="mm")
    bg.save(path, quality=90)


def main():
    out = os.path.join(OUT, "pins")
    os.makedirs(out, exist_ok=True)
    rows = []
    for slug, pdf, theme, lid, board, variants, desc, keywords in PRODUCTS:
        doc = pymupdf.open(os.path.join(OUT, pdf))
        for n, (headline, subline, pages) in enumerate(variants, start=1):
            name = f"{slug}-{n}.jpg"
            make_pin(doc, theme, headline, subline, pages, os.path.join(out, name))
            rows.append({"Title": headline[:100], "Media URL": RAW + name, "Pinterest board": board,
                         "Thumbnail": "", "Description": desc[:500],
                         "Link": f"https://www.etsy.com/listing/{lid}", "Publish date": "",
                         "Keywords": keywords})
            print(name)
    with open(os.path.join(out, "pinterest-bulk-upload.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} pins + pinterest-bulk-upload.csv in {out}")


if __name__ == "__main__":
    main()
