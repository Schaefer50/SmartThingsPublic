#!/usr/bin/env python3
"""Build the "Undated Life & Budget Planner" printable bundle for Etsy.

Produces one PDF per (theme, paper size) in pdf-products/output/, plus Etsy
listing photos in pdf-products/output/listing-photos/<theme>/.

    pip install reportlab pymupdf pillow
    python3 pdf-products/build_planner.py            # all themes, all sizes
    python3 pdf-products/build_planner.py --theme sage --size letter
"""

import argparse
import os

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")

PRODUCT = "Undated Life & Budget Planner"
SHOP = "Tucker Technologies"

THEMES = {
    "sage": {"accent": "#7D9A83", "soft": "#E6EDE7", "ink": "#3E4A42", "line": "#C9D3CB"},
    "blush": {"accent": "#C98B8B", "soft": "#F6E7E5", "ink": "#4A3E3E", "line": "#E2CFCD"},
    "neutral": {"accent": "#A48E74", "soft": "#F1EBE3", "ink": "#453D35", "line": "#DAD0C4"},
}
SIZES = {"letter": LETTER, "a4": A4}

pdfmetrics.registerFont(TTFont("Serif", os.path.join(HERE, "fonts", "PlayfairDisplay-VF.ttf")))
pdfmetrics.registerFont(TTFont("Sans", os.path.join(HERE, "fonts", "Lato-Regular.ttf")))
pdfmetrics.registerFont(TTFont("SansBold", os.path.join(HERE, "fonts", "Lato-Bold.ttf")))

MARGIN = 40


