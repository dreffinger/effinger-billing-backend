# PLAIN ENGLISH (Working Denials - triage every denied ERA line so nothing is silently written off)
# Decides: For each denied charge line on the ERA remits, WHAT it is (CARC/RARC) and WHAT to do about it -
#   FIX (correctable -> rebill), COB (bill the right payer), TIMELY (appeal if proof, else write off),
#   REVIEW (needs a human judgment), CREDENTIALING (payer/provider enrollment gap), PATIENT (move to patient/secondary),
#   DUPLICATE (confirm the original paid, then close), CONTRACTUAL/INFO (normal adjustment, no action).
# Rules it uses: a CARC->disposition table (TABLE / DENIAL_RULES below - since 11/26/2026 the one table the AR aging engine reads
#   too; William edits it here). A visit's disposition = its most
#   actionable line. Read-only: it never posts, rebills or writes off. It emits working_denials_<date>.json + renders
#   the Working Denials board. Correcting/rebilling/writing-off stays a deliberate step (cascade rules or William).
# Never touches: AMD. Pure triage + report.
import json, sys, datetime, collections, glob, os

# CARC (reason code, group-independent) -> (disposition, what to do). Groups: CO contractual, PR patient, OA other, PI payer-initiated.
# 11/26/2026 (William's answers - the work queue): this is the ONE denial-code table of the practice. Each row carries the board's
#   disposition and words AND the AR-aging family (tools/button/aging_refresh.py imports family() and INFO_REASONS from here; until
#   that day it kept a second table and disagreed - 27/26/200/31/49 were wrong payer there and UNCLASSIFIED here: 44 OPEN visits, $9.0K).
#   Every old row keeps its disposition and words; every code in the repository's denial data now has a rule or REVIEW (William's turn);
#   27/26/200/31/49 (and 32/177/140/20/21/B11) are wrong payer -> the coverage cascade; CO-151 on CCM is the re-date of 10/4/2026.
# code -> (disposition, what to do, aging family or None)
TABLE = {
 # --- correctable: fix the claim and rebill (freq-1) ---
 "16":  ("FIX",  "Missing/incorrect info - review the RARC (MA63 dx, N290 rendering NPI, M56 payer id...) and dig deeper before any rebill (William 9/12)", "CORRECT"),
 "125": ("FIX",  "Submission/billing error - correct the flagged data and rebill", "CORRECT"),
 "4":   ("FIX",  "Procedure inconsistent with modifier / missing modifier - add/fix modifier, rebill", "CORRECT"),
 "11":  ("FIX",  "Diagnosis inconsistent with procedure - recheck dx linkage, rebill", "CORRECT"),
 "181": ("FIX",  "Procedure code invalid on DOS - recode, rebill", "CORRECT"),
 "197": ("FIX",  "Auth/precert absent - attach the auth (facesheet/VA), rebill; no auth -> hold, do not bill", None),
 "288": ("FIX",  "Referral absent - obtain referral, rebill", None),
 "B9":  ("FIX",  "Hospice - William 9/12: rebill Medicare with GV modifier (only if DOS within 12 months; older = untimely write-off). CCM codes are the exception: a CCM line denied B9, or denied after going out with GV, is written off WONCS - William 10/15/2026 (see triage_line)", None),
 "226": ("FIX",  "Records requested from provider - William follows up from the list (no auto action)", None),
 "227": ("FIX",  "Info requested from patient not furnished - follow up", None),
 "252": ("FIX",  "Attachment/document required - resubmit with the attachment", None),
 "58":  ("REVIEW","Place of service inconsistent - on a nursing-building line sent as 32 Medicare is saying the resident was in a Part A stay (rules.md 11/10/2026, part 7): name the chart for William; he says for that claim whether it is corrected to 31 and sent again as a new claim; never again at 32, never resent unchanged; on any other line read the RARC", None),
 # new 11/26/2026
 "151": ("FIX",  "Frequency denial - on a CCM claim (a monthly total) re-date the claim to the LAST DAY of its month and send it as an original claim (rules.md 10/4/2026; the new-visit-and-void pattern of 11/19/2026); two CCM claims in one month on one chart = the duplicate is voided, never rebilled; on any other code William reads the RARC", "REDATE"),
 "146": ("FIX",  "Diagnosis invalid for the date of service - the primary-diagnosis cascade (dx_primary_fix) when the remark names the primary position, else William says the code", "CORRECT"),
 "5":   ("FIX",  "Procedure code / type of bill inconsistent with the place of service - William says the place of service (rules.md 11/10/2026 part 7), then rebill as an original", "CORRECT"),
 "163": ("FIX",  "Attachment referenced on the claim was not received - William sends the records (like 252)", None),
 "251": ("FIX",  "Attachment received was incomplete or deficient - William sends the complete records (like 252)", None),
 # --- coordination of benefits: bill the right payer ---
 "22":  ("COB",  "Wrong payer / COB - run the Stedi insurance cascade (MBI lookup / eligibility / discovery), then rebill the right payer (William 9/12)", "WRONG_PAYER"),
 "109": ("COB",  "Not covered by this payer - Stedi insurance cascade to find the right payer, then rebill", "WRONG_PAYER"),
 "24":  ("COB",  "Charges covered under a capitation/MA plan - bill the MA plan (Insurance Refresh cascade)", "WRONG_PAYER"),
 # new 11/26/2026 - wrong payer / coverage: the coverage cascade (RULE C), then ONE re-route (freq1_visit.reroute); never the patient balance
 "27":  ("COB",  "Expenses incurred after coverage terminated - wrong payer: the coverage cascade (RULE C) finds the live plan, then ONE re-route (freq1_visit.reroute); never the patient balance", "WRONG_PAYER"),
 "26":  ("COB",  "Expenses incurred prior to coverage - wrong payer: the coverage cascade (RULE C), then ONE re-route; never the patient balance", "WRONG_PAYER"),
 "200": ("COB",  "Expenses incurred during a lapse in coverage - wrong payer: the coverage cascade (RULE C), then ONE re-route; never the patient balance", "WRONG_PAYER"),
 "31":  ("COB",  "Patient cannot be identified as our insured - wrong insurance: the coverage cascade (RULE C), then ONE re-route", "WRONG_PAYER"),
 "49":  ("COB",  "Routine / screening service not covered by this payer - the coverage cascade (RULE C) decides the payer, then ONE re-route", "WRONG_PAYER"),
 "32":  ("COB",  "Patient is not an eligible dependent - wrong insurance: the coverage cascade (RULE C), then ONE re-route", "WRONG_PAYER"),
 "177": ("COB",  "Patient has not met the eligibility requirements - coverage problem: the coverage cascade (RULE C), then ONE re-route", "WRONG_PAYER"),
 "140": ("COB",  "Insured id and name do not match - wrong member id means wrong insurance (rules.md 10/14/2026): the coverage cascade (RULE C), then ONE re-route", "WRONG_PAYER"),
 "20":  ("COB",  "Covered by the liability carrier - the coverage cascade (RULE C) decides the payer", "WRONG_PAYER"),
 "21":  ("COB",  "Liability of the no-fault carrier - the coverage cascade (RULE C) decides the payer", "WRONG_PAYER"),
 "B11": ("COB",  "Transferred to the proper payer - confirm that payer holds the claim (coverage cascade) before any re-route", "WRONG_PAYER"),
 # --- timely filing: appeal with proof, else deliberate write-off ---
 "29":  ("TIMELY","Timely filing expired - appeal with proof of timely submission if we have it; else WOINS untimely", None),
 # --- non-covered / needs judgment ---
 "96":  ("REVIEW","Non-covered charge - read the RARC; patient-responsibility, non-covered benefit, or recode", "NONCOVERED"),
 "97":  ("REVIEW","Bundled/included in another service - confirm; usually no separate payment", "BUNDLED"),
 "204": ("REVIEW","Not covered under the patient's plan - bill secondary or patient, or write off", "WRONG_PAYER"),
 "234": ("REVIEW","Procedure not paid separately - confirm bundling", "BUNDLED"),
 "A1":  ("REVIEW","Denied, remark code required - read the RARC for the real reason", "NONCOVERED"),
 "50":  ("REVIEW","Not deemed medically necessary - review; appeal with notes or write off", "NONCOVERED"),
 # new 11/26/2026 - William's turn
 "119": ("REVIEW","Benefit maximum for the period reached - William decides: appeal or write off", "NONCOVERED"),
 "236": ("REVIEW","Procedure / modifier combination not compatible with another service the same day (NCCI) - confirm the bundling", "BUNDLED"),
 "B15": ("REVIEW","Needs a qualifying service that was not received or covered - confirm the bundling", "BUNDLED"),
 "39":  ("REVIEW","Services denied when the authorization was requested - William decides on an appeal", None),
 "167": ("REVIEW","Diagnosis not covered - William decides on a diagnosis correction or an appeal", None),
 "286": ("REVIEW","Appeal procedures not followed or time limits not met - William decides", None),
 "6":   ("REVIEW","Procedure inconsistent with the patient's age - William reads the claim", None),
 "9":   ("REVIEW","Diagnosis inconsistent with the patient's age - William reads the claim", None),
 "13":  ("REVIEW","The payer says the date of death precedes the date of service - the date-of-death rule decides (void a charge dated after the death), never a rebill", None),
 "102": ("REVIEW","Major medical adjustment - William reads the remit", None),
 "198": ("REVIEW","Authorization exceeded - William decides on an appeal or a new authorization", None),
 "207": ("REVIEW","Reason 207 - William reads the remit", None),
 "216": ("REVIEW","Based on the findings of a review organization - William decides on an appeal", None),
 "222": ("REVIEW","Exceeds the contracted maximum of hours / days / units for the period - William decides", None),
 "261": ("REVIEW","Procedure inconsistent with the patient's history - William reads the claim", None),
 "272": ("REVIEW","Coverage / program guidelines not met - William decides on an appeal", None),
 "275": ("REVIEW","Prior payer's patient responsibility not covered - William decides (cost-share write-off or the patient)", None),
 "276": ("REVIEW","Services the prior payer denied are not covered by this payer - William decides", None),
 "B14": ("REVIEW","Only one visit or consultation per physician per day is covered - William decides", None),
 "B16": ("REVIEW","'New patient' qualifications were not met - a code change is a new visit and a void of the old line (rules.md 11/19/2026) - William says the code", None),
 "B20": ("REVIEW","Service partly or fully furnished by another provider - William reads the claim", None),
 # --- credentialing / enrollment gaps ---
 "242": ("CRED", "Services not by network provider - credentialing gap (see Credentialing Board)", "CRED"),
 "243": ("CRED", "Services not authorized by network/primary provider - credentialing/referral", "CRED"),
 "185": ("CRED", "Rendering provider not eligible to perform - enrollment gap (e.g. Pam Medicaid)", "CRED"),
 "B7":  ("CRED", "Provider not certified/eligible for this service/date - enrollment", "CRED"),
 # new 11/26/2026
 "170": ("CRED", "Payment denied when performed / billed by this type of provider - enrollment (see Credentialing Board)", "CRED"),
 "147": ("CRED", "Provider contracted / negotiated rate expired or not on file - contract (see Credentialing Board)", "CRED"),
 "256": ("CRED", "Service not payable per the managed care contract - contract / network (see Credentialing Board)", "CRED"),
 "299": ("CRED", "Billing provider not eligible to receive payment for the service - enrollment (see Credentialing Board)", "CRED"),
 # --- patient responsibility: move, don't fix ---
 "1":   ("PATIENT","Deductible - move to patient or secondary", None),
 "2":   ("PATIENT","Coinsurance - move to patient or secondary", None),
 "3":   ("PATIENT","Copay - move to patient or secondary", None),
 # --- duplicates: confirm original paid, then close (NOT a rebill) ---
 "18":  ("DUPLICATE","Exact duplicate claim/service - confirm the original was paid, then close (do not rebill)", None),
 "B13": ("DUPLICATE","Previously paid - confirm the original payment, then close (do not rebill)", None),
 # --- contractual / informational: normal, no action ---
 "45":  ("CONTRACTUAL","Charge exceeds fee schedule (contractual write-down) - normal, no action", None),
 "23":  ("INFO","Impact of prior payer adjudication (COB info) - informational", None),
 "253": ("INFO","Sequestration reduction - informational", None),
 "246": ("INFO","Non-payable code for required reporting only (a quality code such as 1123F, or the option code M0004) - reporting line - nothing to do, never bill a cent of it to the patient. Remark N620 on the 1123F line shows Medicare received the code and that it is valid for the year; whether the measure is met shows only in the feedback on the Medicare quality-program site. A one-cent charge on that line is contractual", None),
 "94":  ("INFO","Processed in excess/duplicate of charges - informational", None),
 "253 ":("INFO","Sequestration - informational", None),
}

