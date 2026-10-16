# PLAIN ENGLISH (A/R aging by payer, chat 10/15/2026 - William: "where all the columns and rebilled and outstanding claims
#   are with payers ... by 30 / 60 / 90 / over 120 days with recs to wait, correct and resend, or write off")
# Decides: nothing in AMD. READ-ONLY over two local snapshots: unpaid_raw_1015.json (massrebillsearch = every open insurance
#   balance, with the LAST-BILLED carrier) and patient_db/<pid>/txh_1015.json (the chart's live transaction history: bill dates,
#   payments with CARC reasons, write-offs). For every unpaid visit it works out: days since the claim was LAST SENT, days since
#   the date of service, whether a primary payment already exists (then the balance is a secondary / cost-share remainder),
#   the latest posted denial (CARC) and the recommendation by William's standing rules.
# Rules it uses (practices/ehpa/rules.md + the billing skills):
#   - 0-30 days since sent: WAIT. 31-60: WAIT (UNI20/BCBS: do not rebill - ERA backlog). 61-90: check status / resend as an
#     ORIGINAL (freq 1). 91-120: fix & resend. >120 (10/13 rule): anything that old must be waiting on an adjudication -
#     otherwise fix+resend, or write off.
#   - A PRIMARY claim unpaid > 12 months from DOS = WOINS untimely. A SECONDARY balance is timely from the primary's remit,
#     not the DOS: primary remit > 12 months old -> write off (WOCLTREQ cost-share / WOINS); recent remit -> rebill the secondary.
#   - Denials by CARC follow the Working Denials table; CCM (99490/99491/99487/99489/99439/99437/G0506) denied with a GV
#     modifier, or denied CO-B9 hospice -> WONCS write-off (William 10/15: CCM isn't covered for hospice patients).
#     CCM billed to straight Medicaid (MCAD) -> write off. Wrong-payer denials (PR27/26/200/31/109/22/24) -> insurance cascade.
#   - Patient balances are not in this list (insurance balances only); nothing here is a write-off until William says so.
# Never touches: AMD. Output: aging_1015_summary.json (tables) + aging_1015_visits.csv (one row per visit, chart ids only).
import csv, datetime, json, os, re, collections, sys

WS = "/home/claude/unbilled"
TODAY = datetime.date.today()
CCM = {"99490", "99491", "99487", "99489", "99439", "99437", "G0506", "G0511", "99424", "99425", "99426", "99427"}
WRONG_PAYER = {"27", "26", "200", "31", "109", "22", "24", "204", "49"}
BACKLOG = {"UNI20", "BCBS"}
num = lambda s: re.sub(r"\D", "", str(s or ""))

def mdy(s):
    m = re.match(r"\s*(\d\d)/(\d\d)/(\d{4})", str(s or ""))
    return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else None

def iso(s):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)", str(s or ""))
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None

def norm(carc):
    c = str(carc or "").strip().upper()
    for g in ("CO", "OA", "PR", "PI", "CR"):
        if c.startswith(g) and len(c) > len(g): return c[len(g):]
    return c

def group(carc):
    c = str(carc or "").strip().upper()
    return c[:2] if c[:2] in ("CO", "OA", "PR", "PI", "CR") else ""

def bucket(days):
    if days is None: return "unknown"
    if days <= 30: return "0-30"
    if days <= 60: return "31-60"
    if days <= 90: return "61-90"
    if days <= 120: return "91-120"
    return "over 120"

rows = json.load(open(os.path.join(WS, "unpaid_raw_1015.json")))
CAR = {k: v[0] for k, v in json.load(open(os.path.join(WS, "carriers.json"))).items() if isinstance(v, list)}
DEC = {}
try:
    DEC = {k: iso(v.get("dod")) for k, v in json.load(open("/home/claude/practices/ehpa/registers/deceased_cache.json")).items() if v.get("dod") and re.match(r"\d{4}-\d{2}-\d{2}$", str(v.get("dod")))}
except Exception: pass
MEDICAID_FAMILY = {"MCAD", "SUN01", "FLO99", "SIM01", "WEL04", "UHCMA", "HUM07"}

