"""MODE C — supplement pass for bucket 4_COSTSHARE_MEDICARE (Medicare paid, 20% sitting on the patient).
Step 1 (free): patient's plans on file. A non-Medicare, non-Medicaid plan without an end date = supplement ON FILE -> bill it.
Step 2 (Stedi discovery, ~$1.50): only patients with NO secondary on file.
Step 3: classify hits: MEDIGAP/commercial secondary -> add plan + bill; MEDICAID -> dual (QMB path); MA plan -> flag (primary may be wrong); nothing -> self-pay bucket.
Writes supplement_pass_<date>.jsonl (resumable) + summary. --post adds plans / moves balances / rebills for CLEAN Medigap hits only."""
import sys, json, os, time, re, datetime, argparse
sys.path.insert(0, "/home/claude/effinger-billing-backend/core"); sys.path.insert(0, "/home/claude/unbilled")
import amd, stedi, requests
# hard per-call timeouts: a wedged call must not stall the pass
_orig_post = stedi._post
def _fast_post(url, body):
    r = requests.post(url, headers=stedi.H, json=body, timeout=150); r.raise_for_status(); return r.json()
stedi._post = _fast_post
S = json.load(open("/home/claude/unbilled/.session.json")); _WEB = S["web"]; _TOK = S["token"]
_sess = requests.Session()
def _mt(): return datetime.datetime.now().strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")
def _demog(pid):
    body = '<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"><usercontext>%s</usercontext></ppmdmsg>' % (_mt(), pid, _TOK)
    return _sess.post(_WEB + "/xmlrpc/processrequest.aspx", data=body, headers={"Content-Type": "text/xml"}, cookies={"token": _TOK}, timeout=25).text
from collections import defaultdict
STAMP = datetime.date.today().isoformat(); W = "/home/claude/unbilled"
CAR = json.load(open(f"{W}/carriers.json")); CAR2CODE = {v: k for k, v in CAR.items()}
MEDICAID_CARS = {"car6113", "car6194", "car6174", "car42019", "car41991", "car41992", "car42008"}
MEDICARE_CAR = "car6085"
OUT = f"{W}/supplement_pass_{STAMP}.jsonl"
done = set()
if os.path.exists(OUT):
    for ln in open(OUT):
        try: done.add(json.loads(ln)["pid"])
        except: pass
f = open(OUT, "a")
def plans(pid):
    t = _demog(pid)
    out = []
    for m in re.finditer(r'<insplan ([^>]*?)/?>', t):
        a = m.group(1); g = lambda k: (re.search(k + r'="([^"]*)"', a) or [None, ''])[1]
        out.append({"id": g(r"\bid"), "carrier": g("carrier"), "seq": g("sequence"), "end": g("enddate"), "num": g("subscribernum")})
    dob = (re.search(r'\bdob="([^"]*)"', t) or [None, ''])[1]; nm = (re.search(r'\bname="([^"]*)"', t) or [None, ''])[1]
    return out, dob, nm
def dob8(d):
    m = re.match(r'(\d\d)/(\d\d)/(\d{4})', d or ''); return (m.group(3) + m.group(1) + m.group(2)) if m else ''
# candidate patients: bucket 4_COSTSHARE_MEDICARE from today's Patient A/R split
from openpyxl import load_workbook
wb = load_workbook(f"{W}/Patient_AR_split_{STAMP}.xlsx", read_only=True); ws = wb["Charges"]
hdr = None; cands = defaultdict(lambda: {"bal": 0.0, "charges": []})
for row in ws.iter_rows(values_only=True):
    if hdr is None: hdr = list(row); continue
    r = dict(zip(hdr, row))
    if r.get("bucket") != "4_COSTSHARE_MEDICARE": continue
    pid = str(r["patientid"]); cands[pid]["bal"] += float(r.get("patbalance") or 0); cands[pid]["name"] = r.get("patientname")
    cands[pid]["charges"].append({"cid": str(r["chargedetailid"]), "vid": str(r["visitid"]), "dos": str(r.get("dateofservice"))[:10], "bal": float(r.get("patbalance") or 0)})
