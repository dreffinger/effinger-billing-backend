# PLAIN ENGLISH (Board answers of 11/19/2026 - William's facesheet pastes entered and the waiting visits sent)
# Decides: Nothing on its own. William answered the Insurance Refresh Board cards of the never-billed feed charts on
#          11/19/2026 06:57-07:50Z by pasting the hospital facesheet insurance block (or his word). For each chart in ITEMS
#          this helper does exactly what the card promised: (1) ends a plan William's sheet replaces, (2) adds the plan the
#          sheet names (carrier + member number, NO group number, begin date as given), (3) sets the chart's default insurance
#          order, (4) runs AdvancedMD's free eligibility check on the new plan and prints its answer, (5) for every visit of
#          the card that carries NO payment: checks the first diagnosis (a never-primary first code is held, not sent), sets
#          the visit's insurance order by the full-visit echo and sends ONE frequency-1 original claim (freq1_visit.reroute).
# Rules it uses: William's facesheet is the source (rules.md 11/10 Q3: a plan from a face sheet or by hand - send); no group
#          numbers; one rebill per visit; never rebill a visit that carries a payment; deceased guard inside amd.rebill_charge.
# Never touches: any visit not named in ITEMS, balances, codes, other plans.
# Usage: python3 board_answers_1119.py [--live] [--only A,B] [--plans-only] [--visits-only]
# Register: registers/board_answers_1119.json (chart / plan / visit ids only)
import amd, add_ins, ins_update, elig_amd, freq1_visit, resave, dx_primary_fix, txh, re, sys, json, time, os
LIVE = "--live" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
PLANS = "--visits-only" not in sys.argv; VISITS = "--plans-only" not in sys.argv
ITEMS = json.load(open("board_answers_1119_items.json"))     # workspace only (member numbers) - never mirrored
REG = "registers/board_answers_1119.json"; reg = json.load(open(REG)) if os.path.exists(REG) else {}
def L(m): print(m, flush=True)
amd.login_cached()
for it in ITEMS:
    k = it["letter"]
    if ONLY and k not in ONLY: continue
    pid = str(it["pid"]); r = reg.setdefault(k, {"pid": pid, "plans": {}, "visits": {}})
    L("\n== %s pat%s ==" % (k, pid))
    _, plans, order0 = ins_update._plans(pid)
    if PLANS:
        for insid, ed in (it.get("end") or {}).items():
            cur = plans.get(insid, {})
            if cur.get("enddate"): L("  end %s: already ended %s" % (insid, cur["enddate"])); continue
            if not LIVE: L("  DRY end %s on %s" % (insid, ed)); continue
            L("  end %s on %s -> %s" % (insid, ed, ins_update.update(pid, insid, enddate=ed)))
        newseq = {}
        for i, pl in enumerate(it.get("add") or []):
            have = [p for p in plans.values() if p.get("carrier") == pl["car"] and (p.get("subscribernum") or "").upper() == pl["id"].upper() and not p.get("enddate")]
            if have:
                newseq[i] = have[0].get("sequence"); r["plans"][pl["car"]] = have[0]["id"]; L("  plan %s already on chart: %s seq %s" % (pl["car"], have[0]["id"], newseq[i])); continue
            if not LIVE: L("  DRY add %s begin %s" % (pl["car"], pl.get("begin"))); newseq[i] = "new%d" % i; continue
            insid, seq = add_ins.add(pid, pl["car"], pl["id"], pl.get("begin"), "1", pl.get("fin", "CC"))
            L("  add %s -> %s seq %s" % (pl["car"], insid, seq))
            if not insid: r["plans"][pl["car"]] = "FAILED " + str(seq)[:120]; continue
            newseq[i] = seq; r["plans"][pl["car"]] = insid; time.sleep(0.4)
        order = it.get("order")
        if order:
            for i, s in newseq.items(): order = order.replace("{%d}" % i, str(s))
            r["order"] = order
            if LIVE and "new" not in order and "{" not in order:
                _, plans, now = ins_update._plans(pid)
                first = [p["id"] for p in plans.values() if p.get("sequence") == order.split(",")[0]]
                if (now or "").replace(" ", "") != order and first:
                    L("  chart order %s -> %s : %s" % (now, order, ins_update.update(pid, first[0], sequence=order)))
                else: L("  chart order already %s" % now)
                for p in plans.values():
                    if p.get("sequence") in order.split(","):
                        try: L("  271 %s seq %s: %s" % (p["id"], p.get("sequence"), elig_amd.one_line(elig_amd.run_plan(pid, p["id"].replace("ins", ""), True))[:330]))
                        except Exception as e: L("  271 %s failed %s" % (p["id"], str(e)[:80]))
            else: L("  %s chart order -> %s" % ("DRY" if not LIVE else "SKIP (plan add failed)", order))
    if VISITS:
        order = r.get("order") or it.get("order")
        if not order or "new" in order or "{" in order: L("  visits: order not settled (%s) - %s" % (order, "dry run" if not LIVE else "NOT sent")); continue
        for vid, cid in (it.get("visits") or {}).items():
            if r["visits"].get(vid, "").find("204") >= 0: L("  v%s already sent this run" % vid); continue
            st = dx_primary_fix.live_state(pid, vid)
            if any(c["pays"] for c in st): r["visits"][vid] = "SKIP payment posted"; L("  v%s SKIP - a payment is posted" % vid); continue
            vis, pat, allc, dxm = dx_primary_fix.visit_dx(cid)
            held = None
            for c in allc:
                codes = [dxm.get(d) for d in (c.get("diagcodes") or "").split(",") if d]
                act, _new = dx_primary_fix.plan(codes, None)
                if act != "ok": held = "%s first dx %s -> %s" % (c.get("id"), codes[:1], act)
            if held: r["visits"][vid] = "HELD dx: " + held; L("  v%s HELD - %s" % (vid, held)); continue
            res = freq1_visit.reroute(vid, cid, order, None, dry=not LIVE)
            r["visits"][vid] = res[-90:]; L("  v%s %s" % (vid, res[-260:])); time.sleep(0.4)
    if LIVE: json.dump(reg, open(REG, "w"), indent=1)
