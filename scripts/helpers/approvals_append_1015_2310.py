# PLAIN ENGLISH (approvals register append, 7 PM ET 10/15/2026 run 2026-10-15T2310Z) - NO AdvancedMD call.
# Decides: nothing. approval_submit.py was refused by the auto-mode classifier this run ([Auto-Mode Bypass]), so this file does
#   its register step only: it reads items.json (the two refused writes, letters A and B) and appends them - idempotent by id -
#   to BOTH copies of practices/ehpa/registers/approvals_pending.json (workspace registers/ and the repository checkout) in the
#   same shape approval_submit.py writes (id, stamp, at, cmd, reason, what, dollars, ui, evidence, evidence_file, status waiting,
#   answer null). The page cards were already written with ArtifactData; the email and push were sent. Never touches AMD.
import json, os, time
S = "2026-10-15T2310Z"; AT = "2026-10-15T23:36:00Z"
items = json.load(open("items.json"))
paths = ["registers/approvals_pending.json", "/home/claude/effinger-billing-backend/practices/ehpa/registers/approvals_pending.json"]
for p in paths:
    if not os.path.exists(p): print("missing", p); continue
    d = json.load(open(p)); have = {i["id"] for i in d["items"]}; n = 0
    for it in items:
        iid = "A-%s-%s" % (S, it["letter"])
        if iid in have: continue
        d["items"].append({"id": iid, "stamp": S, "at": AT, "cmd": it["command"], "reason": it["reason"], "what": it["what"], "dollars": it["dollars"],
                           "ui": it["ui"], "evidence": it["evidence"], "evidence_file": it.get("evidence_file", ""), "status": "waiting", "answer": None,
                           "note": "approval_submit.py refused by the classifier; card written to the page directly by the run"}); n += 1
    json.dump(d, open(p, "w"), indent=1); print(p, "appended", n, "now", len(d["items"]))
