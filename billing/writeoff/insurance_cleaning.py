# PLAIN ENGLISH (Insurances cleaning task — patient A/R split)
# Decides: Which patient balances are (1) QMB/dual -> write off, (2) never-adjudicated & untimely -> write off,
#          (3) never-adjudicated & timely -> rebill/cascade, (4) adjudicated cost-sharing on non-Medicaid patients -> NOT a write-off
#          (bill the supplement if one exists, else patient statement).
# Rules it uses: "adjudicated" = the payer set an ALLOWED amount (never "has a balance" — the 5/31/2026 WOINSBANK lesson);
#          a Medicaid patient cannot be balance-billed; primary claims >12 months unpaid = untimely; never write off a
#          UNI20/BCBS never-adjudicated balance (possible unposted ERA); write-offs post ONLY with --post and the codes given.
# Never touches: bucket 4 balances, any charge with a posted non-void payment on the insurance side, UNI20/BCBS never-adjudicated.
# ---
"""Insurances cleaning task (on demand). Usage:
  python3 insurance_cleaning.py                       # classify + workbook + summary (read-only)
  python3 insurance_cleaning.py --verify-dual         # also confirm the dual/Medicaid flag via getdemographic for every non-dual patient (paced)
  python3 insurance_cleaning.py --post --qmb-code QMB --untimely-code WOINS [--small-balance 25] [--max N]
                                                      # post write-offs for buckets 1 and 2 (+ small-balance tail) via move_to_ins + manual_post
Outputs (in /home/claude/unbilled): patbal_open_<date>.json, Patient_AR_split_<date>.xlsx, patbal_summary_<date>.json,
  Writeoff_register_<date>.xlsx (only when --post), insurance_cleaning_<date>.log.
"""
import sys, os, json, time, re, datetime, argparse
sys.path.insert(0, "/home/claude/unbilled")
import amd, requests
import xml.etree.ElementTree as ET
from collections import defaultdict

W = "/home/claude/unbilled"
STAMP = datetime.date.today().isoformat()
MEDICAID_TYPE = {"MCAD", "SUN01", "WEL04", "WEL07", "SIM01", "STA03", "FLO99", "FCC"}
MEDICARE = {"FLO02"}
BACKLOG_CARRIERS = {"UNI20", "BCBS", "BCBS1"}      # possible unposted ERA: never write off a never-adjudicated balance here
CCM = {"99487", "99489", "99490", "99491", "pcode492676", "pcode492677", "pcode492674", "pcode492675"}

LOGF = open(f"{W}/insurance_cleaning_{STAMP}.log", "a")
def L(m): print(m, flush=True); LOGF.write(m + "\n"); LOGF.flush()
def f(x):
    try: return float(x or 0)
    except: return 0.0
def age_days(d):
    try: return (datetime.date.today() - datetime.date.fromisoformat(str(d)[:10])).days
    except: return 9999

def patient_balances(years=3):
    """masswriteoffsearch isinsbalance:false = every charge carrying a PATIENT balance (captured 9/7/2026)."""
    web, tok = amd.login_cached()
    end = datetime.date.today(); start = end - datetime.timedelta(days=365 * years)
    body = {"carrierids": None, "isinsbalance": False, "billstartdate": start.isoformat(), "billenddate": end.isoformat(),
            "patientids": None, "providerids": None, "facilityids": None, "financialclassids": None,
            "dateofservicestartdate": None, "dateofserviceenddate": None}
    r = requests.post("https://pm-api-103.advancedmd.com/api/masswriteoff/masswriteoffsearch", json=body,
                      headers={"Authorization": "Bearer " + tok, "Accept": "application/json"}, timeout=180)
    r.raise_for_status()
    d = r.json(); rows = d.get("chargedetails", []) if isinstance(d, dict) else d
    json.dump(rows, open(f"{W}/patbal_open_{STAMP}.json", "w"))
    return rows

def plans(pid):
    t = amd.post('<ppmdmsg action="getdemographic" class="demographics" patientid="pat%s" nocookie="1"/>' % pid)
    out = []
    for m in re.finditer(r'<insplan ([^>]*?)/?>', t):
        a = m.group(1); g = lambda k: (re.search(k + r'="([^"]*)"', a) or [None, ''])[1]
        out.append({"id": g(r"\bid"), "carrier": g("carrier"), "seq": g("sequence"), "end": g("enddate")})
    return out

