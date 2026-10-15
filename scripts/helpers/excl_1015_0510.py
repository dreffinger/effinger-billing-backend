# PLAIN ENGLISH (Exclusions column work of the 2026-10-15T0510Z run - claim runs 1700294 and 1700302, 59 rows read live)
# Decides per row from the live transaction history read this run (work/read_excl_tx.json, re-read before any write):
#   A  'CH FH PREF0283 MISSING PAYER DOC CONTROL NUM' Florida Blue SECONDARY claims whose Medicare / UHC primary remit is OLDER than
#      12 months (2022-2023 dates of service; 27 rows on run 1700302): the 10/14 chat pass re-sent every one of them as an original
#      (rule 7) and the clearinghouse rejected them again - the secondary window is closed (William 9/7: a secondary is timely
#      from the primary's remit date; 10/13 aged A/R: fixed or written off, never parked; chat 10/14 rule 9 and the approved card
#      A-2026-10-14T1910Z-C did the same for charts 25416 / 47643) -> WOINS the open insurance balance with a dated note
#      (check number UNTIMELY1015), then complete the exclusion (hideexclusions).
#   B  the same rejection on Florida Blue SECONDARY claims whose Medicare remit is INSIDE 12 months (16 rows, 2024-2026 dates of
#      service, Medicare paid 09-10/2026): the secondary claim cannot carry Medicare's claim control number because Medicare's
#      payment was posted without an ERA line (old-claims / 277 postings) - the crossover-wait rule (9/20, 10/5): complete the row
#      without a rebill, nothing written off; Florida Blue gets the Medicare crossover; listed in the report.
#   C  Aetna (AET07) 'ACK RETURNED AS UNPROCESSABLE' SECONDARY claims on 2022-2023 dates of service whose primary (Medicare 2023,
#      Humana 12/2023 - 03/2024) remit is older than 12 months (8 rows on run 1700294, charts 46253 and 12233870): the same
#      closed-window rule -> WOINS the open balance, complete.
#   D  Aetna (AET07) 'unprocessable' on chart 17472859 (5 visits 01/31-02/04/2025, Medicare paid 05/31/2026 - inside 12 months;
#      AMD 271: 'Aetna Medicare Dual Extra (PPO D-SNP)' ACTIVE 2026): HELD - not written off, not re-sent; board row for William.
#   E  AET12 PREF0288 (chart 24750, carrier CPID): HELD (board row aet12-carrier-cpid).
# --dry (default) plans; --live writes; --only A,B,C runs the named sections. Register registers/excl_1015_0510_<dry|live>.json.
# Rules it uses: write-off = manual_post.post(cid, carrier code, 0.0, open insurance balance, WOINS, UNTIMELY1015, None, note);
#   a charge whose live balance changed since the read is skipped; one hideexclusions call per claim run; never a rebill here.
# Never touches: payments, charts with a payment newer than 12 months (section B/D rows), the AET12 row.
import amd, manual_post, resave, json, sys, re, time, datetime
LIVE = "--live" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else set("ABC")
STAMP = "2026-10-15T0510Z"
amd.login_cached()
D = json.load(open("work/read_excl_tx.json"))
EX = {e["vid"]: e for e in D["exclusions"]}
TX = D["tx"]
REG = {"stamp": STAMP, "live": LIVE, "A": [], "B": [], "C": [], "held": [], "hidden": {}}
def save(): json.dump(REG, open("registers/excl_1015_0510_%s.json" % ("live" if LIVE else "dry"), "w"), indent=1, default=str)
def num(s): return re.sub(r"\D", "", str(s or ""))
def mdy(s):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s or ""); return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else None
CUT = datetime.date(2025, 10, 15)   # a primary remit before this date is older than 12 months
def last_primary_pay(rows):
    d = None
    for r in rows:
        for p in r.get("payments", []):
            if p.get("void") == "1": continue
            try: amt = float(p.get("amount") or 0)
            except: amt = 0
            if amt < 0 and p.get("carrier") not in ("BCBS", "AET07", "AET12"):
                dd = mdy(p.get("date"))
                if dd and (d is None or dd > d): d = dd
    return d
