#!/usr/bin/env python3
"""
PLAIN ENGLISH (William, 10/23/2026 00:33 ET): "add a Refresh button to the top right of ALL of these artifacts".

This file holds the one Refresh control every billing page carries at its top-right corner and the tool that
puts it on a saved page: a small "↻ Refresh" pill (Midnight colours, independent of the page's own styles, visible
in light and dark, icon-only under 520px so it never covers a phone's title) plus a "refreshed HH:MM" stamp that
appears next to it when a refresh completes.

What the button does on a click:
  * if the page defines window.__ehpaRefresh (a function returning a promise), it is called: the page re-fetches
    its live data without a full reload - the boards re-read their store and the Drive inbox and re-render, the
    Billing Button page re-reads the scheduled task's last run and the report, Outstanding Claims re-pulls the
    snapshot from GitHub. The hook may resolve to the string 'reload' when the page is in a view with nothing to
    re-fetch (no store, no connector); the button then falls back to a full reload.
  * if the page has no loader (a static page), it reloads the page. The stamp survives the reload (sessionStorage)
    so "refreshed HH:MM" still shows next to the button afterwards.
  * failures show "could not refresh (reason)" in the stamp; the stamp fades after 12 s.

The hook is a one-line window.__ehpaRefresh = async function(){...} that the page's own script defines inside its
closure (the loaders are closure-scoped), inserted by add_hook() before a known anchor line. Nothing here is written
to the DOM until the snippet runs, so the page's own code is untouched apart from that one line.

Usage:
  python3 tools/button/refresh_button.py <in.html> <out.html> [--nudge ".pal,.tools"] [--hook-anchor "async function initSync(){" --hook-js "window.__ehpaRefresh=..."]
  --nudge adds top padding to the named top-right clusters on desktop widths so the fixed pill does not sit on them.
The older, reload-only "ehpa-refresh" button and its css/js (10/22) are removed when present, so a page carries one
Refresh control.
"""
import re, sys

MARK = 'ehpa-refresh-top'

CSS = """<style id="ehpa-refresh-css">
/* the Refresh control (top right): re-fetches the page's live data through window.__ehpaRefresh, or reloads the page when it has no loader - Midnight colours, independent of the page's own styles */
.ehpa-refresh-top{position:fixed;top:calc(10px + env(safe-area-inset-top,0px));right:12px;z-index:2147483001;display:flex;align-items:center;gap:8px;font-family:'Quicksand',system-ui,-apple-system,'Segoe UI',sans-serif;pointer-events:none}
.ehpa-refresh-top>*{pointer-events:auto}
.ehpa-refresh{display:inline-flex;align-items:center;gap:6px;font:700 13px/1 'Quicksand',system-ui,-apple-system,'Segoe UI',sans-serif;color:#082f35;background:#70d6f8;border:1px solid rgba(8,47,53,.35);border-radius:999px;padding:8px 13px;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.22);white-space:nowrap}
.ehpa-refresh:hover{filter:brightness(1.07)}
.ehpa-refresh:focus-visible{outline:3px solid #f841e0;outline-offset:2px}
.ehpa-refresh[disabled]{opacity:.75;cursor:wait}
.ehpa-refresh .ico{display:inline-block;font-size:15px;line-height:1}
.ehpa-refresh.spin .ico{animation:ehpaspin .8s linear infinite}
.ehpa-rf-stamp{display:none;font:600 12px/1.2 'Quicksand',system-ui,-apple-system,'Segoe UI',sans-serif;color:#fff;background:rgba(8,47,53,.94);border:1px solid #70d6f8;border-radius:999px;padding:6px 10px;white-space:nowrap;max-width:min(62vw,340px);overflow:hidden;text-overflow:ellipsis}
.ehpa-rf-stamp.show{display:inline-block}
.ehpa-rf-stamp.err{border-color:#ff8a80;color:#ffd2cf}
@keyframes ehpaspin{to{transform:rotate(360deg)}}
@media (prefers-reduced-motion:reduce){.ehpa-refresh.spin .ico{animation:none}}
@media (max-width:520px){.ehpa-refresh .txt{display:none} .ehpa-refresh{padding:7px 10px}}
</style>"""

HTML = """<div class="ehpa-refresh-top" id="ehpa-refresh-top" role="group" aria-label="Refresh this page">
  <span class="ehpa-rf-stamp" id="ehpa-rf-stamp" role="status" aria-live="polite"></span>
  <button type="button" class="ehpa-refresh" id="ehpa-rf-btn" aria-label="Refresh" title="Re-fetches this page's live data (or reloads the page when it has nothing to re-fetch)"><span class="ico" aria-hidden="true">↻</span><span class="txt">Refresh</span></button>
</div>"""

