#!/usr/bin/env python3
# PLAIN ENGLISH (the ehpa main logo and colour scheme - William 10/12/2026: "save that artifact's design as the ehpa main logo
#   and color scheme"; the artifact is the ehpa Billing Button page, https://claude.ai/artifact/5Eyw5K3ydS13uDHkR8JJyZ)
# Decides: nothing. The page's header mark and its :root colour tokens are the source of truth. This script copies them out
#   into brand/ so every page, app and installer draws the same thing:
#     brand/ehpa-logo.svg        the mark on the hero square (what the page shows, what the desktop icon is)
#     brand/ehpa-mark.svg        the ring and plus alone, transparent, for dark backgrounds
#     brand/ehpa-logo-256.png, brand/ehpa-logo-1024.png, brand/ehpa.ico (16-256 px)
#     brand/ehpa-brand.json      the Midnight tokens (dark and light), gradient, fonts, radii - read straight from the page's CSS
#     brand/ehpa-tokens.css      the same tokens as a :root block to paste into a new page
#     desktop/icon.png, desktop/icon.ico   the desktop app's icon, a copy of the logo
#   Geometry (a 64-unit square): ring centre (32,32) radius 23.04, stroke 5.4, round caps, drawn from 3 o'clock counter-clockwise
#   round to (47.42,49.12) so the opening sits at the right and runs down; plus arms 19.84..44.16, stroke 6.2, round caps; hero
#   square #041d21, corner radius 12/46 of the side.
#   python3 brand/make_logo.py
import json, math, os, re, shutil
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PAGE = os.path.join(REPO, "tools", "button", "billing_button_page.html")

RING_PATH = "M55.04 32A23.04 23.04 0 1 0 47.42 49.12"
PLUS_PATH = "M32 19.84V44.16M19.84 32H44.16"
SKY, MAGENTA, HERO = "#70d6f8", "#f841e0", "#041d21"
CX = CY = 32.0
R, RING_W, PLUS_W, ARM = 23.04, 5.4, 6.2, (19.84, 44.16)
START_DEG = math.degrees(math.atan2(49.12 - CY, 47.42 - CX))   # where the ring stops, about 48 degrees below 3 o'clock

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="256" height="256" role="img" aria-label="ehpa">
  <title>ehpa</title>
  <rect width="64" height="64" rx="16.7" fill="%s"/>
  <path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>
  <path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>
</svg>
""" % (HERO, RING_PATH, SKY, RING_W, PLUS_PATH, MAGENTA, PLUS_W)

MARK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="256" height="256" role="img" aria-label="ehpa">
  <title>ehpa</title>
  <path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>
  <path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/>
</svg>
""" % (RING_PATH, SKY, RING_W, PLUS_PATH, MAGENTA, PLUS_W)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def draw_logo(size, scale=8):
    """Render at size*scale with the page's geometry, then shrink for smooth edges."""
    s = size * scale
    u = s / 64.0
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 12 / 46), fill=hexrgb(HERO))
    w = RING_W * u                                    # PIL arcs run clockwise from 3 o'clock: START..360 leaves the gap at the right, running down
    box = [CX * u - R * u, CY * u - R * u, CX * u + R * u, CY * u + R * u]
    d.arc(box, start=START_DEG, end=360.0, fill=hexrgb(SKY), width=int(round(w)))
    for ang in (START_DEG, 0.0):
        px, py = CX * u + R * u * math.cos(math.radians(ang)), CY * u + R * u * math.sin(math.radians(ang))
        d.ellipse([px - w / 2, py - w / 2, px + w / 2, py + w / 2], fill=hexrgb(SKY))
    pw = PLUS_W * u
    a0, a1 = ARM[0] * u, ARM[1] * u
    d.line([(CX * u, a0), (CX * u, a1)], fill=hexrgb(MAGENTA), width=int(round(pw)))
    d.line([(a0, CY * u), (a1, CY * u)], fill=hexrgb(MAGENTA), width=int(round(pw)))
    for px, py in ((CX * u, a0), (CX * u, a1), (a0, CY * u), (a1, CY * u)):
        d.ellipse([px - pw / 2, py - pw / 2, px + pw / 2, py + pw / 2], fill=hexrgb(MAGENTA))
    return im.resize((size, size), Image.LANCZOS)


