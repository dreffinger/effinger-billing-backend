# PLAIN ENGLISH (board_apply - what the Insurance Refresh Board will show once it has applied a run file, 11/25/2026)
# Decides: nothing in AMD, nothing on the board. It is the board page's own apply rules, written out in Python, so a run can
#   work out BEFORE it uploads its board_updates_<stamp>.json what the board will look like afterwards - which cards will be on
#   William's turn, with what ask and how many dollars. The evening 'current face sheets needed' email is built from that answer
#   (facesheets_needed.py), which is what keeps the email and the board saying the same thing.
# Rules it uses (the same ones as boards/templates/tracker.html since 11/25/2026 - change both together;
#   tools/selftest/test_board_page.js proves the page, tools/selftest/test_facesheets_needed.py proves this file):
#   1. A run file speaks for the moment its run READ the board: its `asof`, else the earlier of its `created` and the time
#      Drive received it.
#   2. A card's own word is the latest of: stateAt (the file time of the last file whose status / need / why were applied),
#      William's newest note (every action of his writes one), and `updated` when somebody else wrote it (a chat session
#      writing the board directly - told apart because the page stamps syncAt with the same value when IT writes updated).
#   3. A file's status / need / why apply only when the file is newer than the card's own word; its notes and checks always land.
#   4. notes / checks / api only ever grow on a card that exists - whether they arrive in `append` or inside `set` - and an
#      entry already there is not added twice. `updated`, stateAt and syncAt never come from a file.
#   5. An op that changes nothing writes nothing.
#   The charge-facility badge rules (which badge a card keeps) are the page's own and are not repeated here: they decide a
#   label, never whose turn a card is.
# Never touches: AMD, Drive, the board. Only the dicts it is given.
# Usage: import board_apply as ba; rows = {id: card}; ba.apply_file(rows, file_body, now_iso); ba.turn_of(rows[id])
# ---
import copy, datetime, json, re

BOARD_APPLY_VERSION = "2026-11-25.1"
LISTS = ("notes", "checks", "api")
STATE_KEYS = ("status", "need", "why")
PAGE_OWN = ("updated", "stateAt", "syncAt")
NEW_ROW = {"patient": "", "dob": "", "facility": "", "amdid": "", "mbi": "", "insid": "", "inscarrier": "", "insplans": "",
           "lastfac": "", "lastdos": "", "need": "", "why": "", "amount": 0, "status": "claude", "notes": []}


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


_ISO = re.compile(r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d)(?::(\d\d)(\.\d+)?)?\s*(Z|[+-]\d\d:?\d\d)?$")


def tms(t):
    """Milliseconds of an ISO time; 0 when it cannot be read (the page's Date.parse). A time with no zone is read as UTC."""
    m = _ISO.match(str(t or "").strip())
    if not m:
        return 0
    try:
        base = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)),
                                 int(m.group(6) or 0), tzinfo=datetime.timezone.utc)
    except ValueError:
        return 0
    off = 0
    tz = m.group(8)
    if tz and tz != "Z":
        off = (1 if tz[0] == "+" else -1) * (int(tz[1:3]) * 60 + int(tz[-2:]))
    return int(round((base.timestamp() + float(m.group(7) or 0) - off * 60) * 1000))


def file_time(body, drive_created=None):
    """The moment a run file speaks for: asof, else the earlier of created and the Drive upload time."""
    if isinstance(body, dict) and tms(body.get("asof")):
        return str(body["asof"])
    cands = [t for t in ((body or {}).get("created"), drive_created) if tms(t)]
    return min(cands, key=tms) if cands else ""


def last_william_at(row):
    best = ""
    for n in (row or {}).get("notes") or []:
        if isinstance(n, dict) and n.get("who") == "William" and tms(n.get("at")) > tms(best):
            best = str(n.get("at"))
    return best


def last_other_at(row):
    """The newest note that is not William's (a run or a chat)."""
    best = ""
    for n in (row or {}).get("notes") or []:
        if isinstance(n, dict) and n.get("who") != "William" and tms(n.get("at")) > tms(best):
            best = str(n.get("at"))
    return best


def row_state_at(row):
    if not row:
        return ""
    u = str(row.get("updated") or "")
    ext = u if (u and u != str(row.get("syncAt") or "")) else ""
    best = ""
    for t in (str(row.get("stateAt") or ""), last_william_at(row), ext):
        if tms(t) > tms(best):
            best = t
    return best


def turn_of(row):
    s = (row or {}).get("status")
    return "done" if s == "done" else ("william" if s == "william" else "claude")


def amount_of(v):
    """The board's own reading of an amount: a number, or the number a text starts with ('$315.00', '1,250.50')."""
    if isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v) if v == v and abs(v) != float("inf") else 0.0
    m = re.match(r"^-?\d+(?:\.\d+)?", re.sub(r"[$,\s]", "", str(v if v is not None else "")))
    return float(m.group(0)) if m else 0.0