# what the board shows: code -> (disposition, what to do)
DENIAL_RULES = {k: (v[0], v[1]) for k, v in TABLE.items()}

# tools/button/aging_refresh.py's families (it imports family() and INFO_REASONS from this file). AGING_EXTRA keeps an entry that is not a CARC (the remark MA130 sat in the correctable set) so the set
# is exactly what it was before 11/26/2026.
AGING_EXTRA = {"CORRECT": {"MA130"}}


def family(name):
    """The codes of one aging family (WRONG_PAYER, BUNDLED, CORRECT, CRED, NONCOVERED, REDATE) as a set."""
    return {k.strip() for k, v in TABLE.items() if v[2] == name} | set(AGING_EXTRA.get(name, ()))


# the reasons that never make a visit read as denied: contractual, informational and the PR cost-share codes (aging_refresh INFO_REASONS)
INFO_REASONS = tuple(sorted({k.strip() for k, v in TABLE.items() if v[0] in ("CONTRACTUAL", "INFO", "PATIENT")}))
DISPO_ORDER = ["FIX","COB","TIMELY","WRITEOFF","CRED","REVIEW","PATIENT","DUPLICATE","CONTRACTUAL","INFO","UNCLASSIFIED"]
ACTIONABLE = {"FIX","COB","TIMELY","WRITEOFF","CRED","REVIEW"}
# CCM / care-management codes: a denied CCM line on a hospice patient is never appealed or rebilled (William 10/15/2026:
# "ccm denied with gv modifier write off, ccm isn't covered for hospice patients"). Evidence the same night: Medicare DOES pay
# CCM billed with GV (17 of 29 CCM-GV visits on the unpaid list were paid in Oct 2026), so the rule is about the DENIED ones.
CCM_CODES = {"99490", "99491", "99487", "99489", "99439", "99437", "G0506", "G0511", "99424", "99425", "99426", "99427"}
# REPORTING LINES (11/10/2026, Medicare review M7): a no-charge quality code (1123F / 1124F, advance care plan) or option code (M0004) that
# the feed import adds rides at $0.00 or $0.01 on a Medicare claim. Whatever reason or group code its remittance line carries, it is INFO:
# never work, never a rebill, never a patient balance. triage() itself checks it, so the board's roll-up and the refresh step both pass it.
REPORTING_CODES = {"1123F", "1124F", "M0004"}
REPORTING_WORDS = "reporting line - nothing to do, never bill a cent of it to the patient"

