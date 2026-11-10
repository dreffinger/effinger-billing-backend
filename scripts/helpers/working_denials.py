# PLAIN ENGLISH (Working Denials - triage every denied ERA line so nothing is silently written off)
# Decides: For each denied charge line on the ERA remits, WHAT it is (CARC/RARC) and WHAT to do about it -
#   FIX (correctable -> rebill), COB (bill the right payer), TIMELY (appeal if proof, else write off),
#   REVIEW (needs a human judgment), CREDENTIALING (payer/provider enrollment gap), PATIENT (move to patient/secondary),
#   DUPLICATE (confirm the original paid, then close), CONTRACTUAL/INFO (normal adjustment, no action).
# Rules it uses: a CARC->disposition table (denial_rules below - William edits this). A visit's disposition = its most
#   actionable line. Read-only: it never posts, rebills or writes off. It emits working_denials_<date>.json + renders
#   the Working Denials board. Correcting/rebilling/writing-off stays a deliberate step (cascade rules or William).
# Never touches: AMD. Pure triage + report.
import json, sys, datetime, collections, glob, os

# CARC (reason code, group-independent) -> (disposition, what to do). Groups: CO contractual, PR patient, OA other, PI payer-initiated.
DENIAL_RULES = {
 # --- correctable: fix the claim and rebill (freq-1) ---
 "16":  ("FIX",  "Missing/incorrect info - review the RARC (MA63 dx, N290 rendering NPI, M56 payer id...) and dig deeper before any rebill (William 9/12)"),
 "125": ("FIX",  "Submission/billing error - correct the flagged data and rebill"),
 "4":   ("FIX",  "Procedure inconsistent with modifier / missing modifier - add/fix modifier, rebill"),
 "11":  ("FIX",  "Diagnosis inconsistent with procedure - recheck dx linkage, rebill"),
 "181": ("FIX",  "Procedure code invalid on DOS - recode, rebill"),
 "197": ("FIX",  "Auth/precert absent - attach the auth (facesheet/VA), rebill; no auth -> hold, do not bill"),
 "288": ("FIX",  "Referral absent - obtain referral, rebill"),
 "B9":  ("FIX",  "Hospice - William 9/12: rebill Medicare with GV modifier (only if DOS within 12 months; older = untimely write-off)"),
 "58":  ("REVIEW","Place of service inconsistent - on a nursing-building line sent as 32 Medicare is saying the resident was in a Part A stay (rules.md 11/10/2026, part 7): name the chart for William; he says for that claim whether it is corrected to 31 and sent again as a new claim; never again at 32, never resent unchanged; on any other line read the RARC"),
 "226": ("FIX",  "Records requested from provider - William follows up from the list (no auto action)"),
 "227": ("FIX",  "Info requested from patient not furnished - follow up"),
 "252": ("FIX",  "Attachment/document required - resubmit with the attachment"),
 # --- coordination of benefits: bill the right payer ---
 "22":  ("COB",  "Wrong payer / COB - run the Stedi insurance cascade (MBI lookup / eligibility / discovery), then rebill the right payer (William 9/12)"),
 "109": ("COB",  "Not covered by this payer - Stedi insurance cascade to find the right payer, then rebill"),
 "24":  ("COB",  "Charges covered under a capitation/MA plan - bill the MA plan (Insurance Refresh cascade)"),
 # --- timely filing: appeal with proof, else deliberate write-off ---
 "29":  ("TIMELY","Timely filing expired - appeal with proof of timely submission if we have it; else WOINS untimely"),
 # --- non-covered / needs judgment ---
 "96":  ("REVIEW","Non-covered charge - read the RARC; patient-responsibility, non-covered benefit, or recode"),
 "97":  ("REVIEW","Bundled/included in another service - confirm; usually no separate payment"),
 "204": ("REVIEW","Not covered under the patient's plan - bill secondary or patient, or write off"),
 "234": ("REVIEW","Procedure not paid separately - confirm bundling"),
 "A1":  ("REVIEW","Denied, remark code required - read the RARC for the real reason"),
 "50":  ("REVIEW","Not deemed medically necessary - review; appeal with notes or write off"),
 # --- credentialing / enrollment gaps ---
 "242": ("CRED", "Services not by network provider - credentialing gap (see Credentialing Board)"),
 "243": ("CRED", "Services not authorized by network/primary provider - credentialing/referral"),
 "185": ("CRED", "Rendering provider not eligible to perform - enrollment gap (e.g. Pam Medicaid)"),
 "B7":  ("CRED", "Provider not certified/eligible for this service/date - enrollment"),
 # --- patient responsibility: move, don't fix ---
 "1":   ("PATIENT","Deductible - move to patient or secondary"),
 "2":   ("PATIENT","Coinsurance - move to patient or secondary"),
 "3":   ("PATIENT","Copay - move to patient or secondary"),
 # --- duplicates: confirm original paid, then close (NOT a rebill) ---
 "18":  ("DUPLICATE","Exact duplicate claim/service - confirm the original was paid, then close (do not rebill)"),
 # --- contractual / informational: normal, no action ---
 "45":  ("CONTRACTUAL","Charge exceeds fee schedule (contractual write-down) - normal, no action"),
 "23":  ("INFO","Impact of prior payer adjudication (COB info) - informational"),
 "253": ("INFO","Sequestration reduction - informational"),
 "94":  ("INFO","Processed in excess/duplicate of charges - informational"),
 "253 ":("INFO","Sequestration - informational"),
}
DISPO_ORDER = ["FIX","COB","TIMELY","CRED","REVIEW","PATIENT","DUPLICATE","CONTRACTUAL","INFO","UNCLASSIFIED"]
ACTIONABLE = {"FIX","COB","TIMELY","CRED","REVIEW"}

