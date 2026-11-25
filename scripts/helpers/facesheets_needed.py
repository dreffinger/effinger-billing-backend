# PLAIN ENGLISH (facesheets_needed - the ONE source of the evening 'current face sheets needed' email and of the board cards behind it, 11/25/2026)
# Decides: nothing in AMD. William 11/25/2026: "insurance refresh boards are showing zero but the facesheets email is showing a
#   bunch that are needed ... they should be synced together and showing the same thing". What had happened: the email was
#   written each night from the previous night's list and a stale copy of the board, the board never received the run files, and
#   a reply that still needed something from him was posted as a note without handing the card back. From 11/25 on:
#     build    - takes the board as this run read it and the run's own board_updates file, works out what the board WILL show
#                once it applies the file (board_apply.py - the board page's own rules), and writes the email from exactly the
#                cards that will be on William's turn: face sheets / cards / numbers first, then decisions. The email's count
#                and dollars are the board's "Your turn" tile. It also lists what the run still has to settle before it sends:
#                answers of his that nobody replied to, charts the feed sweep says cannot be claimed that have no card on his
#                turn, and asks whose chart has nothing waiting any more (already billed - the 11/19 case, twelve of eighteen).
#     handback - writes the op that hands a card back to William: status 'william', the need rewritten, and the reply note, in
#                ONE op. A note alone leaves the card on Claude's turn where he never sees it.
#   The list is never typed from memory, from last night's email, or from a digest.
# Rules it uses: the board page's apply rules (board_apply.py); board files pass through board_ops.clean_file; no name, birth
#   date or member number in the register it writes (chart numbers, kinds and dollars only) - the email text and the board
#   file hold patient data and stay in the workspace / Drive / Gmail.
# Never touches: AMD, the board, Drive, Gmail. The run uploads the file and sends the email text it wrote.
# Usage:
#   python3 facesheets_needed.py build --items-dir <dir of <card id>.json> | --items <items.json> --file <board_updates_<stamp>.json>
#        --stamp <run stamp> [--asof <iso time the board was read>] [--sweep <feed_order_sweep_*.json>]
#        [--outstanding <outstanding_latest.json>] [--out-dir outbox] [--register-dir registers] [--when "7:39 PM ET 11/25"]
#   python3 facesheets_needed.py handback --file <board_updates_<stamp>.json> --card <card id> --need "<what is needed now>"
#        --note "<the reply, in Claude's voice>" [--why "..."] [--amount 421] [--ask facesheet|decision] [--source "<run name>"]
# ---
import argparse, datetime, glob, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_apply as ba
try:
    import board_ops
except Exception:                                        # the gate is optional for a dry look; a run always has it
    board_ops = None

FACESHEETS_NEEDED_VERSION = "2026-11-25.1"
SUBJECT = "current face sheets needed"
# what makes an ask a face sheet / card / number ask (the first sentence of the card's need); everything else is a decision
ASK_FACESHEET = re.compile(r"face ?sheet|\bcard\b|member (id|number|#)|medicare number|\bmbi\b|authori[sz]ation|\bauth\b|"
                           r"does not match medicare|number needed|\bid needed", re.I)
ASK_DECISION = re.compile(r"^\s*(your call|confirm or void|add the carrier|which plan|two visits past)", re.I)


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def money(n):
    n = float(n or 0)
    return ("$%s" % format(int(round(n)), ",")) if abs(n - round(n)) < 0.005 else ("$%s" % format(round(n, 2), ",.2f"))


def headline(need):
    """The one thing needed now - the board's own rule: the need's first sentence, its 'WILLIAM:' style prefix dropped."""
    s = re.sub(r"^\s*(?:WILLIAM(?: FLAG)?|CLAUDE|DONE[^:]{0,40}|RESOLVED[^:]{0,40}|CLOSED[^:]{0,40}|Rebilled[^:]{0,40})\s*:\s*", "",
               str(need or ""), flags=re.I).strip()
    if not s:
        return ""
    m = re.match(r"^([\s\S]{15,230}?[.!?])(?=\s|$)", s)
    h = m.group(1) if m else s
    if len(h) > 230:
        cut = h.rfind(" ", 0, 215)
        h = h[: cut if cut > 80 else 215] + "…"
    return h