def tokens_from_page():
    """The :root blocks of the Billing Button page: dark first, then the light overrides."""
    css = open(PAGE, encoding="utf-8").read()
    dark = re.search(r"\n:root\{([^}]*)\}", css).group(1)
    light = re.search(r':root\[data-theme="light"\]\{([^}]*)\}', css).group(1)

    def parse(block):
        out = {}
        for m in re.finditer(r"--([a-z0-9-]+):([^;]+);", block):
            out[m.group(1)] = m.group(2).strip()
        return out
    return parse(dark), parse(light)


def main():
    dark, light = tokens_from_page()
    colours = ["bg", "bg-deep", "surface", "surface-2", "deep", "line", "line-strong", "ink", "ink-2", "muted", "dim",
               "on-accent", "accent", "accent-soft", "magenta", "ok", "ok-soft", "warn", "warn-soft", "bad", "bad-soft", "hero"]
    brand = {
        "name": "ehpa", "theme": "Midnight", "source": "tools/button/billing_button_page.html (the ehpa Billing Button artifact)",
        "logo": {"svg": "brand/ehpa-logo.svg", "mark_svg": "brand/ehpa-mark.svg", "png": ["brand/ehpa-logo-256.png", "brand/ehpa-logo-1024.png"],
                 "ico": "brand/ehpa.ico", "ring": SKY, "plus": MAGENTA, "square": HERO,
                 "geometry": "64-unit square; ring centre (32,32) r 23.04 stroke 5.4, open at the right running down (3 o'clock to 48 degrees below); plus 19.84-44.16 stroke 6.2; round caps; corner radius 12/46"},
        "colors": {"dark": {k: dark[k] for k in colours if k in dark}, "light": {k: light[k] for k in colours if k in light}},
        "gradient": {"dark": dark.get("grad"), "light": light.get("grad")},
        "fonts": {"text": "Quicksand 400-700", "mono": "JetBrains Mono 500-600",
                  "link": "https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap"},
        "radii": {"md": dark.get("r-md"), "lg": dark.get("r-lg"), "xl": dark.get("r-xl"), "pill": dark.get("pill")},
        "rules": ["dark first; light only when the device asks or the page's Theme button is pressed",
                  "two floating buttons bottom right on every billing page: Run all billing (gradient) and Open a billing chat (sky)",
                  "the mark is never recoloured or rotated; the opening of the ring stays at the right, running down"],
    }
    os.makedirs(HERE, exist_ok=True)
    open(os.path.join(HERE, "ehpa-logo.svg"), "w").write(LOGO_SVG)
    open(os.path.join(HERE, "ehpa-mark.svg"), "w").write(MARK_SVG)
    draw_logo(256).save(os.path.join(HERE, "ehpa-logo-256.png"))
    draw_logo(1024, scale=4).save(os.path.join(HERE, "ehpa-logo-1024.png"))
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [draw_logo(n) for n in sizes]
    frames[-1].save(os.path.join(HERE, "ehpa.ico"), format="ICO", sizes=[(n, n) for n in sizes], append_images=frames[:-1])
    json.dump(brand, open(os.path.join(HERE, "ehpa-brand.json"), "w"), indent=1)
    css = ["/* ehpa Midnight tokens - generated by brand/make_logo.py from the Billing Button page; paste into a new page's <style> */",
           ":root{" + ";".join("--%s:%s" % (k, v) for k, v in dark.items()) + ";color-scheme:dark}",
           '@media (prefers-color-scheme:light){:root:not([data-theme="dark"]){' + ";".join("--%s:%s" % (k, v) for k, v in light.items()) + ";color-scheme:light}}",
           ':root[data-theme="light"]{' + ";".join("--%s:%s" % (k, v) for k, v in light.items()) + ";color-scheme:light}", ""]
    open(os.path.join(HERE, "ehpa-tokens.css"), "w").write("\n".join(css))
    desk = os.path.join(REPO, "desktop")
    shutil.copy2(os.path.join(HERE, "ehpa-logo-256.png"), os.path.join(desk, "icon.png"))
    shutil.copy2(os.path.join(HERE, "ehpa.ico"), os.path.join(desk, "icon.ico"))
    print("brand/ written (%d dark tokens, %d light tokens); desktop/icon.png + icon.ico refreshed" % (len(dark), len(light)))


if __name__ == "__main__":
    main()
