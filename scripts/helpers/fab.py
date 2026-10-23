#!/usr/bin/env python3
# PLAIN ENGLISH (the two floating buttons every billing page carries - William 10/11/2026: "a manual run-all button to the left
#   of the open-chat button on all of the billing artifacts"; 10/23/2026: the button starts a CLAUDE run, not the GitHub engine)
# Decides: nothing. Given a saved copy of a billing artifact's HTML, puts the pair of buttons on it - "Run all billing" (opens the
#   ehpa Billing Button page at its trigger; one tap there fires the Claude scheduled task trig_01S771Si8VJ8DvcwgHMHGYB5, which works
#   the board input, the Claims Center columns, ERA posting, the cascade and the approved packages by the standing prompts and may ask
#   William for an approval in its session) and "Open a billing chat" (the ehpa cloud project) - bottom right, in the Midnight colours,
#   self-contained so no page style is touched. A page that already carries the chat button (the Insurance Refresh Board) gets the Run
#   button added to the left of it inside its own bar. Idempotent: a page that already has the Run button is left as it is; --rewrite
#   updates the wording of a button that is already there.
#   python3 tools/button/fab.py <in.html> <out.html> [--rewrite]
import re, sys

BUTTON_PAGE = "https://claude.ai/artifact/5Eyw5K3ydS13uDHkR8JJyZ"
CHAT = "https://claude.ai/project/01a083fd-4e9a-75fc-be20-7d5bcd7ddbd9"
MARK = "ehpa-run-fab"
# the wording of the Run button (10/23/2026: a Claude run by the standing prompts; approvals may be asked in the session)
RUN_SMALL = "Claude · columns · ERA · cascade · packages"
RUN_TITLE = ("Opens the ehpa Billing Button page at its trigger: one tap there starts a Claude billing run that works the board, every "
             "Claims Center column, ERA posting, the cascade and the approved packages by the standing prompts; the run may ask for an "
             "approval. The report comes back to that page.")
IRB_TITLE = "Opens the ehpa Billing Button page at its trigger: one tap there starts a Claude billing run by the standing prompts; the run may ask for an approval."
# the wording the pages carried before 10/23/2026 (what --rewrite replaces)
OLD_TITLE = ("Opens the ehpa Billing Button page at its trigger: one tap there runs every billing script on GitHub - the columns, ERA posting, "
             "the cascade, the approved packages - with no approval prompts. The report comes back to that page.")
OLD_IRB_TITLE = "Opens the ehpa Billing Button page at its trigger: one tap there runs every billing script on GitHub with no approval prompts."
OLD_SMALL = "columns · ERA · cascade · packages"

RUN_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
           'stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M10 8l6 4-6 4z" fill="currentColor"/></svg>')
CHAT_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            'stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-8 8H8l-5 3 1.2-4.2A8 8 0 1 1 21 12z"/><path d="M8.5 11h7M8.5 14h4"/></svg>')

CSS = """
<style id="%(mark)s-css">
/* the two billing buttons (bottom right): Run all billing + Open a billing chat - Midnight colours, independent of the page's own styles */
.%(mark)s{position:fixed;right:16px;bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:2147483000;display:flex;align-items:stretch;border-radius:999px;overflow:hidden;box-shadow:0 8px 28px rgba(0,0,0,.28);max-width:calc(100vw - 32px);font-family:'Quicksand',system-ui,-apple-system,'Segoe UI',sans-serif}
.%(mark)s a{display:inline-flex;align-items:center;gap:10px;padding:12px 18px 12px 16px;text-decoration:none;font:700 15px/1.15 'Quicksand',system-ui,-apple-system,'Segoe UI',sans-serif;white-space:nowrap;color:#082f35}
.%(mark)s a.run{background:linear-gradient(135deg,#70d6f8 0%%,#f841e0 100%%);color:#082f35}
.%(mark)s a.chat{background:#70d6f8;color:#082f35;border-left:1px solid rgba(8,47,53,.25)}
.%(mark)s a:hover{filter:brightness(1.07)} .%(mark)s a:focus-visible{outline:3px solid #f841e0;outline-offset:-3px}
.%(mark)s svg{width:22px;height:22px;flex:none}
.%(mark)s .txt small{display:block;font:400 11.5px/1.2 'Quicksand',system-ui,sans-serif;opacity:.85;margin-top:2px}
@media (max-width:760px){.%(mark)s .txt small{display:none} .%(mark)s a{font-size:14px;padding:11px 14px}}
</style>
""" % {"mark": MARK}

HTML = """
<div class="%(mark)s" id="%(mark)s" role="complementary" aria-label="Billing buttons">
  <a class="run" href="%(btn)s#trigger" target="_blank" rel="noopener" title="%(title)s">%(run_svg)s<span class="txt">Run all billing<small>%(small)s</small></span></a>
  <a class="chat" href="%(chat)s" target="_blank" rel="noopener" title="Opens the ehpa cloud project in a new tab - a billing chat with the repo, the skills, the captured-calls vocabulary and the AMD login.">%(chat_svg)s<span class="txt">Open a billing chat<small>ehpa cloud · repo, skills, AMD login</small></span></a>
</div>
""" % {"mark": MARK, "btn": BUTTON_PAGE, "chat": CHAT, "run_svg": RUN_SVG, "chat_svg": CHAT_SVG, "title": RUN_TITLE, "small": RUN_SMALL}

# the Insurance Refresh Board already has its own bar (.fab with #fab-open): the Run button goes to the left of the chat button
IRB_CSS = """<style id="%(mark)s-css">.fab a.fab-run{background:linear-gradient(135deg,#70d6f8 0%%,#f841e0 100%%)!important;color:#082f35!important;border-right:1px solid rgba(8,47,53,.25)}</style>
""" % {"mark": MARK}
IRB_HTML = ('<a class="fab-main fab-run" id="fab-run" href="%s#trigger" target="_blank" rel="noopener" title="%s">%s<span class="txt">Run all billing<small>%s</small></span></a>\n  '
            % (BUTTON_PAGE, IRB_TITLE, RUN_SVG, RUN_SMALL))


def rewrite(html):
    """Updates the wording of a Run button that is already on the page (10/23/2026). Returns (html, what)."""
    n = 0
    for old, new in ((OLD_TITLE, RUN_TITLE), (OLD_IRB_TITLE, IRB_TITLE),
                     ("Run all billing<small>" + OLD_SMALL + "</small>", "Run all billing<small>" + RUN_SMALL + "</small>")):
        if old in html:
            html = html.replace(old, new)
            n += 1
    return html, ("wording updated (%d)" % n) if n else "nothing to rewrite"


def inject(html):
    if MARK in html or 'id="fab-run"' in html:
        return html, "already there"
    if 'id="fab-open"' in html and 'class="fab"' in html:
        i = html.find('<a class="fab-main" id="fab-open"')
        if i < 0:
            i = html.find('id="fab-open"')
            i = html.rfind("<a", 0, i)
        html = html[:i] + IRB_HTML + html[i:]
        j = html.rfind("</body>")
        html = html[:j] + IRB_CSS + html[j:]
        return html, "run button added to the page's own bar"
    j = html.rfind("</body>")
    if j < 0:
        return html + CSS + HTML, "appended (no </body>)"
    return html[:j] + CSS + HTML + html[j:], "two buttons added"


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    html = open(src, encoding="utf-8").read()
    out, what = rewrite(html) if "--rewrite" in sys.argv else inject(html)
    open(dst, "w", encoding="utf-8").write(out)
    print(what, "->", dst)