def kind_of(row):
    k = str(row.get("ask") or "").lower()
    if k in ("facesheet", "decision"):
        return k
    h = headline(row.get("need"))
    if ASK_DECISION.search(h):
        return "decision"
    return "facesheet" if ASK_FACESHEET.search(h) else "decision"


def charts_of(row):
    return [n for n in re.findall(r"\d+", str(row.get("amdid") or "")) if 4 <= len(n) <= 9]


def load_items(items_dir=None, items_file=None):
    rows = {}
    if items_dir:
        for p in sorted(glob.glob(os.path.join(items_dir, "*.json"))):
            rows[os.path.basename(p)[:-5]] = json.load(open(p))
    if items_file:
        data = json.load(open(items_file))
        for r in (data if isinstance(data, list) else data.get("items") or list(data.values())):
            if isinstance(r, dict) and r.get("id"):
                rows[str(r["id"])] = r
    return rows


def sweep_blocked(sweep):
    """chart -> [visit ids] the feed order sweep lists as waiting on William (an empty insurance order it could not settle)."""
    out = {}
    for v in (sweep or {}).get("visits") or []:
        text = " ".join(str(v.get(k) or "") for k in ("next", "save"))
        if "EMPTY" in str(v.get("state") or "") and re.search(r"for William", text):
            chart = re.sub(r"\D", "", str(v.get("chart") or ""))
            if chart:
                out.setdefault(chart, []).append(re.sub(r"\D", "", str(v.get("visit") or "")))
    return out


def outstanding_by_chart(outstanding):
    out = {}
    for r in (outstanding or {}).get("rows") or []:
        c = str(r.get("patientid") or "")
        e = out.setdefault(c, {"n": 0, "dollars": 0.0})
        e["n"] += 1; e["dollars"] += float(r.get("insbalance") or 0)
    return out