def norm(carc):
    """AMD reasoncode carries a doubled group prefix: 'CO18'->'18', 'COA1'->'A1', 'PI29'->'29'. Strip one leading group token."""
    c = str(carc or "").strip().upper()
    for g in ("CO", "OA", "PR", "PI", "CR"):
        if c.startswith(g) and len(c) > len(g): return c[len(g):]
    return c

def age_days(dos):
    try: return (datetime.date.today() - datetime.date.fromisoformat(str(dos)[:10])).days
    except Exception: return None

def triage(carc):
    code = norm(carc)
    if code in DENIAL_RULES: return DENIAL_RULES[code]
    return ("UNCLASSIFIED", "No rule yet for CARC %s - review and add to DENIAL_RULES" % code)

def amd_status(visits):
    """Cross-check each denied visit against AMD: RESOLVED (a real payment posted), WRITTEN-OFF, OPEN. Cached per patient.
    Overlays RESUBMITTED from wd_resubmitted.json (visits the ACT step rebilled, with the date)."""
    import txh
    resub = json.load(open("wd_resubmitted.json")) if os.path.exists("wd_resubmitted.json") else {}
    cache = {}
    for v in visits:
        pid = v.get("pid"); vid = str(v.get("visitid"))
        if not pid or int(pid) <= 0: v["status"] = "UNMATCHED"; continue
        if pid not in cache:
            try:
                st = {}
                for c in txh.fetch(pid).iter("charge"):
                    if c.get("void") == "1": continue
                    k = c.get("visit"); s = st.setdefault(k, {"pays": 0, "wos": 0, "bal": 0.0})
                    s["pays"] += sum(1 for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0)
                    s["wos"] += sum(1 for w in c.iter("writeoff") if w.get("void") != "1" and float(w.get("amount") or 0) != 0)
                    s["bal"] += float(c.get("insbal") or 0) + float(c.get("patbal") or 0)
                cache[pid] = st
            except Exception: cache[pid] = None
        st = cache[pid]
        if st is None: v["status"] = "UNKNOWN"; continue
        s = st.get(vid)
        if vid in resub: v["status"] = "RESUBMITTED"; v["resubmitted"] = resub[vid]
        elif not s: v["status"] = "UNMATCHED"
        elif s["pays"]: v["status"] = "RESOLVED"
        elif s["wos"] and s["bal"] <= 0: v["status"] = "WRITTEN-OFF"
        else: v["status"] = "OPEN"
    return visits

