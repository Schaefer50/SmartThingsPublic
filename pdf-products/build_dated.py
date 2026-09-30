#!/usr/bin/env python3
"""Build the dated, hyperlinked "<year> Life & Budget Planner".

    python3 pdf-products/build_dated.py                     # 2027, sage, all sizes, both week starts
    python3 pdf-products/build_dated.py --year 2028 --theme blush --size letter --start sunday

Every page has clickable month tabs; monthly calendars link to their weekly pages.
"""

import argparse
import calendar
import datetime as dt
import os

from reportlab.lib.colors import white

from build_planner import MARGIN, OUT, SHOP, SIZES, THEMES, Planner, HERE

STARTS = {"sunday": calendar.SUNDAY, "monday": calendar.MONDAY}
DAY = dt.timedelta(days=1)


class DatedPlanner(Planner):
    def __init__(self, path, size, theme, year, first_weekday):
        super().__init__(path, size, theme, product=f"{year} Life & Budget Planner")
        self.year, self.fw = year, first_weekday
        self.cal = calendar.Calendar(firstweekday=first_weekday)
        self.day_names = [calendar.day_name[(first_weekday + i) % 7] for i in range(7)]
        self.start_name = calendar.day_name[first_weekday]
        self.index = {}  # bookmark key -> page number (1-based)

    # ---------- dates ----------
    def week_start(self, day):
        return day - (day.weekday() - self.fw) % 7 * DAY

    def weeks(self):
        """Start dates of every week that overlaps the year."""
        start, last = self.week_start(dt.date(self.year, 1, 1)), dt.date(self.year, 12, 31)
        out = []
        while start <= last:
            out.append(start)
            start += 7 * DAY
        return out

    def week_month(self, start):
        """Weeks are filed under the month of their first day inside the year."""
        return max(start, dt.date(self.year, 1, 1)).month

    @staticmethod
    def week_key(start):
        return f"w{start.isoformat()}"

    @staticmethod
    def week_title(start):
        end = start + 6 * DAY
        if start.month == end.month:
            return f"{calendar.month_name[start.month]} {start.day} – {end.day}"
        return f"{calendar.month_abbr[start.month]} {start.day} – {calendar.month_abbr[end.month]} {end.day}"

    # ---------- chrome ----------
    def tabs(self, current):
        """Clickable side tabs: year overview + 12 months."""
        c, t = self.c, self.t
        x, w = self.w - MARGIN + 12, 22
        top, bottom = self.h - MARGIN - 40, MARGIN + 30
        items = [("YEAR", "year")] + [(calendar.month_abbr[m].upper(), f"m{m}") for m in range(1, 13)]
        th = (top - bottom) / len(items)
        for i, (label, key) in enumerate(items):
            yy = top - (i + 1) * th
            on = key == current
            c.setFillColor(t["accent"] if on else t["soft"])
            c.roundRect(x, yy + 1.5, w, th - 3, 4, stroke=0, fill=1)
            c.saveState()
            c.translate(x + w / 2 + 2.5, yy + th / 2)
            c.rotate(90)
            c.setFont("SansBold", 6.5)
            c.setFillColor(white if on else t["ink"])
            c.drawCentredString(0, 0, label)
            c.restoreState()
            c.linkRect("", key, (x, yy, x + w, yy + th), relative=0)

    # ---------- pages ----------
    def cover_dated(self):
        c, t, w, h = self.c, self.t, self.w, self.h
        c.setFillColor(t["soft"])
        c.rect(0, 0, w, h, stroke=0, fill=1)
        c.setFillColor(t["accent"])
        c.circle(w * 0.85, h * 0.88, 150, stroke=0, fill=1)
        c.setFillColor(t["line"])
        c.circle(w * 0.1, h * 0.12, 110, stroke=0, fill=1)
        c.setStrokeColor(t["accent"])
        c.rect(MARGIN, MARGIN, w - 2 * MARGIN, h - 2 * MARGIN, stroke=1, fill=0)
        c.setFillColor(t["ink"])
        c.setFont("Serif", 120)
        c.drawCentredString(w / 2, h * 0.56, str(self.year))
        c.setFont("Serif", 34)
        c.drawCentredString(w / 2, h * 0.56 - 60, "Life & Budget Planner")
        c.setStrokeColor(t["accent"])
        c.line(w / 2 - 50, h * 0.56 - 84, w / 2 + 50, h * 0.56 - 84)
        c.setFont("Sans", 11)
        c.setFillColor(t["accent"])
        c.drawCentredString(w / 2, h * 0.56 - 106, "PLAN  ·  SAVE  ·  GROW")
        c.setFont("SansBold", 9)
        c.drawCentredString(w / 2, h * 0.56 - 128, f"{self.start_name.upper()} START")
        c.setFont("Sans", 10)
        c.setFillColor(t["ink"])
        c.drawCentredString(w / 2, h * 0.26, "This planner belongs to")
        c.setStrokeColor(t["ink"])
        c.setLineWidth(0.6)
        c.line(w / 2 - 110, h * 0.26 - 30, w / 2 + 110, h * 0.26 - 30)

    def contents_dated(self):
        c, t = self.c, self.t
        y = self.header("Contents")
        c.setFont("Sans", 9)
        c.setFillColor(t["ink"])
        c.drawString(MARGIN, y, "Tap any item, or use the tabs on the right of every page.")
        y -= 34
        left = [("Year at a Glance", "year"), ("Yearly Goals", "goals"), ("Important Dates", "dates"),
                ("Bill Payment Tracker", "bills"), ("Savings Challenge", "savings"),
                ("Lined Notes", "notes"), ("Dot Grid", "dots")]
        right = [(f"{calendar.month_name[m]}", f"m{m}") for m in range(1, 13)]
        colw = (self.inner - 30) / 2
        for col, items in enumerate((left, right)):
            x = MARGIN + col * (colw + 30)
            self.label(x, y + 14, "Planning" if col == 0 else "Months")
            for i, (name, key) in enumerate(items):
                yy = y - 8 - i * 30
                c.setFont("Serif", 14)
                c.setFillColor(t["ink"])
                c.drawString(x, yy, name)
                c.setStrokeColor(t["line"])
                c.setDash(1, 3)
                c.line(x + c.stringWidth(name, "Serif", 14) + 8, yy + 3, x + colw - 24, yy + 3)
                c.setDash()
                c.setFont("Sans", 10)
                c.setFillColor(t["accent"])
                c.drawRightString(x + colw, yy, str(self.index.get(key, "")))
                c.linkRect("", key, (x, yy - 8, x + colw, yy + 18), relative=0)

    def year_glance(self):
        c, t = self.c, self.t
        y = self.header(f"{self.year} at a Glance")
        cols, rows, gap = 3, 4, 14
        gw = (self.inner - (cols - 1) * gap) / cols
        gh = (y - MARGIN - 20 - (rows - 1) * gap) / rows
        for m in range(1, 13):
            col, row = (m - 1) % cols, (m - 1) // cols
            x0, y0 = MARGIN + col * (gw + gap), y - row * (gh + gap)
            c.setFillColor(t["soft"])
            c.roundRect(x0, y0 - gh, gw, gh, 6, stroke=0, fill=1)
            c.setFont("Serif", 13)
            c.setFillColor(t["ink"])
            c.drawString(x0 + 10, y0 - 20, calendar.month_name[m])
            c.linkRect("", f"m{m}", (x0, y0 - gh, x0 + gw, y0), relative=0)
            cw = (gw - 16) / 7
            c.setFont("SansBold", 6.5)
            c.setFillColor(t["accent"])
            for i, name in enumerate(self.day_names):
                c.drawCentredString(x0 + 8 + cw * i + cw / 2, y0 - 36, name[0])
            rh = (gh - 48) / 6
            c.setFont("Sans", 7.5)
            c.setFillColor(t["ink"])
            for r, week in enumerate(self.cal.monthdatescalendar(self.year, m)):
                for i, day in enumerate(week):
                    if day.month == m:
                        c.drawCentredString(x0 + 8 + cw * i + cw / 2, y0 - 50 - r * rh, str(day.day))

    def important_dates(self):
        y = self.header("Important Dates")
        cols, rows, gap = 3, 4, 12
        gw = (self.inner - (cols - 1) * gap) / cols
        gh = (y - MARGIN - 20 - (rows - 1) * gap) / rows
        for m in range(1, 13):
            col, row = (m - 1) % cols, (m - 1) // cols
            self.section(MARGIN + col * (gw + gap), y - row * (gh + gap), gw, gh,
                         calendar.month_name[m], spacing=18)

    def month_calendar(self, m):
        c, t = self.c, self.t
        y = self.header(f"{calendar.month_name[m]} {self.year}")
        weeks = self.cal.monthdatescalendar(self.year, m)
        cw = self.inner / 7
        notes_h = 120
        c.setFillColor(t["accent"])
        c.roundRect(MARGIN, y - 20, self.inner, 20, 4, stroke=0, fill=1)
        c.setFillColor(white)
        c.setFont("SansBold", 8)
        for i, name in enumerate(self.day_names):
            c.drawCentredString(MARGIN + cw * i + cw / 2, y - 14, name[:3].upper())
        top = y - 22
        ch = (top - MARGIN - 20 - notes_h - 26) / len(weeks)
        c.setLineWidth(0.6)
        for r, week in enumerate(weeks):
            y0 = top - (r + 1) * ch
            for i, day in enumerate(week):
                x0 = MARGIN + i * cw
                inside = day.month == m
                if not inside:
                    c.setFillColor(t["soft"])
                    c.rect(x0, y0, cw, ch, stroke=0, fill=1)
                elif day.weekday() >= 5:
                    c.saveState()
                    c.setFillColor(t["soft"])
                    c.setFillAlpha(0.4)
                    c.rect(x0, y0, cw, ch, stroke=0, fill=1)
                    c.restoreState()
                c.setStrokeColor(t["line"])
                c.rect(x0, y0, cw, ch, stroke=1, fill=0)
                c.setFont("SansBold" if inside else "Sans", 10 if inside else 8)
                c.setFillColor(t["ink"] if inside else t["line"])
                c.drawString(x0 + 6, y0 + ch - 14, str(day.day))
            # the whole row opens that week's page
            c.linkRect("", self.week_key(week[0]), (MARGIN, y0, MARGIN + self.inner, y0 + ch), relative=0)
        c.setFont("Sans", 7.5)
        c.setFillColor(t["accent"])
        c.drawString(MARGIN, top - len(weeks) * ch - 14, "Tip: tap any week to open its weekly page.")
        self.section(MARGIN, top - len(weeks) * ch - 26, self.inner, notes_h, "Goals & notes this month")

    def week_page(self, start):
        c, t = self.c, self.t
        y = self.header(self.week_title(start), "Year")
        half = (self.inner - 15) / 2
        bh = (y - MARGIN - 20 - 3 * 10) / 4
        for i in range(7):
            day = start + i * DAY
            col, row = i % 2, i // 2
            x, yy = MARGIN + col * (half + 15), y - row * (bh + 10)
            self.section(x, yy, half, bh, f"{self.day_names[i]}  ·  {calendar.month_abbr[day.month]} {day.day}",
                         spacing=18)
            if day.weekday() >= 5:
                c.setFillColor(t["accent"])
                c.circle(x + half - 12, yy - 10, 2.5, stroke=0, fill=1)
        x, yy = MARGIN + half + 15, y - 3 * (bh + 10)
        self.section(x, yy, half, bh, "Top priorities", lines=False)
        self.checklist(x + 10, yy - 38, x + half - 10, yy - bh + 6, 18)

    # ---------- assembly ----------
    def plan(self):
        """(key, outline title, outline level, draw function, tab, prefilled field) per page."""
        mname = calendar.month_name
        pages = [("cover", "Cover", 0, self.cover_dated, None, None),
                 ("contents", "Contents", 0, self.contents_dated, None, None),
                 ("year", "Year at a Glance", 0, self.year_glance, "year", None),
                 ("goals", "Yearly Goals", 0, self.goals, "year", str(self.year)),
                 ("dates", "Important Dates", 0, self.important_dates, "year", None),
                 ("bills", "Bill Payment Tracker", 0, self.bills, "year", str(self.year)),
                 ("savings", "Savings Challenge", 0, self.savings, "year", None)]
        weeks = self.weeks()
        for m in range(1, 13):
            fill = f"{mname[m]} {self.year}"
            pages += [(f"m{m}", mname[m], 0, lambda m=m: self.month_calendar(m), f"m{m}", None),
                      (f"b{m}", "Budget", 1, self.budget, f"m{m}", fill),
                      (f"h{m}", "Habits", 1, self.habits, f"m{m}", fill)]
            for s in weeks:
                if self.week_month(s) == m:
                    pages.append((self.week_key(s), self.week_title(s), 1,
                                  lambda s=s: self.week_page(s), f"m{m}", str(self.year)))
        pages += [("notes", "Lined Notes", 0, self.notes_lined, None, None),
                  ("dots", "Dot Grid", 0, self.notes_dots, None, None)]
        return pages

    def build(self):
        pages = self.plan()
        self.index = {key: i + 1 for i, (key, *_) in enumerate(pages)}
        for key, title, level, draw, tab, fill in pages:
            self.c.bookmarkPage(key)
            self.c.addOutlineEntry(title, key, level=level)
            self.fill_text = fill
            draw()
            if key != "cover":
                self.tabs(tab)
                self.footer()
            self.c.showPage()
        self.c.save()
        return self.index


