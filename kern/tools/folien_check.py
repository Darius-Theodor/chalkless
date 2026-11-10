"""Check a Chalkless slide deck (offline HTML presentation) display step by display step.

Usage:
  python kern/tools/folien_check.py <deck.html> [--out DIR] [--json] [--pdf] [--min-font PX]
                                    [--min-small PX] [--viewport WxH] [--channel NAME] [--settle MS]
  python kern/tools/folien_check.py --help
  python kern/tools/folien_check.py --self-test

What it does (headless, nothing is installed or downloaded):
  - loads the deck in the installed Edge or Chrome through Playwright (channel msedge, then chrome, then a
    Playwright browser only if one is already present); no browser found -> says so, structural check only
  - blocks the network: every request that is not file:, data: or blob: is aborted and counted as an error
  - finds every display step through the frame convention (window.deck: count, stepsOf, go) of
    kern/gestaltung/deck-rahmen.html and renders each one (with --out: one PNG per state, bNN-sMM.png,
    plus uebersicht.png with the end states if pillow is present)
  - per state: content outside the visible area (overflow), teacher notes visible or their sentences in the
    visible text, smallest font size in design px (1920x1080), pictures marked as missing, raw template
    leftovers ({{...}}, file names), bottom edge of the content
  - console errors and page errors, a reload test of a middle state (?step=N#bK, then reload), one key press
  - optional print PDF (--pdf) into DIR, with its page count
  - writes DIR/folien_check.json (with --out) or prints the JSON (--json)

Exit codes:
  0  no problem found
  1  problem: overflow, notes visible, network request, console error
  2  load error: file missing, page did not load, or no renderer (Playwright or browser missing);
     then only the structural check ran and the display was NOT seen

Font sizes are a report, never a failure. --min-font (reading text, default 28) and --min-small (secondary
text, default 24) only produce hints. Choose the floor for the age group from kern/gestaltung/folien.md
section 4; 28 is the adult reference at 1920x1080, not a rule for children.

Not checked by this tool (say so in the check line): real legibility in the room (projector brightness,
contrast in daylight, distance of the back row), whether the slides keep the meaning and every task of the
lesson plan, spelling and facts, what a picture shows, the presenter window, full screen and touch
behaviour, other aspect ratios unless --viewport is given.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

VERSION = "1"
W, H = 1920, 1080
NOT_CHECKED = [
    "real legibility in the room: projector brightness, contrast in daylight, distance of the back row",
    "meaning and tasks of the lesson plan kept (compare with the plan yourself)",
    "spelling and facts on the slides",
    "what the pictures show and whether a drawing is recognisable",
    "presenter window, full screen, touch and remote control behaviour",
]
ALLOWED_SCHEMES = ("file:", "data:", "blob:", "about:")
EXTERNAL_RE = re.compile(r"""(?:url\(\s*['"]?|@import\s+['"]?)\s*(https?:|//)""", re.I)
LEFTOVER_RE = re.compile(r"\{\{|\}\}|\b[\w-]+\.(?:png|jpe?g|gif|webp|svg|prompt\.md|html)\b|\bTODO\b|\bPLATZHALTER\b", re.I)


def out(text: str) -> None:
    """Print ASCII-safe on any console (cp1252 pipes included)."""
    sys.stdout.write(text.encode("ascii", "backslashreplace").decode("ascii") + "\n")


# ---------------------------------------------------------------- structural check (stdlib only)

class Structure(HTMLParser):
    REQ_TAGS = {"img", "script", "link", "source", "iframe", "video", "audio", "embed", "object", "track", "image", "use"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.beats = 0
        self.notes = 0
        self.notes_without_hidden = 0
        self.external = []
        self.leftovers = []
        self.missing_pictures = []
        self.stack = []          # (tag, skip_text)
        self.skip_depth = 0
        self.frame = False
        self.in_missing = 0
        self.missing_text = ""
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "meta" and a.get("name") == "chalkless-deck-rahmen":
            self.frame = True
        if tag == "section" and "beat" in cls:
            self.beats += 1
        skip = tag in ("script", "style") or (tag == "aside" and "notes" in cls)
        if tag == "aside" and "notes" in cls:
            self.notes += 1
            if "hidden" not in a:
                self.notes_without_hidden += 1
        if tag in self.REQ_TAGS or tag == "a":
            for key in ("src", "href", "srcset", "poster", "data", "xlink:href"):
                v = (a.get(key) or "").strip()
                if not v:
                    continue
                if tag == "a" and key == "href":
                    continue            # a link is not a request
                if re.match(r"^(https?:)?//", v, re.I):
                    self.external.append(f"<{tag} {key}={v[:80]}>")
        if a.get("style") and EXTERNAL_RE.search(a["style"]):
            self.external.append(f"<{tag} style=url(...)>")
        if "pic-missing" in cls:
            self.in_missing += 1
            self.missing_text = ""
        if tag == "title":
            self.in_title = True
        if tag not in ("meta", "link", "br", "img", "input", "hr", "source", "wbr", "col", "area", "base", "track", "embed", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "use", "stop"):
            self.stack.append((tag, skip, "pic-missing" in cls))
            if skip:
                self.skip_depth += 1

    def handle_endtag(self, tag):
        while self.stack:
            t, skip, missing = self.stack.pop()
            if skip:
                self.skip_depth -= 1
            if missing:
                self.in_missing -= 1
                self.missing_pictures.append(re.sub(r"\s+", " ", self.missing_text).strip())
            if t == tag:
                break
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.stack and self.stack[-1][0] == "style" and EXTERNAL_RE.search(data):
            self.external.append("<style> url(http...) or @import")
        if self.skip_depth:
            return
        if self.in_missing:
            self.missing_text += data
        m = LEFTOVER_RE.search(data)
        if m and data.strip():
            self.leftovers.append(data.strip()[:80])


def structural(html: str) -> dict:
    s = Structure()
    try:
        s.feed(html)
    except Exception as e:  # noqa: BLE001 - a broken file must not crash the report
        return {"error": f"{type(e).__name__}: {e}"}
    if "{{" in s.title:
        s.leftovers.append("<title> " + s.title.strip()[:60])
    return {"frame": s.frame, "beats": s.beats, "notes": s.notes, "notes_without_hidden": s.notes_without_hidden,
            "external_refs": s.external, "template_leftovers": s.leftovers, "missing_pictures": s.missing_pictures}


# ---------------------------------------------------------------- browser part

JS_MEASURE = r"""
([minFont, minSmall]) => {
  const vw = innerWidth, vh = innerHeight;
  const u = Math.max(Math.min(vw / 1920, vh / 1080), 0.6);
  const vis = (el) => {
    if (!el || !el.isConnected) return false;
    if (el.checkVisibility) { if (!el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) return false; }
    else { for (let e = el; e; e = e.parentElement) { const c = getComputedStyle(e); if (c.display === 'none' || c.visibility === 'hidden' || parseFloat(c.opacity) === 0) return false; } }
    const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0;
  };
  const root = document.querySelector('main section.beat[data-active]') || document.body;
  const res = { overflow: [], notes_visible: [], fonts: [], below: [], missing_pictures: [], leftovers: [], broken_images: [], bottom: 0, text: '' };
  const leftoverRe = /\{\{|\}\}|\b[\w-]+\.(png|jpe?g|gif|webp|svg|prompt\.md|html)\b|\bTODO\b|\bPLATZHALTER\b/i;
  const tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const texts = [];
  let n;
  while ((n = tw.nextNode())) {
    const t = n.textContent.replace(/\s+/g, ' ').trim();
    if (!t) continue;
    const el = n.parentElement;
    if (!el || el.closest('[data-ui], .notes, script, style, .sr-only')) continue;
    if (!vis(el)) continue;
    const range = document.createRange(); range.selectNodeContents(n);
    const r = range.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize) / u;
    const small = !!el.closest('.secondary, [data-small], .pic-missing');
    texts.push(t);
    res.fonts.push({ fs: Math.round(fs * 10) / 10, small, text: t.slice(0, 50) });
    if (fs < (small ? minSmall : minFont) - 0.05) res.below.push({ fs: Math.round(fs * 10) / 10, small, text: t.slice(0, 50) });
    res.bottom = Math.max(res.bottom, r.bottom);
    if (r.right > vw + 1 || r.bottom > vh + 1 || r.left < -1 || r.top < -1)
      res.overflow.push({ kind: 'text', text: t.slice(0, 50), left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom) });
    if (leftoverRe.test(t)) res.leftovers.push(t.slice(0, 80));
  }
  for (const el of root.querySelectorAll('svg, img, figure, table, div, li, p, button, blockquote, h1, h2, h3, ul, ol, .pic-missing')) {
    if (el.closest('[data-ui], .notes') || !vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.right > vw + 1 || r.bottom > vh + 1 || r.left < -1 || r.top < -1) {
      const name = el.tagName.toLowerCase() + (typeof el.className === 'string' && el.className ? '.' + el.className.split(/\s+/)[0] : '');
      res.overflow.push({ kind: 'box', text: name, left: Math.round(r.left), top: Math.round(r.top), right: Math.round(r.right), bottom: Math.round(r.bottom) });
    }
    if (el.tagName === 'IMG' && el.complete && el.naturalWidth === 0) res.broken_images.push((el.getAttribute('src') || '').slice(0, 60));
    if (el.matches('svg, img, .pic-missing, .star, .box, .words > li, .cards > li')) res.bottom = Math.max(res.bottom, Math.min(r.bottom, vh * 2));
  }
  for (const el of root.querySelectorAll('.pic-missing')) if (vis(el)) res.missing_pictures.push(el.textContent.replace(/\s+/g, ' ').trim().slice(0, 80));
  if (document.documentElement.scrollWidth > vw + 1) res.overflow.push({ kind: 'page', text: 'horizontal scroll width ' + document.documentElement.scrollWidth });
  for (const el of document.querySelectorAll('.notes, aside.notes')) {
    if (vis(el)) res.notes_visible.push({ kind: 'element', text: el.textContent.replace(/\s+/g, ' ').trim().slice(0, 60) });
  }
  const visible = texts.join(' ').toLowerCase();
  const beatNotes = root.querySelectorAll ? root.querySelectorAll('aside.notes, .notes') : [];
  for (const el of beatNotes) {
    const sentences = el.textContent.replace(/\s+/g, ' ').split(/(?<=[.!?])\s+/);
    for (const s of sentences) {
      const k = s.trim().toLowerCase();
      if (k.length >= 40 && visible.includes(k)) res.notes_visible.push({ kind: 'text', text: s.trim().slice(0, 60) });
    }
  }
  const all = res.fonts.map(f => f.fs), reading = res.fonts.filter(f => !f.small).map(f => f.fs);
  res.min_font = all.length ? Math.min(...all) : null;
  res.min_reading_font = reading.length ? Math.min(...reading) : null;
  res.bottom_pct = Math.round(res.bottom / vh * 1000) / 10;
  res.font_count = res.fonts.length;
  delete res.fonts;
  return res;
}
"""

JS_STATE = "() => window.deck ? {i: window.deck.index, s: window.deck.step} : null"
JS_HIDE_HUD = ("() => { document.documentElement.setAttribute('data-idle', ''); "
               "let st = document.getElementById('folien-check-style'); if (!st) { st = document.createElement('style'); "
               "st.id = 'folien-check-style'; st.textContent = '.hud{visibility:hidden !important}'; document.head.appendChild(st); } }")


def launch(p, channel: str | None):
    tried = []
    for ch in ([channel] if channel else ["msedge", "chrome"]):
        try:
            b = p.chromium.launch(channel=ch, headless=True)
            return b, ch, tried
        except Exception as e:  # noqa: BLE001
            tried.append(f"{ch}: {str(e).splitlines()[0][:100]}")
    if not channel:
        try:
            exe = p.chromium.executable_path
            if exe and Path(exe).exists():          # only a browser that is already there; never a download
                return p.chromium.launch(headless=True), "playwright-chromium", tried
            tried.append("playwright-chromium: not present (not downloaded)")
        except Exception as e:  # noqa: BLE001
            tried.append(f"playwright-chromium: {str(e).splitlines()[0][:100]}")
    return None, None, tried


def contact_sheet(pngs: list[Path], target: Path) -> bool:
    try:
        from PIL import Image, ImageDraw
    except Exception:  # noqa: BLE001
        return False
    if not pngs:
        return False
    cols, tw = 3, 480
    ims = [Image.open(p) for p in pngs]
    th = int(tw * ims[0].height / ims[0].width)
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * (tw + 12) + 12, rows * (th + 30) + 12), "#dddddd")
    d = ImageDraw.Draw(sheet)
    for k, (im, p) in enumerate(zip(ims, pngs)):
        x, y = 12 + (k % cols) * (tw + 12), 12 + (k // cols) * (th + 30)
        sheet.paste(im.convert("RGB").resize((tw, th)), (x, y))
        d.text((x, y + th + 6), p.stem, fill="#222222")
    sheet.save(target)
    return True


def pdf_pages(path: Path) -> int | None:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001
        try:
            return len(re.findall(rb"/Type\s*/Page\b", path.read_bytes()))
        except Exception:  # noqa: BLE001
            return None


def render_check(deck: Path, a, report: dict) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:  # noqa: BLE001
        report["load_error"] = "Playwright is not installed: display not checked (see kern/tools/voraussetzungen.py, route 'slides')"
        return 2
    vw, vh = a.viewport
    outdir = Path(a.out).resolve() if a.out else None
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
    net, console, warnings = report["network"], report["console_errors"], report["console_warnings"]
    with sync_playwright() as p:
        browser, used, tried = launch(p, a.channel)
        report["browser_tried"] = tried
        if not browser:
            report["load_error"] = "no Edge or Chrome found for Playwright (nothing was downloaded): display not checked"
            return 2
        report["browser"] = f"{used} {browser.version}"
        ctx = browser.new_context(viewport={"width": vw, "height": vh}, device_scale_factor=1, reduced_motion="reduce")

        def route(r):
            url = r.request.url
            if url.startswith(ALLOWED_SCHEMES):
                r.continue_()
            else:
                if url not in net:
                    net.append(url)
                r.abort()
        ctx.route("**/*", route)
        page = ctx.new_page()
        page.on("console", lambda m: (console if m.type == "error" else warnings).append(m.text[:200]) if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: console.append(f"pageerror: {str(e)[:200]}"))
        page.on("requestfailed", lambda r: net.append(r.url) if not r.url.startswith(ALLOWED_SCHEMES) and r.url not in net else None)
        try:
            page.goto(deck.as_uri(), wait_until="load", timeout=20000)
        except Exception as e:  # noqa: BLE001
            report["load_error"] = f"page did not load: {str(e).splitlines()[0][:160]}"
            browser.close()
            return 2
        page.wait_for_timeout(a.settle)
        info = page.evaluate("() => window.deck ? {count: window.deck.count, steps: Array.from({length: window.deck.count}, (_, i) => window.deck.stepsOf(i)), titles: Array.from(document.querySelectorAll('main section.beat')).map(b => [b.id, b.getAttribute('data-title') || ''])} : null")
        report["frame_api"] = bool(info)
        if not info:
            report["hints"].append("no window.deck: not built on kern/gestaltung/deck-rahmen.html; only the loaded view was checked")
            info = {"count": 1, "steps": [0], "titles": [["page", document_title(page)]]}
        report["beats"] = info["count"]
        report["steps_per_beat"] = info["steps"]
        page.evaluate(JS_HIDE_HUD)
        mins = [a.min_font, a.min_small]
        end_pngs = []
        for i in range(info["count"]):
            for s in range(info["steps"][i] + 1):
                if report["frame_api"]:
                    page.evaluate("([i, s]) => window.deck.go(i, s)", [i, s])
                    try:
                        page.wait_for_function("([i, s]) => window.deck.index === i && window.deck.step === s && document.querySelectorAll('main section.beat')[i].hasAttribute('data-active')", arg=[i, s], timeout=4000)
                    except Exception:  # noqa: BLE001
                        report["hints"].append(f"state b{i + 1} step {s} not reached through window.deck.go")
                page.wait_for_timeout(a.settle)
                m = page.evaluate(JS_MEASURE, mins)
                bid, title = info["titles"][i] if i < len(info["titles"]) else (f"b{i + 1}", "")
                st = {"beat": i + 1, "id": bid, "title": title, "step": s, "max": info["steps"][i]}
                st.update(m)
                if outdir:
                    png = outdir / f"b{i + 1:02d}-s{s:02d}.png"
                    page.screenshot(path=str(png))
                    st["png"] = png.name
                    if s == info["steps"][i]:
                        end_pngs.append(png)
                report["states"].append(st)
        # one key press: from the first state, ArrowRight must change the state
        if report["frame_api"]:
            page.evaluate("() => window.deck.go(0, 0)")
            page.wait_for_timeout(a.settle)
            before = page.evaluate(JS_STATE)
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(a.settle)
            after = page.evaluate(JS_STATE)
            report["keys"] = {"before": before, "after": after, "ok": before != after}
            if before == after and (info["count"] > 1 or info["steps"][0] > 0):
                report["hints"].append("ArrowRight did not advance the deck")
        # reload test of a middle state
        if report["frame_api"]:
            cands = [k for k in range(info["count"]) if info["steps"][k] > 0] or list(range(info["count"]))
            k = cands[len(cands) // 2]
            s = math.ceil(info["steps"][k] / 2)
            target = {"beat": k + 1, "step": s}
            rl = {"target": target}
            try:
                s0 = max(s - 1, 0)
                page.goto(deck.as_uri() + f"?step={s0}#b{k + 1}", wait_until="load")
                page.wait_for_timeout(a.settle * 2)
                rl["via_url"] = page.evaluate(JS_STATE)
                rl["via_url_ok"] = rl["via_url"] == {"i": k, "s": s0}
                if s > s0:                      # one step forward by key, so the reload starts from a navigated state
                    page.keyboard.press("ArrowRight")
                    page.wait_for_timeout(a.settle)
                rl["before_reload"] = page.evaluate(JS_STATE)
                page.reload(wait_until="load")
                page.wait_for_timeout(a.settle * 2)
                page.evaluate(JS_HIDE_HUD)
                page.wait_for_timeout(a.settle)
                rl["after_reload"] = page.evaluate(JS_STATE)
                m = page.evaluate(JS_MEASURE, mins)
                rl["overflow"] = m["overflow"]
                rl["notes_visible"] = m["notes_visible"]
                want = {"i": k, "s": s}
                rl["ok"] = rl["via_url_ok"] and rl["before_reload"] == want and rl["after_reload"] == want and not m["notes_visible"] and not m["overflow"]
                if outdir:
                    page.screenshot(path=str(outdir / "reload.png"))
                    rl["png"] = "reload.png"
                if rl["after_reload"] and rl["after_reload"].get("i") == k and rl["after_reload"].get("s") != s:
                    report["hints"].append("reload keeps the beat but not the build step")
                elif not rl["ok"]:
                    report["hints"].append("reload test: state after reload differs from the state before")
            except Exception as e:  # noqa: BLE001
                rl["ok"] = False
                rl["error"] = str(e).splitlines()[0][:160]
            report["reload"] = rl
        if a.pdf and outdir:
            try:
                page.evaluate("() => { if (window.deckPrepPrint) window.deckPrepPrint(); }")
                pdf = outdir / (deck.stem + ".pdf")
                page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
                page.evaluate("() => { if (window.deckEndPrint) window.deckEndPrint(); }")
                report["pdf"] = {"file": pdf.name, "pages": pdf_pages(pdf), "beats": info["count"]}
            except Exception as e:  # noqa: BLE001
                report["pdf"] = {"error": str(e).splitlines()[0][:160]}
        elif a.pdf:
            report["hints"].append("--pdf needs --out")
        if outdir and end_pngs and contact_sheet(end_pngs, outdir / "uebersicht.png"):
            report["contact_sheet"] = "uebersicht.png"
        browser.close()
    return 0


def document_title(page) -> str:
    try:
        return page.title()
    except Exception:  # noqa: BLE001
        return ""


def summarise(report: dict, a) -> int:
    st = report["states"]
    overflow = sum(len(s["overflow"]) for s in st) + len(report.get("reload", {}).get("overflow", []) or [])
    notes = sum(len(s["notes_visible"]) for s in st) + len(report.get("reload", {}).get("notes_visible", []) or [])
    below = sum(len(s["below"]) for s in st)
    fonts = [s["min_font"] for s in st if s["min_font"] is not None]
    reading = [s["min_reading_font"] for s in st if s["min_reading_font"] is not None]
    leftovers = sorted({x for s in st for x in s["leftovers"]})
    missing = sorted({x for s in st for x in s["missing_pictures"]})
    broken = sorted({x for s in st for x in s["broken_images"]})
    report["summary"] = {
        "states": len(st), "overflow": overflow, "notes_visible": notes, "network": len(report["network"]),
        "console_errors": len(report["console_errors"]), "min_font": min(fonts) if fonts else None,
        "min_reading_font": min(reading) if reading else None, "below_min_font": below,
        "min_font_reference": {"reading": a.min_font, "small": a.min_small},
        "missing_pictures": missing, "template_leftovers": leftovers, "broken_images": broken,
    }
    probs = report["problems"]
    if report.get("load_error"):
        probs.append("load: " + report["load_error"])
    if overflow:
        probs.append(f"overflow: {overflow} element(s) outside the visible area")
    if notes:
        probs.append(f"notes visible: {notes}")
    if report["network"]:
        probs.append(f"network: {len(report['network'])} external request(s) blocked")
    if report["console_errors"]:
        probs.append(f"console errors: {len(report['console_errors'])}")
    if below:
        report["hints"].append(f"{below} text element(s) below the reference size (reading {a.min_font}, small {a.min_small}); check against the floor for the age group")
    if leftovers:
        report["hints"].append("raw template text or file names visible: " + "; ".join(leftovers[:5]))
    if broken:
        report["hints"].append("pictures that did not load: " + "; ".join(broken[:5]))
    stc = report.get("structure", {})
    if stc.get("notes_without_hidden"):
        report["hints"].append(f"{stc['notes_without_hidden']} aside.notes without the hidden attribute")
    if stc.get("template_leftovers"):
        report["hints"].append("template text in the file (title or text outside the slides): " + "; ".join(stc["template_leftovers"][:3]))
    if stc.get("external_refs") and not report["network"]:
        report["hints"].append("external references in the file: " + "; ".join(stc["external_refs"][:3]))
    if report.get("load_error"):
        return 2
    return 1 if (overflow or notes or report["network"] or report["console_errors"]) else 0


def print_summary(report: dict) -> None:
    out(f"folien_check {VERSION}: {report['deck']}")
    if report.get("browser"):
        out(f"browser: {report['browser']} | viewport {report['viewport']}")
    s = report.get("summary", {})
    if report["states"]:
        out(f"beats: {report.get('beats')} | states: {s.get('states')} | steps per beat: {' '.join(str(x) for x in report.get('steps_per_beat', []))}")
        out(f"overflow: {s.get('overflow')} | notes visible: {s.get('notes_visible')} | network: {s.get('network')} | console errors: {s.get('console_errors')}")
        out(f"smallest text: {s.get('min_font')} px, smallest reading text: {s.get('min_reading_font')} px (design px at 1920x1080); "
            f"below reference: {s.get('below_min_font')}")
        out(f"pictures marked as missing: {len(s.get('missing_pictures', []))} | template leftovers: {len(s.get('template_leftovers', []))}")
        bottoms = [st["bottom_pct"] for st in report["states"] if st["step"] == st["max"]]
        if bottoms:
            out(f"content bottom edge of the end states: {min(bottoms)}-{max(bottoms)} % of the height")
        rl = report.get("reload")
        if rl:
            out(f"reload test b{rl['target']['beat']} step {rl['target']['step']}: {'ok' if rl.get('ok') else 'NOT ok'} "
                f"(?step= gave {rl.get('via_url')}, before reload {rl.get('before_reload')}, after reload {rl.get('after_reload')}; i = beat - 1, s = step)")
        if report.get("pdf"):
            out(f"pdf: {report['pdf']}")
    else:
        stc = report.get("structure", {})
        out(f"structure only: beats {stc.get('beats')}, notes {stc.get('notes')} (without hidden {stc.get('notes_without_hidden')}), "
            f"external refs {len(stc.get('external_refs', []))}, leftovers {len(stc.get('template_leftovers', []))}")
    for pr in report["problems"]:
        out("PROBLEM " + pr)
    for h in report["hints"]:
        out("HINT " + h)
    out("not checked: " + "; ".join(report["nicht_geprueft"]))
    out("RESULT " + ("OK" if report["exit_code"] == 0 else ("PROBLEMS" if report["exit_code"] == 1 else "NOT RENDERED")) + f" (exit {report['exit_code']})")


def parse_viewport(v: str):
    m = re.fullmatch(r"(\d{3,5})x(\d{3,5})", v.strip().lower())
    if not m:
        raise argparse.ArgumentTypeError("viewport as WIDTHxHEIGHT, e.g. 1920x1080")
    return int(m.group(1)), int(m.group(2))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="folien_check.py", description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n\n".join(__doc__.split("\n\n")[1:]))
    ap.add_argument("deck", nargs="?", help="the deck HTML file")
    ap.add_argument("--out", help="folder for PNGs, the JSON report and the optional PDF (outside the instance)")
    ap.add_argument("--json", action="store_true", help="print the JSON report instead of the summary")
    ap.add_argument("--pdf", action="store_true", help="also print the deck to PDF into --out (optional; slides need no PDF)")
    ap.add_argument("--min-font", type=float, default=28.0, help="reference for reading text in design px (hint only, default 28)")
    ap.add_argument("--min-small", type=float, default=24.0, help="reference for secondary text in design px (hint only, default 24)")
    ap.add_argument("--viewport", type=parse_viewport, default=(W, H), help="WIDTHxHEIGHT, default 1920x1080 (e.g. 1024x768 for a 4:3 projector)")
    ap.add_argument("--channel", help="browser channel to use (msedge or chrome); default: msedge, then chrome")
    ap.add_argument("--settle", type=int, default=300, help="wait after each step in ms (default 300)")
    ap.add_argument("--self-test", action="store_true", help="run kern/tools/tests/test_folien_check.py")
    a = ap.parse_args(argv)
    if a.self_test:
        import subprocess
        test = Path(__file__).resolve().parent / "tests" / "test_folien_check.py"
        return subprocess.call([sys.executable, "-B", str(test), "-v"])
    if not a.deck:
        ap.print_usage()
        out("error: the deck HTML file is missing (see --help)")
        return 2
    deck = Path(a.deck).resolve()
    report = {"tool": "folien_check", "version": VERSION, "deck": str(deck), "viewport": f"{a.viewport[0]}x{a.viewport[1]}",
              "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "states": [], "network": [], "console_errors": [],
              "console_warnings": [], "problems": [], "hints": [], "nicht_geprueft": list(NOT_CHECKED)}
    if a.viewport != (W, H):
        report["nicht_geprueft"].append("the 1920x1080 view (this run used another viewport)")
    else:
        report["nicht_geprueft"].append("other aspect ratios (run again with --viewport 1024x768 for a 4:3 projector)")
    if not deck.is_file():
        report["load_error"] = "file not found"
        rc = 2
    else:
        html = deck.read_text(encoding="utf-8", errors="replace")
        report["structure"] = structural(html)
        rc = render_check(deck, a, report)
        if rc == 2:
            report["nicht_geprueft"].insert(0, "the display itself: no renderer, only the HTML structure was checked")
    rc = summarise(report, a) if rc == 0 else max(rc, summarise(report, a))
    report["exit_code"] = rc
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if a.out:
        od = Path(a.out).resolve()
        od.mkdir(parents=True, exist_ok=True)
        (od / "folien_check.json").write_text(text, encoding="utf-8")
    if a.json:
        out(json.dumps(report, ensure_ascii=True, indent=1))
    else:
        print_summary(report)
    return rc


if __name__ == "__main__":
    sys.exit(main())
