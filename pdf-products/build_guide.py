#!/usr/bin/env python3
"""Build a printable PDF guide (ebook + worksheets) from a Markdown-like file.

    python3 pdf-products/build_guide.py guides/beginners-budget-guide.md
    python3 pdf-products/build_guide.py guides/beginners-budget-guide.md --theme blush --size a4

Content format (see guides/*.md):
    ---front matter---      title / subtitle / kicker / file
    # Chapter               new page; "Step 3: Name" shows "STEP 3" above the name
    ## Heading
    plain paragraph         **bold** and *italic* allowed
    - bullet
    [ ] checklist item
    > TIP: text            callout box (any LABEL: works)
    | a | b | c |           table; first row is the header
    @worksheet name         full-page worksheet (see WORKSHEETS below)
"""

import argparse
import os
import re

from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, KeepTogether,
                                ListFlowable, ListItem, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from build_planner import HERE, MARGIN, OUT, SHOP, SIZES, THEMES, Planner

pdfmetrics.registerFont(TTFont("SansItalic", os.path.join(HERE, "fonts", "Lato-Italic.ttf")))
pdfmetrics.registerFont(TTFont("SansBoldItalic", os.path.join(HERE, "fonts", "Lato-BoldItalic.ttf")))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="SansBold",
                              italic="SansItalic", boldItalic="SansBoldItalic")


# ---------- parsing ----------

def parse(path):
    text = open(path, encoding="utf-8").read()
    meta = {}
    if text.startswith("---"):
        head, text = text[3:].split("\n---", 1)
        for line in head.strip().splitlines():
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    blocks, para = [], []

    def flush():
        if para:
            blocks.append(("p", " ".join(para)))
            para.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush()
            continue
        for prefix, kind in (("# ", "h1"), ("## ", "h2"), ("- ", "li"), ("[ ] ", "check"),
                             ("> ", "callout"), ("@worksheet ", "worksheet")):
            if line.startswith(prefix):
                flush()
                blocks.append((kind, line[len(prefix):].strip()))
                break
        else:
            if line.startswith("|"):
                flush()
                row = [c.strip() for c in line.strip("|").split("|")]
                if blocks and blocks[-1][0] == "table":
                    blocks[-1][1].append(row)
                else:
                    blocks.append(("table", [row]))
            else:
                para.append(line.strip())
    flush()
    return meta, blocks


def inline(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)


# ---------- flowables ----------

class Check(Flowable):
    """Checkbox + wrapped text."""

    def __init__(self, text, style, color):
        super().__init__()
        self.p = Paragraph(inline(text), style)
        self.color = color

    def wrap(self, aw, ah):
        self.w, self.h = self.p.wrap(aw - 22, ah)
        return aw, self.h + 4

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(0.9)
        self.canv.roundRect(2, self.h - 11, 10, 10, 2)
        self.p.drawOn(self.canv, 22, 0)


class Worksheet(Flowable):
    """Occupies a whole page and draws a worksheet directly onto the canvas."""

    def __init__(self, guide, name):
        super().__init__()
        self.guide, self.name = guide, name
        self.title = WORKSHEET_TITLES[name]

    def wrap(self, aw, ah):
        return aw, 1

    def drawOn(self, canvas, x, y, _sW=0):
        p = Planner(None, self.guide.size, THEMES[self.guide.theme],
                    product=self.guide.meta["title"], canv=canvas)
        canvas.saveState()
        WORKSHEETS[self.name](p)
        p.footer()
        canvas.restoreState()


# ---------- guide-only worksheets (drawn with the planner's helpers) ----------