def chart_plans(pid):
    p = os.path.join(WS, "patient_db", pid, "plans_1015.json")
    if not os.path.exists(p): return None
    d = json.load(open(p)); out = []
    for pl in d.get("plans", []):
        out.append({"code": CAR.get(pl.get("carrier"), pl.get("carrier")), "seq": pl.get("sequence"), "begin": mdy(pl.get("begindate")), "end": mdy(pl.get("enddate"))})
    return {"plans": out, "insorder": d.get("insorder"), "deceased": d.get("deceased")}

out = []
missing_txh = 0
for r in rows:
    pid = str(r["patientid"]); vid = str(r["visitid"])
    carrier = (r.get("carriercode") or "NONE").strip() or "NONE"
    bal = round(float(r.get("insbalance") or 0), 2)
    dos = iso(r.get("dateofservice"))
    rec = {"pid": pid, "visitid": vid, "chart": "", "payer_last_billed": carrier, "dos": dos.isoformat() if dos else "", "fee": r.get("totalvisitamount"),
           "ins_balance": bal, "icn": bool(r.get("icn")), "corrected": bool(r.get("correctedclaim"))}
    p = os.path.join(WS, "patient_db", pid, "txh_1015.json")
    charges = []
    if os.path.exists(p):
        charges = [c for c in json.load(open(p))["charges"] if num(c.get("visit") or c.get("visitid")) == vid and c.get("void") != "1"]
    if not charges:
        missing_txh += 1
    cpts = sorted({c.get("proccode", "") for c in charges})
    mods = sorted({(c.get("modcodes") or c.get("modifiers") or "").strip() for c in charges} - {""})
    bill_dates = [mdy(c.get("billdate")) for c in charges if mdy(c.get("billdate"))]
    last_sent = max(bill_dates) if bill_dates else None
    pays = [p for c in charges for p in c.get("payments", []) if p.get("void") != "1"]
    real_pays = [p for p in pays if abs(float(p.get("amount") or 0)) > 0.005]
    zero_pays = [p for p in pays if abs(float(p.get("amount") or 0)) <= 0.005]
    zero_denials = [p for p in zero_pays if p.get("reasons")]
    pr_only_zero = [p for p in zero_denials if all(group(code) == "PR" and norm(code) in ("1", "2", "3") for code, amt in p.get("reasons", []))]
    denial_codes = sorted({norm(code) for p in zero_denials if p not in pr_only_zero for code, amt in p.get("reasons", []) if norm(code) not in ("45", "253", "23", "94", "1", "2", "3")})
    last_denial = max([mdy(p.get("date")) for p in zero_denials if mdy(p.get("date"))] or [None], key=lambda d: d or datetime.date.min)
    first_real = min([mdy(p.get("date")) for p in real_pays if mdy(p.get("date"))] or [None], key=lambda d: d or datetime.date.max)
    primary_paid_by = sorted({p.get("carrier", "") for p in real_pays})
    pr_left = round(sum(float(amt or 0) for p in real_pays + pr_only_zero for code, amt in p.get("reasons", []) if group(code) == "PR"), 2)
    contractual = round(sum(float(amt or 0) for p in real_pays for code, amt in p.get("reasons", []) if norm(code) in ("45", "253", "144")), 2)
    wo_total = round(sum(abs(float(w.get("amount") or 0)) for c in charges for w in c.get("writeoffs", []) if w.get("void") != "1"), 2)
    days_sent = (TODAY - last_sent).days if last_sent else None
    days_dos = (TODAY - dos).days if dos else None
    secondary = bool(real_pays) and (carrier not in primary_paid_by)
    settled_primary = (bool(real_pays) and carrier in primary_paid_by) or (bool(pr_only_zero) and not real_pays and carrier in {p.get("carrier") for p in pr_only_zero})
    is_ccm = bool(set(cpts) & CCM)
    has_gv = any("GV" in m.upper() for m in mods)
    plans = chart_plans(pid)
    live_secondary = []
    if plans and dos:
        for pl in plans["plans"]:
            if pl["code"] in primary_paid_by or pl["code"] == carrier: continue
            if pl["end"] and pl["end"] < dos: continue
            if pl["begin"] and pl["begin"] > dos + datetime.timedelta(days=400): continue
            live_secondary.append(pl["code"])
    live_secondary = sorted(set(live_secondary))
    dod = DEC.get(pid)
    # --- recommendation by the standing rules ---
    why = []; rec_ = "WAIT"
    b = bucket(days_sent)
    if not charges:
        rec_, why = "REVIEW", ["chart history not in tonight's snapshot - read it before acting"]
    elif dod and dos and dos > dod:
        rec_, why = "WRITE OFF", ["date of service is AFTER the date of death on Medicare's record (%s) - void/write off, never bill" % dod.isoformat()]
    elif is_ccm and carrier == "MCAD":
        rec_, why = "WRITE OFF", ["CCM to straight Medicaid is never paid (10/13 rule) -> WONCS"]
    elif is_ccm and not real_pays and ("B9" in denial_codes or (has_gv and denial_codes and last_denial and (not last_sent or last_sent <= last_denial))):
        rec_, why = "WRITE OFF", ["CCM denied on a hospice patient (%s%s) -> WONCS, no appeal (10/15 rule: CCM denied with GV / CO-B9 is written off)" % ("GV, " if has_gv else "", ",".join(denial_codes) or "B9")]
    elif settled_primary:
        prim_age = (TODAY - first_real).days if first_real else ((TODAY - last_denial).days if last_denial else None)
        contractual_left = round(max(0.0, bal - pr_left), 2) if real_pays else 0.0
        parts = []
        if contractual_left > 0.01: parts.append("WOINS contractual $%.2f (payreasons repair: the 9/9 postings carried no adjustment)" % contractual_left)
        if live_secondary and (prim_age is None or prim_age <= 365):
            rec_ = "CORRECT & RESEND"; why = ["primary paid; cost-share $%.2f belongs to the chart's secondary %s - move it there and bill (%s)" % (min(bal, pr_left) if pr_left else bal, "/".join(live_secondary), "; ".join(parts) if parts else "no contractual left")]
        elif live_secondary:
            rec_ = "WRITE OFF"; why = ["primary paid %d days ago; secondary %s window closed -> WOCLTREQ $%.2f%s" % (prim_age, "/".join(live_secondary), min(bal, pr_left) if pr_left else bal, "; " + "; ".join(parts) if parts else "")]
        else:
            code = "WOCAID2ND" if (set(primary_paid_by) & MEDICAID_FAMILY) else "WOCLTREQ"
            rec_ = "WRITE OFF"; why = ["primary paid, no secondary on the chart -> %s cost-share $%.2f%s (10/13 rule: nothing stays on the patient)" % (code, min(bal, pr_left) if pr_left else bal, "; " + "; ".join(parts) if parts else "")]
    elif denial_codes and last_denial and (not last_sent or last_sent <= last_denial):
        if "29" in denial_codes:
            rec_, why = "WRITE OFF", ["denied CO-29 timely filing -> WOLATE unless proof of timely submission exists"]
        elif "B9" in denial_codes:
            rec_, why = ("CORRECT & RESEND" if days_dos is not None and days_dos <= 365 else "WRITE OFF"), ["hospice CO-B9 on an E/M: rebill Medicare with GV" if days_dos is not None and days_dos <= 365 else "hospice CO-B9 and DOS > 12 months -> untimely write-off"]
        elif set(denial_codes) & WRONG_PAYER:
            rec_, why = "CORRECT & RESEND", ["wrong-payer denial (%s) -> insurance cascade (AMD 271 / Stedi), re-route, never patient balance" % ",".join(sorted(set(denial_codes) & WRONG_PAYER))]
        elif "18" in denial_codes and len(denial_codes) == 1:
            rec_, why = "WAIT", ["CO-18 duplicate - the original is in play; confirm it paid, then close (no rebill)"]
        elif set(denial_codes) & {"97", "234", "B15", "236"}:
            rec_, why = "WRITE OFF", ["bundled / not paid separately (%s) -> contractual write-off" % ",".join(denial_codes)]
        elif set(denial_codes) & {"4", "16", "125", "11", "181", "MA130", "5"}:
            rec_, why = "CORRECT & RESEND", ["correctable denial (%s): fix the flagged data, rebill as an original" % ",".join(denial_codes)]
        elif set(denial_codes) & {"242", "243", "185", "B7"}:
            rec_, why = "CORRECT & RESEND", ["credentialing/enrollment denial (%s) - fix enrollment or write off" % ",".join(denial_codes)]
        elif set(denial_codes) & {"96", "50", "A1", "151", "119"}:
            rec_, why = ("WRITE OFF" if days_dos and days_dos > 365 else "CORRECT & RESEND"), ["non-covered / medical-necessity / frequency denial (%s): review the RARC; appeal or write off" % ",".join(denial_codes)]
        else:
            rec_, why = "CORRECT & RESEND", ["denied (%s) with nothing sent since - triage the CARC" % ",".join(denial_codes)]
    elif secondary:
        prim_age = (TODAY - first_real).days if first_real else None
        if prim_age is not None and prim_age > 365:
            rec_, why = "WRITE OFF", ["secondary / cost-share balance; primary remit %d days old (> 12 months) -> WOCLTREQ / WOINS" % prim_age]
        elif days_sent is None:
            rec_, why = "CORRECT & RESEND", ["secondary never sent; primary paid %s -> bill the secondary now" % (first_real.isoformat() if first_real else "?")]
        elif days_sent <= 60:
            rec_, why = "WAIT", ["secondary claim sent %d days ago" % days_sent]
        else:
            rec_, why = "CORRECT & RESEND", ["secondary unanswered %d days: check status, resend as original (verify the plan is live first)" % days_sent]
    elif days_dos is not None and days_dos > 365 and not real_pays:
        rec_, why = "WRITE OFF", ["primary claim unpaid > 12 months from DOS, no adjudication on file -> WOINS untimely (dated note)%s" % (" - backlog payer: pull the 277 / ConnectCenter first" if carrier in BACKLOG else "")]
    elif days_sent is None:
        rec_, why = "CORRECT & RESEND", ["no bill date on the charges - the claim never went out; send it"]
    elif b == "0-30":
        rec_, why = "WAIT", ["sent %d days ago - inside normal adjudication" % days_sent]
    elif b == "31-60":
        rec_, why = "WAIT", ["sent %d days ago - watch; %s" % (days_sent, "ERA-backlog payer, do not rebill" if carrier in BACKLOG else "check 277 status if still silent at 60")]
    elif b == "61-90":
        rec_, why = ("WAIT" if carrier in BACKLOG else "CORRECT & RESEND"), ["sent %d days ago, no answer: %s" % (days_sent, "backlog payer - pull the 277 before any rebill" if carrier in BACKLOG else "claim-status check; no record at the payer -> resend as original")]
    elif b == "91-120":
        rec_, why = "CORRECT & RESEND", ["sent %d days ago, no answer - verify the plan, fix and resend as original" % days_sent]
    else:
        rec_, why = "CORRECT & RESEND", ["sent %d days ago, no adjudication on file (10/13 rule) - %s" % (days_sent, "backlog payer: 277 / ConnectCenter check, then resend or write off" if carrier in BACKLOG else "verify the plan, fix and resend as original")]
    rec.update({"cpts": " ".join(cpts), "modifiers": " ".join(mods), "last_sent": last_sent.isoformat() if last_sent else "", "days_since_sent": days_sent,
                "days_since_dos": days_dos, "bucket_sent": b, "bucket_dos": bucket(days_dos), "primary_paid_by": " ".join(primary_paid_by), "primary_paid_on": first_real.isoformat() if first_real else "",
                "is_secondary_balance": secondary, "settled_primary": settled_primary, "live_secondary_on_chart": " ".join(live_secondary), "pr_cost_share": pr_left, "contractual_on_remit": contractual, "writeoffs_posted": wo_total,
                "denial_codes": " ".join(denial_codes), "last_denial": last_denial.isoformat() if last_denial else "", "deceased_dod": dod.isoformat() if dod else "",
                "recommendation": rec_, "why": "; ".join(why)})
    out.append(rec)

