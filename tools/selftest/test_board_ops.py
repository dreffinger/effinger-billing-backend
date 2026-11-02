#!/usr/bin/env python3
# PLAIN ENGLISH (self-test, 11/2/2026) - proves offline that board update files never carry `updated` in a set and that a new card
#   on a chart that already has cards is linked as a twin (or appended to when it is the same work item), never merged.
#   Run: python3 tools/selftest/test_board_ops.py
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "helpers"))
import board_ops as b
FAILS = []
def check(n, c):
    print(("ok   " if c else "FAIL ") + n); (c or FAILS.append(n))
doc = {"schema": "irb-board-updates/1", "created": "2026-11-02T20:00:00Z", "ops": [
    {"op": "upsert", "collection": "items", "id": "a", "set": {"status": "done", "updated": "2026-11-02T19:00:00Z"}},
    {"op": "update", "collection": "items", "id": "b", "set": {"updated": "x", "need": "n"}},
    {"op": "replace", "collection": "items", "id": "c", "data": {"patient": "P", "updated": "x", "status": "claude"}}]}
b.clean_file(doc)
check("no set carries updated", all("updated" not in (o.get("set") or {}) and "updated" not in (o.get("data") or {}) for o in doc["ops"]))
check("status/need kept by default", doc["ops"][0]["set"]["status"] == "done" and doc["ops"][1]["set"]["need"] == "n")
d2 = {"ops": [{"op": "upsert", "id": "a", "set": {"status": "x", "why": "y", "need": "z", "amount": 1}}, {"op": "replace", "id": "c", "data": {"status": "claude"}}]}
b.clean_file(d2, strict=True)
check("strict strips status/need/why on existing rows, keeps other fields", d2["ops"][0]["set"] == {"amount": 1} and d2["ops"][1]["data"]["status"] == "claude")
items = [{"id": "tully-1", "amdid": "17471204", "status": "done"}, {"id": "tully-2", "amdid": "17471204", "status": "claude"}, {"id": "z", "amdid": "45447, 17476874", "status": "william"}]
check("twin_ids finds both cards on the chart", b.twin_ids(items, "17471204") == ["tully-1", "tully-2"])
check("twin_ids matches a listed chart", b.twin_ids(items, "17476874") == ["z"])
ops = b.plan_new_row(items, {"id": "tully-3", "amdid": "17471204", "patient": "T", "status": "william", "updated": "bad"}, now="N")
new = ops[0]["set"]
check("new distinct card carries twins + naming note, no updated", new["twins"] == ["tully-1", "tully-2"] and "updated" not in new and "tully-1 (done)" in new["notes"][-1]["text"] and "tully-2 (claude)" in new["notes"][-1]["text"])
check("reciprocal twins on both other cards", [(o["id"], o["set"]["twins"]) for o in ops[1:]] == [("tully-1", ["tully-3"]), ("tully-2", ["tully-3"])])
ops = b.plan_new_row(items, {"id": "tully-9", "amdid": "17471204", "need": "resend"}, same_item=True, now="N")
check("same work item appends to the open card, no new row", len(ops) == 1 and ops[0]["id"] == "tully-2" and ops[0]["set"] == {} and ops[0]["append"]["notes"])
ops = b.plan_new_row(items, {"id": "fresh", "amdid": "999"}, now="N")
check("chart with no card -> plain new row, no twins", len(ops) == 1 and "twins" not in ops[0]["set"])
check("existing id is appended, never recreated", b.plan_new_row(items, {"id": "z", "amdid": "45447", "need": "q"}, now="N")[0]["set"] == {})
print("FAILS:", FAILS or "none"); sys.exit(1 if FAILS else 0)