def build(rows_before, body, asof=None, sweep=None, outstanding=None, stamp="", when="", now=None):
    """Returns {'email': text, 'subject': SUBJECT, 'rows': [...], 'checks': {...}, 'register': {...}}. Changes nothing."""
    now = now or now_iso()
    before = {k: dict(v) for k, v in rows_before.items()}
    after = json.loads(json.dumps(rows_before))
    body = dict(body or {})
    if asof:
        body["asof"] = asof
    res = ba.apply_file(after, body, now)
    mine = [(rid, r) for rid, r in after.items() if ba.turn_of(r) == "william"]
    mine.sort(key=lambda x: (str(x[1].get("patient") or "").upper(), -ba.amount_of(x[1].get("amount"))))
    lines = {"facesheet": [], "decision": []}
    reg_rows = []
    for rid, r in mine:
        k = kind_of(r)
        was = before.get(rid)
        new = was is None or ba.turn_of(was) != "william"
        amt = ba.amount_of(r.get("amount"))
        bits = [str(r.get("patient") or rid)]
        if r.get("dob"):
            bits.append("DOB " + str(r.get("dob")))
        if charts_of(r):
            bits.append("chart " + ", ".join(charts_of(r)))
        fac = str(r.get("facility") or r.get("lastfac") or "").strip()
        if fac:
            bits.append(fac)
        bits.append(headline(r.get("need")) or "(nothing written on the card)")
        if amt > 0:
            bits.append(money(amt))
        lines[k].append(" - ".join(bits) + ("  [new on your turn]" if new else ""))
        reg_rows.append({"charts": charts_of(r), "kind": k, "amount": round(amt, 2), "new": bool(new)})
    total = sum(x["amount"] for x in reg_rows)
    fs_total = sum(x["amount"] for x in reg_rows if x["kind"] == "facesheet")
    dc_total = sum(x["amount"] for x in reg_rows if x["kind"] == "decision")
    # ---- what the run still has to settle before the email goes out
    checks = {"unanswered": [], "sweep_missing": [], "nothing_waiting": []}
    for rid, r in after.items():
        if ba.turn_of(r) == "claude" and ba.tms(ba.last_william_at(r)) > ba.tms(ba.last_other_at(r)):
            checks["unanswered"].append({"card": rid, "charts": charts_of(r), "answered": ba.last_william_at(r)})
    blocked = sweep_blocked(sweep)
    open_by_chart = {}
    for rid, r in after.items():
        if ba.turn_of(r) != "done":
            for c in charts_of(r):
                open_by_chart.setdefault(c, []).append((rid, r))
    for chart, visits in sorted(blocked.items()):
        cards = open_by_chart.get(chart) or []
        ok = any(ba.turn_of(r) == "william" or ba.tms(ba.last_william_at(r)) > ba.tms(ba.last_other_at(r)) for _, r in cards)
        if not ok:
            checks["sweep_missing"].append({"chart": chart, "visits": visits, "cards": [rid for rid, _ in cards]})
    if outstanding is not None:
        owing = outstanding_by_chart(outstanding)
        for rid, r in mine:
            cs = charts_of(r)
            if kind_of(r) != "facesheet" or not cs:
                continue
            if not any(c in blocked or owing.get(c, {}).get("n") for c in cs):
                checks["nothing_waiting"].append({"card": rid, "charts": cs})
    # ---- the email
    n = len(mine)
    head = "Current face sheets needed - %s%s: " % (when or "evening run", (" (run %s)" % stamp) if stamp else "")
    if not n:
        email = head + "none needed today. Nothing is on your turn on the Insurance Refresh Board."
    else:
        out = [head + "%d card%s on your turn, %s waiting. This is the Insurance Refresh Board's \"Your turn\" list - the tile there reads %d and %s once the board has loaded this run's file."
               % (n, "" if n == 1 else "s", money(total), n, money(total)), ""]
        if lines["facesheet"]:
            out.append("FACE SHEET / CARD / NUMBER NEEDED (%d, %s):" % (len(lines["facesheet"]), money(fs_total)))
            out += ["%d. %s" % (i, t) for i, t in enumerate(lines["facesheet"], 1)]
            out.append("")
        if lines["decision"]:
            out.append("DECISIONS WAITING ON YOU (%d, %s):" % (len(lines["decision"]), money(dc_total)))
            out += ["%d. %s" % (i, t) for i, t in enumerate(lines["decision"], 1)]
            out.append("")
        out.append("Drop the facesheet or card in Drive (bht hca / tmh / PCC facesheets) or paste it on the board card and press Post -> Claude; "
                   "the next run adds the plan and sends the claims.")
        email = "\n".join(out)
    register = {"what": "face sheets needed (facesheets_needed.py %s) - chart numbers, kinds and dollars only" % FACESHEETS_NEEDED_VERSION,
                "stamp": stamp, "at": now, "asof": body.get("asof") or "", "your_turn": n, "dollars": round(total, 2),
                "facesheet": {"n": len(lines["facesheet"]), "dollars": round(fs_total, 2)},
                "decision": {"n": len(lines["decision"]), "dollars": round(dc_total, 2)},
                "rows": reg_rows,
                "file": {k: res[k] for k in ("ops", "kept", "stale", "new", "failed")},
                "checks": {"unanswered": [{"charts": x["charts"], "answered": x["answered"]} for x in checks["unanswered"]],
                           "sweep_missing": [{"chart": x["chart"], "visits": x["visits"]} for x in checks["sweep_missing"]],
                           "nothing_waiting": [{"charts": x["charts"]} for x in checks["nothing_waiting"]]}}
    return {"subject": SUBJECT, "email": email, "rows": reg_rows, "checks": checks, "register": register, "after": after, "file": res}


def handback_op(card, need, note, why=None, amount=None, ask=None, at=None):
    """ONE op: the card goes back to William with the need rewritten and the reply note."""
    if not (card and str(need or "").strip() and str(note or "").strip()):
        raise ValueError("a hand-back needs the card, the need and the reply note")
    setv = {"status": "william", "need": str(need).strip()}
    if why:
        setv["why"] = str(why)
    if amount is not None:
        setv["amount"] = amount
    if ask:
        setv["ask"] = ask
    return {"op": "upsert", "collection": "items", "id": card, "set": setv,
            "append": {"notes": [{"who": "Claude", "text": str(note).strip(), "at": at or now_iso()}]}}


def _load_file(path, source=None, asof=None):
    if os.path.exists(path):
        return json.load(open(path))
    t = now_iso()
    doc = {"schema": "irb-board-updates/1", "source": source or "billing run", "created": t, "ops": []}
    if asof:
        doc["asof"] = asof
    return doc