# ---- tables ----
def table(key):
    t = collections.OrderedDict()
    for r in out:
        k = r[key]; bb = r["bucket_sent"]
        d = t.setdefault(k, {"visits": 0, "amt": 0.0, "buckets": collections.OrderedDict((x, {"n": 0, "amt": 0.0}) for x in ("0-30", "31-60", "61-90", "91-120", "over 120", "unknown")), "recs": collections.OrderedDict((x, {"n": 0, "amt": 0.0}) for x in ("WAIT", "CORRECT & RESEND", "WRITE OFF", "REVIEW"))})
        d["visits"] += 1; d["amt"] += r["ins_balance"]
        d["buckets"][bb]["n"] += 1; d["buckets"][bb]["amt"] += r["ins_balance"]
        d["recs"][r["recommendation"]]["n"] += 1; d["recs"][r["recommendation"]]["amt"] += r["ins_balance"]
    for d in t.values():
        d["amt"] = round(d["amt"], 2)
        for x in d["buckets"].values(): x["amt"] = round(x["amt"], 2)
        for x in d["recs"].values(): x["amt"] = round(x["amt"], 2)
    return collections.OrderedDict(sorted(t.items(), key=lambda kv: -kv[1]["amt"]))

summary = {"asof": TODAY.isoformat(), "visits": len(out), "total": round(sum(r["ins_balance"] for r in out), 2), "patients": len({r["pid"] for r in out}),
           "missing_txh": missing_txh, "by_payer": table("payer_last_billed"),
           "by_bucket_sent": {b: {"n": sum(1 for r in out if r["bucket_sent"] == b), "amt": round(sum(r["ins_balance"] for r in out if r["bucket_sent"] == b), 2)} for b in ("0-30", "31-60", "61-90", "91-120", "over 120", "unknown")},
           "by_bucket_dos": {b: {"n": sum(1 for r in out if r["bucket_dos"] == b), "amt": round(sum(r["ins_balance"] for r in out if r["bucket_dos"] == b), 2)} for b in ("0-30", "31-60", "61-90", "91-120", "over 120", "unknown")},
           "by_rec": {b: {"n": sum(1 for r in out if r["recommendation"] == b), "amt": round(sum(r["ins_balance"] for r in out if r["recommendation"] == b), 2)} for b in ("WAIT", "CORRECT & RESEND", "WRITE OFF", "REVIEW")},
           "by_rec_reason": collections.OrderedDict(sorted({(r["recommendation"], r["why"].split(":")[0].split(" - ")[0][:70]): None for r in out}.keys()))}
