"""Render the profile README cards into cards/ from data/contributions.json.

Usage:  python scripts/render_cards.py           animated cards
        STATIC=1 python scripts/render_cards.py  final frame only (for screenshots)
Also writes preview.html (gitignored) so the whole stack can be checked in a browser.
"""
import base64, html, json, math, os, re, subprocess, sys, tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "cards"
STATIC = os.environ.get("STATIC") == "1"

# ---- About me (edit here) -------------------------------------------------
NAME = "Assawin Chittanandha"
ABOUT = "Frontend software engineer in Bangkok, building fast sites and CMS tooling with Astro, React and PHP."
PORTRAIT = next((p for p in ROOT.glob("portrait.*") if p.suffix.lower() in (".jpg", ".jpeg", ".png")), None)
FEATURED = ["strapi-export-import-excel"]  # repo cards, in this order
TILES = [  # (kicker, title, subtitle); the links live in README.md
    ("01", "Projects", "All my repositories"),
    ("02", "LinkedIn", "Experience & background"),
    ("03", "Email", "chittanandhaassawin@gmail.com"),
]

# ---- Brand, taken from the CardPortfolio theme -----------------------------
GOLD, GOLD_2 = "#ffdb70", "#ffbb5c"  # --orange-yellow-crayola -> --text-gradient-yellow end
WHITE, GRAY, MUTED = "#fafafa", "#d6d6d6", "rgba(214,214,214,.7)"  # --white-2, --light-gray(-70)
JET, ONYX = "#383838", "#2b2b2c"  # border, empty cell
W = 840

FONT_FILES = {400: ROOT / "fonts/Poppins-Regular.ttf", 600: ROOT / "fonts/Poppins-SemiBold.ttf"}
FONTS = {w: TTFont(p) for w, p in FONT_FILES.items()}

CSS = """
@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes grow{from{transform:scaleY(0)}}
@keyframes fade{from{opacity:0}}
.a{animation:up .8s cubic-bezier(.2,.7,.2,1) both}
.bar{transform-box:fill-box;transform-origin:50% 100%;animation:grow .9s cubic-bezier(.2,.7,.2,1) both}
.f{animation:fade .5s ease-out both}
.still{display:none}
"""
# Final frame: CSS animations off, SMIL elements swapped for their static twins.
STILL = "*{animation:none!important}.smil{display:none}.still{display:inline}"
CSS += STILL if STATIC else "@media (prefers-reduced-motion:reduce){%s}" % STILL

DEFS = f"""<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2d2d2f"/><stop offset="1" stop-color="#1e1e20"/></linearGradient>
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD_2}"/></linearGradient>
<linearGradient id="goldv" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD_2}"/></linearGradient>
</defs>"""


# ---- helpers ---------------------------------------------------------------
def width(s, size, weight=400):
    f = FONTS[weight]
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    return sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in s) * size / f["head"].unitsPerEm


def wrap(s, size, max_w, max_lines=99, weight=400):
    lines = []
    for word in s.split():
        if lines and width(lines[-1] + " " + word, size, weight) <= max_w:
            lines[-1] += " " + word
        else:
            lines.append(word)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;") + "…"
    return lines


def text(x, y, s, size, weight=400, fill=MUTED, cls="", delay=None, extra=""):
    style = f' style="animation-delay:{delay:.2f}s"' if delay is not None else ""
    c = f' class="{cls}"' if cls else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="P,Poppins,sans-serif" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}"{c}{style} {extra}>{escape(s)}</text>')


def subset_woff(path, chars):
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "f.woff"
        subprocess.run([sys.executable, "-m", "fontTools.subset", str(path),  # = pyftsubset
                        "--text=" + "".join(sorted(chars)), "--flavor=woff",
                        "--layout-features=kern,liga", f"--output-file={out}"], check=True)
        return base64.b64encode(out.read_bytes()).decode()


def card(name, h, body, delay, w=W):
    chars = set(html.unescape(re.sub(r"<[^>]+>", "", body))) | {" "}
    faces = "".join(
        f"@font-face{{font-family:P;font-weight:{wt};src:url(data:font/woff;base64,{subset_woff(p, chars)}) format('woff')}}"
        for wt, p in FONT_FILES.items())
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f"<style>{faces}{CSS}</style>{DEFS}"
           f'<g class="a" style="animation-delay:{delay:.2f}s">'
           f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="18" '
           f'fill="url(#bg)" stroke="{JET}"/>{body}</g></svg>')
    (CARDS / f"{name}.svg").write_text(svg)