def _add_all(base, extra):
    out = list(base or [])
    for e in (extra if isinstance(extra, list) else [extra]):
        if not any(canon(x) == canon(e) for x in out):
            out.append(e)
    return out


def apply_op(rows, op, ftime, now):
    """Apply one op to rows (id -> card, the `items` collection). Returns 'skip' (another collection), 'kept' (the card
    was left exactly as it was), 'stale' (its status / need / why were held back), 'new' (a card was created), or None."""
    if not isinstance(op, dict):
        raise ValueError("op is not an object")
    col = str(op.get("collection") or "items"); rid = str(op.get("id") or ""); kind = str(op.get("op") or "upsert").lower()
    if col != "items":
        return "skip"
    if not rid:
        raise ValueError("op has no id")
    if kind == "delete":
        rows.pop(rid, None); return None
    cur = rows.get(rid)
    if kind == "replace":
        if not isinstance(op.get("data"), dict):
            raise ValueError("replace needs data")
        if cur is not None and ftime and tms(row_state_at(cur)) > tms(ftime):
            return "stale"
        data = copy.deepcopy(op["data"])
        for k in PAGE_OWN:
            data.pop(k, None)
        if cur is not None:
            his = [n for n in (cur.get("notes") or []) if isinstance(n, dict) and n.get("who") == "William"]
            if his:
                data["notes"] = sorted(_add_all(data.get("notes") if isinstance(data.get("notes"), list) else [], copy.deepcopy(his)),
                                       key=lambda n: tms(n.get("at")) if isinstance(n, dict) else 0)
        data["updated"] = now; data["syncAt"] = now; data["stateAt"] = ftime or now
        rows[rid] = data
        return None
    if kind not in ("upsert", "update", "create", "merge"):
        raise ValueError("unknown op: " + kind)
    setv = op.get("set") if isinstance(op.get("set"), dict) else (op.get("data") if isinstance(op.get("data"), dict) else {})
    app = op.get("append") if isinstance(op.get("append"), dict) else {}
    if cur is None and kind == "update":
        raise ValueError("no such row: items/" + rid)
    patch = copy.deepcopy(setv)
    for k in PAGE_OWN:
        patch.pop(k, None)
    stale = bool(cur is not None and ftime and tms(row_state_at(cur)) > tms(ftime))
    sets_state = any(k in patch for k in STATE_KEYS)
    if stale:
        for k in STATE_KEYS:
            patch.pop(k, None)
    lists = {}
    if cur is not None:
        for k in LISTS:
            if isinstance(patch.get(k), list):
                lists[k] = patch.pop(k)
    for k, v in app.items():
        lists[k] = (lists.get(k) or []) + (v if isinstance(v, list) else [v])
    for k, extra in lists.items():
        base = patch[k] if isinstance(patch.get(k), list) else ((cur or {}).get(k) if isinstance((cur or {}).get(k), list) else [])
        patch[k] = _add_all(base, extra)
    if cur is not None:
        diff = {k: v for k, v in patch.items() if canon(cur.get(k)) != canon(v)}
        applies = sets_state and not stale and bool(ftime)
        next_state = ftime if applies else row_state_at(cur)
        if not diff:
            if applies and tms(ftime) > tms(cur.get("stateAt")):
                cur["stateAt"] = ftime
            return "stale" if (stale and sets_state) else "kept"
        if not all(k == "chargefac" for k in diff):
            diff["updated"] = now; diff["syncAt"] = now
            if next_state and next_state != str(cur.get("stateAt") or ""):
                diff["stateAt"] = next_state
        cur.update(diff)
        return "stale" if (stale and sets_state) else None
    doc = copy.deepcopy(NEW_ROW); doc["patient"] = rid.upper(); doc["created"] = now
    doc.update(patch)
    doc["updated"] = now; doc["syncAt"] = now; doc["stateAt"] = ftime or now
    rows[rid] = doc
    return "new"


def apply_file(rows, body, now, drive_created=None):
    """Apply one run file. Returns counts {ops, kept, stale, new, skipped, failed, ftime}."""
    out = {"ops": 0, "kept": 0, "stale": 0, "new": 0, "skipped": 0, "failed": 0, "ftime": file_time(body, drive_created), "errors": []}
    for op in (body or {}).get("ops") or []:
        try:
            r = apply_op(rows, op, out["ftime"], now)
        except Exception as e:
            out["failed"] += 1; out["errors"].append(str(e)[:100]); continue
        if r == "skip":
            out["skipped"] += 1
        elif r == "kept":
            out["kept"] += 1
        else:
            out["ops"] += 1
            if r == "stale":
                out["stale"] += 1
            if r == "new":
                out["new"] += 1
    return out


def apply_files(rows, files, now):
    """files: list of (drive_created_iso, title, body) - applied oldest first, as the page does."""
    return [(title, apply_file(rows, body, now, created)) for created, title, body in sorted(files, key=lambda f: (str(f[0]), str(f[1])))]