class Planner:
    def __init__(self, path, size, theme, product=PRODUCT, canv=None):
        """Draw to a new PDF at `path`, or onto an existing canvas `canv`."""
        self.product = product
        self.c = canv or canvas.Canvas(path, pagesize=size)
        self.c.setTitle(product)
        self.c.setAuthor(SHOP)
        self.w, self.h = size
        self.t = {k: HexColor(v) for k, v in theme.items()}
        self.toc = []

    # ---------- drawing helpers ----------
    def header(self, title, subtitle=None):
        """Page title with a fill-in field. Returns the y below the header."""
        c, t = self.c, self.t
        c.setFillColor(t["ink"])
        c.setFont("Serif", 26)
        c.drawString(MARGIN, self.h - MARGIN - 22, title)
        c.setStrokeColor(t["accent"])
        c.setLineWidth(1.2)
        c.line(MARGIN, self.h - MARGIN - 34, self.w - MARGIN, self.h - MARGIN - 34)
        if subtitle:
            c.setFont("Sans", 8.5)
            c.setFillColor(t["accent"])
            label = subtitle.upper()
            lw = c.stringWidth(label, "Sans", 8.5)
            x = self.w - MARGIN - 130
            c.drawString(x - lw - 6, self.h - MARGIN - 20, label)
            c.setStrokeColor(t["line"])
            c.setLineWidth(0.7)
            c.line(x, self.h - MARGIN - 22, self.w - MARGIN, self.h - MARGIN - 22)
            # dated planners pre-fill the field (e.g. the month name)
            if getattr(self, "fill_text", None):
                c.setFont("Serif", 12)
                c.setFillColor(t["ink"])
                c.drawString(x + 6, self.h - MARGIN - 19, self.fill_text)
        return self.h - MARGIN - 52

    def label(self, x, y, text, color=None):
        self.c.setFont("SansBold", 8)
        self.c.setFillColor(color or self.t["accent"])
        self.c.drawString(x, y, text.upper())

    def section(self, x, y, w, h, title, lines=True, spacing=20, fill=False):
        """A titled box, optionally ruled."""
        c, t = self.c, self.t
        if fill:
            c.setFillColor(t["soft"])
            c.roundRect(x, y - h, w, h, 6, stroke=0, fill=1)
        c.setStrokeColor(t["line"])
        c.setLineWidth(0.8)
        c.roundRect(x, y - h, w, h, 6, stroke=1, fill=0)
        c.setFillColor(t["soft"])
        c.roundRect(x, y - 20, w, 20, 6, stroke=0, fill=1)
        c.rect(x, y - 20, w, 8, stroke=0, fill=1)
        self.label(x + 10, y - 14, title, t["ink"])
        if lines:
            self.rules(x + 10, y - 20 - spacing, x + w - 10, y - h + 6, spacing)

    def rules(self, x1, y_top, x2, y_bottom, spacing=20):
        self.c.setStrokeColor(self.t["line"])
        self.c.setLineWidth(0.5)
        y = y_top
        while y >= y_bottom:
            self.c.line(x1, y, x2, y)
            y -= spacing

    def checkbox(self, x, y, s=8):
        self.c.setStrokeColor(self.t["accent"])
        self.c.setLineWidth(0.8)
        self.c.roundRect(x, y, s, s, 1.5, stroke=1, fill=0)

    def checklist(self, x1, y_top, x2, y_bottom, spacing=20):
        self.rules(x1 + 14, y_top, x2, y_bottom, spacing)
        y = y_top
        while y >= y_bottom:
            self.checkbox(x1, y + 2)
            y -= spacing

    def table(self, x, y, widths, headers, rows, row_h=20, header_h=None):
        """Header row + empty rows. Returns bottom y."""
        c, t = self.c, self.t
        hh = header_h or row_h
        total = sum(widths)
        c.setFillColor(t["accent"])
        c.roundRect(x, y - hh, total, hh, 4, stroke=0, fill=1)
        c.setFont("SansBold", 7.5)
        c.setFillColor(HexColor("#FFFFFF"))
        cx = x
        for wd, hd in zip(widths, headers):
            c.drawCentredString(cx + wd / 2, y - hh / 2 - 2.5, hd.upper())
            cx += wd
        c.setStrokeColor(t["line"])
        c.setLineWidth(0.5)
        for r in range(1, rows + 1):
            ry = y - hh - row_h * r
            if r % 2 == 0:
                c.setFillColor(t["soft"])
                c.rect(x, ry, total, row_h, stroke=0, fill=1)
            c.line(x, ry, x + total, ry)
        bottom = y - hh - row_h * rows
        cx = x
        for wd in widths[:-1]:
            cx += wd
            c.line(cx, y - hh, cx, bottom)
        c.rect(x, bottom, total, y - bottom, stroke=1, fill=0)
        return bottom

    def footer(self):
        c = self.c
        c.setFont("Sans", 7)
        c.setFillColor(self.t["line"])
        c.drawCentredString(self.w / 2, 18, f"{self.product}  ·  {SHOP}  ·  For personal use only")

    @property
    def inner(self):
        return self.w - 2 * MARGIN

    # ---------- pages ----------
    def cover(self):
        c, t = self.c, self.t
        c.setFillColor(t["soft"])
        c.rect(0, 0, self.w, self.h, stroke=0, fill=1)
        c.setFillColor(t["accent"])
        c.circle(self.w * 0.85, self.h * 0.88, 150, stroke=0, fill=1)
        c.setFillColor(t["line"])
        c.circle(self.w * 0.1, self.h * 0.12, 110, stroke=0, fill=1)
        c.setStrokeColor(t["accent"])
        c.setLineWidth(1)
        c.rect(MARGIN, MARGIN, self.w - 2 * MARGIN, self.h - 2 * MARGIN, stroke=1, fill=0)
        c.setFillColor(t["ink"])
        c.setFont("Sans", 11)
        c.drawCentredString(self.w / 2, self.h * 0.60, "U N D A T E D")
        c.setFont("Serif", 50)
        c.drawCentredString(self.w / 2, self.h * 0.52, "Life & Budget")
        c.drawCentredString(self.w / 2, self.h * 0.52 - 58, "Planner")
        c.setStrokeColor(t["accent"])
        c.line(self.w / 2 - 50, self.h * 0.52 - 82, self.w / 2 + 50, self.h * 0.52 - 82)
        c.setFont("Sans", 11)
        c.setFillColor(t["accent"])
        c.drawCentredString(self.w / 2, self.h * 0.52 - 104, "PLAN  ·  SAVE  ·  GROW")
        c.setFont("Sans", 10)
        c.setFillColor(t["ink"])
        c.drawCentredString(self.w / 2, self.h * 0.26, "This planner belongs to")
        c.setStrokeColor(t["ink"])
        c.setLineWidth(0.6)
        c.line(self.w / 2 - 110, self.h * 0.26 - 30, self.w / 2 + 110, self.h * 0.26 - 30)

    def contents(self):
        c, t = self.c, self.t
        y = self.header("Contents")
        c.setFont("Sans", 9)
        c.setFillColor(t["ink"])
        c.drawString(MARGIN, y, "Tap any section to jump to it. Print the pages you need as many times as you like.")
        y -= 30
        for i, (name, key) in enumerate(self.toc[2:], start=1):
            c.setFillColor(t["accent"])
            c.setFont("Serif", 16)
            c.drawString(MARGIN, y, f"{i:02d}")
            c.setFillColor(t["ink"])
            c.setFont("Sans", 12)
            c.drawString(MARGIN + 40, y, name)
            c.setStrokeColor(t["line"])
            c.setDash(1, 3)
            c.line(MARGIN + 50 + c.stringWidth(name, "Sans", 12), y + 3, self.w - MARGIN, y + 3)
            c.setDash()
            c.linkRect("", key, (MARGIN, y - 6, self.w - MARGIN, y + 16), relative=0)
            y -= 34

    def goals(self):
        y = self.header("Yearly Goals", "Year")
        half = (self.inner - 15) / 2
        areas = ["Health & Fitness", "Money & Career", "Relationships", "Personal Growth",
                 "Home & Lifestyle", "Fun & Adventure"]
        bh = (y - MARGIN - 20 - 150) / 3
        for i, area in enumerate(areas):
            col, row = i % 2, i // 2
            self.section(MARGIN + col * (half + 15), y - row * (bh + 12), half, bh, area)
        yb = y - 3 * (bh + 12)
        self.section(MARGIN, yb, self.inner, 138, "My word for the year & why")

    def monthly_calendar(self):
        c, t = self.c, self.t
        y = self.header("Monthly Calendar", "Month")
        days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        cw = self.inner / 7
        notes_h = 110
        ch = (y - 22 - MARGIN - 20 - notes_h - 12) / 6
        c.setFillColor(t["accent"])
        c.roundRect(MARGIN, y - 20, self.inner, 20, 4, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.setFont("SansBold", 8)
        for i, d in enumerate(days):
            c.drawCentredString(MARGIN + cw * i + cw / 2, y - 14, d)
        top = y - 22
        c.setStrokeColor(t["line"])
        c.setLineWidth(0.6)
        for r in range(6):
            for col in range(7):
                x0, y0 = MARGIN + col * cw, top - (r + 1) * ch
                if col >= 5:
                    c.setFillColor(t["soft"])
                    c.rect(x0, y0, cw, ch, stroke=0, fill=1)
                c.rect(x0, y0, cw, ch, stroke=1, fill=0)
                c.circle(x0 + 11, y0 + ch - 11, 7, stroke=1, fill=0)
        self.section(MARGIN, top - 6 * ch - 12, self.inner, notes_h, "Notes & priorities")

    def weekly(self):
        y = self.header("Weekly Planner", "Week of")
        half = (self.inner - 15) / 2
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        bh = (y - MARGIN - 20 - 3 * 10) / 4
        for i, d in enumerate(days):
            col, row = i % 2, i // 2
            self.section(MARGIN + col * (half + 15), y - row * (bh + 10), half, bh, d, spacing=18)
        x = MARGIN + half + 15
        yy = y - 3 * (bh + 10)
        self.section(x, yy, half, bh, "Top priorities", lines=False)
        self.checklist(x + 10, yy - 38, x + half - 10, yy - bh + 6, 18)

    def daily(self):
        c = self.c
        y = self.header("Daily Planner", "Date")
        left = self.inner * 0.58
        right = self.inner - left - 15
        rx = MARGIN + left + 15
        h = y - MARGIN - 20
        self.section(MARGIN, y, left, h, "Schedule", lines=False)
        c.setFont("Sans", 8)
        c.setFillColor(self.t["accent"])
        slot = (h - 30) / 16
        for i in range(16):
            yy = y - 30 - i * slot
            hour = 6 + i
            c.drawRightString(MARGIN + 40, yy - 4, f"{(hour - 1) % 12 + 1}{'am' if hour < 12 else 'pm'}")
            self.rules(MARGIN + 48, yy - 6, MARGIN + left - 10, yy - 6)
        th = (h - 36) / 4
        self.section(rx, y, right, th, "Top 3 today", lines=False)
        self.checklist(rx + 10, y - 40, rx + right - 10, y - th + 8, 24)
        self.section(rx, y - th - 12, right, th, "To do", lines=False)
        self.checklist(rx + 10, y - th - 50, rx + right - 10, y - 2 * th - 4, 18)
        self.section(rx, y - 2 * (th + 12), right, th, "Meals & water")
        self.section(rx, y - 3 * (th + 12), right, th, "Grateful for")

    def habits(self):
        c, t = self.c, self.t
        y = self.header("Habit Tracker", "Month")
        name_w = 120
        cols = 31
        cell = (self.inner - name_w) / cols
        rows = 15
        rh = min(cell * 1.6, (y - MARGIN - 180) / (rows + 1))
        c.setFont("SansBold", 6.5)
        c.setFillColor(t["accent"])
        c.roundRect(MARGIN, y - rh, self.inner, rh, 4, stroke=0, fill=1)
        c.setFillColor(HexColor("#FFFFFF"))
        c.drawString(MARGIN + 8, y - rh / 2 - 2, "HABIT")
        for d in range(cols):
            c.drawCentredString(MARGIN + name_w + cell * d + cell / 2, y - rh / 2 - 2, str(d + 1))
        c.setStrokeColor(t["line"])
        c.setLineWidth(0.5)
        for r in range(rows):
            ry = y - rh * (r + 2)
            if r % 2:
                c.setFillColor(t["soft"])
                c.rect(MARGIN, ry, self.inner, rh, stroke=0, fill=1)
            c.rect(MARGIN, ry, name_w, rh, stroke=1, fill=0)
            for d in range(cols):
                c.circle(MARGIN + name_w + cell * d + cell / 2, ry + rh / 2, min(cell, rh) * 0.3, stroke=1, fill=0)
        c.rect(MARGIN, y - rh * (rows + 1), self.inner, rh * (rows + 1), stroke=1, fill=0)
        yb = y - rh * (rows + 1) - 15
        half = (self.inner - 15) / 2
        self.section(MARGIN, yb, half, yb - MARGIN - 20, "Wins this month")
        self.section(MARGIN + half + 15, yb, half, yb - MARGIN - 20, "What to adjust")

    def mood(self):
        c, t = self.c, self.t
        y = self.header("Mood & Sleep Log", "Month")
        widths = [40, 110, 70, 70, self.inner - 290]
        self.table(MARGIN, y, widths, ["Day", "Mood (1-5)", "Sleep hrs", "Energy", "Note"], 31,
                   row_h=(y - MARGIN - 30) / 32)
        c.setFont("Sans", 7.5)
        c.setFillColor(t["ink"])
        rh = (y - MARGIN - 30) / 32
        for d in range(31):
            c.drawCentredString(MARGIN + 20, y - rh * (d + 2) + rh / 2 - 3, str(d + 1))

    def budget(self):
        y = self.header("Monthly Budget", "Month")
        half = (self.inner - 15) / 2
        rx = MARGIN + half + 15
        # income + summary
        b = self.table(MARGIN, y, [half * 0.6, half * 0.4], ["Income source", "Amount"], 5)
        self.section(rx, y, half, y - b, "Summary", lines=False, fill=True)
        c = self.c
        c.setFont("Sans", 9)
        c.setFillColor(self.t["ink"])
        for i, row in enumerate(["Total income", "Total expenses", "Savings", "Left over"]):
            yy = y - 38 - i * ((y - b - 30) / 4)
            c.drawString(rx + 12, yy, row)
            self.rules(rx + half * 0.55, yy - 2, rx + half - 12, yy - 2)
        y2 = b - 15
        cats = [("Housing & bills", 7), ("Food & household", 5), ("Transport", 4),
                ("Personal & fun", 9), ("Debt & savings", 8)]
        avail = y2 - MARGIN - 20
        col_left = cats[:3]
        col_right = cats[3:]
        rh_l = (avail - 35 * len(col_left) + 15) / sum(n for _, n in col_left)
        rh_r = (avail - 35 * len(col_right) + 15) / sum(n for _, n in col_right)
        for colx, group, rh in ((MARGIN, col_left, rh_l), (rx, col_right, rh_r)):
            yy = y2
            for name, n in group:
                yy = self.table(colx, yy, [half * 0.5, half * 0.25, half * 0.25],
                                [name, "Budget", "Actual"], n, row_h=rh, header_h=20) - 15

    def expenses(self):
        y = self.header("Expense Tracker", "Month")
        w = self.inner
        rows = int((y - MARGIN - 30) / 20) - 1
        self.table(MARGIN, y, [w * 0.12, w * 0.43, w * 0.25, w * 0.2],
                   ["Date", "Description", "Category", "Amount"], rows)

    def bills(self):
        c, t = self.c, self.t
        y = self.header("Bill Payment Tracker", "Year")
        name_w = 110
        due_w = 40
        mw = (self.inner - name_w - due_w) / 12
        months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
        widths = [name_w, due_w] + [mw] * 12
        rows = int((y - MARGIN - 30) / 24) - 1
        self.table(MARGIN, y, widths, ["Bill", "Due"] + months, rows, row_h=24)
        c.setStrokeColor(t["accent"])
        for r in range(rows):
            for m in range(12):
                self.checkbox(MARGIN + name_w + due_w + mw * m + mw / 2 - 4, y - 24 * (r + 2) + 8)

    def savings(self):
        c, t = self.c, self.t
        y = self.header("Savings Challenge", "Goal")
        c.setFont("Sans", 9)
        c.setFillColor(t["ink"])
        c.drawString(MARGIN, y, "Saving for: ______________________      Total: $5,050      Color in each amount as you save it.")
        y -= 20
        cols, rows = 10, 10
        cell = min(self.inner / cols, (y - MARGIN - 140) / rows)
        x0 = MARGIN + (self.inner - cell * cols) / 2
        c.setFont("Sans", 8)
        for r in range(rows):
            for col in range(cols):
                n = r * cols + col + 1
                cx, cy = x0 + col * cell + cell / 2, y - r * cell - cell / 2
                c.setStrokeColor(t["accent"])
                c.setFillColor(t["soft"] if (r + col) % 2 else HexColor("#FFFFFF"))
                c.circle(cx, cy, cell * 0.42, stroke=1, fill=1)
                c.setFillColor(t["ink"])
                c.drawCentredString(cx, cy - 3, f"${n}")
        yb = y - rows * cell - 15
        self.section(MARGIN, yb, self.inner, yb - MARGIN - 20, "Deposit log", spacing=18)

    def debt(self):
        y = self.header("Debt Payoff Tracker", "Debt")
        c, t = self.c, self.t
        half = (self.inner - 15) / 2
        self.section(MARGIN, y, half, 90, "Creditor / balance / rate", spacing=22)
        self.section(MARGIN + half + 15, y, half, 90, "Why I'm paying this off", spacing=22)
        y -= 105
        # payoff thermometer: 20 bars
        c.setFont("Sans", 8)
        bar_w = self.inner / 20
        for i in range(20):
            c.setStrokeColor(t["accent"])
            c.setFillColor(t["soft"])
            c.roundRect(MARGIN + i * bar_w + 2, y - 40, bar_w - 4, 40, 3, stroke=1, fill=1)
            c.setFillColor(t["ink"])
            c.drawCentredString(MARGIN + i * bar_w + bar_w / 2, y - 52, f"{(i + 1) * 5}%")
        y -= 70
        w = self.inner
        rows = int((y - MARGIN - 30) / 20) - 1
        self.table(MARGIN, y, [w * 0.15, w * 0.25, w * 0.2, w * 0.2, w * 0.2],
                   ["Date", "Payment", "Interest", "Principal", "Balance"], rows)

    def meals(self):
        y = self.header("Meal Planner", "Week of")
        w = self.inner
        left = w * 0.66
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        dw = 44
        mw = (left - dw) / 3
        hh = 20
        rh = (y - hh - MARGIN - 20) / 7
        self.table(MARGIN, y, [dw, mw, mw, mw], ["", "Breakfast", "Lunch", "Dinner"], 7, row_h=rh, header_h=hh)
        c = self.c
        c.setFont("SansBold", 8)
        c.setFillColor(self.t["accent"])
        for i, d in enumerate(days):
            c.drawCentredString(MARGIN + dw / 2, y - hh - rh * (i + 1) + rh / 2 - 3, d.upper())
        rx = MARGIN + left + 15
        rw = w - left - 15
        self.section(rx, y, rw, y - MARGIN - 20, "Grocery list", lines=False)
        self.checklist(rx + 10, y - 40, rx + rw - 10, MARGIN + 28, 20)

    def cleaning(self):
        y = self.header("Cleaning Schedule", "Week of")
        half = (self.inner - 15) / 2
        blocks = ["Daily", "Weekly", "Monthly", "Seasonal"]
        bh = (y - MARGIN - 20 - 12) / 2
        for i, b in enumerate(blocks):
            col, row = i % 2, i // 2
            x = MARGIN + col * (half + 15)
            yy = y - row * (bh + 12)
            self.section(x, yy, half, bh, b, lines=False)
            self.checklist(x + 10, yy - 40, x + half - 10, yy - bh + 8, 20)

    def notes_lined(self):
        y = self.header("Notes")
        self.rules(MARGIN, y - 10, self.w - MARGIN, MARGIN + 20, 22)

    def notes_dots(self):
        c = self.c
        y = self.header("Dot Grid")
        c.setFillColor(self.t["line"])
        s = 14.17  # 5 mm
        yy = y - 10
        while yy >= MARGIN + 20:
            xx = MARGIN
            while xx <= self.w - MARGIN:
                c.circle(xx, yy, 0.8, stroke=0, fill=1)
                xx += s
            yy -= s

    def build(self):
        pages = [
            ("Cover", self.cover),
            ("Contents", None),
            ("Yearly Goals", self.goals),
            ("Monthly Calendar", self.monthly_calendar),
            ("Weekly Planner", self.weekly),
            ("Daily Planner", self.daily),
            ("Habit Tracker", self.habits),
            ("Mood & Sleep Log", self.mood),
            ("Monthly Budget", self.budget),
            ("Expense Tracker", self.expenses),
            ("Bill Payment Tracker", self.bills),
            ("Savings Challenge", self.savings),
            ("Debt Payoff Tracker", self.debt),
            ("Meal Planner", self.meals),
            ("Cleaning Schedule", self.cleaning),
            ("Lined Notes", self.notes_lined),
            ("Dot Grid", self.notes_dots),
        ]
        # contents links need every bookmark key; they resolve at save time
        self.toc = [(name, f"p{i}") for i, (name, _) in enumerate(pages)]
        for i, (name, fn) in enumerate(pages):
            self.c.bookmarkPage(f"p{i}")
            self.c.addOutlineEntry(name, f"p{i}", level=0)
            (fn or self.contents)()
            if i:
                self.footer()
            self.c.showPage()
        self.c.save()
        return len(pages)


def listing_images(pdf_path, out_dir, theme):
    """Etsy listing photos (2700x2025, 4:3): hero cover, what's-inside grid, sizes."""
    try:
        import pymupdf
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("  (skip listing images: pip install pymupdf pillow)")
        return
    os.makedirs(out_dir, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    t = THEMES[theme]
    W, H = 2700, 2025
    serif = lambda n: ImageFont.truetype(os.path.join(HERE, "fonts", "PlayfairDisplay-VF.ttf"), n)
    sans = lambda n: ImageFont.truetype(os.path.join(HERE, "fonts", "Lato-Bold.ttf"), n)

    def page_img(i, height):
        pix = doc[i].get_pixmap(dpi=200)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)

    def shadowed(bg, im, x, y):
        bg.paste(Image.new("RGB", im.size, t["line"]), (x + 10, y + 10))
        bg.paste(im, (x, y))

    # 1. hero: cover + two inner pages fanned
    bg = Image.new("RGB", (W, H), t["soft"])
    d = ImageDraw.Draw(bg)
    for i, x in ((8, 1480), (4, 1160)):
        shadowed(bg, page_img(i, 1500), x, 330)
    shadowed(bg, page_img(0, 1650), 180, 190)
    d.rectangle((0, H - 170, W, H), fill=t["accent"])
    d.text((W / 2, H - 85), f"{len(doc)} PRINTABLE PAGES  ·  US LETTER + A4  ·  INSTANT DOWNLOAD",
           font=sans(62), fill="white", anchor="mm")
    bg.save(os.path.join(out_dir, "01-hero.jpg"), quality=92)

    # 2. what's inside grid
    bg = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(bg)
    d.text((W / 2, 140), "What's Inside", font=serif(120), fill=t["ink"], anchor="mm")
    inner = list(range(2, len(doc)))
    cols, rows = 5, 3
    ph = 540
    cw = (W - 180) // cols
    for k, i in enumerate(inner[: cols * rows]):
        im = page_img(i, ph)
        x = 90 + (k % cols) * cw + (cw - im.width) // 2
        y = 260 + (k // cols) * (ph + 40)
        shadowed(bg, im, x, y)
    bg.save(os.path.join(out_dir, "02-whats-inside.jpg"), quality=92)

    # 3-5. close-ups of best-selling page types
    for n, (i, title) in enumerate(((8, "Monthly Budget"), (6, "Habit Tracker"), (11, "Savings Challenge")), start=3):
        bg = Image.new("RGB", (W, H), t["soft"])
        d = ImageDraw.Draw(bg)
        shadowed(bg, page_img(i, 1800), 1250, 110)
        d.text((150, 700), title, font=serif(130), fill=t["ink"])
        d.text((155, 900), "Print at home or use on", font=sans(60), fill=t["accent"])
        d.text((155, 980), "GoodNotes & Notability", font=sans(60), fill=t["accent"])
        bg.save(os.path.join(out_dir, f"{n:02d}-{title.lower().replace(' ', '-')}.jpg"), quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", choices=THEMES, action="append")
    ap.add_argument("--size", choices=SIZES, action="append")
    ap.add_argument("--no-images", action="store_true", help="skip Etsy listing photos")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for theme in args.theme or THEMES:
        for size in args.size or SIZES:
            path = os.path.join(OUT, f"Life-Budget-Planner_{theme}_{size.upper()}.pdf")
            n = Planner(path, SIZES[size], THEMES[theme]).build()
            print(f"{path}  ({n} pages, {os.path.getsize(path) // 1024} KB)")
            if not args.no_images and size == "letter":
                listing_images(path, os.path.join(OUT, "listing-photos", theme), theme)


if __name__ == "__main__":
    main()