reasons = collections.defaultdict(lambda: {"n": 0, "amt": 0.0})
for r in out:
    k = r["recommendation"] + " | " + re.sub(r"\$[\d,]+\.\d\d", "$X", re.sub(r"\d+ days", "N days", r["why"].split(";")[0]))[:110]
    reasons[k]["n"] += 1; reasons[k]["amt"] += r["ins_balance"]
summary["by_rec_reason"] = collections.OrderedDict(sorted(((k, {"n": v["n"], "amt": round(v["amt"], 2)}) for k, v in reasons.items()), key=lambda kv: -kv[1]["amt"]))
json.dump(summary, open(os.path.join(WS, "aging_1015_summary.json"), "w"), indent=1)
cols = ["pid", "visitid", "dos", "cpts", "modifiers", "fee", "ins_balance", "payer_last_billed", "last_sent", "days_since_sent", "bucket_sent", "days_since_dos", "bucket_dos", "primary_paid_by", "primary_paid_on", "is_secondary_balance", "settled_primary", "live_secondary_on_chart", "pr_cost_share", "contractual_on_remit", "writeoffs_posted", "denial_codes", "last_denial", "deceased_dod", "icn", "corrected", "recommendation", "why"]
with open(os.path.join(WS, "aging_1015_visits.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
    for r in sorted(out, key=lambda r: (r["recommendation"], -r["ins_balance"])): w.writerow(r)
print(json.dumps({k: v for k, v in summary.items() if k in ("visits", "total", "patients", "missing_txh", "by_bucket_sent", "by_bucket_dos", "by_rec")}, indent=1))