JS = """<script id="ehpa-refresh-js">
(function(){
  var btn=document.getElementById('ehpa-rf-btn'), st=document.getElementById('ehpa-rf-stamp'); if(!btn||!st) return;
  var busy=false, timer=null, KEY='ehpa-refreshed-at';
  function hhmm(d){ try{ return d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}); }catch(e){ return d.getHours()+':'+('0'+d.getMinutes()).slice(-2); } }
  function stamp(text,cls,ms){ st.textContent=text; st.className='ehpa-rf-stamp show'+(cls?' '+cls:''); clearTimeout(timer); if(ms!==0) timer=setTimeout(function(){ st.className='ehpa-rf-stamp'; }, ms||12000); }
  function reload(){ try{ sessionStorage.setItem(KEY, String(Date.now())); }catch(e){} location.reload(); }
  try{ var t=sessionStorage.getItem(KEY); if(t){ sessionStorage.removeItem(KEY); if(Date.now()-Number(t)<30000) stamp('refreshed '+hhmm(new Date())); } }catch(e){}
  btn.addEventListener('click', function(){
    if(busy) return; var hook=window.__ehpaRefresh;
    if(typeof hook!=='function'){ stamp('reloading\\u2026',null,0); reload(); return; }
    busy=true; btn.disabled=true; btn.classList.add('spin'); stamp('refreshing\\u2026',null,0);
    Promise.resolve().then(function(){ return hook(); }).then(function(r){
      if(r==='reload'){ reload(); return; }
      stamp('refreshed '+hhmm(new Date()));
    }).catch(function(e){ stamp('could not refresh ('+((e&&(e.code||e.message))||'error')+')','err',15000); })
    .then(function(){ busy=false; btn.disabled=false; btn.classList.remove('spin'); });
  });
})();
</script>"""

OLD_BTN = re.compile(r'<button[^>]*class="ehpa-refresh[^"]*"[^>]*>.*?</button>\s*', re.S)
OLD_CSS = re.compile(r'<style id="ehpa-refresh-css">.*?</style>\s*', re.S)
OLD_JS = re.compile(r'<script id="ehpa-refresh-js">.*?</script>\s*', re.S)


def remove_old(html):
    """drop the 10/22 reload-only button and its css/js (and any earlier copy of this snippet)"""
    n = 0
    for rx in (OLD_JS, OLD_CSS, OLD_BTN):
        html, k = rx.subn('', html); n += k
    html, k = re.subn(r'<div class="ehpa-refresh-top".*?</div>\s*', '', html, flags=re.S); n += k
    return html, n


def nudge_css(selectors):
    sel = ','.join(s.strip() for s in selectors.split(',') if s.strip())
    if not sel:
        return ''
    return '<style id="ehpa-refresh-nudge">@media (min-width:761px){' + sel + '{padding-top:42px}}</style>\n'


def inject(html, nudge=None):
    html, removed = remove_old(html)
    block = CSS + '\n' + (nudge_css(nudge) if nudge else '') + HTML + '\n' + JS + '\n'
    i = html.rfind('</body>')
    if i >= 0:
        html = html[:i] + block + html[i:]
    else:
        html = html.rstrip('\n') + '\n\n' + block
    return html, removed


def add_hook(html, anchor, hook_js):
    """insert the page's window.__ehpaRefresh line before the first occurrence of anchor (which must exist)"""
    i = html.find(anchor)
    if i < 0:
        raise SystemExit('hook anchor not found: ' + anchor[:60])
    if 'window.__ehpaRefresh' in html:
        raise SystemExit('the page already defines window.__ehpaRefresh')
    return html[:i] + hook_js.rstrip() + '\n' + html[i:]


def main(argv):
    if len(argv) < 3:
        print(__doc__); return 2
    src, dst = argv[1], argv[2]
    nudge = None; anchor = None; hook = None
    i = 3
    while i < len(argv):
        a = argv[i]
        if a == '--nudge': nudge = argv[i + 1]; i += 2
        elif a == '--hook-anchor': anchor = argv[i + 1]; i += 2
        elif a == '--hook-js': hook = argv[i + 1]; i += 2
        elif a == '--hook-file': hook = open(argv[i + 1], encoding='utf-8').read(); i += 2
        else: raise SystemExit('unknown option ' + a)
    html = open(src, encoding='utf-8').read()
    if anchor and hook:
        html = add_hook(html, anchor, hook)
    html, removed = inject(html, nudge)
    open(dst, 'w', encoding='utf-8').write(html)
    print('refresh button added | old refresh pieces removed:', removed, '| hook:', 'yes' if (anchor and hook) else 'none (reload)', '| nudge:', nudge or '-', '|', len(html), 'bytes ->', dst)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