# ---- stats -----------------------------------------------------------------
def streaks(counts):
    """(current, longest). Today with no contributions yet doesn't break the current streak."""
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    tail = counts[:-1] if counts and not counts[-1] else counts
    current = len(tail) - len("".join("1" if c else "0" for c in tail).rstrip("1"))
    return current, longest


assert streaks([1, 1, 0, 1, 1, 1, 0]) == (3, 3)
assert streaks([2, 0, 1, 1]) == (2, 2)
assert streaks([0, 0]) == (0, 0)


# ---- cards -----------------------------------------------------------------
TILE_W, TILE_H = 272, 120


def hero():
    has_photo = PORTRAIT is not None
    text_w = 560 if has_photo else W - 80
    about = wrap(ABOUT, 16, text_w)
    h = 168 + 26 * len(about) + 22
    name_w = width(NAME, 40, 600)
    body = text(40, 62, "HELLO, I'M", 12, 600, f"url(#gold)", "a", .1, 'letter-spacing="3"')
    body += text(40, 112, NAME, 40, 600, WHITE, "a", .2)
    line = f'M40 130H{40 + name_w:.0f}'
    # user-space gradient: a bbox gradient on a zero-height line renders nothing
    body += (f'<linearGradient id="ul" gradientUnits="userSpaceOnUse" x1="40" x2="{40 + name_w:.0f}" y1="0" y2="0">'
             f'<stop offset="0" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD_2}"/></linearGradient>')
    body += (f'<path class="smil" d="{line}" stroke="url(#ul)" stroke-width="3" stroke-linecap="round" fill="none" '
             f'pathLength="1" stroke-dasharray="1" stroke-dashoffset="1">'
             f'<animate attributeName="stroke-dashoffset" from="1" to="0" begin=".6s" dur="1s" fill="freeze" '
             f'calcMode="spline" keyTimes="0;1" keySplines=".2 .7 .2 1"/></path>')
    body += f'<path class="still" d="{line}" stroke="url(#ul)" stroke-width="3" stroke-linecap="round"/>'
    for i, l in enumerate(about):
        body += text(40, 168 + 26 * i, l, 16, 400, GRAY, "a", .45 + .08 * i)
    if has_photo:
        mime = "png" if PORTRAIT.suffix.lower() == ".png" else "jpeg"
        img = base64.b64encode(PORTRAIT.read_bytes()).decode()
        cx, cy, r = W - 40 - 70, h / 2, 70
        body += (f'<g class="a" style="animation-delay:.3s"><clipPath id="pc"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
                 f'<image href="data:image/{mime};base64,{img}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" '
                 f'clip-path="url(#pc)" preserveAspectRatio="xMidYMid slice"/>'
                 f'<circle cx="{cx}" cy="{cy}" r="{r + 4}" fill="none" stroke="url(#gold)" stroke-width="2"/></g>')
    card("hero", h, body, 0)


def tiles():
    for i, (kicker, title, sub) in enumerate(TILES):
        d = .35 + .15 * i
        body = text(24, 40, kicker, 12, 600, "url(#gold)", "", None, 'letter-spacing="2"')
        body += f'<path d="M232 30l12-12M235 18h9v9" stroke="{GOLD}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        body += text(24, 76, title, 20, 600, WHITE)
        body += text(24, 98, wrap(sub, 13, TILE_W - 48, 1)[0], 13)
        card(f"tile-{i + 1}", TILE_H, body, d, TILE_W)


