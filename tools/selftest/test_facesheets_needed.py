#!/usr/bin/env python3
# PLAIN ENGLISH (self-test, 11/25/2026) - proves offline, with invented cards only, that
#   (1) board_apply.py applies a run file by the board page's own rules: of several waiting files the NEWEST one's status / need /
#       why win; William's action after a file was written still wins (measured against `asof`, the time the run read the board);
#       a chat's direct write is respected; notes / checks / api only ever grow, even when a file sends a whole card again; an op
#       that changes nothing changes nothing; an amount typed as text is read as its number;
#   (2) facesheets_needed.py writes the evening 'current face sheets needed' email from exactly the cards that will be on William's
#       turn once the board has applied the run's file - same count, same dollars as the board's "Your turn" tile - and says
#       'none needed today' when there are none;
#   (3) it names what the run must settle first: an answer of William's nobody replied to, a chart the feed sweep says cannot be
#       claimed with no card on his turn, and an ask whose chart has nothing waiting any more;
#   (4) a hand-back is ONE op that sets status 'william', rewrites the need and carries the reply note;
#   (5) the register it writes for the repository holds no name and no birth date;
#   (6) the mirror refuses an older copy of either helper (their version lines are in tools/mirror/mirror.py).
#   Run: python3 tools/selftest/test_facesheets_needed.py
import json, os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "helpers"))
import board_apply as ba
import facesheets_needed as fn

FAILS = []


def check(n, c, detail=None):
    print(("ok   " if c else "FAIL ") + n + ("" if c or detail is None else "  -> %r" % (detail,)))
    (c or FAILS.append(n))


def card(**kw):
    r = {"patient": "TESTCARD,ONE", "dob": "", "facility": "", "amdid": "", "mbi": "", "need": "old need", "why": "", "amount": 0,
         "status": "claude", "notes": [], "created": "2026-10-01T00:00:00Z", "updated": "2026-10-01T00:00:00Z"}
    r.update(kw); return r


def f(created, ops, **kw):
    d = {"schema": "irb-board-updates/1", "source": "test", "created": created, "ops": ops}
    d.update(kw); return d


NOW = "2026-11-25T03:00:00.000Z"

# ---------- (1) the apply rules
rows = {"x": card(notes=[{"who": "William", "text": "my answer", "at": "2026-11-10T00:00:00Z"}], updated="2026-11-10T00:00:00Z")}
ba.apply_files(rows, [
    ("2026-11-20T00:00:00Z", "a", f("2026-11-20T00:00:00Z", [{"op": "upsert", "id": "x", "set": {}, "append": {"checks": [{"ok": "no", "src": "a", "result": "r", "when": "1"}]}}])),
    ("2026-11-21T00:00:00Z", "b", f("2026-11-21T00:00:00Z", [{"op": "upsert", "id": "x", "set": {"status": "william", "need": "N2"}, "append": {"notes": [{"who": "Claude", "text": "still needed", "at": "2026-11-21T00:00:00Z"}]}}])),
    ("2026-11-22T00:00:00Z", "c", f("2026-11-22T00:00:00Z", [{"op": "upsert", "id": "x", "set": {"why": "because c"}}])),
], NOW)
check("1. of three waiting files the later one hands the card back and the newest one's why lands",
      rows["x"]["status"] == "william" and rows["x"]["need"] == "N2" and rows["x"]["why"] == "because c", rows["x"])
check("1. every file's checks and notes landed", len(rows["x"]["checks"]) == 1 and len(rows["x"]["notes"]) == 2)
check("1. the card carries the state time of the newest file and the page's own stamp", rows["x"]["stateAt"] == "2026-11-22T00:00:00Z" and rows["x"]["syncAt"] == rows["x"]["updated"] == NOW, rows["x"])

ans = lambda: card(status="claude", need="his answer is here", notes=[{"who": "William", "text": "answer", "at": "2026-11-24T12:00:00Z"}], updated="2026-11-24T12:00:00Z")
rows = {"y": ans(), "z": ans(), "v": ans()}
ba.apply_file(rows, f("2026-11-24T11:00:00Z", [{"op": "upsert", "id": "y", "set": {"status": "william", "need": "old ask"}, "append": {"notes": [{"who": "Claude", "text": "late note", "at": "2026-11-24T11:00:00Z"}]}}]), NOW)
ba.apply_file(rows, f("2026-11-24T13:00:00Z", [{"op": "upsert", "id": "z", "set": {"status": "william", "need": "asked before he answered"}}], asof="2026-11-24T11:00:00Z"), NOW)
ba.apply_file(rows, f("2026-11-24T15:00:00Z", [{"op": "upsert", "id": "v", "set": {"status": "william", "need": "body time later than the upload"}}]), NOW, drive_created="2026-11-24T11:30:00Z")
check("1. a file written before his answer does not take the card back, but its note lands",
      rows["y"]["status"] == "claude" and rows["y"]["need"] == "his answer is here" and any(n["text"] == "late note" for n in rows["y"]["notes"]), rows["y"])