def listing_images(pdf_path, index, theme, year, dest):
    """Etsy listing photos (2700x2025)."""
    import pymupdf
    from PIL import Image, ImageDraw, ImageFont

    os.makedirs(dest, exist_ok=True)
    doc = pymupdf.open(pdf_path)
    t = THEMES[theme]
    W, H = 2700, 2025
    serif = lambda n: ImageFont.truetype(os.path.join(HERE, "fonts", "PlayfairDisplay-VF.ttf"), n)
    sans = lambda n: ImageFont.truetype(os.path.join(HERE, "fonts", "Lato-Bold.ttf"), n)
    first_week = next(k for k in index if k.startswith("w") and index[k] > index["m1"])
    pg = lambda key: index[key] - 1

    def page_img(i, height):
        pix = doc[i].get_pixmap(dpi=200)
        im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)

    def paste(bg, im, x, y):
        bg.paste(Image.new("RGB", im.size, t["line"]), (x + 10, y + 10))
        bg.paste(im, (x, y))

    # 1. hero
    bg = Image.new("RGB", (W, H), t["soft"])
    d = ImageDraw.Draw(bg)
    for i, x in ((pg(first_week), 1480), (pg("m1"), 1160)):
        paste(bg, page_img(i, 1500), x, 330)
    paste(bg, page_img(0, 1650), 180, 190)
    d.rectangle((0, H - 170, W, H), fill=t["accent"])
    d.text((W / 2, H - 85), f"{len(doc)} PAGES  ·  HYPERLINKED  ·  SUNDAY + MONDAY START",
           font=sans(62), fill="white", anchor="mm")
    bg.save(os.path.join(dest, "01-hero.jpg"), quality=92)

    # 2. what's inside
    bg = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(bg)
    d.text((W / 2, 140), "What's Inside", font=serif(120), fill=t["ink"], anchor="mm")
    keys = ["contents", "year", "goals", "dates", "m1", first_week, "b1", "h1", "bills", "savings"]
    cols, ph = 5, 800
    cw = (W - 180) // cols
    for k, key in enumerate(keys):
        im = page_img(pg(key), ph)
        paste(bg, im, 90 + (k % cols) * cw + (cw - im.width) // 2, 270 + (k // cols) * (ph + 50))
    bg.save(os.path.join(dest, "02-whats-inside.jpg"), quality=92)

    # 3-5. close-ups
    closeups = [(pg("m1"), "Monthly Pages", ["Every month of", f"{year}, fully dated"]),
                (pg(first_week), "Weekly Spreads", ["Dated pages for", "every week of the year"]),
                (pg("year"), "Clickable Tabs", ["Tap to jump to any", "month in GoodNotes"])]
    for n, (i, title, sub) in enumerate(closeups, start=3):
        bg = Image.new("RGB", (W, H), t["soft"])
        d = ImageDraw.Draw(bg)
        paste(bg, page_img(i, 1800), 1250, 110)
        d.text((150, 700), title, font=serif(120), fill=t["ink"])
        for j, line in enumerate(sub):
            d.text((155, 900 + j * 80), line, font=sans(60), fill=t["accent"])
        bg.save(os.path.join(dest, f"0{n}-{title.lower().replace(' ', '-')}.jpg"), quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2027)
    ap.add_argument("--theme", choices=THEMES, default="sage")
    ap.add_argument("--size", choices=SIZES, action="append")
    ap.add_argument("--start", choices=STARTS, action="append")
    ap.add_argument("--no-images", action="store_true")
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    for size in args.size or SIZES:
        for start in args.start or STARTS:
            path = os.path.join(OUT, f"{args.year}-Planner_{args.theme}_{size.upper()}_{start.title()}-start.pdf")
            index = DatedPlanner(path, SIZES[size], THEMES[args.theme], args.year, STARTS[start]).build()
            print(f"{path}  ({len(index)} pages, {os.path.getsize(path) // 1024} KB)")
            if not args.no_images and size == "letter" and start == "sunday":
                listing_images(path, index, args.theme, args.year,
                               os.path.join(OUT, "listing-photos", f"{args.year}-Planner-{args.theme}"))


if __name__ == "__main__":
    main()
