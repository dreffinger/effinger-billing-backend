#!/usr/bin/env python3
# PLAIN ENGLISH (three Insurance Refresh Board cards William answered in chat on 11/25/2026 05:01-05:27 UTC - the chat left each
#   card on Claude's turn with the exact instruction; this is the "next run" it named)
# Decides: nothing. Per card, the standing rules on William's own words (the numbers are read from the saved board cards, never typed):
#   (A) [name]-17478200: he created the Detego Health carrier ("detego is in amd"; lookupcarrier found DET01 car307812, cpid 9436).
#       Add the Detego plan - policy from his facesheet paste, begin 10/07/2026, subscriber self, NO group number - as the chart's only plan,
#       patient order 1; write his authorization on both HCA visits (full-visit echo with preauth=, the captured way to put the first
#       authorization on the chart's main referral plan) with insorder 1, read it back, then ONE frequency-1 original claim each
#       (freq1_visit.run). No electronic eligibility exists for this payer (his word): the plan is entered on the face sheet alone.
#   (B) [name]-17478219: his hospital sheet names WELLCARE MEDICARE (member on the sheet, effective 1/1/2025). ONE Stedi
#       eligibility check per service date (payer 14163) - 09/01/2026 (v19459521, at Medicare since 10/29) and 10/22/2026 (v19459226,
#       never billed). Active on the date -> WEL04 car6174 plan added (begin 01/01/2025, no group), patient order WellCare first, the
#       visit re-routed / sent to WellCare (freq1_visit.reroute - one rebill). Not active -> nothing written for that date; the card goes
#       back to William with the CHP member-number ask (Medicare's dated answer names Capital Health Plan).
#   (C) [name]-17478332: his current hospital sheet names Florida Blue Medicare Advantage, member XJPH..., effective 12/1/2024.
#       Add BCBS car6062 (the carrier the other Florida Blue MA charts use) with it (begin 12/01/2024, no group), Stedi eligibility dated
#       11/03/2026 (payer BCBSF); active -> Florida Blue first on v19460350 and sent (freq1_visit.reroute); not active -> try once without
#       the three-letter prefix (his instruction); still not -> the exact answer on the card, back to William.
# --dry = reads and prints, no plan added, no save, no claim. Register registers/board_plans_2026-11-25T0557Z[_dry].json (ids, no names).
# Never touches: other charts, payments, write-offs, charge codes, the Medicare plans (nothing end-dated here).
# Usage: python3 board_plans_1125b.py [--live] [--only <pid>]
import amd, add_ins, ins_update, elig_amd, freq1_visit, resave, stedi, feed_order_sweep as fos, re, json, sys, time, os
LIVE = "--live" in sys.argv; S = "2026-11-25T0557Z"
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
BOARD = "/tmp/claude-0/-home-claude-effinger-billing-backend/54dad968-8e54-5d62-b91f-c8705cdd698d/scratchpad/board_0557/items"
def card(cid):
    o = json.load(open(os.path.join(BOARD, cid + ".json"))); return o.get("data", o)
def wnotes(cid):
    return "\n".join(n.get("text", "") for n in card(cid).get("notes") or [] if str(n.get("who", "")).lower().startswith("william"))
def plans(pid):
    raw, pl, order = ins_update._plans(pid); return list(pl.values()), order
def preauth_resave(cid, order, preauth):
    """full-visit echo (every live charge, CHG_FIELDS) with insorder + preauth; verifies the order, the charges and the admission dates."""
    vis, pat, allc = resave.visit_charges(cid); before = resave.order_list(vis); adm0 = resave.admit_codes(allc)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = order; va["preauth"] = preauth
    if not LIVE: return True, "DRY resave visit %s insorder %s -> %s preauth set (%d live charges echoed, admit %s)" % (vis.get("id"), vis.get("insorder"), order, len(allc), adm0)
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
                 "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r: return False, "resave FAULT " + re.sub(r"\s+", " ", r[:300])
    v2, p2, c2 = resave.visit_charges(cid); adm, still = resave.admit_back(v2.get("id") or vis.get("id"), c2, adm0, "" if adm0 else resave.admit_of(vis))
    live = [c.get("id") for c in c2]; sent = [c.get("id") for c in allc]
    ok = (v2.get("insorder") or "").replace(" ", "") == order and len(live) == len(sent) and not still and (v2.get("preauth") or "") == preauth
    return ok, "resave visit %s insorder %s -> %s, preauth %s, %d live (was %d)%s%s" % (vis.get("id"), vis.get("insorder"), v2.get("insorder"), "ok" if (v2.get("preauth") or "") == preauth else "NOT written (%r)" % v2.get("preauth"), len(c2), len(allc), adm, "" if ok else " - NOT as asked")
