# PLAIN ENGLISH (Old-claims disposition - the apply step, one approval package at a time)
# Decides: nothing new. Applies the packages William approved from old_claims_disposition_<stamp>.json (built by
#   old_claims_classify.py from the live chart facts + the payers' 277 answers): POST-277 = the payer's own paid amount, check
#   number and paid date posted as the payment (manual_post / addpayments) with the remainder written off as planned;
#   WO-* = the write-off alone; RESEND / MEDICARE-UNANSWERED = ONE frequency-1 rebill per visit (amd.rebill_charge enforces it).
# Rules it uses: dry by default (--live posts); every charge is RE-READ live first - a charge already carrying a non-void payment
#   with the same check number, or with no open insurance balance, is skipped as 'already posted'/'settled'; a patient-side balance
#   is moved back to insurance first (move_to_ins.move); pay + write-off never exceed the open insurance balance (manual_post refuses
#   over-apply); the deceased guard inside amd.rebill_charge blocks any resend after a date of death. Resumable: 'DONE <cid> <what>'
#   lines in the log are never repeated. Every write-off lands in Writeoff_register_<date>.xlsx (date, patient, carrier, dos, amount,
#   note) so the ledger counts it, and registers/old_claims_apply_<stamp>.json keeps chart/visit/charge ids + dollars (no names).
# Never touches: visits outside the selected packages; voided charges; anything the live read says is settled or already posted.
"""Usage: python3 old_claims_apply.py --only A[,B,...] [--live] [--stamp 1009] [--max N] [--vids v1,v2] [--skip-dec]"""
import amd, manual_post, move_to_ins, resave, freq1_visit, json, sys, re, os, time, datetime, collections
import xml.etree.ElementTree as ET
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--stamp", "1009"); LIVE = "--live" in a; MX = int(opt("--max", 10**9)); ONLY = set(opt("--only", "").split(",")) - {""}
VIDS = set(opt("--vids", "").split(",")) - {""}; SKIPDEC = "--skip-dec" in a
if not ONLY: sys.exit("--only <package letters> is required (A..H; add -dec for the deceased-flagged sub-packages)")
SRC = next((p for p in ("old_claims_disposition_%s.json" % STAMP, "registers/old_claims_disposition_%s.json" % STAMP) if os.path.exists(p)), None)
if not SRC: sys.exit("no old_claims_disposition_%s.json in the workspace or registers/ (the repo copy carries chart ids only)" % STAMP)
D = json.load(open(SRC)); PK = D["packages"]
sel = [v for v in D["visits"] if v["pkg"] in ONLY and (not VIDS or v["vid"] in VIDS) and v["actions"]][:MX]
LOGF = "old_claims_apply_%s.log" % STAMP; done = set(l.split()[1] + "|" + l.split()[2] for l in open(LOGF) if l.startswith("DONE ")) if os.path.exists(LOGF) else set()
LOG = open(LOGF, "a"); REG = "registers/old_claims_apply_%s.json" % STAMP; os.makedirs("registers", exist_ok=True)
reg = json.load(open(REG)) if os.path.exists(REG) else {"stamp": STAMP, "items": []}
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def mdy(s):
    s = (s or "").strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"):
        try: return datetime.datetime.strptime(s[:10] if ("-" in s or "/" in s) else s[:8], fmt).strftime("%m/%d/%Y")
        except Exception: pass
    return datetime.date.today().strftime("%m/%d/%Y")
XL = "Writeoff_register_%s.xlsx" % datetime.date.today().isoformat()
def xl_add(rows):
    if not rows: return
    import openpyxl
    wb = openpyxl.load_workbook(XL) if os.path.exists(XL) else openpyxl.Workbook(); ws = wb.active
    if ws.max_row == 1 and not ws.cell(1, 1).value: ws.append(["date", "patient", "carrier", "dos", "amount", "note"])
    for r in rows: ws.append(r)
    wb.save(XL)
