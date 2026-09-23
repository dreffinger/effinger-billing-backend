#!/usr/bin/env python3
import os
# PLAIN ENGLISH (William 9/23/2026: "rebill all these ones to Medicare ... and write off the ones you are recommending")
# Decides: (A) which Florida-Blue-first visits go to Medicare now: only visits whose LAST bill went to BCBS (a claim already at
#          Medicare since 9/12-9/16 is pending - never a duplicate); patient balances from $0 wrong-payer denials come back to
#          insurance first (your 9/3 rule), the visit order becomes Medicare-first, the claim goes out as frequency 1.
#          (B) visits already at Medicare whose balance still sits on the patient: move back only (no rebill).
#          (C) the patient's default order (insorder) becomes Medicare-first where the chart carries BCBS ahead of FLO02.
#          (D) write-offs from writeoff_plan.json: WOCAID2ND (dual coinsurance FCC refused) / WONCS (never-covered lines),
#          $0 payment + write-off through addpayments under the FCC / FB carrier; FCC members whose chart lacked the FCC plan get it.
# Rules: deceased guard inside every rebill (amd.rebill_charge); full-visit echo (move_to_ins); over-apply refused (manual_post);
#          one register (execute_0923_register.json) so a re-run never repeats a step.  --dry prints the plan only.
import sys, os, re, json, time, datetime
sys.path.insert(0, os.environ.get("SCANS_DIR", "/home/claude/scans") + "")
import amd, ins_update, add_ins, freq1_visit, move_to_ins, manual_post, txh, payreasons
D = os.environ.get("SCANS_DIR", "/home/claude/scans") + ""; DRY = "--dry" in sys.argv; TODAY = datetime.date.today().strftime("%m/%d/%Y")
REG = D + "/execute_0923_register.json"; register = json.load(open(REG)) if os.path.exists(REG) else []
LOGF = open(D + "/execute_0923.log", "a")
def L(m): print(m, flush=True); LOGF.write(m + "\n"); LOGF.flush()
def done(step, key): return any(r["step"] == step and r["key"] == key and r["ok"] for r in register)
def rec(step, key, ok, **kw):
    register.append(dict(step=step, key=key, ok=ok, when=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), **kw)); json.dump(register, open(REG, "w"), indent=1)
T = json.load(open(D + "/fb_rebill_targets.json")); ATTR = json.load(open(D + "/fb_rebill_charge_attrs.json")); WO = json.load(open(D + "/writeoff_plan.json"))
# ---------------------------------------------------------------- A/B: Medicare rebills and move-backs
rebill, moveback, skipped = [], [], []
for t in T:
    last = {ATTR.get(c, {}).get("carrier") for c in t["cids"]}; bd = {ATTR.get(c, {}).get("billdate") for c in t["cids"]}
    if not t["flo02"]: skipped.append((t, "no Medicare plan on the chart - insurance cascade, not a rebill")); continue
    if last == {"FLO02"}:
        if t["pat"] > 0: moveback.append(t)
        else: skipped.append((t, "already at Medicare (billed %s) - pending, not re-sent" % ",".join(sorted(x for x in bd if x))))
        continue
    rebill.append(t)
L("== plan: %d rebill to Medicare ($%.2f), %d move-back only ($%.2f), %d skipped" % (len(rebill), sum(x["ins"] + x["pat"] for x in rebill), len(moveback), sum(x["pat"] for x in moveback), len(skipped)))
for t, why in skipped: L("   skip %s %s %s: %s" % (t["acct"], t["patient"][:18], t["dos"], why))
if not DRY: amd.login_cached()
# C: patient default order Medicare-first (once per patient)
seen = set()
for t in rebill + moveback:
    pid = t["pid"]
    if pid in seen or not t["flo02"]: continue
    seen.add(pid)
    order = t["flo02_seq"] + ("," + ",".join(s for s in t["bcbs_seqs"] if s) if t["bcbs_seqs"] else "")
    if t["flo02_seq"] == "1": continue                       # already Medicare-first
    if done("order", pid): continue
    if DRY: L("   DRY patient %s (%s): insorder -> %s" % (pid, t["patient"][:18], order)); continue
    d = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    cur = (re.search(r'<patient [^>]*insorder="([^"]*)"', d) or [None, ""])[1]
    if cur.startswith(t["flo02_seq"]): L("   patient %s insorder already %s" % (pid, cur)); rec("order", pid, True, note="already " + cur); continue
    ok, msg = ins_update.update(pid, t["flo02"], sequence=order); time.sleep(0.6)
    d2 = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    after = (re.search(r'<patient [^>]*insorder="([^"]*)"', d2) or [None, ""])[1]
    L("   patient %s (%s) insorder %s -> %s (%s %s)" % (pid, t["patient"][:18], cur, after, ok, msg[:60])); rec("order", pid, ok and after.startswith(t["flo02_seq"]), before=cur, after=after)