amd.login_cached(); reg = {}
# ---------- (A) GREEN 17478200 - Detego Health ----------
if not ONLY or ONLY == "17478200":
    pid = "17478200"; row = {"card": "[name]-17478200", "steps": [], "visits": {}}
    t = wnotes("[name]-17478200"); m = re.search(r"DETEGO.{0,200}?Policy #\s*(\d{6,12})", t, re.S | re.I); auth = re.search(r"Auth\s*(\d{6,12})", t)
    policy = m.group(1) if m else ""; auth = auth.group(1) if auth else ""
    print("== GREEN pat%s policy %s auth %s" % (pid, "found" if policy else "NOT FOUND", "found" if auth else "NOT FOUND"))
    if policy and auth:
        pl, order = plans(pid); have = [p for p in pl if p.get("carrier") == "car307812" and not p.get("enddate")]
        if have: insid, seq = have[0]["id"], have[0]["sequence"]; row["steps"].append(["DET01 plan already on the chart", insid, seq])
        elif not LIVE: insid, seq = None, "1"; row["steps"].append(["DRY would add DET01 car307812", policy[-4:], "10/07/2026"])
        else:
            insid, seq = add_ins.add(pid, "car307812", policy, "10/07/2026"); row["steps"].append(["add DET01", insid, seq]); print("  add DET01 ->", insid, seq)
        if insid and LIVE:
            try: res = ins_update.update(pid, insid, sequence=str(seq)); row["steps"].append(["patient order", str(seq), str(res)[:160]]); print("  patient order", seq, "->", str(res)[:160])
            except Exception as e: row["steps"].append(["patient order error", str(e)[:120]])
        for vid, cid in (("19459188", "23371598"), ("19459194", "23371604")):
            ok, msg = preauth_resave(cid, str(seq), auth); print("  v%s %s" % (vid, msg[:220])); row["visits"][vid] = {"resave": msg[:240]}
            if ok and LIVE: r = freq1_visit.run(vid, cid, int(seq)); row["visits"][vid]["rebill"] = str(r)[-80:]; print("    rebill ->", str(r)[-80:]); time.sleep(0.4)
            elif not ok: row["visits"][vid]["rebill"] = "not sent - the save was not as asked"
    reg[pid] = row
# ---------- (B) KOUSSER 17478219 - WellCare Medicare ----------
if not ONLY or ONLY == "17478219":
    pid = "17478219"; row = {"card": "[name]-17478219", "steps": [], "visits": {}, "answers": {}}
    t = wnotes("[name]-17478219"); m = re.search(r"[name]\s+4/11/1951\s+(\d{6,12})", t); member = m.group(1) if m else ""
    print("== KOUSSER pat%s WellCare member %s" % (pid, "found" if member else "NOT FOUND"))
    active = {}
    if member:
        for dos8 in ("20260901", "20261022"):
            try:
                j = stedi.elig("14163", "SHELBY", "KOUSSER", "19510411", member, dos8, pid=pid)
                os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_elig_14163_%s.json" % (pid, dos8), "w"))
                v, words, rng = fos.verdict(j, dos8, False, "19510411"); active[dos8] = (v == "yes"); row["answers"][dos8] = [v, words[:240], rng]; print("  WellCare on %s: %s - %s" % (dos8, v, words[:200]))
            except Exception as e: row["answers"][dos8] = ["error", "%s: %s" % (type(e).__name__, str(e)[:120])]; print("  WellCare on", dos8, "error", e)
        if any(active.values()):
            pl, order = plans(pid); have = [p for p in pl if p.get("carrier") == "car6174" and not p.get("enddate")]
            if have: insid, seq = have[0]["id"], have[0]["sequence"]; row["steps"].append(["WEL04 plan already on the chart", insid, seq])
            elif not LIVE: insid, seq = None, str(len(pl) + 1); row["steps"].append(["DRY would add WEL04 car6174", member[-4:], "01/01/2025", "seq", seq])
            else:
                insid, seq = add_ins.add(pid, "car6174", member, "01/01/2025"); row["steps"].append(["add WEL04", insid, seq]); print("  add WEL04 ->", insid, seq)
                try: s = elig_amd.run_plan(pid, insid, force=True); row["steps"].append(["AMD 271", elig_amd.one_line(s)[:300]]); print("  271:", elig_amd.one_line(s)[:300])
                except Exception as e: row["steps"].append(["AMD 271 error", str(e)[:100]])
                others = [p.get("sequence") for p in pl if not p.get("enddate")]; want = ",".join([str(seq)] + [o for o in others if o != seq])
                try: res = ins_update.update(pid, insid, sequence=want); row["steps"].append(["patient order", want, str(res)[:160]]); print("  patient order", want, "->", str(res)[:160])
                except Exception as e: row["steps"].append(["patient order error", str(e)[:120]])
            for dos8, vid, cid in (("20260901", "19459521", "23372062"), ("20261022", "19459226", "23371643")):
                if not active.get(dos8): row["visits"][vid] = "not sent - WellCare not active on %s" % dos8; continue
                r = freq1_visit.reroute(vid, cid, str(seq), seq, dry=not LIVE); row["visits"][vid] = str(r)[:240]; print("  v%s -> %s" % (vid, str(r)[:200])); time.sleep(0.4)
    reg[pid] = row
