# PLAIN ENGLISH (Post Florida Blue money that AMD never received - from William's Availity remit exports)
# Decides, per remit line that the comparison (avail_vs_amd.py) found missing in AMD: read the LIVE charge, and when the
#   charge still carries an open insurance balance with no non-void payment under that check number, post the payment by
#   hand exactly as the ERA fallback does - pay = min(remit paid, open insurance balance), write-off = the CO contractual
#   adjustments capped so pay + write-off never exceeds the balance (WOINS), check number = the Availity trace number,
#   deposit date = the check date, note names the source. PR (deductible/coinsurance) is never written off.
# Rules it uses: William 9/13/2026 - post the MAXIMUM AMD accepts and disregard the residual (report only); checks in date
#   order so a reversal-and-repay pair cannot double-post (the balance cap stops the second one); skip a charge whose
#   current carrier is not Florida Blue (report as carrier mismatch); stop after 3 consecutive addpayments faults.
# Never touches: charges with a zero insurance balance, denial-only lines, anything already carrying the check number.
"""Usage: python3 avail_post.py [stamp] [--dry] [--max-faults 3]"""
import amd, resave, txh, manual_post, json, os, re, sys, time, datetime
import xml.etree.ElementTree as ET
args = [a for a in sys.argv[1:] if not a.startswith("--")]
STAMP = args[0] if args else "2026-09-15T0310Z"
dry = "--dry" in sys.argv
MAXF = int(sys.argv[sys.argv.index("--max-faults") + 1]) if "--max-faults" in sys.argv else 3
CMP = json.load(open("registers/availity_vs_amd_%s.json" % STAMP))
REGP = "registers/availity_manual_register.json"
reg = json.load(open(REGP)) if os.path.exists(REGP) else {}
OUT = "registers/availity_post_%s_%s.json" % (STAMP, "dry" if dry else "live")
amd.login_cached()
LOG = open("avail_post.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
L("=== avail_post %s dry=%s ===" % (datetime.datetime.utcnow().isoformat(), dry))

def mdy_key(d):
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", d or ""); return (m.group(3), m.group(1), m.group(2)) if m else ("9999", "", "")
def live_charge(cid):
    rt = ET.fromstring(resave.detail(cid))
    c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid]
    pat = rt.find(".//patient")
    return (c[0] if c else None), (pat.get("id") if pat is not None else None)
tx_cache = {}
def payments_on(pid, cid, fresh=False):
    if fresh or pid not in tx_cache:
        d = {}
        for c in txh.fetch(pid).iter("charge"):
            d[re.sub(r"\D", "", c.get("id") or "")] = {"carrier": c.get("carrier"), "insbal": c.get("insbal"), "patbal": c.get("patbal"),
                "pays": [dict(p.attrib) for p in c.iter("payment")]}
        tx_cache[pid] = d
    return tx_cache[pid].get(cid)

rows = []; faults = 0; posted_n = 0; posted_amt = 0.0; wo_amt = 0.0
checks = sorted([c for c in CMP["checks"] if c["missing"]], key=lambda c: mdy_key(c["check_date"]))
for ck in checks:
    for ln in ck["missing"]:
        key = "%s|%s" % (ck["trace"], ln["cid"])
        row = {"trace": ck["trace"], "check_date": ck["check_date"], "payer": ck["payer"], "cid": ln["cid"], "pid": ln["pid"], "visit": ln["visit"],
               "patient": ln["patient"], "dos": ln["dos"], "cpt": ln["cpt"], "remit_paid": ln["paid"], "adj": ln["adj"]}
        if key in reg and reg[key].get("status") == "posted":
            row["status"] = "already in register"; rows.append(row); continue
        try:
            ch, patid = live_charge(ln["cid"])
        except Exception as e:
            row["status"] = "detail error " + repr(e)[:120]; rows.append(row); L("  %s %s" % (key, row["status"])); continue
        if ch is None:
            row["status"] = "charge not found live"; rows.append(row); continue
        insbal = float(ch.get("insbalance") or 0); row["insbal"] = insbal
        pid = re.sub(r"\D", "", patid or ln["pid"] or "")
        txc = payments_on(pid, ln["cid"])
        row["carrier"] = txc["carrier"] if txc else None
        if txc and any(p.get("checknumber") and ck["trace"] in p["checknumber"] and p.get("void") != "1" for p in txc["pays"]):
            row["status"] = "already posted (check number on charge)"; rows.append(row); continue
        if insbal <= 0.005:
            row["status"] = "no open insurance balance - residual"; rows.append(row); continue
        if txc and txc["carrier"] not in ("BCBS", "HOI", "BCB01", None):
            row["status"] = "carrier mismatch (%s) - report" % txc["carrier"]; rows.append(row); continue
        pay = round(min(ln["paid"], insbal), 2)
        co = round(sum(a for g, c, a in ln["adj"] if g == "CO" and a > 0), 2)
        wo = round(max(0.0, min(co, insbal - pay)), 2)
        if pay <= 0: row["status"] = "nothing to post"; rows.append(row); continue
        note = "Availity remit %s %s (Florida Blue) manual post - run %s" % (ck["trace"], ck["check_date"], STAMP)
        ok, msg = manual_post.post(ln["cid"], "BCBS", pay, wo, "WOINS", ck["trace"], ck["check_date"], note, dry)
        row.update({"pay": pay, "wo": wo, "ok": ok, "msg": msg[:160]})
        if dry:
            row["status"] = "DRY would post"; rows.append(row); L("  DRY %s pay %.2f wo %.2f insbal %.2f %s" % (key, pay, wo, insbal, ln["patient"])); continue
        if ok:
            faults = 0; posted_n += 1; posted_amt += pay; wo_amt += wo; row["status"] = "posted"
            reg[key] = {"status": "posted", "cid": ln["cid"], "trace": ck["trace"], "pay": pay, "wo": wo, "at": datetime.datetime.utcnow().isoformat(), "run": STAMP, "src": "availity-pdf"}
            L("  POSTED %s pay %.2f wo %.2f (insbal %.2f) %s" % (key, pay, wo, insbal, ln["patient"]))
        else:
            faults += 1; row["status"] = "FAULT"; L("  FAULT %s %s" % (key, msg[:200]))
            if "over-apply" in msg: faults -= 1  # not an addpayments fault; the cap logic will be reviewed
            if faults >= MAXF:
                L("stopping after %d consecutive faults" % faults); rows.append(row); break
        rows.append(row)
        json.dump(reg, open(REGP, "w"), indent=1)
    else:
        continue
    break
json.dump(reg, open(REGP, "w"), indent=1)
from collections import Counter
summ = {"dry": dry, "rows": len(rows), "posted": posted_n, "posted_amount": round(posted_amt, 2), "writeoff_amount": round(wo_amt, 2),
        "would_post": round(sum(r.get("pay", 0) for r in rows if r.get("status") == "DRY would post"), 2),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "residual_remit_money": round(sum(r["remit_paid"] for r in rows if r["status"].startswith("no open")), 2)}
json.dump({"summary": summ, "rows": rows}, open(OUT, "w"), indent=1)
L("SUMMARY %s" % json.dumps(summ))
