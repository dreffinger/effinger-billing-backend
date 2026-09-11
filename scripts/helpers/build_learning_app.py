"""Build the Effinger Programming Lab artifact: stamps a PLAIN ENGLISH header on every script listed in
scripts_manifest.py (idempotent), then writes programming_lab.html with all sources embedded."""
import json, os, re, html
from scripts_manifest import CATS, S
HERE = os.path.dirname(os.path.abspath(__file__))
def stamp(fn, m):
    p = os.path.join(HERE, fn); src = open(p).read()
    src = re.sub(r"\A(# PLAIN ENGLISH.*?\n# ---\n)", "", src, flags=re.S)
    hdr = ("# PLAIN ENGLISH (%s)\n# Decides: %s\n# Rules it uses: %s\n# Never touches: %s\n# ---\n" % (m["title"], m["decides"], m["rules"], m["never"]))
    open(p, "w").write(hdr + src)
    return hdr + src
scripts = []
for fn, m in S.items():
    if not os.path.exists(os.path.join(HERE, fn)): continue
    src = stamp(fn, m)
    scripts.append(dict(file=fn, cat=m["cat"], status=m["status"], title=m["title"], decides=m["decides"], rules=m["rules"], never=m["never"], lines=src.count("\n"), src=src))
data = {"cats": [dict(id=c[0], name=c[1], blurb=c[2]) for c in CATS], "scripts": scripts}
tpl = open(os.path.join(HERE, "programming_lab_template.html")).read()
out = tpl.replace("/*__DATA__*/null", json.dumps(data))
open(os.path.join(HERE, "programming_lab.html"), "w").write(out)
print("scripts", len(scripts), "bytes", len(out))
