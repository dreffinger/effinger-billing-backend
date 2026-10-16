#!/usr/bin/env python3
# PLAIN ENGLISH (builds the "ehpa Billing Button" page from its template)
# Decides: nothing. Puts a report JSON (the example shown before a token is saved) and the App Build page link into
#   tools/button/billing_button_page.html and writes the page. The page itself is published as the artifact
#   https://claude.ai/artifact/5Eyw5K3ydS13uDHkR8JJyZ.
#   python3 tools/button/build_button_page.py <report.json> <out.html> [--app-build-url <url>]
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    src, dst = sys.argv[1], sys.argv[2]
    url = sys.argv[sys.argv.index("--app-build-url") + 1] if "--app-build-url" in sys.argv else "__APP_BUILD_URL__"
    rep = json.load(open(src))
    rep = {k: v for k, v in rep.items() if k != "errors"} | {"errors": rep.get("errors", [])}
    html = open(os.path.join(HERE, "billing_button_page.html"), encoding="utf-8").read()
    html = html.replace("__EXAMPLE__", json.dumps(rep, separators=(",", ":")).replace("</", "<\\/")).replace("__APP_BUILD_URL__", url)
    open(dst, "w", encoding="utf-8").write(html)
    print("billing button page -> %s (%d bytes)" % (dst, len(html)))


if __name__ == "__main__":
    main()