def ws_snapshot(p):
    y = p.header("Income & Expenses Snapshot", "Month")
    half = (p.inner - 15) / 2
    b = p.table(MARGIN, y, [half * 0.62, half * 0.38], ["Income source", "Monthly"], 5)
    p.section(MARGIN + half + 15, y, half, y - b, "Summary", lines=False, fill=True)
    c = p.c
    c.setFont("Sans", 9)
    c.setFillColor(p.t["ink"])
    for i, row in enumerate(["Total income", "Total expenses", "Difference (+/-)"]):
        yy = y - 44 - i * ((y - b - 36) / 3)
        c.drawString(MARGIN + half + 27, yy, row)
        p.rules(MARGIN + half + 15 + half * 0.55, yy - 2, MARGIN + half + 15 + half - 12, yy - 2)
    y2 = b - 18
    w = p.inner
    rows = int((y2 - MARGIN - 130) / 20)
    b2 = p.table(MARGIN, y2, [w * 0.36, w * 0.14, w * 0.16, w * 0.34],
                 ["Expense", "Fixed / Flex", "Amount", "Notes"], rows, header_h=20)
    p.section(MARGIN, b2 - 14, w, b2 - 14 - MARGIN - 20, "What surprised me")


def ws_calculator(p):
    c, t = p.c, p.t
    y = p.header("50/30/20 Calculator", "Month")
    w = p.inner
    p.section(MARGIN, y, w, 56, "My monthly take-home pay", lines=False, fill=True)
    c.setFont("Serif", 20)
    c.setFillColor(t["ink"])
    c.drawString(MARGIN + 14, y - 44, "$")
    p.rules(MARGIN + 30, y - 46, MARGIN + 220, y - 46)
    y -= 72
    buckets = [("Needs", "50%", "0.50", "Housing, utilities, groceries, transport, insurance, minimum debt payments"),
               ("Wants", "30%", "0.30", "Dining out, shopping, hobbies, entertainment, subscriptions, travel"),
               ("Savings & debt", "20%", "0.20", "Emergency fund, extra debt payments, retirement, savings goals")]
    bh = (y - MARGIN - 20 - 2 * 12 - 110) / 3
    for name, pct, mult, examples in buckets:
        p.section(MARGIN, y, w, bh, f"{name}  ·  {pct}", lines=False)
        c.setFont("Sans", 8.5)
        c.setFillColor(t["accent"])
        c.drawString(MARGIN + 12, y - 36, examples)
        c.setFont("Sans", 10)
        c.setFillColor(t["ink"])
        c.drawString(MARGIN + 12, y - 60, f"Take-home  $__________  ×  {mult}  =  target  $__________")
        c.drawString(MARGIN + 12, y - 84, "My actual amount  $__________      My actual %  ________")
        p.rules(MARGIN + 12, y - 108, MARGIN + w - 12, y - bh + 8, 20)
        y -= bh + 12
    p.section(MARGIN, y, w, y - MARGIN - 20, "What I'll adjust first")


def ws_debt_list(p):
    c, t = p.c, p.t
    y = p.header("Debt List", "Date")
    w = p.inner
    rows = 12
    b = p.table(MARGIN, y, [w * 0.28, w * 0.15, w * 0.1, w * 0.15, w * 0.16, w * 0.16],
                ["Creditor", "Balance", "Rate", "Minimum", "Snowball #", "Avalanche #"], rows, row_h=24, header_h=20)
    y = b - 16
    half = (w - 15) / 2
    p.section(MARGIN, y, half, 110, "Totals", lines=False, fill=True)
    c.setFont("Sans", 9)
    c.setFillColor(t["ink"])
    for i, row in enumerate(["Total debt", "Total minimums", "Extra per month"]):
        yy = y - 44 - i * 26
        c.drawString(MARGIN + 12, yy, row)
        p.rules(MARGIN + half * 0.5, yy - 2, MARGIN + half - 12, yy - 2)
    x = MARGIN + half + 15
    p.section(x, y, half, 110, "My method", lines=False)
    for i, m in enumerate(["Snowball (smallest balance first)", "Avalanche (highest rate first)"]):
        p.checkbox(x + 12, y - 48 - i * 26)
        c.drawString(x + 28, y - 46 - i * 26, m)
    y -= 126
    p.section(MARGIN, y, w, y - MARGIN - 20, "Why I'm becoming debt-free")