maxn = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
print(f"candidates: {len(cands)} patients, ${sum(c['bal'] for c in cands.values()):,.2f}", flush=True)
n = 0; stats = defaultdict(int); cost = 0.0
for pid, c in sorted(cands.items(), key=lambda x: -x[1]["bal"]):
    if pid in done or n >= maxn: continue
    n += 1
    rec = {"pid": pid, "name": c["name"], "bal": round(c["bal"], 2), "n_charges": len(c["charges"])}
    try:
        pl, dob, nm = plans(pid)
    except Exception as e:
        rec["result"] = "PLANS_ERR"; rec["err"] = str(e)[:80]; f.write(json.dumps(rec) + "\n"); f.flush(); continue
    active = [p for p in pl if not p["end"]]
    sec = [p for p in active if p["carrier"] != MEDICARE_CAR and p["carrier"] not in MEDICAID_CARS]
    medicaid = [p for p in active if p["carrier"] in MEDICAID_CARS]
    rec["plans"] = [(CAR2CODE.get(p["carrier"], p["carrier"]), p["seq"], "end" if p["end"] else "active") for p in pl]
    if medicaid:
        rec["result"] = "DUAL_ON_FILE"; stats["dual_on_file"] += 1          # the dual flag missed it -> QMB path, not statements
    elif sec:
        rec["result"] = "SUPPLEMENT_ON_FILE"; rec["supplement"] = (CAR2CODE.get(sec[0]["carrier"], sec[0]["carrier"]), sec[0]["seq"]); stats["supplement_on_file"] += 1
    else:
        # Stedi discovery
        first, last = (nm.split(",") + [""])[1].strip().split(" ")[0] if "," in nm else "", nm.split(",")[0].strip()
        dos = max(x["dos"] for x in c["charges"])
        try:
            j = stedi.disc(first, last, dob8(dob), state="FL", dos=dos.replace("-", ""))
            s = stedi.disc_summ(j); cost += 1.50
            rec["discovery"] = s
            hits = [it for it in (s.get("items") or []) if it.get("payer")]
            names = " | ".join((it.get("payer") or "").upper() for it in hits)
            dod = next((((it.get("dates") or {}).get("dateOfDeath")) for it in hits if (it.get("dates") or {}).get("dateOfDeath")), None)
            if dod: rec["dateOfDeath"] = dod
            nonmedicare = [it for it in hits if not any(k in (it.get("payer") or "").upper() for k in ("CMS", "MEDICARE")) or any(k in (it.get("payer") or "").upper() for k in ("SUPPLEMENT", "MEDIGAP", "ADVANTAGE"))]
            names = " | ".join((it.get("payer") or "").upper() for it in nonmedicare)
            if not hits: rec["result"] = "NONE_FOUND"; stats["none_found"] += 1
            elif not nonmedicare: rec["result"] = "DISC_MEDICARE_ONLY" + ("_DECEASED" if dod else ""); stats[rec["result"].lower()] += 1   # CMS echoed back = no supplement
            elif any(k in names for k in ("MEDICAID", "SUNSHINE", "SIMPLY", "WELLCARE", "STAYWELL", "COMMUNITY CARE")): rec["result"] = "DISC_MEDICAID"; stats["disc_medicaid"] += 1
            elif any(k in names for k in ("ADVANTAGE", "DUAL COMPLETE", "HUMANA", "CAPITAL HEALTH", "UNITEDHEALTHCARE", "AETNA MEDICARE")) and not any(k in names for k in ("SUPPLEMENT", "MEDIGAP")):
                rec["result"] = "DISC_MA_PLAN"; stats["disc_ma_plan"] += 1                     # primary may be wrong -> flag, do not bill as secondary
            else: rec["result"] = "DISC_SUPPLEMENT"; stats["disc_supplement"] += 1
        except Exception as e:
            rec["result"] = "DISC_ERR"; rec["err"] = str(e)[:100]; stats["disc_err"] += 1
        time.sleep(0.5)
    f.write(json.dumps(rec) + "\n"); f.flush()
    if n % 25 == 0: print(f"  {n} patients  stats={dict(stats)}  stedi≈${cost:.2f}", flush=True)
    time.sleep(0.25)
print(f"DONE {n} patients  stats={dict(stats)}  stedi≈${cost:.2f}", flush=True)
json.dump({"stats": dict(stats), "stedi_cost": cost, "patients": n}, open(f"{W}/supplement_pass_summary_{STAMP}.json", "w"))
