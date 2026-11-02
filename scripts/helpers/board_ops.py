# PLAIN ENGLISH (board_ops - the one gate every board_updates_*.json file passes through, 11/2/2026)
# Decides: nothing in AMD, nothing on the board. Pure file logic for the Insurance Refresh Board inbox files
#   (schema irb-board-updates/1) so every run builds them the same way:
#   1. NEVER `updated` IN A `set` (William 11/2): the board page stamps a row's `updated` itself when it applies an op. A file that
#      carried `updated` rolled a row's stamp BACKWARDS past William's Post, which also defeated the 9/14 stale-file guard (the page
#      compares row.updated with file.created) - the next run file then overwrote his answer and the card re-asked the same question.
#      clean_file() strips `updated` from every set (upsert / update / replace data of an existing row). `created` stays on a brand-new
#      row only. The page (artifact v30) strips it too; this is the backend half. Status / need / why: the 9/14 rule keeps them out of
#      inbox `set` ops for rows that already exist and are not Claude's to answer - strict=True strips them as well (default off,
#      because a run answering a row on its turn still hands it back with status).
#   2. ONE CARD PER WORK ITEM, TWIN BY AMD CHART NUMBER: before a NEW items row is created, plan_new_row() looks up the existing cards
#      with the same items[].amdid. Same work item -> append to that card (no new row). A distinct work item -> the new row carries
#      `twins` (ids of the other cards on that chart) plus a note naming them, and each other card gets the reciprocal `twins` set and
#      a note. Distinct work items are NEVER merged onto one card.
# Rules it uses: board rows are read inline by the run (ArtifactData) and handed in as a list of dicts; AMD chart number = row['amdid']
#   (first number when the field lists several: 'amdid' may read '45447, 17476874').
# Never touches: AMD, the board, Drive. Only the dict / file it is given.
# Usage: from board_ops import clean_file, plan_new_row, twin_ids; ops = plan_new_row(items, new_row, same_item=False, now=NOW)
#        doc = clean_file(doc); json.dump(doc, open(name, "w"))      |  CLI: python3 board_ops.py <board_updates.json> [--items items.json]
# ---
import json, re, sys, datetime

STATE_KEYS = ("status", "need", "why")


def chart_numbers(row):
    """AMD chart numbers on a card: 'amdid' may hold one number or a list ('45447, 17476874')."""
    return [n for n in re.findall(r"\d+", str((row or {}).get("amdid") or "")) if n]


def is_done(row):
    return str((row or {}).get("status") or "").lower() in ("done", "closed", "dismissed")


def twin_ids(items, amdid, exclude_id=None):
    """Ids of every existing card on the chart (done or open), except exclude_id."""
    want = set(re.findall(r"\d+", str(amdid or "")))
    return [r.get("id") for r in items if r.get("id") and r.get("id") != exclude_id and want & set(chart_numbers(r))]


def _strip_set(s, strict=False):
    dropped = []
    for k in ("updated",) + (STATE_KEYS if strict else ()):
        if k in s:
            dropped.append(k); s.pop(k)
    return dropped


def clean_op(op, strict=False, new_ids=()):
    """Strip `updated` (and, strict, status/need/why on rows not created this file) from one op. Returns the dropped keys."""
    dropped = []
    if isinstance(op.get("set"), dict):
        keys_before = op["set"]
        if strict and op.get("id") in new_ids:
            dropped += _strip_set(keys_before, strict=False)
        else:
            dropped += _strip_set(keys_before, strict=strict)
    d = op.get("data")
    if op.get("op") == "replace" and isinstance(d, dict):
        dropped += _strip_set(d, strict=False)          # a replaced row is new this run: it keeps its state, never `updated`
    return dropped


def clean_file(doc, strict=False):
    """Make a whole irb-board-updates/1 document safe: no `updated` in any set. Returns doc (mutated) ; doc['_stripped'] is not added -
    the dropped keys are returned by clean_file_report()."""
    clean_file_report(doc, strict)
    return doc


def clean_file_report(doc, strict=False):
    new_ids = {o.get("id") for o in doc.get("ops", []) if o.get("op") == "replace"}
    report = []
    for o in doc.get("ops", []):
        d = clean_op(o, strict, new_ids)
        if d:
            report.append((o.get("collection"), o.get("id"), d))
    return report


def plan_new_row(items, row, same_item=False, now=None, existing_ids=None):
    """Ops for a card the run wants to add. items = the board's current items (inline read). row = the new row's fields (must carry id, amdid).
    same_item=True  -> the run is working the SAME item as an existing open card on that chart: append to it (no new row).
    same_item=False -> a distinct work item: new row with `twins` + a note naming the other cards, reciprocal twins on those cards."""
    now = now or datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    rid = row["id"]
    by_id = {r.get("id"): r for r in items}
    if rid in by_id:                                      # the exact card exists: append only, never re-create it
        note = (row.get("notes") or [{"who": "Claude", "text": row.get("need") or "", "at": now}])
        return [{"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"notes": note}}]
    others = twin_ids(items, row.get("amdid"))
    open_others = [i for i in others if not is_done(by_id.get(i))]
    if same_item and open_others:
        tgt = open_others[0]
        note = row.get("notes") or [{"who": "Claude", "text": "%s %s" % (row.get("need") or "", row.get("why") or ""), "at": now}]
        return [{"op": "upsert", "collection": "items", "id": tgt, "set": {}, "append": {"notes": note}}]
    new = {k: v for k, v in row.items() if k not in ("updated",)}
    new.setdefault("created", now)
    ops = []
    if others:
        def label(i):
            r = by_id.get(i) or {}
            return "%s (%s)" % (i, "done" if is_done(r) else (r.get("status") or "open"))
        new["twins"] = others
        new["notes"] = list(new.get("notes") or []) + [{"who": "Claude", "at": now,
            "text": "Twin cards on AMD chart %s: %s. Separate work items - not merged." % (",".join(chart_numbers(row)[:1]), "; ".join(label(i) for i in others))}]
    ops.append({"op": "upsert", "collection": "items", "id": rid, "set": new})
    for i in others:
        r = by_id.get(i) or {}
        merged = sorted(set(r.get("twins") or []) | {rid})
        ops.append({"op": "upsert", "collection": "items", "id": i, "set": {"twins": merged},
                    "append": {"notes": [{"who": "Claude", "at": now, "text": "Twin card %s added on the same AMD chart (a different work item)." % rid}]}})
    return ops


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    doc = json.load(open(a[0]))
    rep = clean_file_report(doc, strict="--strict" in a)
    json.dump(doc, open(a[0], "w"), indent=1)
    print("cleaned %s: %d op(s) had keys stripped" % (a[0], len(rep)))
    for r in rep:
        print("  ", r)