def ws_sinking(p):
    c, t = p.c, p.t
    y = p.header("Sinking Funds", "Year")
    w = p.inner
    c.setFont("Sans", 9)
    c.setFillColor(t["ink"])
    c.drawString(MARGIN, y, "Cost ÷ months until due = amount to save each month.")
    y -= 16
    rows = 14
    b = p.table(MARGIN, y, [w * 0.3, w * 0.14, w * 0.14, w * 0.1, w * 0.16, w * 0.16],
                ["Expense", "Total cost", "Due date", "Months", "Save monthly", "Saved so far"],
                rows, row_h=26, header_h=20)
    y = b - 16
    p.section(MARGIN, y, w, 60, "Total to save each month", lines=False, fill=True)
    c.setFont("Serif", 20)
    c.setFillColor(t["ink"])
    c.drawString(MARGIN + 14, y - 46, "$")
    p.rules(MARGIN + 30, y - 48, MARGIN + 220, y - 48)
    y -= 76
    p.section(MARGIN, y, w, y - MARGIN - 20, "Notes")


def ws_money_date(p):
    y = p.header("Money Date Checklist", "Date")
    w = p.inner
    half = (w - 15) / 2
    weekly = ["Record this week's spending", "Compare spending to budget", "Move money between categories",
              "Check upcoming bills", "Transfer to savings"]
    monthly = ["Review last month's budget", "Update debt balances", "Update savings totals",
               "Plan next month's budget", "Add birthdays, holidays & bills due", "Celebrate one win"]
    h = 40 + 24 * len(monthly)
    for x, title, items in ((MARGIN, "Weekly check-in · 10 min", weekly),
                            (MARGIN + half + 15, "Monthly money date · 30 min", monthly)):
        p.section(x, y, half, h, title, lines=False)
        c = p.c
        c.setFont("Sans", 9.5)
        c.setFillColor(p.t["ink"])
        for i, item in enumerate(items):
            p.checkbox(x + 12, y - 44 - i * 24)
            c.drawString(x + 28, y - 42 - i * 24, item)
    y -= h + 14
    bh = (y - MARGIN - 20 - 14) / 2
    p.section(MARGIN, y, half, bh, "Wins this month")
    p.section(MARGIN + half + 15, y, half, bh, "What surprised me")
    p.section(MARGIN, y - bh - 14, w, bh, "Next month's focus")


WORKSHEETS = {
    "snapshot": ws_snapshot, "calculator": ws_calculator, "debt_list": ws_debt_list,
    "sinking": ws_sinking, "money_date": ws_money_date,
    "budget": Planner.budget, "expenses": Planner.expenses, "debt": Planner.debt,
    "savings": Planner.savings, "notes_lined": Planner.notes_lined,
}
WORKSHEET_TITLES = {
    "snapshot": "Income & Expenses Snapshot", "calculator": "50/30/20 Calculator",
    "debt_list": "Debt List", "sinking": "Sinking Funds", "money_date": "Money Date Checklist",
    "budget": "Monthly Budget", "expenses": "Expense Tracker", "debt": "Debt Payoff Tracker",
    "savings": "Savings Challenge", "notes_lined": "Notes",
}


# ---------- document ----------