def main():
    stamp = datetime.date.today().strftime("%Y%m%d")
    src = sorted(glob.glob("denials_*.json"))
    if not src: print("no denials_*.json - run the scan first"); return
    rows = json.load(open(src[-1]))
    # roll up to per-visit: keep the most actionable line, and list all codes
    byv = {}
    for r in rows:
        code = str(r.get("carc") or "").strip()
        dispo, action = triage(code)
        key = (r["pid"], r["visitid"])
        rec = byv.get(key)
        rank = DISPO_ORDER.index(dispo) if dispo in DISPO_ORDER else len(DISPO_ORDER)
        if rec is None or rank < rec["_rank"]:
            byv[key] = {"_rank": rank, "patient": r["patient"], "pid": r["pid"], "visitid": r["visitid"],
                "carrier": r["carrier"], "dos": r["dos"], "cpt": r["cpt"], "billed": r.get("billed"),
                "dispo": dispo, "action": action, "carc": norm(code), "reason": r.get("reason"),
                "check": r.get("check"), "amt": abs(r.get("amt") or 0), "codes": set(), "rarc": set(),
                "age": age_days(r["dos"]), "timely": (age_days(r["dos"]) or 9999) <= 365}
        byv[key]["codes"].add("%s/%s" % (r.get("group"), code))
        for x in (r.get("rarc") or []): byv[key]["rarc"].add(x)
        if rec: byv[key]["amt"] = byv[key].get("amt", 0)
    visits = []
    for v in byv.values():
        v["codes"] = sorted(v.pop("codes")); v["rarc"] = sorted(v.pop("rarc")); v.pop("_rank")
        visits.append(v)
    if "--amd" in sys.argv: amd_status(visits)
    else:
        for v in visits: v.setdefault("status", "")
    # summary
    bydispo = collections.defaultdict(lambda: {"visits": 0, "amt": 0.0, "patients": set()})
    for v in visits:
        d = bydispo[v["dispo"]]; d["visits"] += 1; d["amt"] += v["amt"]; d["patients"].add(v["pid"])
    summary = {k: {"visits": val["visits"], "amt": round(val["amt"], 2), "patients": len(val["patients"])} for k, val in bydispo.items()}
    actionable_visits = [v for v in visits if v["dispo"] in ACTIONABLE and v.get("status") not in ("RESOLVED", "RESUBMITTED")]
    timely_act = [v for v in actionable_visits if v.get("timely")]
    bystatus = collections.Counter(v.get("status") or "n/a" for v in visits)
    resub_amt = round(sum(v["amt"] for v in visits if v.get("status") == "RESUBMITTED"), 2)
    resolved_amt = round(sum(v["amt"] for v in visits if v.get("status") == "RESOLVED"), 2)
    out = {"asof": datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC"), "total_lines": len(rows),
           "total_visits": len(visits), "actionable_visits": len(actionable_visits),
           "actionable_amt": round(sum(v["amt"] for v in actionable_visits), 2),
           "timely_visits": len(timely_act), "timely_amt": round(sum(v["amt"] for v in timely_act), 2),
           "bystatus": dict(bystatus), "resub_amt": resub_amt, "resolved_amt": resolved_amt,
           "summary": summary, "visits": sorted(visits, key=lambda v: (DISPO_ORDER.index(v["dispo"]) if v["dispo"] in DISPO_ORDER else 99, -v["amt"]))}
    json.dump(out, open("working_denials_%s.json" % stamp, "w"), indent=1)
    print("visits triaged:", len(visits), "| actionable:", len(actionable_visits), "$%.2f" % out["actionable_amt"])
    for d in DISPO_ORDER:
        if d in summary: print("  %-12s %4d visits  $%12.2f  (%d patients)" % (d, summary[d]["visits"], summary[d]["amt"], summary[d]["patients"]))
    return out

def render_html(out, path="working_denials.html"):
    import json as _j
    # cap the no-action groups so the page stays light; actionable groups ship in full
    CAPS = {"DUPLICATE": 120, "CONTRACTUAL": 60, "INFO": 40, "PATIENT": 60}
    vis = out["visits"]; capped = {}
    kept = []
    seen = collections.Counter()
    for v in vis:
        d = v["dispo"]; lim = CAPS.get(d)
        seen[d] += 1
        if lim and seen[d] > lim:
            capped[d] = capped.get(d, 0) + 1
            continue
        kept.append({k: v.get(k) for k in ("patient","pid","visitid","carrier","dos","cpt","billed","dispo","action","carc","reason","check","amt","codes","rarc","age","timely","status","resubmitted")})
    data = {"asof": out["asof"], "total_lines": out["total_lines"], "total_visits": out["total_visits"],
            "actionable_visits": out["actionable_visits"], "actionable_amt": out["actionable_amt"],
            "timely_visits": out.get("timely_visits", 0), "timely_amt": out.get("timely_amt", 0),
            "bystatus": out.get("bystatus", {}), "resub_amt": out.get("resub_amt", 0), "resolved_amt": out.get("resolved_amt", 0),
            "summary": out["summary"], "capped": capped, "visits": kept}
    html = _template().replace("/*__DATA__*/null", _j.dumps(data))
    open(path, "w").write(html)
    return path

def _template():
    """The board page minus its data line. The live artifact is the source (a 'rerun' regenerates the workspace copy from it); the
    repo copy boards/templates/working_denials_template.html (v7, 10/13/2026: Refresh-from-AMD strip) is the fallback - found
    next to this file wherever the repo is checked out. The Drive 'workspace mirror' copy of 9/29 was trashed 10/13 (stale, no
    Refresh strip) so an old copy can never be picked up first."""
    here = os.path.dirname(os.path.abspath(__file__))
    for p in ("working_denials_template.html", os.path.join(here, "templates", "working_denials_template.html"),
              "/home/claude/effinger-billing-backend/boards/templates/working_denials_template.html"):
        if os.path.exists(p): return open(p).read()
    raise FileNotFoundError("working_denials_template.html (Drive 'workspace mirror' / repo boards/templates)")


if __name__ == "__main__":
    out = main()
    if out: print("board ->", render_html(out))
