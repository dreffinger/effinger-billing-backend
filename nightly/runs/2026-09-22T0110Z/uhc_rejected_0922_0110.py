# PLAIN ENGLISH (UHC portal 'rejected claims' exports, 9pm ET 9/21 slot - run 2026-09-22T0110Z)
# William dropped six rejected_claims*.csv exports (UnitedHealthcare provider portal: claim number, member id,
#   patient account number = AMD visit id + claim letter, submission date, 'Action Required' with a 90-day expiry)
#   into Drive 'bht Optum era downloads' at 00:00-00:05Z 9/22. The export carries NO rejection reason.
# Decides, per claim: (1) find the AMD visit (account number minus the claim letter) on the unpaid list
#   (massrebillsearch {} = every visit with an open insurance balance, by last-billed carrier); (2) not on it -> the
#   visit carries no open insurance balance in AMD (paid / adjusted / written off / patient balance) = 'closed in AMD';
#   (3) on it -> read the chart's tx history (gettxhistory) for the visit's charges: any UHC payment ever, bill date,
#   balances; classify: 'open-pre-0501-2026' (William's standing rule: NEVER rebill UNI20/BCBS visits older than
#   5/1/2026 - unposted-ERA backlog), 'open-2026' (needs the portal's rejection reason before any correction),
#   'open-other-carrier' (the visit's open balance is with a different carrier now).
# Never touches: AMD writes, rebills, payments, write-offs. Output: registers/uhc_rejected_<stamp>.json (visit ids
#   only, no names / member ids / claim numbers) and a PHI report CSV for William (SendUserFile only).
import amd, era_post, txh, requests, json, csv, re, time, sys, collections, datetime
STAMP = "2026-09-22T0110Z"
rows = json.load(open("inbox/rejected/all_rejected_rows.json"))
amd.login_cached()
unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=180).json()
print("unpaid list:", len(unp), "visits", flush=True)
byvisit = collections.defaultdict(list)
for v in unp: byvisit[str(v["visitid"])].append(v)
def d(s):
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.datetime.strptime(s.strip()[:10], fmt).date()
        except Exception: pass
    return None
hist = {}
def history(pid):
    if pid in hist: return hist[pid]
    root = txh.fetch(pid); out = {}
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        vid = str(a.get("visitid") or a.get("visit") or "").replace("vst", "")
        pays = [p.attrib for p in c.iter("payment") if p.attrib.get("void") != "1"]
        wos = [w.attrib for w in c.iter("writeoff") if w.attrib.get("void") != "1"]
        out.setdefault(vid, []).append({"cid": a.get("id"), "dos": a.get("dos") or a.get("dateofservice"), "cpt": a.get("proccode"),
            "carrier": a.get("carrier") or a.get("carriercode"), "fee": a.get("amount") or a.get("fee"), "insbal": a.get("insbalance"),
            "patbal": a.get("patbalance"), "billdate": a.get("billdate") or a.get("datebilled"), "insbilled": a.get("insbilled"),
            "pays": [(p.get("carrier") or p.get("carriercode") or p.get("carrierfid"), p.get("amount"), p.get("date"), p.get("checknumber")) for p in pays],
            "wos": [(w.get("code") or w.get("writeoffcode"), w.get("amount"), w.get("date")) for w in wos]})
    hist[pid] = out; time.sleep(0.3); return out