check("1. a file uploaded after his answer but READ before it (asof) does not take the card back", rows["z"]["status"] == "claude", rows["z"]["status"])
check("1. a body time later than the real upload is not trusted over the upload time", rows["v"]["status"] == "claude", rows["v"]["status"])

whole = {"patient": "WHOLECARD,TWO", "amdid": "1234567", "status": "william", "need": "number needed",
         "notes": [{"who": "Claude", "text": "created by the run", "at": "2026-11-24T06:00:00Z"}],
         "checks": [{"ok": "human", "src": "William", "result": "number", "when": "1/1"}]}
rows = {"w": card(patient="WHOLECARD,TWO", amdid="1234567", status="claude", need="number needed", updated="2026-11-24T07:00:00Z",
                  notes=[{"who": "Claude", "text": "created by the run", "at": "2026-11-24T06:00:00Z"}, {"who": "William", "text": "HIS ANSWER", "at": "2026-11-24T07:00:00Z"}],
                  checks=[{"ok": "human", "src": "William", "result": "number", "when": "1/1"}, {"ok": "ok", "src": "later run", "result": "kept", "when": "1/2"}]),
        "r": card(patient="REPLACEDCARD,THREE", notes=[{"who": "Claude", "text": "old", "at": "2026-11-01T00:00:00Z"}, {"who": "William", "text": "HIS OLD WORD", "at": "2026-11-02T00:00:00Z"}], updated="2026-11-02T00:00:00Z")}
r1 = ba.apply_file(rows, f("2026-11-24T06:00:00Z", [{"op": "upsert", "id": "w", "set": whole}]), NOW)
ba.apply_file(rows, f("2026-11-24T08:00:00Z", [{"op": "replace", "id": "r", "data": {"patient": "REPLACEDCARD,THREE", "status": "claude", "need": "rewritten", "notes": [{"who": "Claude", "text": "new", "at": "2026-11-24T08:00:00Z"}]}}]), NOW)
check("1. a whole card sent again cannot wipe his answer or a later check, and doubles nothing",
      [n["text"] for n in rows["w"]["notes"]] == ["created by the run", "HIS ANSWER"] and len(rows["w"]["checks"]) == 2 and rows["w"]["status"] == "claude", rows["w"])
check("1. an op that changes nothing is counted as kept or held back, never as a change", r1["ops"] - r1["stale"] == 0 and rows["w"]["updated"] == "2026-11-24T07:00:00Z", r1)
check("1. a replace keeps William's own notes", rows["r"]["need"] == "rewritten" and [n["text"] for n in rows["r"]["notes"]] == ["HIS OLD WORD", "new"], rows["r"]["notes"])

rows = {"d": card(status="done", need="closed by a chat", stateAt="2026-11-01T00:00:00Z", syncAt="2026-11-01T00:00:00Z", updated="2026-11-24T10:00:00Z"),
        "e": card(status="claude", stateAt="2026-11-01T00:00:00Z", syncAt="2026-11-01T00:00:00Z", updated="2026-11-24T10:00:00Z")}
ba.apply_file(rows, f("2026-11-24T09:00:00Z", [{"op": "upsert", "id": "d", "set": {"status": "william", "need": "written before the chat closed it"}}]), NOW)
ba.apply_file(rows, f("2026-11-24T11:00:00Z", [{"op": "upsert", "id": "e", "set": {"status": "william", "need": "newer than the chat write"}}]), NOW)
check("1. a card a chat closed after the file was written stays closed; a newer file applies", rows["d"]["status"] == "done" and rows["e"]["status"] == "william", (rows["d"]["status"], rows["e"]["status"]))
check("1. amounts typed as text are read as their number", [ba.amount_of(v) for v in (100, "$315.00", "$0 open (visit 19456964 settled)", "", "1,250.50", None)] == [100.0, 315.0, 0.0, 0.0, 1250.5, 0.0])
check("1. times compare by the clock, not by their spelling", ba.tms("2026-11-19T09:35:00Z") > ba.tms("2026-11-19T09:34:59.999Z") and ba.tms("2026-11-19T04:35:00-05:00") == ba.tms("2026-11-19T09:35:00Z"))

