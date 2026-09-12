# 9/11 3pm ET - work the exclusions: duplicates complete, admit dates + freq1, ICN freq1, untimely write-offs
# 7pm ET fix: manual_post.CAR now built from the RICH carriers.json (carN -> [code,name]) - the workspace
# carriers.json is the rich practices/ehpa map; the old line assumed the simple {code: carN} format.
import amd, resave, freq1_visit, manual_post, txh, json, re, time, datetime, collections
import xml.etree.ElementTree as ET
amd.login_cached()
manual_post.CAR = {v[0]: k for k, v in json.load(open("carriers.json")).items()}  # code -> carN (rich carriers.json)
LOG = open("excl_work_0911.log", "a")
def L(m): print(m, flush=True); LOG.write(str(m)+"\n"); LOG.flush()
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
TODAY = datetime.date(2026, 9, 11)
RECENT = TODAY - datetime.timedelta(days=365)

allrows = json.load(open("excl_rows_0911.json"))
def cls(row):
    txt = " | ".join((e.get("name") or "") for e in row["_errs"]).upper()
    for tag, pat in [("duplicate","UDCP"),("duplicate","DUPLICATE OF"),("cpid","PREF0288"),("admitdate","PDTP030"),("icn-freq","PREF0283"),("icn-freq","PREF0264"),("mbr","MBR NOT VALID"),("npi","NPI MUST BE REGISTERED"),("multi-auth","NPV087"),("pick","MEMBER PICK")]:
        if pat in txt: return tag
    return "other"

complete_by_run = collections.defaultdict(list)   # rid -> [(vid, claimid)]
stats = collections.Counter(); wo_register = []; resent = []

HIST = {}
def history_root(pid):
    if pid not in HIST: HIST[pid] = txh.fetch(str(pid))
    return HIST[pid]

def open_charges(pid, vid):
    out = []
    for c in history_root(pid).iter("charge"):
        if c.get("void") != "1" and str(c.get("visit")) == str(vid):
            out.append(c)
    return out

def recent_payment(chs):
    for c in chs:
        for p in c.iter("payment"):
            if p.get("void") != "1" and float(p.get("amount") or 0) != 0:
                try:
                    if d(p.get("date")) >= RECENT: return d(p.get("date"))
                except Exception: pass
    return None

def anchor_99223(pid, dos):
    hs = [(d(c.get("dos")), c.get("proccode")) for c in history_root(pid).iter("charge") if c.get("void") != "1" and c.get("dos")]
    adm = [x for x, p in hs if p == "99223" and x <= dos and (dos - x).days <= 45]
    return max(adm) if adm else None

def set_date(vid, code, admit):
    ext = '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)
    return amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid": "vst"+str(vid), "nocookie":"1"}, ext))

for rid, rows in allrows.items():
    for row in rows:
        k = cls(row); vid = row["id"]; cid0 = row["_chgs"][0]["id"] if row["_chgs"] else None
        name = row["patientname"]; pid = row["patientid"]; car = (row.get("carriercode") or "").split()[0]
        try:
            if k == "duplicate":
                complete_by_run[rid].append((vid, row["claimid"])); stats["duplicate-completed"] += 1
            elif k == "admitdate":
                vis, pat, allc = resave.visit_charges(cid0)
                dos = d(allc[0].get("begindate"))
                codes = sorted({c.get("proccode") for c in allc})
                adm = dos if "99223" in codes else anchor_99223(pid, dos)
                if adm is None:
                    L("HOLD admit %s %s %s: no 99223 anchor" % (name, vid, dos)); stats["hold"] += 1; continue
                for code in codes: set_date(vid, code, adm.strftime("%m/%d/%Y"))
                seq = (vis.get("insorder") or "1")[:1] or "1"
                res = freq1_visit.run("vst"+str(vid), cid0, seq)
                ok = "204" in res
                L("ADMIT %s %s dos %s adm %s %s" % (name, vid, dos, adm, res))
                if ok: complete_by_run[rid].append((vid, row["claimid"])); stats["admit-resent"] += 1; resent.append((name, str(dos), car, sum(float(c.get("totalfee") or 0) for c in row["_chgs"])))
            elif k == "icn-freq":
                vis, pat, allc = resave.visit_charges(cid0)
                seq = (vis.get("insorder") or "1")[:1] or "1"
                res = freq1_visit.run("vst"+str(vid), cid0, seq)
                ok = "204" in res
                L("ICN %s %s %s" % (name, vid, res))
                if ok: complete_by_run[rid].append((vid, row["claimid"])); stats["icn-resent"] += 1; resent.append((name, row["_chgs"][0].get("dos","")[:10], car, sum(float(c.get("totalfee") or 0) for c in row["_chgs"])))
            elif k in ("mbr", "pick", "other"):
                dos = d(row["_chgs"][0].get("dos"))
                if (TODAY - dos).days <= 365:
                    L("HOLD recent %s %s %s %s dos %s" % (k, name, vid, car, dos)); stats["hold-recent"] += 1; continue
                chs = open_charges(pid, vid)
                rp = recent_payment(chs)
                if rp:
                    L("KEEP %s %s: primary paid %s, secondary timely" % (name, vid, rp)); stats["keep-secondary"] += 1; continue
                wrote = 0.0; allok = True
                for c in chs:
                    bal = float(c.get("insbal") or 0)
                    if bal <= 0: continue
                    ok, msg = manual_post.post(c.get("id"), car, 0.0, bal, "WOINS",
                        note="untimely - over 12 months, rejected at clearinghouse/payer, past filing limits (standing rule 9/7)")
                    L("%s WO %s %s %s $%.2f %s" % ("OK" if ok else "FAIL", name, c.get("id"), c.get("dos"), bal, "" if ok else msg[:100]))
                    if ok: wrote += bal
                    else: allok = False
                    time.sleep(0.25)
                if wrote > 0: wo_register.append((name, car, row["_chgs"][0].get("dos","")[:10], wrote))
                if allok:
                    complete_by_run[rid].append((vid, row["claimid"])); stats["untimely-wo-completed"] += 1
            else:
                stats["hold-" + k] += 1
        except Exception as e:
            L("ERR %s %s %s: %s" % (k, name, vid, str(e)[:150])); stats["err"] += 1
        time.sleep(0.1)

# complete (hideexclusions) per run
for rid, pairs in complete_by_run.items():
    for i in range(0, len(pairs), 25):
        chunk = pairs[i:i+25]
        r = amd.post(amd.msg("hideexclusions","claimsreports",{"claimrunid":rid,"hide":"-1","nocookie":"1"},
            "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in chunk)))
        L("hide run %s n=%d %s" % (rid, len(chunk), "fault" if "Fault" in r else "ok"))
        time.sleep(0.4)

L("stats: %s" % dict(stats))
json.dump(wo_register, open("wo_register_0911.json","w"), indent=1)
json.dump(resent, open("resent_0911.json","w"), indent=1)
L("wo total: $%.2f over %d visits" % (sum(w[3] for w in wo_register), len(wo_register)))
L("resent total: $%.2f over %d visits" % (sum(r[3] for r in resent), len(resent)))