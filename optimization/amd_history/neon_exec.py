#!/usr/bin/env python3
"""Run SQL against the practice database over Neon's HTTPS SQL route (the path tools/db/neon_db.py uses). The connection string comes
from NEON_DATABASE_URL and is never printed.  Usage: neon_exec.py <prod|preview> --file x.sql | --sql "..."  [--quiet]
Also: neon_exec.py <prod|preview> --env-for-subprocess CMD...   runs CMD with NEON_DATABASE_URL pointed at that branch."""
import os, sys, re, json, subprocess, urllib.request, urllib.parse, urllib.error
REPO = "/home/user/effinger-billing-backend"
def url_for(target):
    u = re.sub(r"\s+", "", os.environ.get("NEON_DATABASE_URL") or "")
    if not u.startswith("postgres"): sys.exit("NEON_DATABASE_URL is not set")
    p = urllib.parse.urlparse(u)
    if target == "prod": return u, p.hostname
    host = open(os.path.join(REPO, "optimization", ".preview_host")).read().strip()
    if not host or host == p.hostname: sys.exit("no separate preview host")
    return urllib.parse.urlunparse(p._replace(netloc=p.netloc.replace(p.hostname, host))), host
def run(url, host, sql, params=None):
    body = json.dumps({"query": sql, "params": params or []}).encode()
    req = urllib.request.Request("https://%s/sql" % host, data=body, method="POST",
        headers={"Neon-Connection-String": url, "Content-Type": "application/json", "Neon-Array-Mode": "true", "Neon-Raw-Text-Output": "true"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r: return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")
        try: msg = json.loads(msg).get("message", msg)
        except Exception: pass
        raise RuntimeError("SQL failed: %s | statement: %s" % (msg[:500], re.sub(r"\s+", " ", sql)[:160]))
def table(j, maxw=60):
    cols = [f["name"] for f in j.get("fields", [])]; rows = j.get("rows", [])
    if not cols: print("ok (%s)" % j.get("command", "")); return
    w = [min(maxw, max(len(c), *(len(str(r[i]) if r[i] is not None else "") for r in rows))) if rows else len(c) for i, c in enumerate(cols)]
    print(" | ".join(c.ljust(w[i]) for i, c in enumerate(cols))); print("-+-".join("-" * x for x in w))
    for r in rows: print(" | ".join((str(v) if v is not None else "")[:maxw].ljust(w[i]) for i, v in enumerate(r)))
    print("(%d row%s)" % (len(rows), "" if len(rows) == 1 else "s"))
if __name__ == "__main__":
    a = sys.argv[1:]; target = a[0]; url, host = url_for(target)
    if "--env-for-subprocess" in a:
        cmd = a[a.index("--env-for-subprocess") + 1:]
        sys.exit(subprocess.run(cmd, env=dict(os.environ, NEON_DATABASE_URL=url, NEON_DB_MODE="http")).returncode)
    if "--file" in a:
        text = open(a[a.index("--file") + 1]).read()
        stmts = [s.strip() for s in re.split(r";\s*\n(?=\S)", text) if s.strip()]
        for s in stmts:
            j = run(url, host, s.rstrip(";")); m = re.search(r"(create[^\n]{0,70}|refresh[^\n]{0,70}|drop[^\n]{0,70}|comment[^\n]{0,70})", s, re.I)
            if "--quiet" not in a: print("applied on %s: %s" % (target, (m.group(1) if m else s[:60]).strip()))
    else:
        table(run(url, host, a[a.index("--sql") + 1]))
