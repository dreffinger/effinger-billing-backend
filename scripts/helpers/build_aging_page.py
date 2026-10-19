#!/usr/bin/env python3
# PLAIN ENGLISH (AR Aging page builder, 10/15/2026 - William: "make this chart as an ar aging artifact ... with a refresh button")
# Decides: nothing. Composes boards/templates/ar_aging_template.html from ar_aging_body.html + the shared palette CSS of the
#   Working Denials template (the eight ehpa palettes, both themes, the refresh-strip styles), then injects an aging snapshot
#   (aging_latest.json, schema ar-aging/1 - chart and visit ids only) into `const D=/*__DATA__*/null;` and writes the page.
#   python3 tools/button/build_aging_page.py <aging_latest.json> <out.html>          # page from a snapshot
#   python3 tools/button/build_aging_page.py --template-only                        # just (re)write the template
# Never touches: AMD.
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
T = os.path.join(REPO, "boards", "templates")

def palette_css():
    wd = open(os.path.join(T, "working_denials_template.html"), encoding="utf-8").read()
    a = wd.index("/* ===== default palette: Indigo Night ===== */")
    b = wd.index("*{box-sizing:border-box}", a)
    return wd[a:b]        # the palette blocks + the .rf refresh-strip styles

def template():
    body = open(os.path.join(T, "ar_aging_body.html"), encoding="utf-8").read()
    return body.replace("/*__PALETTE__*/", palette_css(), 1)

def main():
    tpl = template()
    open(os.path.join(T, "ar_aging_template.html"), "w", encoding="utf-8").write(tpl)
    if "--template-only" in sys.argv:
        print("template written"); return
    snap = json.load(open(sys.argv[1])); out = sys.argv[2]
    data = json.dumps(snap, separators=(",", ":")).replace("</", "<\\/")
    page = tpl.replace("const D=/*__DATA__*/null;", "const D=" + data + ";", 1)
    open(out, "w", encoding="utf-8").write(page)
    print("page %s: %d bytes, %d rows, asof %s" % (out, len(page.encode("utf-8")), len(snap.get("rows") or []), snap.get("asof")))

if __name__ == "__main__":
    main()