# ---------- (2) + (3) the email and the checks
board = {
    "alpha-17470001": card(patient="ALPHATEST,ANN", dob="01/02/1940", amdid="17470001", facility="HCA TEST HOSPITAL", status="william", amount=421,
                           need="HCA FACESHEET OR CARD NEEDED ($421): no plan anywhere. More detail here."),
    "bravo-17470002": card(patient="BRAVOTEST,BOB", amdid="17470002", status="william", amount="$315.00", need="CONFIRM OR VOID: $315 written off after the date of death."),
    "charlie-17470003": card(patient="CHARLIETEST,CY", amdid="17470003", status="claude", amount=639, need="CHP member number needed",
                             notes=[{"who": "Claude", "text": "asked", "at": "2026-11-12T00:00:00Z"}, {"who": "William", "text": "same number as before", "at": "2026-11-19T07:39:00Z"}], updated="2026-11-19T07:39:00Z"),
    "delta-17470004": card(patient="DELTATEST,DEE", amdid="17470004", status="claude", amount=100, need="watching",
                           notes=[{"who": "William", "text": "an answer nobody replied to", "at": "2026-10-11T03:20:00Z"}], updated="2026-10-11T03:20:00Z"),
    "echo-17470005": card(patient="ECHOTEST,ED", amdid="17470005", status="william", amount=901, need="FACESHEET OR CARD NEEDED ($901): five hospital visits."),
    "foxtrot-done": card(patient="FOXTROTTEST,FAY", amdid="17470006", status="done", amount=50, need="done"),
}
run_file = f("2026-11-25T00:50:00Z", [fn.handback_op("charlie-17470003", "CHP MEMBER NUMBER NEEDED ($639): CHP will not answer to the Medicare number.",
                                                     "The number you gave is the one already on the chart; CHP refuses it. Still needed: the CHP member number.", amount=639, at="2026-11-25T00:50:00Z")],
             asof="2026-11-25T00:40:00Z")
sweep = {"visits": [{"visit": "vst1", "chart": "pat17470001", "state": "EMPTY insurance order", "next": "for William: the chart has 0 open medical plans now", "save": None},
                    {"visit": "vst2", "chart": "pat17470009", "state": "EMPTY insurance order", "next": "the owner's approved file", "save": "for William: Medicare names another primary payer"},
                    {"visit": "vst3", "chart": "pat17470010", "state": "EMPTY insurance order", "next": "waits for the clinician move", "save": "a chat session"}]}
outstanding = {"rows": [{"patientid": 17470003, "insbalance": 639.0, "visitid": 1}]}
r = fn.build(board, run_file, sweep=sweep, outstanding=outstanding, stamp="2026-11-25T0040Z", when="7:39 PM ET 11/24", now=NOW)
email = r["email"]
check("2. the email counts the cards that will be on his turn after the file is applied (3 already there + 1 handed back)", r["register"]["your_turn"] == 4, r["register"]["your_turn"])
check("2. its dollars are the same cards' dollars, text amounts included", r["register"]["dollars"] == 421 + 315 + 639 + 901, r["register"]["dollars"])
check("2. the email says so in its first line", "4 cards on your turn, $2,276 waiting" in email.split("\n")[0], email.split("\n")[0])
check("2. face sheets first, decisions after", email.index("FACE SHEET / CARD / NUMBER NEEDED (3, $1,961)") < email.index("DECISIONS WAITING ON YOU (1, $315)"), email)
check("2. each line carries the patient, the chart and the one thing needed", "ALPHATEST,ANN - DOB 01/02/1940 - chart 17470001 - HCA TEST HOSPITAL - HCA FACESHEET OR CARD NEEDED ($421): no plan anywhere. - $421" in email, email)
check("2. the card this run handed back is marked new and carries the rewritten need", "CHARLIETEST,CY - chart 17470003 - CHP MEMBER NUMBER NEEDED ($639): CHP will not answer to the Medicare number. - $639  [new on your turn]" in email, email)
check("2. a card on Claude's turn or done is not in the email", "DELTATEST" not in email and "FOXTROTTEST" not in email)
check("2. the board read is not changed by building", board["charlie-17470003"]["status"] == "claude")
check("3. an answer of William's nobody replied to is named", [x["card"] for x in r["checks"]["unanswered"]] == ["delta-17470004"], r["checks"]["unanswered"])
check("3. a chart the sweep says cannot be claimed, with no card on his turn, is named - the clinician-move one is not his",
      [x["chart"] for x in r["checks"]["sweep_missing"]] == ["17470009"], r["checks"]["sweep_missing"])
