#!/usr/bin/env python3
# PLAIN ENGLISH (self-test, 11/26/2026) - proves offline, with invented files only, that the Monday scorecard (scripts/helpers/weekly_scorecard.py)
#   (1) reads the four sections' figures from the files the runs keep: collected, owed by days since the date of service (and Sunday's
#       days-since-sent split), denials, credentialing - and the change from last week;
#   (2) marks an input older than its usual refresh STALE on the page, never silently;
#   (3) names an input it cannot read and still writes the scorecard, with that section marked MISSING;
#   (4) writes the Gmail drafts to PREPARE - never a send: only for cards on William's turn, due within 30 days or overdue, with an e-mail address;
#   (5) puts no patient data in any output (no chart or visit id, no Medicare number, no LAST,FIRST name), and its Sunday copy of the ageing
#       file keeps no date of death;
#   (6) gives the page button the LONGHAND background-color property (Gmail strips the background shorthand) and uses the shorthand nowhere;
#   (7) the denials refresh's posted_last_7d block totals the payments POSTED in the window (insurance vs patient, net of take-backs, by
#       carrier) and counts the denial lines by visit - the same block in both copies of denials_refresh.py.
#   Run: python3 tools/selftest/test_weekly_scorecard.py
import collections, datetime, json, os, re, shutil, sys, tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "helpers"))
sys.path.insert(0, os.path.join(ROOT, "tools", "mirror"))
import weekly_scorecard as wsc
import phi_gate

FAILS = []
# The sample Medicare number and LAST,FIRST name are assembled at run time: the privacy gate scrubs every file a mirror commit carries, this one
# included - written out, they would be rewritten and the checks that look for them would prove nothing (the 11/25/2026 rule of the self-tests).
MBI_S = "1EG4" + "TE5MK73"
NAME_S = "TESTCARD" + "," + "ONE"
NOW = datetime.datetime(2026, 11, 30, 6, 30, tzinfo=datetime.timezone.utc)          # a Monday, the cascade's hour
MON = NOW.date(); FROM, TO = MON - datetime.timedelta(days=7), MON - datetime.timedelta(days=1)
CHARTS = ["9100%04d" % i for i in range(1, 9)]; VISITS = ["9200%04d" % i for i in range(1, 9)]


def check(n, c, detail=None):
    print(("ok   " if c else "FAIL ") + n + ("" if c or detail is None else "  -> %r" % (detail,)))
    (c or FAILS.append(n))


def stamp(t): return t.strftime("%Y-%m-%dT%H%MZ")


