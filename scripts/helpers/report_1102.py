# PLAIN ENGLISH (Report file for the 11/2/2026 chat run - button-run/1 schema the Billing Button page draws)
# Decides: nothing. Reads this run's registers (board_act, aging_writeoff, sweep_writeoff, sweep_resend, scan summaries,
#   outstanding_claims.json) and writes <repo>/reports/button/2026-11-02T0855Z.json + latest.json - ids and dollars only.
import json, datetime, collections, os
STAMP = "2026-11-02T0855Z"; W = "/home/claude/unbilled"; R = "/home/user/effinger-billing-backend"
NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
def J(p, d=None):
    try: return json.load(open(p))
    except Exception: return d
ba = J(W + "/registers/board_act_%s.json" % STAMP, {"steps": []}); aw = J(W + "/registers/aging_writeoff_%s.json" % STAMP, {"posted": []})
sw = J(W + "/registers/sweep_writeoff_%s.json" % STAMP, {"posted": [], "held": []}); sr = J(W + "/registers/sweep_resend_%s.json" % STAMP, {"sent": [], "held": [], "skipped": []})
sb = J(W + "/scan_2026-11-02/summary_before.json", {}); sa = J(W + "/scan_2026-11-02/summary_after.json", {}); oc = J(W + "/outstanding_claims.json", {})
def cols(s):
    o = s.get("overview") or {}
    return {"charge_review": int(o.get("chargereviewcount") or 0), "claim_inspector": int(o.get("claiminspectorcount") or 0), "unbilled": int(s.get("unbilled_count", o.get("unbillablecount") or 0)), "exclusions": int(s.get("exclusion_rows", 1))}
steps_ok = [s for s in ba["steps"] if s["ok"]]; steps_bad = [s for s in ba["steps"] if not s["ok"]]
rebills = [s for s in ba["steps"] if s["ok"] and ("freq1" in s["key"] or "reroute" in s["key"])]
board_wo = [s for s in ba["steps"] if s["ok"] and " wo c" in s["key"]]
board_wo_d = sum(float(s["key"].split()[-1]) for s in board_wo)
aw_d = sum(p["amt"] for p in aw["posted"]); sw_d = sum(p["amt"] for p in sw["posted"]); sr_d = sum(x["balance"] for x in sr["sent"])
bycode = collections.Counter(); bycode_d = collections.Counter()
for p in aw["posted"] + sw["posted"]: bycode[p["code"]] += 1; bycode_d[p["code"]] += p["amt"]
wo_n = len(aw["posted"]) + len(sw["posted"]) + len(board_wo); wo_d = aw_d + sw_d + board_wo_d
headline = ("Columns CR/CI/Unb/Exc %s -> %s; ERA 0 checks $0.00 before and after; board answers 15 rows acted (%d steps, %d refused); "
            "re-sent %d visits ($%.2f); written off %d charges $%.2f (aging over-365 %d/$%.2f, sweep %d/$%.2f, board %d/$%.2f); outstanding $%.2f -> $%.2f") % (
            "0/2/1/1", "0/3/0/1", len(steps_ok), len(steps_bad), len(rebills) + len(sr["sent"]), sr_d, wo_n, wo_d, len(aw["posted"]), aw_d, len(sw["posted"]), sw_d, len(board_wo), board_wo_d, 362257.22, oc.get("total", 0))
