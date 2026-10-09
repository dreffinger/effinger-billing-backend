# PLAIN ENGLISH (Mandatory Approvals register bookkeeping, 5 PM ET 10/9/2026 run 2026-10-09T2110Z): LOCAL FILES ONLY, no AMD call.
# Decides: nothing. Sets a note (--note) or status + answer (--done) on the named approval package ids in BOTH copies of
#   approvals_pending.json (the repo's practices/ehpa/registers and the workspace registers/), exactly as step 0h(1) asks:
#   CLAIM = note "applying <run stamp>"; DONE = status done + answer; REFUSED = note "<stamp>: approved, refused again by the environment".
# Usage: python3 approvals_mark.py --ids A,B --note "applying 2026-10-09T2110Z"
#        python3 approvals_mark.py --ids A --done "2026-10-09T21:40Z applied by backend billing run 2026-10-09T2110Z on William's page approval: ..."
import json, sys
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
ids = set(opt("--ids", "").split(",")) - {""}; note = opt("--note"); done = opt("--done")
if not ids or not (note or done): sys.exit("usage: --ids <id,...> (--note <text> | --done <answer>)")
for p in ("/home/claude/effinger-billing-backend/practices/ehpa/registers/approvals_pending.json", "/home/claude/unbilled/registers/approvals_pending.json"):
    try: d = json.load(open(p))
    except Exception as e: print("skip", p, e); continue
    items = d["items"] if isinstance(d, dict) else d; hit = 0
    for it in items:
        if it.get("id") in ids:
            if note is not None: it["note"] = note
            if done is not None: it["status"] = "done"; it["answer"] = done
            hit += 1
    json.dump(d, open(p, "w"), indent=1); print(p, "updated", hit, "item(s)")