# A: rebills
for t in rebill:
    key = t["acct"]
    if done("rebill", key): continue
    cid0 = t["cids"][0]; seq = t["flo02_seq"]; order = seq + ("," + ",".join(s for s in t["bcbs_seqs"] if s) if t["bcbs_seqs"] else "")
    if DRY: L("   DRY rebill %s %s %s %s: freq1 seq %s, move %.2f pat->ins, insorder %s, rebill seq %s" % (key, t["patient"][:18], t["dos"], t["cpts"], seq, t["pat"], order, seq)); continue
    r1 = freq1_visit.run(t["vid"], cid0, int(seq)); time.sleep(0.6)
    r2 = move_to_ins.move(cid0, order, rebill_seq=int(seq)); time.sleep(0.6)
    ok = ("FAULT" not in str(r1)) and ("FAULT" not in str(r2)) and ("BLOCKED" not in str(r2)) and ("-> 204" in str(r2) or "-> 200" in str(r2) or "rebill seq" in str(r2))
    L("   rebill %s %s %s: %s | %s" % (key, t["patient"][:18], t["dos"], r1, r2)); rec("rebill", key, ok, freq1=str(r1)[:160], move=str(r2)[:200], amount=t["ins"] + t["pat"], patient=t["patient"], dos=t["dos"], cpts=t["cpts"])
# B: move-backs
for t in moveback:
    key = t["acct"]
    if done("moveback", key): continue
    cid0 = t["cids"][0]
    if DRY: L("   DRY move-back %s %s %s: %.2f pat->ins (claim already at Medicare)" % (key, t["patient"][:18], t["dos"], t["pat"])); continue
    r = move_to_ins.move(cid0); time.sleep(0.6)
    L("   move-back %s %s %s: %s" % (key, t["patient"][:18], t["dos"], r)); rec("moveback", key, "FAULT" not in str(r), move=str(r)[:200], amount=t["pat"], patient=t["patient"], dos=t["dos"])
# ---------------------------------------------------------------- D: write-offs
lines = [w for w in WO if w["code"] in ("WOCAID2ND", "WONCS")]
L("== write-offs: %d lines $%.2f (WOCAID2ND %d / WONCS %d)" % (len(lines), sum(w["open"] for w in lines), sum(1 for w in lines if w["code"] == "WOCAID2ND"), sum(1 for w in lines if w["code"] == "WONCS")))
added_plan = set()
for w in lines:
    key = w["cid"]
    if done("writeoff", key): continue
    if w.get("add_plan") and w["pid"] not in added_plan:
        added_plan.add(w["pid"])
        if DRY: L("   DRY add FLO99 plan on pat%s (%s) member %s" % (w["pid"], w["patient"][:18], w["add_plan"]))
        elif not done("plan", w["pid"]):
            insid, seq = add_ins.add(w["pid"], "car42008", w["add_plan"]); L("   add FLO99 plan pat%s -> %s seq %s" % (w["pid"], insid, seq)); rec("plan", w["pid"], bool(insid), insid=insid, seq=seq); time.sleep(0.5)
    if DRY: L("   DRY %s %s %s %s %s $%.2f under %s (%s)" % (w["code"], w["acct"], (w["patient"] or "")[:18], w["dos"], w["cpt"], w["open"], w["carrier"], w["why"][:50])); continue
    # live balance first (never over-apply, never write off a line that moved since the read)
    st = {c["cid"]: c for c in payreasons.visit_state(w["pid"], w["vid"], root=txh.fetch_visit(w["pid"], w["vid"]))}
    live = st.get(w["cid"]); bal = live["insbalance"] if live else 0.0
    if bal <= 0.004: L("   skip %s %s %s: live balance %.2f" % (w["acct"], w["cpt"], w["cid"], bal)); rec("writeoff", key, False, note="live balance %.2f" % bal); continue
    amt = round(min(bal, w["open"]), 2)
    note = "%s: paper FCC/FB $0 statement (%s) - 9/23/2026 sweep, William OK" % (w["code"], w["remark"][:40])
    ok, msg = manual_post.post(w["cid"], w["carrier"], 0.0, amt, w["code"], checknumber="PAPER0923", depositdate=TODAY, note=note)
    L("   %s %s %s %s %s $%.2f under %s -> %s %s" % (w["code"], w["acct"], (w["patient"] or "")[:18], w["dos"], w["cpt"], amt, w["carrier"], ok, msg[:80]))
    rec("writeoff", key, ok, acct=w["acct"], patient=w["patient"], cpt=w["cpt"], dos=w["dos"], amount=amt, code=w["code"], carrier=w["carrier"], msg=msg[:160]); time.sleep(0.5)
# ---------------------------------------------------------------- totals
if not DRY:
    rb = [r for r in register if r["step"] == "rebill" and r["ok"]]; mb = [r for r in register if r["step"] == "moveback" and r["ok"]]; wo = [r for r in register if r["step"] == "writeoff" and r["ok"]]
    L("TOTALS: rebilled to Medicare %d visits $%.2f | moved back to insurance %d visits $%.2f | written off %d lines $%.2f (WOCAID2ND $%.2f, WONCS $%.2f)" % (
        len(rb), sum(r["amount"] for r in rb), len(mb), sum(r["amount"] for r in mb), len(wo), sum(r["amount"] for r in wo), sum(r["amount"] for r in wo if r["code"] == "WOCAID2ND"), sum(r["amount"] for r in wo if r["code"] == "WONCS")))