def classify(rows, verify_dual=False):
    # dual/QMB proxy: any Medicaid-type carrier on any of the patient's charges in this list (or the open-Medicaid list if present)
    dual = set()
    mo = f"{W}/medicaid_open.json"
    if os.path.exists(mo):
        try: dual |= set(str(r["patientid"]) for r in json.load(open(mo)))
        except Exception: pass
    for r in rows:
        if (r.get("carriercode") or "") in MEDICAID_TYPE: dual.add(str(r["patientid"]))
    if verify_dual:   # tighten: ask AMD for every non-dual patient's plans (paced; ~0.5 s each)
        cand = sorted(set(str(r["patientid"]) for r in rows) - dual)
        L(f"verify-dual: checking {len(cand)} patients' plans")
        car2code = {v: k for k, v in json.load(open(f"{W}/carriers.json")).items()} if os.path.exists(f"{W}/carriers.json") else {}
        for i, pid in enumerate(cand):
            try:
                for p in plans(pid):
                    if car2code.get(p["carrier"], "") in MEDICAID_TYPE or p["carrier"] in ("car6113", "car6194", "car6174", "car42019", "car41991", "car42008"):
                        dual.add(pid); break
            except Exception as e: L(f"  plans err pat{pid}: {str(e)[:60]}")
            time.sleep(0.4)
    out = []
    for r in rows:
        bal = f(r.get("patbalance")); pid = str(r["patientid"]); car = r.get("carriercode") or "?"
        adjudicated = f(r.get("allowedamount")) > 0          # a payer ALLOWED money = the correct payer acted
        touched = bool(r.get("lastpaymentdate"))
        old = age_days(r.get("dateofservice")) >= 365
        isdual = pid in dual
        if isdual and (adjudicated or touched):
            b = "1_QMB_WRITEOFF"                                  # Medicaid on file: cannot balance-bill; verify crossover billed first
        elif isdual:
            b = "1_QMB_NEVER_ADJ" if old else "3_CASCADE_TIMELY"   # dual + never adjudicated: bill Medicaid if timely, else untimely
        elif not adjudicated and not touched:
            b = ("2_UNTIMELY_WRITEOFF" if old else "3_CASCADE_TIMELY")
            if car in BACKLOG_CARRIERS: b = "2b_BACKLOG_HOLD"      # UNI20/BCBS never-adjudicated: possible unposted ERA -> never blind write-off
        elif not adjudicated and touched:
            b = "B_ZERO_DENIAL_TRANSFER"                          # $0 posting only: PR-transfer bug -> move back to insurance
        else:
            b = "4_COSTSHARE_MEDICARE" if car in MEDICARE else "4_COSTSHARE_MA_COMMERCIAL"   # NOT a write-off
        out.append(dict(r, bucket=b, dual=isdual, adjudicated=adjudicated, age_days=age_days(r.get("dateofservice"))))
    return out, dual

def workbook(cls):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook(); ws = wb.active; ws.title = "Summary"
    tot = defaultdict(lambda: [0, 0.0, set()])
    for r in cls: tot[r["bucket"]][0] += 1; tot[r["bucket"]][1] += f(r["patbalance"]); tot[r["bucket"]][2].add(r["patientid"])
    ws.append(["bucket", "charges", "patients", "patient balance", "action"])
    ACT = {"1_QMB_WRITEOFF": "write off (QMB code) after confirming Medicaid crossover was billed",
           "1_QMB_NEVER_ADJ": "untimely on a Medicaid patient -> write off (QMB/untimely)",
           "2_UNTIMELY_WRITEOFF": "primary >12mo never paid -> WOINS untimely, dated note",
           "2b_BACKLOG_HOLD": "UNI20/BCBS never-adjudicated: check for unposted ERA first, never blind write-off",
           "3_CASCADE_TIMELY": "still correctable -> rebill / insurance cascade",
           "B_ZERO_DENIAL_TRANSFER": "denial auto-transferred to patient -> move back to insurance (move_to_ins) + find real payer",
           "4_COSTSHARE_MEDICARE": "Medicare 20% coinsurance: bill supplement if on file / Stedi discovery / else patient statement — NOT a write-off",
           "4_COSTSHARE_MA_COMMERCIAL": "MA/commercial copay/coins: patient statement, small-balance policy — NOT a write-off"}
    for b in sorted(tot): ws.append([b, tot[b][0], len(tot[b][2]), round(tot[b][1], 2), ACT.get(b, "")])
    ws.append([]); ws.append(["TOTAL", len(cls), len(set(r["patientid"] for r in cls)), round(sum(f(r["patbalance"]) for r in cls), 2), ""])
    for c in ws[1]: c.font = Font(bold=True)
    det = wb.create_sheet("Charges")
    cols = ["bucket", "patientname", "patientid", "chartnumber", "dateofservice", "age_days", "chargecode", "carriercode", "totalchargeamount",
            "allowedamount", "patpayment", "patbalance", "insbalance", "lastpaymentdate", "dual", "visitid", "chargedetailid", "providerprofilecode"]
    det.append(cols)
    for c in det[1]: c.font = Font(bold=True)
    for r in sorted(cls, key=lambda x: (x["bucket"], x.get("patientname") or "", x.get("dateofservice") or "")):
        det.append([r.get(k, "") for k in cols])
    bp = wb.create_sheet("By patient")
    bp.append(["patientname", "patientid", "dual", "buckets", "charges", "patient balance"])
    agg = {}
    for r in cls:
        a = agg.setdefault(r["patientid"], {"name": r.get("patientname"), "dual": r["dual"], "b": set(), "n": 0, "bal": 0.0})
        a["b"].add(r["bucket"]); a["n"] += 1; a["bal"] += f(r["patbalance"])
    for pid, a in sorted(agg.items(), key=lambda x: -x[1]["bal"]):
        bp.append([a["name"], pid, a["dual"], ", ".join(sorted(a["b"])), a["n"], round(a["bal"], 2)])
    path = f"{W}/Patient_AR_split_{STAMP}.xlsx"; wb.save(path); return path, tot