def norm(carc):
    """AMD reasoncode carries a doubled group prefix: 'CO18'->'18', 'COA1'->'A1', 'PI29'->'29'. Strip one leading group token."""
    c = str(carc or "").strip().upper()
    for g in ("CO", "OA", "PR", "PI", "CR"):
        if c.startswith(g) and len(c) > len(g): return c[len(g):]
    return c

def age_days(dos):
    try: return (datetime.date.today() - datetime.date.fromisoformat(str(dos)[:10])).days
    except Exception: return None

def triage(carc, cpt=""):
    code = norm(carc)
    if str(cpt or "").strip().upper() in REPORTING_CODES: return ("INFO", "%s (%s, reason %s)" % (REPORTING_WORDS, str(cpt).strip().upper(), code))
    if code in DENIAL_RULES: return DENIAL_RULES[code]
    return ("UNCLASSIFIED", "No rule yet for CARC %s - review and add to DENIAL_RULES" % code)

def triage_line(carc, cpt="", mods=""):
    """CPT-aware triage (10/15/2026): a CCM line denied CO-B9, or denied (any non-informational, non-cost-share CARC) after it went
    out carrying the GV hospice modifier, is a WONCS write-off - no appeal, no rebill (William 10/15/2026). Everything else = triage(carc)."""
    code = norm(carc); c = str(cpt or "").strip().upper(); m = str(mods or "").upper()
    if c in REPORTING_CODES: return triage(carc, c)      # a reporting line is INFO whatever its reason code
    if c in CCM_CODES and (code == "B9" or ("GV" in m and code not in ("45", "253", "23", "94", "1", "2", "3"))):
        return ("WRITEOFF", "CCM denied on a hospice patient (%s%s) -> WONCS, no appeal (William 10/15/2026: CCM denied with GV / CO-B9 is written off)" % ("GV, " if "GV" in m else "", code))
    return triage(carc, c)

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
        dispo, action = triage(code, r.get("cpt"))      # the procedure too: a reporting line (1123F / 1124F / M0004) is INFO whatever its reason code
        key = (r["pid"], r["visitid"])
        rec = byv.get(key)
        rank = DISPO_ORDER.index(dispo) if dispo in DISPO_ORDER else len(DISPO_ORDER)
        if norm(code) == "58" and dispo == "REVIEW": rank = -1      # Medicare's place-of-service answer always leads its visit (rules.md 11/10/2026 part 7; challenge review 11/10/2026): never hidden behind a rebill class on the same visit
        if rec is None or rank < rec["_rank"]:
            byv[key] = {"_rank": rank, "patient": r["patient"], "pid": r["pid"], "visitid": r["visitid"],
                "carrier": r["carrier"], "dos": r["dos"], "cpt": r["cpt"], "billed": r.get("billed"),
                "dispo": dispo, "action": action, "carc": norm(code), "reason": r.get("reason"),
                "check": r.get("check"), "amt": abs(r.get("amt") or 0), "codes": (rec["codes"] if rec else set()), "rarc": (rec["rarc"] if rec else set()),      # a more actionable line keeps the codes already seen on the visit
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