to_hide = {}
for vid, e in EX.items():
    rows = [r for r in TX.get("%s:%s" % (e["pid"], vid), []) if isinstance(r, dict) and r.get("void") != "1"]
    errs = " ".join(e["errs"]); car = e["carrier"]; run = e["run"]
    lp = last_primary_pay(rows)
    open_bal = sum(float(r.get("insbal") or 0) for r in rows)
    rec = {"run": run, "vid": vid, "claimid": e["claimid"], "pid": e["pid"], "carrier": car, "dos": e["charges"][0]["dos"], "last_primary_pay": str(lp), "open": round(open_bal, 2)}
    if car == "AET12": rec["why"] = "carrier CPID hold"; REG["held"].append(rec); continue
    if "PREF0283" in errs and car == "BCBS":
        sec = "A" if (lp is not None and lp < CUT) else "B"
    elif car == "AET07":
        sec = "C" if (lp is not None and lp < CUT) else "D"
    else:
        rec["why"] = "unclassified " + errs[:80]; REG["held"].append(rec); continue
    if sec == "D": rec["why"] = "AET07 secondary, primary remit inside 12 months - held for William"; REG["held"].append(rec); continue
    if sec not in ONLY: continue
    rec["steps"] = []
    if sec in ("A", "C"):
        for r in rows:
            bal = float(r.get("insbal") or 0)
            if bal <= 0: continue
            cid = num(r.get("id"))
            note = "%s secondary balance DOS %s: primary remit %s (>12 months), secondary window closed, clearinghouse/payer rejected the 10/13-10/14 resend (%s) - WOINS untimely (10/13 aged A/R rule, run %s)" % (car, r.get("dos"), lp, errs[:40].strip(), STAMP)
            try:
                ok, msg = manual_post.post(cid, car, 0.0, round(bal, 2), "WOINS", "UNTIMELY1015", None, note, dry=not LIVE)
            except Exception as ex: ok, msg = False, "EXC " + str(ex)[:120]
            rec["steps"].append((cid, r.get("proccode"), round(bal, 2), ok, msg[:120]))
            if LIVE: time.sleep(0.5)
        if all(s[3] for s in rec["steps"]) or not rec["steps"]:
            to_hide.setdefault(run, []).append((vid, e["claimid"]))
            rec["hide"] = True
    else:   # B crossover-wait: complete only
        rec["steps"].append(("crossover-wait: complete, no rebill, no write-off", round(open_bal, 2)))
        to_hide.setdefault(run, []).append((vid, e["claimid"])); rec["hide"] = True
    REG[sec].append(rec); save()
for run, items in to_hide.items():
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (vv, cl) for vv, cl in items) + "</visitlist>"
    if not LIVE: REG["hidden"][run] = {"n": len(items), "dry": True, "visits": [v for v, _ in items]}; continue
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    REG["hidden"][run] = {"n": len(items), "ok": "Fault" not in r, "resp": re.sub(r"\s+", " ", r[:160])}
    time.sleep(0.5)
save()
wo = sum(s[2] for sec in ("A", "C") for rc in REG[sec] for s in rc.get("steps", []))
print("SUMMARY live=%s A=%d rows B=%d rows C=%d rows held=%d; write-offs $%.2f; hide %s" % (LIVE, len(REG["A"]), len(REG["B"]), len(REG["C"]), len(REG["held"]), wo, {k: v.get("n") for k, v in REG["hidden"].items()}))
for sec in ("A", "B", "C"):
    for rc in REG[sec]: print(sec, rc["vid"], rc["pid"], rc["dos"], "lastpay", rc["last_primary_pay"], "open", rc["open"], [(s[0], s[2], s[3]) if len(s) > 3 else s for s in rc.get("steps", [])][:3])
for rc in REG["held"]: print("HELD", rc)
