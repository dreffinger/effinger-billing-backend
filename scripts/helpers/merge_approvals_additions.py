# PLAIN ENGLISH (approvals additions merge, 7 AM ET 10/7/2026 run)
# Decides: nothing. A run whose approval_submit.py --push-main was refused leaves its package as
#   "<stamp> approvals_additions.json" in Drive 'chat history'; this merges such a file into BOTH copies of
#   approvals_pending.json (workspace + repo) by item id (an id already present is left exactly as it is),
#   so the hourly approvals sync and the 0h(1) apply step see the card on main.
# Never touches: AdvancedMD, the page, Drive, git.
# Usage: python3 merge_approvals_additions.py <additions json> [<more additions json>...]
import json, sys
COPIES = ["/home/claude/unbilled/registers/approvals_pending.json",
          "/home/claude/effinger-billing-backend/practices/ehpa/registers/approvals_pending.json"]
for fn in sys.argv[1:]:
    add = json.load(open(fn))
    items = add.get("items", add if isinstance(add, list) else [])
    for path in COPIES:
        try: reg = json.load(open(path))
        except FileNotFoundError: reg = {"items": []}
        lst = reg["items"] if isinstance(reg, dict) else reg
        have = {i.get("id") for i in lst}
        n = 0
        for it in items:
            if it.get("id") and it["id"] not in have:
                lst.append(it); have.add(it["id"]); n += 1
        json.dump(reg, open(path, "w"), indent=1)
        print("%s: +%d from %s (now %d items)" % (path, n, fn, len(lst)))