amd.login_cached(); L("=== old_claims_apply %s %s packages %s: %d visits ===" % (STAMP, "LIVE" if LIVE else "DRY", ",".join(sorted(ONLY)), len(sel)))
n_pay = n_wo = n_send = n_skip = 0; d_pay = d_wo = 0.0; xlrows = []
for v in sel:
    if v["deceased"] and SKIPDEC: L("SKIP v%s deceased flag (--skip-dec)" % v["vid"]); n_skip += 1; continue
    note = "old-claims disposition %s (William 10/9/2026: close old claims from the payer's answer): %s" % (STAMP, "; ".join(v["notes"])[:160])
    for act in v["actions"]:
        cid = re.sub(r"\D", "", str(act["cid"])); key = cid + "|" + ("send" if "resend_seq" in act else "post")
        if key in done: continue
        if "resend_seq" in act:
            if not LIVE: L("DRY SEND v%s charge%s seq %s (%s %s)" % (v["vid"], cid, act["resend_seq"], v["carrier"], v["dos"])); n_send += 1; continue
            r = freq1_visit.run(str(v["vid"]), cid, str(act["resend_seq"])); sent = ("204" in str(r) or "SKIPPED" in str(r))
            L("%s %s send v%s seq %s -> %s" % ("DONE" if sent else "FAIL", cid, v["vid"], act["resend_seq"], str(r)[:120]))
            if sent: n_send += 1; reg["items"].append({"pid": v["pid"], "vid": v["vid"], "cid": cid, "what": "freq1 resend", "seq": act["resend_seq"], "result": str(r)[:80], "at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"})
            time.sleep(0.4); continue
        # live re-read of the charge
        try: rt = ET.fromstring(resave.detail(cid))
        except Exception as e: L("FAIL %s read %s" % (cid, str(e)[:100])); continue
        c = next((x for x in rt.iter("charge") if x.get("id") == "charge" + cid), None)
        if c is None or c.get("void") == "1": L("SKIP %s not live" % cid); n_skip += 1; continue
        insbal = float(c.get("insbalance") or 0); patbal = float(c.get("patbalance") or 0)
        chk = str(act.get("check") or ""); have = [p for p in c.iter("payment") if p.get("void") != "1" and (p.get("checknumber") or "") == chk and chk not in ("", "277")]
        if have: L("SKIP %s already posted (check %s)" % (cid, chk)); n_skip += 1; continue
        if insbal <= 0.004 and patbal > 0.004 and LIVE:
            r = move_to_ins.move(cid); L("  moved patient balance back to insurance charge%s -> %s" % (cid, str(r)[:100])); time.sleep(0.4)
            rt = ET.fromstring(resave.detail(cid)); c = next(x for x in rt.iter("charge") if x.get("id") == "charge" + cid); insbal = float(c.get("insbalance") or 0)
        if insbal <= 0.004: L("SKIP %s settled (insbalance 0%s)" % (cid, ", patbal %.2f" % patbal if patbal else "")); n_skip += 1; continue
        pay = min(float(act.get("pay") or 0), insbal); wo = float(act.get("wo") or 0); wo = min(wo, max(0.0, insbal - pay)) if wo else 0.0
        if act.get("wocode") in ("WOINS", "WOCAID2ND", "WOLATE", "WOPDEOB") and wo and abs((pay + wo) - insbal) > 0.005 and act.get("pay", 0) + act.get("wo", 0) >= act.get("insbal", 0) - 0.005:
            wo = max(0.0, insbal - pay)   # the plan closed the charge: keep it closed on the live balance
        if pay <= 0 and wo <= 0: L("SKIP %s nothing to post" % cid); n_skip += 1; continue
        ok, msg = manual_post.post(cid, v["carrier"], round(pay, 2), round(wo, 2), act.get("wocode") or "WOINS", checknumber=chk, depositdate=mdy(act.get("paiddate")), note=note, dry=not LIVE)
        tag = ("DONE" if ok else "FAIL") if LIVE else ("DRY" if ok else "DRY-FAIL")
        L("%s %s post v%s %s %s %s pay %.2f wo %.2f %s chk %s -> %s" % (tag, cid, v["vid"], v["carrier"], v["dos"], act.get("cpt", ""), pay, wo, act.get("wocode") or "", chk, str(msg)[:90]))
        if ok:
            if pay > 0: n_pay += 1; d_pay += pay
            if wo > 0: n_wo += 1; d_wo += wo; xlrows.append([datetime.date.today().isoformat(), v["patient"], v["carrier"], v["dos"], round(wo, 2), "%s %s" % (act.get("wocode"), note[:200])])
            if LIVE: reg["items"].append({"pid": v["pid"], "vid": v["vid"], "cid": cid, "pkg": v["pkg"], "tier": v["tier"], "pay": round(pay, 2), "wo": round(wo, 2), "wocode": act.get("wocode"), "check": chk, "at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"})
        time.sleep(0.35)
    if LIVE: json.dump(reg, open(REG, "w"), indent=1)
if LIVE: xl_add(xlrows)
L("=== %s done: %d payments $%.2f, %d write-offs $%.2f, %d resends, %d skipped%s ===" % ("LIVE" if LIVE else "DRY", n_pay, d_pay, n_wo, d_wo, n_send, n_skip, ("; write-off register " + XL) if (LIVE and xlrows) else ""))