class Guide(BaseDocTemplate):
    def __init__(self, path, meta, size, theme):
        self.meta, self.size, self.theme = meta, size, theme
        self.t = {k: HexColor(v) for k, v in THEMES[theme].items()}
        super().__init__(path, pagesize=size, title=meta["title"], author=SHOP,
                         leftMargin=MARGIN + 22, rightMargin=MARGIN + 22,
                         topMargin=MARGIN + 30, bottomMargin=MARGIN + 20)
        w, h = size
        body = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        full = Frame(0, 0, w, h, id="full")
        self.addPageTemplates([PageTemplate("cover", [full], onPage=self.draw_cover),
                               PageTemplate("body", [body], onPage=self.draw_body),
                               PageTemplate("worksheet", [full])])

    def draw_cover(self, c, doc):
        t, (w, h), m = self.t, self.size, self.meta
        c.saveState()
        c.setFillColor(t["soft"])
        c.rect(0, 0, w, h, stroke=0, fill=1)
        c.setFillColor(t["accent"])
        c.circle(w * 0.88, h * 0.9, 160, stroke=0, fill=1)
        c.setFillColor(t["line"])
        c.circle(w * 0.08, h * 0.1, 120, stroke=0, fill=1)
        c.setStrokeColor(t["accent"])
        c.rect(MARGIN, MARGIN, w - 2 * MARGIN, h - 2 * MARGIN, stroke=1, fill=0)
        c.setFillColor(t["accent"])
        c.setFont("SansBold", 10)
        c.drawCentredString(w / 2, h * 0.62, " ".join(m.get("kicker", "")))
        c.setFillColor(t["ink"])
        c.setFont("Serif", 46)
        words = m["title"].split()
        lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 3 else [m["title"]]
        for i, ln in enumerate(lines):
            c.drawCentredString(w / 2, h * 0.54 - i * 54, ln)
        yb = h * 0.54 - (len(lines) - 1) * 54
        c.setStrokeColor(t["accent"])
        c.line(w / 2 - 50, yb - 28, w / 2 + 50, yb - 28)
        c.setFont("SansItalic", 14)
        c.setFillColor(t["accent"])
        c.drawCentredString(w / 2, yb - 54, m.get("subtitle", ""))
        c.setFont("Sans", 10)
        c.setFillColor(t["ink"])
        c.drawCentredString(w / 2, MARGIN + 30, SHOP.upper())
        c.restoreState()

    def draw_body(self, c, doc):
        t, (w, h) = self.t, self.size
        c.saveState()
        c.setStrokeColor(t["line"])
        c.setLineWidth(0.6)
        c.line(MARGIN + 22, h - MARGIN - 8, w - MARGIN - 22, h - MARGIN - 8)
        c.setFont("Sans", 7.5)
        c.setFillColor(t["accent"])
        c.drawString(MARGIN + 22, h - MARGIN, self.meta["title"].upper())
        c.drawRightString(w - MARGIN - 22, h - MARGIN, SHOP.upper())
        c.setFillColor(t["ink"])
        c.setFont("Sans", 9)
        c.drawCentredString(w / 2, MARGIN - 6, str(doc.page))
        c.restoreState()

    def afterFlowable(self, f):
        key = None
        if isinstance(f, Paragraph) and getattr(f, "toc_title", None):
            key, level, title = f"ch{self.seq}", 0, f.toc_title
        elif isinstance(f, Worksheet):
            key, level, title = f"ws{self.seq}", 1, f.title
        if key:
            self.seq += 1
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level)
            self.notify("TOCEntry", (level, title, self.page, key))

    def handle_documentBegin(self):
        self.seq = 0
        super().handle_documentBegin()


def styles(t):
    base = ParagraphStyle("body", fontName="Sans", fontSize=10.5, leading=15.5, textColor=t["ink"],
                          spaceAfter=8)
    return {
        "body": base,
        "kicker": ParagraphStyle("kicker", fontName="SansBold", fontSize=10, leading=12,
                                 textColor=t["accent"], spaceAfter=4),
        "h1": ParagraphStyle("h1", fontName="Serif", fontSize=32, leading=38, textColor=t["ink"],
                             spaceAfter=18),
        "h2": ParagraphStyle("h2", fontName="Serif", fontSize=17, leading=22, textColor=t["ink"],
                             spaceBefore=10, spaceAfter=6),
        "li": ParagraphStyle("li", parent=base, spaceAfter=4),
        "cell": ParagraphStyle("cell", fontName="Sans", fontSize=9.5, leading=12.5, textColor=t["ink"]),
        "cellhead": ParagraphStyle("cellhead", fontName="SansBold", fontSize=8.5, leading=11, textColor=white),
        "callout": ParagraphStyle("callout", parent=base, fontSize=10.5, leading=15.5, spaceAfter=0),
        "toc0": ParagraphStyle("toc0", fontName="Sans", fontSize=12, leading=14, textColor=t["ink"],
                               spaceBefore=2),
        "toc1": ParagraphStyle("toc1", fontName="Sans", fontSize=10, leading=12.5, textColor=t["ink"],
                               leftIndent=22, spaceBefore=1),
    }