def activity(days, delay):
    counts = [c for _, c in days]
    current, longest = streaks(counts)
    active = sum(1 for c in counts if c)
    busy_day, busy = max(days, key=lambda d: d[1])
    by_month = Counter()
    for d, c in days:
        by_month[d[:7]] += c
    months = sorted(by_month)[-12:]
    top = max(by_month[m] for m in months) or 1

    body = text(32, 48, "Contributions", 20, 600, WHITE)
    body += text(32, 72, f"{sum(by_month[m] for m in months):,} in the last 12 months", 13)
    base, max_h, slot = 236, 120, 43
    body += f'<path d="M32 {base + .5}H548" stroke="{JET}"/>'
    for i, m in enumerate(months):
        v = by_month[m]
        bh = max(3, v / top * max_h) if v else 0
        x = 32 + i * slot + 8
        d = delay + .35 + .05 * i
        if bh:
            body += (f'<rect class="bar" style="animation-delay:{d:.2f}s" x="{x}" y="{base - bh:.1f}" '
                     f'width="27" height="{bh:.1f}" rx="5" fill="url(#goldv)"/>')
            body += text(x + 13.5, base - bh - 8, f"{v:,}", 11, 600, WHITE, "f", d + .5, 'text-anchor="middle"')
        body += text(x + 13.5, base + 20, date.fromisoformat(m + "-01").strftime("%b"), 11, 400, MUTED, "",
                     None, 'text-anchor="middle"')
    body += f'<path d="M580 40V256" stroke="{JET}"/>'

    bd = date.fromisoformat(busy_day)
    stats = [("CURRENT STREAK", f"{current} day{'s' * (current != 1)}", ""),
             ("LONGEST STREAK", f"{longest} days", ""),
             ("ACTIVE DAYS", f"{active}", f"of {len(days)}"),
             ("BUSIEST DAY", f"{busy}", f"{bd:%b} {bd.day}, {bd.year}")]
    for i, (label, value, note) in enumerate(stats):
        y, d = 62 + 54 * i, delay + .5 + .1 * i
        g = text(612, y, label, 11, 600, MUTED, "", None, 'letter-spacing="1.5"')
        g += text(612, y + 28, value, 22, 600, "url(#gold)" if i == 0 else WHITE)
        if note:
            g += text(620 + width(value, 22, 600), y + 28, note, 12)
        if i == 0:  # live dot next to the streak
            cx = 622 + width(label, 11, 600) + 1.5 * len(label)
            g += f'<circle cx="{cx:.1f}" cy="{y - 4}" r="3.5" fill="{GOLD}"/>'
            g += (f'<circle class="smil" cx="{cx:.1f}" cy="{y - 4}" r="3.5" fill="none" stroke="{GOLD}">'
                  f'<animate attributeName="r" values="3.5;10" dur="1.8s" repeatCount="indefinite"/>'
                  f'<animate attributeName="opacity" values=".8;0" dur="1.8s" repeatCount="indefinite"/></circle>')
        body += f'<g class="a" style="animation-delay:{d:.2f}s">{g}</g>'
    card("activity", 280, body, delay)


def repo_cards(repos, delay):
    for old in CARDS.glob("repo-*.svg"):
        old.unlink()
    for i, r in enumerate(repos):
        desc = wrap(r["description"] or "No description yet.", 14, W - 64, 2)
        body = text(32, 50, r["name"], 20, 600, "url(#gold)")
        body += f'<path d="M790 32l12-12M793 20h9v9" stroke="{GOLD}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        for j, l in enumerate(desc):
            body += text(32, 80 + 22 * j, l, 14, 400, GRAY)
        y = 80 + 22 * len(desc) + 20
        x = 32
        lang = r["primaryLanguage"]
        if lang:
            body += f'<circle cx="{x + 6}" cy="{y - 5}" r="6" fill={quoteattr(lang["color"] or GRAY)}/>'
            body += text(x + 18, y, lang["name"], 13)
            x += 18 + width(lang["name"], 13) + 24
        star = " ".join(f"{x + 7 + (7 if k % 2 == 0 else 3) * math.sin(k * math.pi / 5):.1f},"
                        f"{y - 5 - (7 if k % 2 == 0 else 3) * math.cos(k * math.pi / 5):.1f}" for k in range(10))
        body += f'<polygon points="{star}" fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-linejoin="round"/>'
        body += text(x + 20, y, f'{r["stargazerCount"]:,}', 13)
        x += 20 + width(f'{r["stargazerCount"]:,}', 13) + 24
        body += (f'<g fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-linecap="round">'
                 f'<circle cx="{x + 3}" cy="{y - 11}" r="2"/><circle cx="{x + 11}" cy="{y - 11}" r="2"/>'
                 f'<circle cx="{x + 7}" cy="{y + 1}" r="2"/><path d="M{x + 3} {y - 9}v1q0 3 4 3t4-3v-1M{x + 7} {y - 5}v4"/></g>')
        body += text(x + 20, y, f'{r["forkCount"]:,}', 13)
        card(f"repo-{i + 1}", y + 30, body, delay + .2 * i)


