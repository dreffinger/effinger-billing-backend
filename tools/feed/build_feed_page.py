#!/usr/bin/env python3
# PLAIN ENGLISH (builds the "Claimocity Feed Monitoring" page from its template)
# Decides: nothing. Puts the current reports/feed/feed_monitor.json into tools/feed/feed_monitor_page.html as the page's first-paint
#   snapshot and writes the page; the artifact then reads the live file from GitHub main through the viewer's GitHub connector.
#   python3 tools/feed/build_feed_page.py [reports/feed/feed_monitor.json] [out.html]
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(os.path.dirname(HERE))
src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "reports", "feed", "feed_monitor.json")
dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "reports", "feed", "feed_monitor_page.html")
snap = json.dumps(json.load(open(src)), separators=(",", ":")).replace("</", "<\\/")
html = open(os.path.join(HERE, "feed_monitor_page.html"), encoding="utf-8").read().replace("__SNAPSHOT__", snap)
os.makedirs(os.path.dirname(dst), exist_ok=True); open(dst, "w", encoding="utf-8").write(html)
print("feed monitoring page -> %s (%d bytes)" % (dst, len(html.encode())))