# ---------- (C) CAMERON 17478332 - Florida Blue Medicare Advantage ----------
if not ONLY or ONLY == "17478332":
    pid = "17478332"; row = {"card": "[name]-17478332", "steps": [], "visits": {}, "answers": {}}
    t = wnotes("[name]-17478332"); m = re.search(r"\b([A-Z]{4}\d{8})\b", t); member = m.group(1) if m else ""
    print("== CAMERON pat%s Florida Blue member %s" % (pid, "found" if member else "NOT FOUND"))
    if member:
        pl, order = plans(pid); have = [p for p in pl if p.get("carrier") == "car6062" and not p.get("enddate")]
        if have: insid, seq = have[0]["id"], have[0]["sequence"]; row["steps"].append(["BCBS plan already on the chart", insid, seq])
        elif not LIVE: insid, seq = None, str(len(pl) + 1); row["steps"].append(["DRY would add BCBS car6062", member[-4:], "12/01/2024", "seq", seq])
        else:
            insid, seq = add_ins.add(pid, "car6062", member, "12/01/2024"); row["steps"].append(["add BCBS", insid, seq]); print("  add BCBS ->", insid, seq)
        ok_dos = False
        for num in (member, member[3:]):
            try:
                fn = "patient_db/%s/stedi_elig_BCBSF_20261103_%s.json" % (pid, num[-4:])
                if os.path.exists(fn): j = json.load(open(fn))      # the dry run's answer of this same run - not bought twice
                else:
                    j = stedi.elig("BCBSF", "JO", "CAMERON", "19361128", num, "20261103", pid=pid)
                    os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open(fn, "w"))
                v, words, rng = fos.verdict(j, "20261103", False, "19361128"); row["answers"][num[-4:]] = [v, words[:240], rng]; print("  Florida Blue on 11/03/2026 with ...%s: %s - %s" % (num[-4:], v, words[:200]))
                if v == "yes": ok_dos = True; break
            except Exception as e: row["answers"][num[-4:]] = ["error", "%s: %s" % (type(e).__name__, str(e)[:120])]; print("  error", e)
        if insid and LIVE:
            try: s = elig_amd.run_plan(pid, insid, force=True); row["steps"].append(["AMD 271", elig_amd.one_line(s)[:300]]); print("  271:", elig_amd.one_line(s)[:300])
            except Exception as e: row["steps"].append(["AMD 271 error", str(e)[:100]])
        if ok_dos:
            if insid and LIVE and not have:
                others = [p.get("sequence") for p in pl if not p.get("enddate")]; want = ",".join([str(seq)] + [o for o in others if o != seq])
                try: res = ins_update.update(pid, insid, sequence=want); row["steps"].append(["patient order", want, str(res)[:160]]); print("  patient order", want, "->", str(res)[:160])
                except Exception as e: row["steps"].append(["patient order error", str(e)[:120]])
            r = freq1_visit.reroute("19460350", "23373024", str(seq), seq, dry=not LIVE); row["visits"]["19460350"] = str(r)[:240]; print("  v19460350 -> %s" % str(r)[:200])
        else: row["visits"]["19460350"] = "not sent - Florida Blue did not answer active on 11/03/2026"
    reg[pid] = row
json.dump(reg, open("registers/board_plans_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1); print("register written")