def build(src, theme="sage", size="letter"):
    meta, blocks = parse(src)
    path = os.path.join(OUT, f"{meta['file']}_{theme}_{size.upper()}.pdf")
    doc = Guide(path, meta, SIZES[size], theme)
    t, st = doc.t, styles(doc.t)

    toc = TableOfContents(dotsMinLevel=0)
    toc.levelStyles = [st["toc0"], st["toc1"]]
    story = [Spacer(1, 1), NextPageTemplate("body"), PageBreak(),
             Paragraph("Contents", st["h1"]), toc]

    bullets = []

    def flush_bullets():
        if bullets:
            story.append(ListFlowable([ListItem(Paragraph(inline(b), st["li"]), leftIndent=16,
                                                value="•") for b in bullets],
                                      bulletType="bullet", bulletColor=t["accent"], leftIndent=16,
                                      spaceAfter=8))
            bullets.clear()

    chapter = 0
    for kind, val in blocks:
        if kind != "li":
            flush_bullets()
        if kind == "h1":
            story += [NextPageTemplate("body"), PageBreak()]
            m = re.match(r"(Step \d+):\s*(.+)", val)
            if m:
                story.append(Paragraph(m.group(1).upper(), st["kicker"]))
                title = m.group(2)
            else:
                title = val
            para = Paragraph(inline(title), st["h1"])
            para.toc_title = val
            story.append(para)
        elif kind == "h2":
            story += [CondPageBreak(90), Paragraph(inline(val), st["h2"])]
        elif kind == "p":
            story.append(Paragraph(inline(val), st["body"]))
        elif kind == "li":
            bullets.append(val)
        elif kind == "check":
            story.append(Check(val, st["li"], t["accent"]))
        elif kind == "callout":
            label, _, body = val.partition(":")
            cell = Paragraph(f'<font name="SansBold" color="#{t["accent"].hexval()[2:]}">'
                             f"{label.strip()}</font>&nbsp;&nbsp;{inline(body.strip())}", st["callout"])
            box = Table([[cell]], colWidths=[doc.width])
            box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), t["soft"]),
                ("LINEBEFORE", (0, 0), (0, -1), 3, t["accent"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
            story += [Spacer(1, 4), box, Spacer(1, 12)]
        elif kind == "table":
            rows = [[Paragraph(inline(c), st["cellhead"] if i == 0 else st["cell"]) for c in r]
                    for i, r in enumerate(val)]
            tbl = Table(rows, colWidths=[doc.width / len(val[0])] * len(val[0]), repeatRows=1)
            style = [("BACKGROUND", (0, 0), (-1, 0), t["accent"]),
                     ("LINEBELOW", (0, 1), (-1, -1), 0.5, t["line"]),
                     ("BOX", (0, 0), (-1, -1), 0.6, t["line"]),
                     ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                     ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
            for r in range(2, len(rows), 2):
                style.append(("BACKGROUND", (0, r), (-1, r), t["soft"]))
            tbl.setStyle(TableStyle(style))
            story += [Spacer(1, 4), KeepTogether(tbl) if len(rows) < 12 else tbl, Spacer(1, 12)]
        elif kind == "worksheet":
            story += [NextPageTemplate("worksheet"), PageBreak(), Worksheet(doc, val)]
    flush_bullets()
    doc.multiBuild(story)
    return path, meta


def listing_images(pdf_path, meta, theme):
    """Etsy listing photos (2700x2025): cover hero, sample pages, worksheets."""
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont

    out_dir = os.path.join(OUT, "listing-photos", f"{meta['file']}-{theme}")
    os.makedirs(out_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    t = THEMES[theme]
    W, H = 2700, 2025
    serif = lambda n: ImageFont.truetype(os.path.join(HERE, "fonts", "PlayfairDisplay-VF.ttf"), n)
    sans = lambda n: ImageFont.truetype(os.path.join(HERE, "fonts", "Lato-Bold.ttf"), n)
    toc = doc.get_toc()
    first = {title: page - 1 for _, title, page in toc}
    worksheets = [page - 1 for lvl, _, page in toc if lvl == 2]

    def page_img(i, height):
        pix = doc[i].get_pixmap(dpi=200)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)

    def paste(bg, im, x, y):
        bg.paste(Image.new("RGB", im.size, t["line"]), (x + 10, y + 10))
        bg.paste(im, (x, y))

    n_pages = len(doc)
    n_ws = len(worksheets)

    # 1. hero
    bg = Image.new("RGB", (W, H), t["soft"])
    d = ImageDraw.Draw(bg)
    for i, x in ((first["Step 3: Build Your First Budget"], 1480), (worksheets[1], 1160)):
        paste(bg, page_img(i, 1500), x, 330)
    paste(bg, page_img(0, 1650), 180, 190)
    d.rectangle((0, H - 170, W, H), fill=t["accent"])
    d.text((W / 2, H - 85), f"{n_pages}-PAGE GUIDE  ·  {n_ws} WORKSHEETS  ·  INSTANT DOWNLOAD",
           font=sans(62), fill="white", anchor="mm")
    bg.save(os.path.join(out_dir, "01-hero.jpg"), quality=92)

    # 2. inside the guide: chapter openers
    bg = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(bg)
    d.text((W / 2, 140), "8 Simple Steps", font=serif(120), fill=t["ink"], anchor="mm")
    chapters = [page - 1 for lvl, title, page in toc if lvl == 1 and title.startswith("Step")]
    cols, ph = 4, 800
    cw = (W - 180) // cols
    for k, i in enumerate(chapters[:8]):
        im = page_img(i, ph)
        paste(bg, im, 90 + (k % cols) * cw + (cw - im.width) // 2, 270 + (k // cols) * (ph + 50))
    bg.save(os.path.join(out_dir, "02-eight-steps.jpg"), quality=92)

    # 3. worksheets grid
    bg = Image.new("RGB", (W, H), t["soft"])
    d = ImageDraw.Draw(bg)
    d.text((W / 2, 140), f"{n_ws} Printable Worksheets", font=serif(120), fill=t["ink"], anchor="mm")
    cols, ph = 5, 800
    cw = (W - 180) // cols
    for k, i in enumerate(worksheets[:10]):
        im = page_img(i, ph)
        paste(bg, im, 90 + (k % cols) * cw + (cw - im.width) // 2, 270 + (k // cols) * (ph + 50))
    bg.save(os.path.join(out_dir, "03-worksheets.jpg"), quality=92)

    # 4-5. close-ups
    for n, (i, title, sub) in enumerate((
            (first["Step 3: Build Your First Budget"], "Real Examples", ["Step-by-step budget", "with real numbers"]),
            (first["Your 30-Day Quick-Start Plan"], "30-Day Plan", ["A simple checklist to", "build your budget"])), start=4):
        bg = Image.new("RGB", (W, H), t["soft"])
        d = ImageDraw.Draw(bg)
        paste(bg, page_img(i, 1800), 1250, 110)
        d.text((150, 700), title, font=serif(130), fill=t["ink"])
        for j, line in enumerate(sub):
            d.text((155, 900 + j * 80), line, font=sans(60), fill=t["accent"])
        bg.save(os.path.join(out_dir, f"0{n}-{title.lower().replace(' ', '-')}.jpg"), quality=92)
    return out_dir


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--theme", choices=THEMES, default="sage")
    ap.add_argument("--size", choices=SIZES, action="append")
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()
    src = args.source if os.path.isabs(args.source) else os.path.join(HERE, args.source)
    os.makedirs(OUT, exist_ok=True)
    for size in args.size or SIZES:
        path, meta = build(src, args.theme, size)
        import pymupdf
        print(f"{path}  ({len(pymupdf.open(path))} pages, {os.path.getsize(path) // 1024} KB)")
        if not args.no_images and size == "letter":
            print("  photos:", listing_images(path, meta, args.theme))


if __name__ == "__main__":
    main()