check("3. an ask whose chart has nothing waiting any more is named (already billed)", [x["card"] for x in r["checks"]["nothing_waiting"]] == ["echo-17470005"], r["checks"]["nothing_waiting"])
r0 = fn.build({"foxtrot-done": board["foxtrot-done"]}, f("2026-11-25T00:50:00Z", []), stamp="s", now=NOW)
check("2. nothing on his turn -> 'none needed today'", "none needed today" in r0["email"] and r0["register"]["your_turn"] == 0, r0["email"])

# ---------- (4) the hand-back op, and the command line end to end
op = run_file["ops"][0]
check("4. a hand-back is ONE op: status william + the need + the reply note", op["set"]["status"] == "william" and op["set"]["need"].startswith("CHP MEMBER NUMBER NEEDED") and op["append"]["notes"][0]["who"] == "Claude" and "updated" not in op["set"], op)
try:
    fn.handback_op("x", "need", ""); check("4. a hand-back without a reply note is refused", False)
except ValueError:
    check("4. a hand-back without a reply note is refused", True)
with tempfile.TemporaryDirectory() as d:
    items = os.path.join(d, "items"); os.makedirs(items)
    for k, v in board.items():
        json.dump(v, open(os.path.join(items, k + ".json"), "w"))
    bf = os.path.join(d, "outbox", "board_updates_T.json")
    py = [sys.executable, os.path.join(ROOT, "scripts", "helpers", "facesheets_needed.py")]
    p1 = subprocess.run(py + ["handback", "--file", bf, "--card", "charlie-17470003", "--need", "CHP MEMBER NUMBER NEEDED ($639): still needed.", "--note", "Still needed: the CHP member number.", "--amount", "639", "--asof", "2026-11-25T00:40:00Z", "--source", "test run"], capture_output=True, text=True, cwd=d)
    p2 = subprocess.run(py + ["handback", "--file", bf, "--card", "delta-17470004", "--need", "WILLIAM: which plan?", "--note", "Read your 10/11 note; which plan should it go to?", "--ask", "decision"], capture_output=True, text=True, cwd=d)
    sw = os.path.join(d, "sweep.json"); json.dump({"visits": sweep["visits"][:1]}, open(sw, "w"))
    p3 = subprocess.run(py + ["build", "--items-dir", items, "--file", bf, "--stamp", "T", "--sweep", sw, "--out-dir", os.path.join(d, "outbox"), "--register-dir", os.path.join(d, "registers")], capture_output=True, text=True, cwd=d)
    doc = json.load(open(bf)); reg = json.load(open(os.path.join(d, "registers", "facesheets_needed_T.json"))); mail = open(os.path.join(d, "outbox", "facesheets_email_T.txt")).read()
    check("4. the command line writes the hand-backs into the run's file and keeps asof", p1.returncode == 0 and p2.returncode == 0 and len(doc["ops"]) == 2 and doc["asof"] == "2026-11-25T00:40:00Z", (p1.stderr, p2.stderr))
    check("4. build then reports the board in step with the email (exit 0, SYNC OK)", p3.returncode == 0 and "SYNC OK" in p3.stdout and reg["your_turn"] == 5, p3.stdout[-400:] + p3.stderr[-300:])
    check("4. the email file is what build printed it would send", "5 cards on your turn" in mail and "DELTATEST,DEE" in mail, mail[:200])
    # ---------- (5) the register is safe for the repository
    blob = json.dumps(reg)
    check("5. the register holds no patient name, no birth date and no card id", not any(s in blob for s in ("ALPHATEST", "BRAVOTEST", "CHARLIETEST", "01/02/1940", "alpha-", "charlie-")), blob[:300])
    check("5. it does hold the chart numbers, kinds and dollars", {"charts": ["17470001"], "kind": "facesheet", "amount": 421.0, "new": False} in reg["rows"], reg["rows"])

# ---------- (6) the mirror's markers
mirror = open(os.path.join(ROOT, "tools", "mirror", "mirror.py")).read()
check("6. the mirror refuses an older copy of facesheets_needed.py", ('FACESHEETS_NEEDED_VERSION = "%s"' % fn.FACESHEETS_NEEDED_VERSION) in mirror)
check("6. the mirror refuses an older copy of board_apply.py", ('BOARD_APPLY_VERSION = "%s"' % ba.BOARD_APPLY_VERSION) in mirror)

print("FAILS: " + (", ".join(FAILS) if FAILS else "none"))
sys.exit(1 if FAILS else 0)