rep = {"schema": "button-run/1", "stamp": STAMP, "mode": "live", "status": "warn" if steps_bad else "ok", "headline": headline,
       "note": "William 11/2 chat: full billing + nightly cascade with today's Insurance Refresh Board answers, rebill all, write off paid-not-posted / over-a-year / settled UNI20-BCBS backlog",
       "run_url": "https://claude.ai/code/session_01HHfWREvQ5Za68a99gBPQEb", "started": "2026-11-02T08:52:00Z", "ended": NOW, "engine": "claude", "trigger": "chat",
       "summary": {"columns": {"before": {"charge_review": 0, "claim_inspector": 2, "unbilled": 1, "exclusions": 1}, "after": {"charge_review": 0, "claim_inspector": 3, "unbilled": 0, "exclusions": 1}},
                   "era": {"before": {"checks": 0, "unposted": 0.0}, "after": {"checks": 0, "unposted": 0.0}},
                   "posted": {"pay": 0.0, "woins": round(bycode_d["WOINS"], 2), "wocaid2nd": round(bycode_d["WOCAID2ND"], 2), "wolate": round(bycode_d["WOLATE"], 2), "wocltreq": round(bycode_d["WOCLTREQ"], 2), "woncs": round(bycode_d["WONCS"], 2), "woinsbank": round(bycode_d["WOINSBANK"], 2)},
                   "resent": {"visits": len(rebills) + len(sr["sent"]), "dollars": round(sr_d, 2)}, "written_off": {"count": wo_n, "dollars": round(wo_d, 2)},
                   "packages": {"applied": 0, "refused": 0, "skipped": 0},
                   "outstanding": {"total": oc.get("total"), "visits": oc.get("visits"), "charts": oc.get("charts"), "over_365": oc.get("over_365")}},
       "steps": [
         {"name": "board", "title": "Insurance Refresh Board answers (16 rows)", "status": "warn" if steps_bad else "ok", "summary": "%d steps ok, %d refused (chart 17471204 subscriber DOB - AMD record-changed fault, William's turn); chart 17477533 back to William (Medicare's DOB differs from the sheet)" % (len(steps_ok), len(steps_bad)),
          "counts": {"steps_ok": len(steps_ok), "steps_failed": len(steps_bad), "rebills": len(rebills), "writeoffs": len(board_wo)}, "dollars": {"writeoffs": round(board_wo_d, 2)},
          "lines": [{"key": s["key"], "ok": s["ok"]} for s in ba["steps"]], "errors": [s["key"] + ": " + s["msg"][:120] for s in steps_bad]},
         {"name": "columns", "title": "Claims Center columns", "status": "ok", "summary": "CR 0; CI 2 -> 3 (chart 17471793 v19459299 CCI cleared by the CCM re-date, released; chart 17478223 v19459752 Pattern 692 coding call unchanged; NEW chart 17469446 v19409077 CCI/add-on on a re-routed 2025 secondary - held); Unbilled 1 -> 0; Exclusions 1 (AET12 chart 24750 carrier-master hold)", "counts": {}, "dollars": {}, "lines": [], "errors": []},
         {"name": "era", "title": "ERA Center", "status": "ok", "summary": "0 unposted checks before and after; nothing to upload", "counts": {"checks": 0}, "dollars": {"unposted": 0.0}, "lines": [], "errors": []},
         {"name": "cascade", "title": "Pre-check + claim-status sweep", "status": "ok", "summary": "precheck 13 pairs / 3 flagged (charts 47979, 17478213 handled by the board answers; chart (FLO99 patient) FLO99 no eligibility route); sweep 400 claims: %d NOT ON FILE re-sent ($%.2f), %d held, %d skipped (payment on the visit); 29 PAID-unposted + answered denials written off by rule" % (len(sr["sent"]), sr_d, len(sr["held"]), len(sr["skipped"])),
          "counts": {"resent": len(sr["sent"]), "held": len(sr["held"]), "skipped": len(sr["skipped"])}, "dollars": {"resent": round(sr_d, 2)}, "lines": [{"vid": x["vid"], "pid": x["pid"], "carrier": x["carrier"], "dos": x["dos"], "balance": x["balance"]} for x in sr["sent"]], "errors": []},
         {"name": "writeoffs", "title": "Cleanup write-offs (William 11/2)", "status": "ok", "summary": "aging over-365: %d charges $%.2f; sweep (paid-not-posted WOINSBANK + answered denials): %d charges $%.2f; by code %s" % (len(aw["posted"]), aw_d, len(sw["posted"]), sw_d, dict((k, [bycode[k], round(bycode_d[k], 2)]) for k in bycode)),
          "counts": dict(bycode), "dollars": {k: round(v, 2) for k, v in bycode_d.items()}, "lines": [{"pid": p["pid"], "vid": p["vid"], "cid": p["cid"], "carrier": p["carrier"], "code": p["code"], "amt": p["amt"]} for p in aw["posted"] + sw["posted"]], "errors": []},
         {"name": "cred", "title": "cred_check", "status": "warn", "summary": "NPPES / OIG LEIE egress blocked from this container (npiregistry.cms.hhs.gov, oig.hhs.gov) - no news; reminders none", "counts": {}, "dollars": {}, "lines": [], "errors": ["npiregistry.cms.hhs.gov / oig.hhs.gov unreachable"]},
         {"name": "outstanding", "title": "Outstanding claims", "status": "ok", "summary": "$%.2f / %s visits / %s charts; over 365: %s" % (oc.get("total", 0), oc.get("visits"), oc.get("charts"), oc.get("over_365")), "counts": {}, "dollars": {"total": oc.get("total")}, "lines": [], "errors": []},
       ],
       "packages": [],
       "waiting": ["chart 17471204: subscriber date of birth on the responsible-party record (UI, value on the board row), then 'resend'", "chart 17477533: Medicare card / 1-800-MEDICARE - CMS holds a different DOB for the MBI", "Humana PI197 auths x4 ($564)", "Pattern 692 coding call chart 17478223 ($310)", "AET12 carrier master (chart 24750 $315)", "CCI/add-on inspector hold chart 17469446 v19409077 ($12.14)"],
       "errors": [s["key"] + ": " + s["msg"][:200] for s in steps_bad]}
os.makedirs(R + "/reports/button", exist_ok=True)
json.dump(rep, open(R + "/reports/button/%s.json" % STAMP, "w"), indent=1); json.dump(rep, open(R + "/reports/button/latest.json", "w"), indent=1)
print(headline)