def put(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh: json.dump(obj, fh)


def world(base, out_age_h=5, aging=True):
    """an invented repository clone + workspace, as the Monday run finds them"""
    repo, ws = os.path.join(base, "repo"), os.path.join(base, "ws")
    rb = os.path.join(repo, "reports", "button")
    rows = [(CHARTS[0], VISITS[0], "FLO02", 100.0, 30), (CHARTS[1], VISITS[1], "FLO02", 50.0, 31), (CHARTS[2], VISITS[2], "UNI20", 25.0, 90),      # each on a bucket's edge
            (CHARTS[3], VISITS[3], "FLO99", 40.0, 120), (CHARTS[4], VISITS[4], "HUM01", 60.0, 365), (CHARTS[5], VISITS[5], "BCBS", 30.0, 366)]
    put(os.path.join(rb, "outstanding_latest.json"), {"schema": "outstanding-claims/1", "at": (NOW - datetime.timedelta(hours=out_age_h)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of": MON.isoformat(), "total": 305.0, "visits": 6, "charts": 6,
        "rows": [{"visitid": v, "patientid": p, "carriercode": c, "insbalance": b, "days": d, "dos": (MON - datetime.timedelta(days=d)).isoformat()} for p, v, c, b, d in rows]})
    den_asof = (NOW - datetime.timedelta(hours=5)).strftime("%Y-%m-%d %H:%M UTC")
    put(os.path.join(rb, "working_denials_latest.json"), {"schema": "working-denials-snapshot/1", "asof": den_asof, "visits": [
        {"pid": CHARTS[0], "visitid": VISITS[0], "dispo": "FIX", "status": "OPEN", "open_balance": 100.0, "codes": ["CO/CO16"], "carc": "16", "amt": 100.0, "denied_on": (FROM + datetime.timedelta(days=1)).isoformat()},
        {"pid": CHARTS[1], "visitid": VISITS[1], "dispo": "UNCLASSIFIED", "status": "OPEN", "open_balance": 50.0, "codes": ["CO/CO27"], "carc": "27", "amt": 50.0, "denied_on": (FROM + datetime.timedelta(days=2)).isoformat()},
        {"pid": CHARTS[2], "visitid": VISITS[2], "dispo": "PATIENT", "status": "OPEN", "open_balance": 25.0, "codes": ["PR/PR2"], "carc": "2", "amt": 25.0},
        {"pid": CHARTS[4], "visitid": VISITS[4], "dispo": "COB", "status": "RESOLVED", "open_balance": 0.0, "codes": ["CO/CO22"], "carc": "22", "amt": 60.0}],
        "posted_last_7d": {"from": FROM.isoformat(), "to": TO.isoformat(), "insurance": 4000.0, "patient": 150.0, "takebacks": 75.0, "insurance_lines": 40,
                           "patient_lines": 3, "adjudicated_lines": 50, "by_carrier": {"FLO02": 3000.0, "UNI20": 1000.0},
                           "denials": {"visits": 6, "lines": 8, "dollars": 900.0, "wrong_payer_visits": 2}}})
    for t, pay, mode in ((NOW - datetime.timedelta(days=3, hours=6), 500.0, "live"), (NOW - datetime.timedelta(hours=11, minutes=40), 250.0, "live"),
                         (NOW - datetime.timedelta(days=2), 999.0, "dry"), (NOW - datetime.timedelta(days=9), 777.0, "live"), (NOW - datetime.timedelta(minutes=50), 888.0, "live")):
        put(os.path.join(rb, stamp(t) + ".json"), {"schema": "button-run/1", "stamp": stamp(t), "mode": mode, "ended": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                    "summary": {"posted": {"pay": pay}}})
    if aging:
        put(os.path.join(rb, "aging_latest.json"), {"schema": "ar-aging/1", "asof": (NOW - datetime.timedelta(hours=25)).strftime("%Y-%m-%d %H:%M UTC"), "total": 310.0,
            "by_rec": {"WAIT": {"n": 3, "amt": 150.0}, "CORRECT & RESEND": {"n": 2, "amt": 100.0}, "WRITE OFF": {"n": 1, "amt": 60.0}, "REVIEW": {"n": 0, "amt": 0}}, "rows": []})
    put(os.path.join(repo, "practices", "ehpa", "registers", "tf_writeoff_watch.json"), {"items": [{"id": "watch-a", "status": "open", "visits": [{"vid": VISITS[6], "insbal": 80.0}, {"vid": VISITS[7], "insbal": 20.0, "outcome": "written-off"}]}]})
    d = lambda n: (MON + datetime.timedelta(days=n)).isoformat()
    put(os.path.join(ws, "cred_board_rows.json"), [
        {"id": "pay-aetna", "name": "Aetna recredentialing", "holder": "Dr. Effinger", "due": d(10), "cycle": "36 months", "turn": "william", "need": "Attest the CAQH profile and send the signed form", "contacts": "Provider relations: enroll@aetna-example.org"},
        {"id": "we-license", "name": "Florida medical license", "holder": "Dr. Effinger", "due": d(-5), "cycle": "24 months", "turn": "william", "need": "Renew on the state portal", "contacts": ""},
        {"id": "grp-medicare", "name": "Medicare revalidation", "due": d(20), "cycle": "5 years", "turn": "claude", "need": "Watch PECOS for the notice", "contacts": "pecos@cms-example.gov"},
        {"id": "pay-later", "name": "Humana recredentialing", "due": d(60), "turn": "william", "need": "Not yet", "contacts": "humana@example.org"},
        {"id": "pay-mixed", "name": "Sunshine recredentialing", "due": d(3), "turn": "william", "need": "Card note " + MBI_S + " " + NAME_S, "contacts": "sunshine@example.org"},
        {"id": "we-dea", "name": "DEA registration", "due": d(15), "turn": "done", "need": "Renewed online", "contacts": "dea@example.gov"},
        {"id": "we-board", "name": "Board certification", "due": "TBD", "turn": "william"}])
    t = (NOW - datetime.timedelta(hours=1)).timestamp(); os.utime(os.path.join(ws, "cred_board_rows.json"), (t, t))    # STEP 4b wrote it an hour ago
    put(os.path.join(ws, "cred_check_%s.json" % MON.strftime("%Y%m%d")), {"date": MON.isoformat(), "nppes_changes": [], "leie": {"rows": 80000, "matches": []},
                                                                         "revalidation": {"1": [{"enrollment": "I1", "due": "TBD"}]}, "reminders": []})
    put(os.path.join(ws, "last.json"), {"schema": "weekly-scorecard-week/1", "week_of": (MON - datetime.timedelta(days=7)).isoformat(), "collected_minimum": 3000.0, "owed_total": 400.0})
    return repo, ws


def build(repo, ws, out, *extra):
    argv = ["build", "--repo", repo, "--ws", ws, "--out", out, "--now", NOW.strftime("%Y-%m-%dT%H:%M:%SZ"), "--last", os.path.join(ws, "last.json")] + list(extra)
    rc = wsc.main(argv)
    j = lambda n: json.load(open(os.path.join(out, n % MON.isoformat())))
    return rc, j("scorecard_%s.json"), j("scorecard_week_%s.json"), j("drafts_%s.json"), open(os.path.join(out, "scorecard_%s.html" % MON.isoformat()), encoding="utf-8").read()


def figs(sc):
    return {f["key"]: f for s in sc["sections"].values() for f in s["figures"]}


tmp = tempfile.mkdtemp(prefix="scorecard_test_")
try:
    # ---------- (1) the four sections from invented files
    repo, ws = world(os.path.join(tmp, "a"))
    out = os.path.join(tmp, "a", "outbox")
    rc, sc, wk, dr, page = build(repo, ws, out, "--page-url", "https://claude.ai/artifact/test-scorecard-page")
    F = figs(sc)
    check("1. collected: posted in AdvancedMD = insurance + patient of posted_last_7d, the routines' ERA dollars = the week's live run reports only",
          rc == 0 and F["collected_minimum"]["value"] == 4150.0 and F["collected_insurance"]["value"] == 4000.0 and F["collected_patient"]["value"] == 150.0
          and F["routines_posted"]["value"] == 750.0 and sc["sections"]["collected"]["top_payers"][0] == {"carrier": "FLO02", "dollars": 3000.0}, {k: F[k]["value"] for k in ("collected_minimum", "routines_posted")})
    check("1. owed: the open insurance balance in the six buckets by days since the date of service, and Sunday's wait / resend / write off",
          [F[k]["value"] for k in ("owed_0_30", "owed_31_60", "owed_61_90", "owed_91_120", "owed_121_365", "owed_over_12_months")] == [100.0, 50.0, 25.0, 40.0, 60.0, 30.0]
          and F["owed_total"]["value"] == 305.0 and F["owed_visits"]["value"] == 6 and (F["aging_wait"]["value"], F["aging_resend"]["value"], F["aging_write_off"]["value"]) == (150.0, 100.0, 60.0)
          and "they DIFFER" not in " ".join(sc["sections"]["owed"]["checks"]), sc["sections"]["owed"]["buckets"])
    check("1. denials: the week's denial lines by visit (wrong payer among them), and what is still open on denied visits - cost-share left out",
          (F["denials_new_visits"]["value"], F["denials_new_lines"]["value"], F["denials_wrong_payer_visits"]["value"], F["denial_rate"]["value"]) == (6, 8, 2, 0.16)
          and (F["denied_open_visits"]["value"], F["denied_open_balance"]["value"], F["denied_open_wrong_payer_visits"]["value"]) == (2, 150.0, 1), {k: F[k]["value"] for k in F if k.startswith("deni")})
    items = {i["card"]: i for i in sc["sections"]["credentialing"]["items"]}
    check("1. credentialing: every card due within 30 days or overdue (name, due, days left, need, whose turn) - not the one due in 60 days, not one with no date",
          sorted(items) == ["grp-medicare", "pay-aetna", "pay-mixed", "we-dea", "we-license"] and items["we-license"]["days_left"] == -5 and items["pay-aetna"]["turn"] == "william"
          and items["grp-medicare"]["turn"] == "claude" and F["cred_due_30"]["value"] == 4 and F["cred_overdue"]["value"] == 1
          and any(x.startswith("OVERDUE 5 days: Florida medical license") for x in sc["your_turn"]), sorted(items))
    check("1. the change from last week, the 'Your turn' exceptions (FLO99, the timely-filing watch) and the week document's totals",
          {c["key"]: c["change"] for c in sc["change"]} == {"collected_minimum": 1150.0, "owed_total": -95.0}
          and any(x.startswith("FCC (FLO99): $40 open on 1 visit -") for x in sc["your_turn"]) and any(x.startswith("Timely-filing watch: 1 visit ($80)") for x in sc["your_turn"])
          and wk["week_of"] == MON.isoformat() and wk["period_from"] == FROM.isoformat() and wk["owed_over_12_months"] == 30.0 and wk["collected_minimum"] == 4150.0
          and wk["stale"] == [] and wk["missing"] == [] and "$" not in sc["headline"], (sc["change"], sc["your_turn"], sc["headline"]))

    # ---------- (2) STALE
    repo2, ws2 = world(os.path.join(tmp, "b"), out_age_h=20)
    rc, sc2, wk2, dr2, page2 = build(repo2, ws2, os.path.join(tmp, "b", "outbox"))
    F2 = figs(sc2)
    check("2. an unpaid list 20 hours old (refreshed every 6) is STALE - on its figures, in the week document and on the page, never silently",
          sc2["inputs"]["outstanding"]["status"] == "STALE" and F2["owed_total"]["status"] == "STALE" and F2["owed_total"]["value"] == 305.0
          and wk2["stale"] == [wsc.F_OUT] and "Inputs not current" in page2 and "STALE" in page2 and sc2["sections"]["owed"]["status"] == "STALE"
          and sc2["inputs"]["runs"]["status"] == "ok" and F2["collected_minimum"]["status"] == "ok", sc2["inputs"]["outstanding"])

    # ---------- (3) MISSING
    repo3, ws3 = world(os.path.join(tmp, "c"), aging=False)
    os.remove(os.path.join(ws3, "cred_board_rows.json"))
    out3 = os.path.join(tmp, "c", "outbox")
    rc, sc3, wk3, dr3, page3 = build(repo3, ws3, out3)
    F3 = figs(sc3)
    check("3. an input it cannot read is named and its figures are MISSING - the rest of the scorecard is still written",
          rc == 0 and sorted(os.listdir(out3)) == sorted(n % MON.isoformat() for n in ("drafts_%s.json", "scorecard_%s.html", "scorecard_%s.json", "scorecard_week_%s.json"))
          and F3["aging_resend"]["status"] == "MISSING" and wk3["aging_resend"] is None and F3["owed_total"]["value"] == 305.0
          and sc3["sections"]["credentialing"]["status"] == "MISSING" and wk3["missing"] == [wsc.F_AGING, wsc.F_ROWS] and dr3["drafts"] == []
          and wsc.F_AGING in page3 and "MISSING" in page3 and sc3["sections"]["collected"]["status"] == "ok", (sc3["inputs"], wk3["missing"]))

    # ---------- (4) the drafts - prepared, never sent
    d0 = dr["drafts"]
    check("4. ONE draft: the card on William's turn, due within 30 days, with an address - a create_draft with a plain body, never a send",
          [x["card"] for x in d0] == ["pay-aetna"] and d0[0]["action"] == "create_draft" and d0[0]["to"] == ["enroll@aetna-example.org"] and d0[0]["created"] is True
          and "NEVER send" in dr["rule"] and "Aetna recredentialing" in d0[0]["subject"] and not re.search(r"<[a-z]|\*\*", d0[0]["body"])
          and d0[0]["card_op"]["op"] == "update" and d0[0]["card_op"]["set"] == {} and "nothing was sent" in d0[0]["card_op"]["append"]["notes"][0]["text"]
          and "Drafts waiting for you" in page and d0[0]["subject"] in page and any("no e-mail address on the card" in x for x in sc["your_turn"]), d0)
    rc, sc4, wk4, dr4, page4 = build(repo, ws, os.path.join(tmp, "a", "outbox2"), "--not-created", "pay-aetna")
    check("4. a draft the run could not create is said so under 'Your turn', and not listed as waiting",
          dr4["drafts"][0]["created"] is False and wk4["drafts_prepared"] == 0 and any("could not be prepared tonight" in x for x in sc4["your_turn"])
          and "None this week." in page4.split("Drafts waiting for you", 1)[1][:400], sc4["your_turn"])

    # ---------- (5) no patient data
    texts = []
    for o in (out, out3):
        for n in os.listdir(o): texts.append((n, open(os.path.join(o, n), encoding="utf-8").read()))
    leaks = [(n, x) for n, t in texts for x in CHARTS + VISITS + [MBI_S, NAME_S] if x in t]
    gate = [(n, h) for n, t in texts for h in phi_gate.check(t)]
    check("5. no output carries a chart or visit id, the card's Medicare number or LAST,FIRST name - and the card that held them gets no draft",
          not leaks and not gate and items["pay-mixed"]["need"].startswith("(withheld") and "pay-mixed" not in [x["card"] for x in d0]
          and any(x.startswith("Sunshine recredentialing: no draft made") for x in sc["your_turn"]), (leaks, gate))
    dday = (MON - datetime.timedelta(days=40)).isoformat()
    src = os.path.join(tmp, "aging_ws.json"); dst = os.path.join(tmp, "keep", "aging_latest.json")
    put(src, {"schema": "ar-aging/1", "asof": "x", "rows": [
        {"pid": CHARTS[6], "visitid": VISITS[6], "dod": dday, "rec": "WRITE OFF", "why": "date of service is AFTER the date of death on Medicare's record (" + dday + ") - void, never bill"},
        {"pid": CHARTS[7], "visitid": VISITS[7], "dod": "", "rec": "WAIT", "sent": dday, "why": "sent 40 days ago - watch"}]})
    wsc.main(["keep-aging", "--src", src, "--dst", dst])
    kept = json.load(open(dst)); kt = open(dst).read()
    check("5. the Sunday copy of the ageing file keeps every row but no date of death (the field and the sentence)",
          len(kept["rows"]) == 2 and kept["rows"][0]["dod"] == "" and kt.count(dday) == 1 and kept["rows"][1]["sent"] == dday and "[DOB]" in kept["rows"][0]["why"], kept["rows"])

    # ---------- (6) the page button
    btn = re.search(r'<a href="https://claude\.ai/artifact/test-scorecard-page" style="([^"]+)"', page)
    check("6. the button-style link carries background-color (longhand) and no part of the e-mail uses the background shorthand",
          bool(btn) and "background-color:" in btn.group(1) and not re.search(r"background\s*:", page) and not re.search(r"background\s*:", page2)
          and "<a href" not in page2 and "page link is not set yet" in page2, btn.group(1) if btn else None)

    # ---------- (7) posted_last_7d in the denials refresh (its own block, exec'd from the file with an invented chart history)
    texts7 = [open(os.path.join(ROOT, p, "denials_refresh.py"), encoding="utf-8").read() for p in ("tools/button", "scripts/helpers")]
    blk = lambda t: t[t.index("def f(x):"):t.index("# ---- end of posted_last_7d's definitions")]
    sys.path.insert(0, os.path.join(ROOT, "boards"))
    from working_denials import norm
    ns = {"datetime": datetime, "collections": collections, "re": re, "TODAY": MON, "norm": norm}
    exec(blk(texts7[0]), ns)
    in1, in2, out1 = (FROM + datetime.timedelta(days=1)).strftime("%m/%d/%Y"), TO.strftime("%m/%d/%Y"), (FROM - datetime.timedelta(days=1)).strftime("%m/%d/%Y")
    xml = ("<r><charge visit='V1'>"
           "<payment amount='120.00' createtime='%s 10:00:00 AM' carrier='FLO02'><payreason code='CO45' amount='40'/></payment>"
           "<payment amount='30.00' createtime='%s 09:00:00 AM' carrier='FLO02' source='1'/>"
           "<payment amount='15.00' date='%s' carrier=''/>"
           "<payment amount='-20.00' createtime='%s 11:00:00 AM' carrier='UNI20'/>"
           "<payment amount='500.00' createtime='%s 08:00:00 AM' carrier='FLO02'/>"
           "<payment amount='60.00' createtime='%s 08:00:00 AM' carrier='FLO02' void='1'/>"
           "<payment amount='0.00' createtime='%s 10:00:00 AM' carrier='HUM01'><payreason code='CO16' amount='160'/><payreason code='CO45' amount='5'/></payment>"
           "</charge><charge visit='V1'><payment amount='0.00' createtime='%s 10:00:00 AM' carrier='HUM01'><payreason code='CO27' amount='90'/></payment></charge>"
           "<charge visit='V2'><payment amount='0.00' createtime='%s 10:00:00 AM' carrier='SUN01'><payreason code='PR1' amount='50'/></payment>"
           "<payment amount='0.00' createtime='%s 10:00:00 AM' carrier='SUN01'><payreason code='OA200' amount='70'/></payment></charge></r>") % (
               in1, in1, in2, in2, out1, in1, in1, in2, in1, in2)
    ns["week"].extend(ns["week_lines"](ET.fromstring(xml)))
    s7 = ns["week_summary"](ns["week"])
    check("7. posted_last_7d: payments by POSTING date (insurance vs patient, net of take-backs, by carrier) and denial lines by visit; both copies carry the block",
          (s7["from"], s7["to"], s7["insurance"], s7["patient"], s7["takebacks"], s7["insurance_lines"], s7["patient_lines"]) == (FROM.isoformat(), TO.isoformat(), 100.0, 45.0, 20.0, 2, 2)
          and s7["by_carrier"] == {"FLO02": 120.0, "UNI20": -20.0} and s7["denials"] == {"visits": 2, "lines": 3, "dollars": 320.0, "wrong_payer_visits": 2}
          and s7["adjudicated_lines"] == 6 and blk(texts7[0]) == blk(texts7[1]) and 'out["posted_last_7d"] = week_summary(week)' in texts7[1], s7)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\n%d failure(s)" % len(FAILS) if FAILS else "\nall checks passed")
sys.exit(1 if FAILS else 0)