def post_writeoffs(cls, qmb_code, untimely_code, small_balance=None, maxn=10**9):
    """Post write-offs for buckets 1 and 2 (and the small-balance tail of bucket 4 if a threshold is given).
    Path: move_to_ins.move(cid) (balance back to the insurance side, captured) -> manual_post.post(..., wocode) (captured).
    A native PATIENT-side adjustment call is NOT captured yet — if William prefers that classification, ask for the paste."""
    import move_to_ins, manual_post
    from openpyxl import Workbook
    reg = Workbook(); ws = reg.active; ws.append(["date", "patient", "carrier", "dos", "amount", "code", "note"])
    n = 0; total = 0.0
    bypat = defaultdict(float)
    for r in cls: bypat[r["patientid"]] += f(r["patbalance"])
    for r in cls:
        if n >= maxn: break
        b = r["bucket"]; bal = f(r["patbalance"]); cid = str(r["chargedetailid"])
        if bal <= 0.005: continue
        if b in ("1_QMB_WRITEOFF", "1_QMB_NEVER_ADJ"): code, note = qmb_code, "QMB/dual — Medicaid on file, not balance-billable (insurances cleaning %s)" % STAMP
        elif b == "2_UNTIMELY_WRITEOFF": code, note = untimely_code, "primary >12 months from DOS, never paid — untimely (insurances cleaning %s)" % STAMP
        elif small_balance and b.startswith("4_") and bypat[r["patientid"]] < small_balance:
            code, note = untimely_code, "small-balance policy < $%s (insurances cleaning %s)" % (small_balance, STAMP)
        else: continue
        try:
            move_to_ins.move(cid)                                   # patient -> insurance side (captured 9/3)
            time.sleep(0.4)
            ok, msg = manual_post.post(cid, r.get("carriercode") or "", 0.0, bal, code, note=note)
            if ok: n += 1; total += bal; ws.append([STAMP, r.get("patientname"), r.get("carriercode"), r.get("dateofservice"), bal, code, note]); L(f"WO {b} {r.get('patientname')} {r.get('dateofservice')} ${bal:.2f} {code}")
            else: L(f"WO FAIL c{cid}: {str(msg)[:100]}")
        except Exception as e:
            L(f"WO EXC c{cid}: {str(e)[:100]}")
        time.sleep(0.5)
    reg.save(f"{W}/Writeoff_register_{STAMP}.xlsx")
    L(f"=== write-offs posted: {n} charges ${total:,.2f} -> Writeoff_register_{STAMP}.xlsx ===")
    return n, total

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify-dual", action="store_true"); ap.add_argument("--post", action="store_true")
    ap.add_argument("--qmb-code"); ap.add_argument("--untimely-code"); ap.add_argument("--small-balance", type=float)
    ap.add_argument("--max", type=int, default=10**9)
    a = ap.parse_args()
    amd.login_cached()
    rows = patient_balances()
    L(f"patient-balance charges: {len(rows)}  ${sum(f(r['patbalance']) for r in rows):,.2f}  patients {len(set(r['patientid'] for r in rows))}")
    cls, dual = classify(rows, verify_dual=a.verify_dual)
    path, tot = workbook(cls)
    json.dump({b: {"charges": v[0], "patients": len(v[2]), "balance": round(v[1], 2)} for b, v in tot.items()}, open(f"{W}/patbal_summary_{STAMP}.json", "w"), indent=1)
    for b in sorted(tot): L(f"  {b:28} {tot[b][0]:5} chg  {len(tot[b][2]):4} pts  ${tot[b][1]:>11,.2f}")
    L(f"workbook: {path}")
    if a.post:
        if not (a.qmb_code and a.untimely_code): sys.exit("--post needs --qmb-code and --untimely-code")
        post_writeoffs(cls, a.qmb_code, a.untimely_code, a.small_balance, a.max)