CUT = datetime.date(2026, 5, 1)
out = []; n = 0
for r in rows:
    acct = r["Patient account number"]; vid = re.sub(r"[A-Z]$", "", acct); letter = acct[-1]
    dos = d(r["First service date"]); rec = {"visitid": vid, "letter": letter, "dos": r["First service date"], "submitted": r["Claim submission date"],
        "expires": r["Action expiration date"], "claim": r["Claim number"], "member": r["Member ID"], "name": "%s,%s" % (r["Last name"], r["First name"])}
    hits = byvisit.get(vid)
    if not hits:
        rec.update({"pid": "", "class": "closed-in-amd", "carrier": "", "insbal": 0.0, "detail": "visit not on the unpaid list - no open insurance balance in AMD"})
    else:
        h = hits[0]; pid = str(h["patientid"]); car = (h.get("carriercode") or "").strip(); bal = float(h.get("insbalance") or 0)
        rec.update({"pid": pid, "carrier": car, "insbal": bal, "icn": h.get("icn") or ""})
        try:
            chg = history(pid).get(vid, [])
        except Exception as e:
            chg = []; rec["detail"] = "txh error %s" % str(e)[:80]
        uhcpay = [p for c in chg for p in c["pays"] if p[1] and not str(p[1]).startswith("-") and float(p[1] or 0) > 0]
        rec["charges"] = [(c["cpt"], c["fee"], c["insbal"], c["patbal"], c["billdate"], c["carrier"]) for c in chg]
        rec["payments"] = [p for c in chg for p in c["pays"]]
        rec["writeoffs"] = [w for c in chg for w in c["wos"]]
        if car != "UNI20": rec["class"] = "open-other-carrier"; rec["detail"] = "open balance now sits with %s, not UHC" % car
        elif uhcpay: rec["class"] = "open-partly-paid"; rec["detail"] = "a payment already sits on the visit (%s) - the re-sent claim duplicated an adjudicated one" % uhcpay[0][3]
        elif dos and dos < CUT: rec["class"] = "open-pre-0501-2026"; rec["detail"] = "UNI20 visit older than 5/1/2026 - William's standing rule: never rebill (unposted-ERA backlog)"
        else: rec["class"] = "open-2026"; rec["detail"] = "open UHC balance, no payment - needs the portal's rejection reason before any correction"
    out.append(rec); n += 1
    if n % 50 == 0: print(n, "done", flush=True)
cls = collections.Counter(x["class"] for x in out)
print("CLASSES:", dict(cls))
for k in cls:
    print(k, "visits", sum(1 for x in out if x["class"] == k), "$%.2f" % sum(x["insbal"] for x in out if x["class"] == k))
print("patients with open UHC balance:", len({x["pid"] for x in out if x["class"].startswith("open") and x["carrier"] == "UNI20"}))
print("by DOS month (open-pre-0501):", collections.Counter(x["dos"][6:] + "-" + x["dos"][:2] for x in out if x["class"] == "open-pre-0501-2026").most_common(20))
print("expiry dates:", collections.Counter(x["expires"] for x in out))
# PHI-free register
reg = [{k: v for k, v in x.items() if k not in ("name", "member", "claim", "icn")} for x in out]
json.dump({"stamp": STAMP, "source": "UHC portal rejected_claims*.csv x6 (Drive bht Optum era downloads, 9/22 00:00-00:05Z)", "n": len(out), "classes": dict(cls), "rows": reg},
          open("registers/uhc_rejected_%s.json" % STAMP, "w"), indent=1)
with open("uhc_rejected_claims_%s.csv" % STAMP, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["patient", "amd_patient", "visit", "claim_letter", "dos", "uhc_claim", "member_id", "submitted", "action_expires", "class", "carrier_now", "open_ins_balance", "charges (cpt,fee,insbal,patbal,billdate,carrier)", "payments", "writeoffs", "detail"])
    for x in sorted(out, key=lambda x: (x["class"], x["name"], x["dos"])):
        w.writerow([x["name"], x.get("pid", ""), x["visitid"], x["letter"], x["dos"], x["claim"], x["member"], x["submitted"], x["expires"], x["class"], x.get("carrier", ""), "%.2f" % x["insbal"], json.dumps(x.get("charges", [])), json.dumps(x.get("payments", [])), json.dumps(x.get("writeoffs", [])), x.get("detail", "")])
print("written registers/uhc_rejected_%s.json and uhc_rejected_claims_%s.csv" % (STAMP, STAMP))