LEVELS = {"NONE": 0, "FIRST_QUARTILE": .3, "SECOND_QUARTILE": .5, "THIRD_QUARTILE": .75, "FOURTH_QUARTILE": 1}


def graph(weeks, total, delay):
    step, size = 15, 12
    x0, y0 = (W - (len(weeks) * step - 3)) / 2, 86
    body = text(32, 46, "Contribution graph", 18, 600, WHITE)
    body += text(W - 32, 46, f"{total:,} contributions in the last year", 13, 400, MUTED, "", None, 'text-anchor="end"')
    last_month = None
    for col, wk in enumerate(weeks):
        m = wk["contributionDays"][0]["date"][5:7]
        if m != last_month and col < len(weeks) - 2:
            body += text(x0 + col * step, y0 - 10, date.fromisoformat(wk["contributionDays"][0]["date"]).strftime("%b"), 11)
            last_month = m
        for day in wk["contributionDays"]:
            row = (date.fromisoformat(day["date"]).weekday() + 1) % 7  # Sunday first, like GitHub
            o = LEVELS[day["contributionLevel"]]
            fill = f'fill="{GOLD}" fill-opacity="{o}"' if o else f'fill="{ONYX}"'
            body += (f'<rect class="f" style="animation-delay:{delay + .3 + col * .012:.2f}s" x="{x0 + col * step:.1f}" '
                     f'y="{y0 + row * step}" width="{size}" height="{size}" rx="3" {fill}/>')
    ly = y0 + 7 * step + 16
    lx = W - 32 - width("More", 11) - 6 - 5 * step
    body += text(lx - 6, ly + 10, "Less", 11, 400, MUTED, "", None, 'text-anchor="end"')
    for k, o in enumerate(LEVELS.values()):
        fill = f'fill="{GOLD}" fill-opacity="{o}"' if o else f'fill="{ONYX}"'
        body += f'<rect x="{lx + k * step:.1f}" y="{ly}" width="{size}" height="{size}" rx="3" {fill}/>'
    body += text(lx + 5 * step + 3, ly + 10, "More", 11)
    card("graph", ly + 36, body, delay)


def readme_repos(repos):
    block = "\n\n".join(f'<a href={quoteattr(r["url"])}><img src="cards/repo-{i + 1}.svg" width="100%" '
                        f'alt={quoteattr(r["name"])}></a>' for i, r in enumerate(repos))
    readme = ROOT / "README.md"
    s = readme.read_text()
    s = re.sub(r"(<!-- repos:start -->).*?(<!-- repos:end -->)", lambda m: f"{m[1]}\n{block}\n{m[2]}", s, flags=re.S)
    readme.write_text(s)
    page = re.sub(r"\n\s*\n", "\n<br>\n", s)
    (ROOT / "preview.html").write_text(
        f'<!doctype html><meta charset="utf-8"><body style="background:#0d1117;max-width:840px;margin:40px auto">{page}')


def main():
    user = json.loads((ROOT / "data/contributions.json").read_text())["data"]["user"]
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"]) for w in cal["weeks"] for d in w["contributionDays"]]
    by_name = {r["name"]: r for r in user["repositories"]["nodes"]}
    missing = [n for n in FEATURED if n not in by_name]
    assert not missing, f"FEATURED repos not found: {missing}"
    repos = [by_name[n] for n in FEATURED]
    CARDS.mkdir(exist_ok=True)
    hero()
    tiles()
    graph(cal["weeks"], cal["totalContributions"], .9)
    activity(days, 1.6)
    repo_cards(repos, 2.3)
    readme_repos(repos)
    print(f"rendered {len(list(CARDS.glob('*.svg')))} cards{' (static)' if STATIC else ''}")


if __name__ == "__main__":
    main()