def _save_file(path, doc):
    if board_ops is not None:
        board_ops.clean_file(doc)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    json.dump(doc, open(path, "w"), indent=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description="the one source of the 'current face sheets needed' email and its board cards")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--items-dir"); b.add_argument("--items"); b.add_argument("--file", required=True); b.add_argument("--stamp", required=True)
    b.add_argument("--asof"); b.add_argument("--sweep"); b.add_argument("--outstanding"); b.add_argument("--out-dir", default="outbox")
    b.add_argument("--register-dir", default="registers"); b.add_argument("--when", default=""); b.add_argument("--source")
    h = sub.add_parser("handback")
    h.add_argument("--file", required=True); h.add_argument("--card", required=True); h.add_argument("--need", required=True)
    h.add_argument("--note", required=True); h.add_argument("--why"); h.add_argument("--amount", type=float); h.add_argument("--ask", choices=["facesheet", "decision"])
    h.add_argument("--source"); h.add_argument("--asof")
    a = ap.parse_args(argv)
    if a.cmd == "handback":
        doc = _load_file(a.file, a.source, a.asof)
        op = handback_op(a.card, a.need, a.note, a.why, a.amount, a.ask)
        doc["ops"] = [o for o in doc.get("ops") or [] if not (o.get("id") == a.card and (o.get("set") or {}).get("status") == "william")] + [op]
        _save_file(a.file, doc)
        print("RESULT handback: card %s back on William's turn in %s (%d ops in the file)" % (a.card, a.file, len(doc["ops"])))
        return 0
    if not (a.items_dir or a.items):
        ap.error("build needs --items-dir or --items (the board as this run read it)")
    rows = load_items(a.items_dir, a.items)
    doc = _load_file(a.file, a.source, a.asof)
    if a.asof:
        doc["asof"] = a.asof
    if not doc.get("asof"):
        print("NOTE: the file has no asof (the time the board was read) - pass --asof; without it the board measures this file by its upload time")
    sweep = json.load(open(a.sweep)) if a.sweep else None
    outstanding = json.load(open(a.outstanding)) if a.outstanding else None
    r = build(rows, doc, sweep=sweep, outstanding=outstanding, stamp=a.stamp, when=a.when)
    _save_file(a.file, doc)                               # the file as it will be uploaded: asof on it, through the gate
    os.makedirs(a.out_dir, exist_ok=True); os.makedirs(a.register_dir, exist_ok=True)
    ep = os.path.join(a.out_dir, "facesheets_email_%s.txt" % a.stamp)
    open(ep, "w").write(r["email"] + "\n")
    rp = os.path.join(a.register_dir, "facesheets_needed_%s.json" % a.stamp)
    json.dump(r["register"], open(rp, "w"), indent=1)
    reg = r["register"]; ck = r["checks"]
    print("board read: %d cards | file: %d ops (%d change, %d already there, %d held back for his newer word, %d new cards, %d failed)"
          % (len(rows), len(doc.get("ops") or []), r["file"]["ops"], r["file"]["kept"], r["file"]["stale"], r["file"]["new"], r["file"]["failed"]))
    for x in ck["unanswered"]:
        print("CHECK unanswered: card %s - William answered %s and nothing replied; act on it, then reply (and hand it back if something is still needed)" % (x["card"], x["answered"]))
    for x in ck["sweep_missing"]:
        print("CHECK not on his turn: chart %s (visits %s) cannot be claimed - the feed sweep waits for William - but no open card for it is on his turn%s"
              % (x["chart"], ", ".join(x["visits"]), (" (cards: %s)" % ", ".join(x["cards"])) if x["cards"] else " (no card at all)"))
    for x in ck["nothing_waiting"]:
        print("CHECK nothing waiting: card %s asks for a face sheet / number but chart %s has no open insurance balance and no visit without a plan - read the chart; if it was billed, reply and close the ask"
              % (x["card"], ", ".join(x["charts"])))
    nck = sum(len(v) for v in ck.values())
    print("RESULT facesheets_needed %s: %d on William's turn, %s (face sheets %d %s; decisions %d %s) | email -> %s | register -> %s | %s"
          % (a.stamp, reg["your_turn"], money(reg["dollars"]), reg["facesheet"]["n"], money(reg["facesheet"]["dollars"]),
             reg["decision"]["n"], money(reg["decision"]["dollars"]), ep, rp,
             "SYNC OK - send the email text as written" if not nck else "%d CHECK line(s) above - settle them (ops in the file), run build again, then send" % nck))
    return 0 if not nck else 3


if __name__ == "__main__":
    sys.exit(main())
