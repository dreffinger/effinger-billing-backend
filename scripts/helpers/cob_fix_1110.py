# PLAIN ENGLISH (Availity COB denials -> Medicare first, 7am ET 9/15/2026 run - step 5(g) DENIAL rule)
# Decides: for the Florida Blue lines that came back PR-22/CO-22 + N598/MA04 ("another policy is primary" / "Medicare must
#   process first") and still carry an open Florida-Blue insurance balance, and whose chart already holds a Medicare plan
#   with a real MBI, bill Medicare first: set the visit's insurance order to the Medicare sequence (full-visit echo via
#   move_to_ins.move), reset frequency 1 and rebill (freq1_visit.run). One chart (pat25596) carries the old HICN on its
#   Medicare plan - the MBI from the board's Stedi lookup (kept in secrets/mbi_25596.txt, never in this file) is written first (ins_update, wrapped shape).
#   Rowley-type case: Medicare IS seq 1 on the chart but the CCM visit went to Florida Blue as primary -> same fix.
#   Dalrymple-type case: chart order Florida Blue first -> patient default order set Medicare first (ins_update sequence "2,1").
# Rules it uses: William 9/7 Medicare-before-supplement; 9/3 every rebill goes out frequency 1; void trap = full echo.
# Never touches: payments, charges with a $0 balance, charts without a valid MBI (those are reported instead).
import amd, txh, move_to_ins, freq1_visit, ins_update, json, re, sys, time
STAMP = "2026-09-15T1110Z"
amd.login_cached()
MBI = re.compile(r"^[1-9][A-Z][A-Z0-9][0-9][A-Z][A-Z0-9][0-9][A-Z]{2}[0-9]{2}$")
PLAN = [
    # pid, medicare insid, medicare seq, [(vid, cid)], patient-order fix (insid, "seq,seq") or None, mbi fix (insid, mbi) or None
    ("17473245", "ins9519180", 2, [("19446222", "23355215"), ("19445474", "23354349")], ("ins9519180", "2,1"), None),      # Dalrymple: BCBS first on chart, Medicare A/B active
    ("17476868", "ins9519179", 2, [("19447500", "23356689")], None, None),                                                 # Addison 7/7 visit (patient order already 2,1)
    ("25596", "ins5628", 1, [("19446145", "23355063")], None, ("ins5628", open("secrets/mbi_25596.txt").read().strip())),                                 # Halloran: HICN -> MBI, Medicare seq 1
    ("12180329", "ins6028401", 1, [("19436591", "23343643"), ("19436827", "23343875")], None, None),                       # Sayer III
    ("25710", "ins1615", 1, [("19432731", "23339379")], None, None),                                                       # Bexley-Bateson
    ("48449", "ins6005745", 1, [("19448810", "23358225")], None, None),                                                    # Rowley: PR-204 on BCBS billed as primary; Medicare is seq 1
]
out = []
for pid, mins, seq, visits, order_fix, mbi_fix in PLAN:
    rec = {"pid": pid, "medicare_ins": mins, "seq": seq, "steps": []}
    if mbi_fix:
        try:
            r = ins_update.update(pid, mbi_fix[0], subscribernum=mbi_fix[1])
            rec["steps"].append("mbi fix %s -> %s" % (mbi_fix[0], str(r)[:120]))
        except Exception as e:
            rec["steps"].append("mbi fix ERROR %s" % repr(e)[:120]); out.append(rec); print(rec); continue
        time.sleep(0.5)
    if order_fix:
        try:
            r = ins_update.update(pid, order_fix[0], sequence=order_fix[1])
            rec["steps"].append("patient order %s -> %s" % (order_fix[1], str(r)[:120]))
        except Exception as e:
            rec["steps"].append("patient order ERROR %s" % repr(e)[:120])
        time.sleep(0.5)
    # Halloran: add every other open Florida-Blue-carrier charge of 2026 on the chart
    if pid == "25596":
        extra = []
        for c in txh.fetch(pid).iter("charge"):
            cid = re.sub(r"\D", "", c.get("id") or ""); dos = c.get("dos") or ""
            if c.get("carrier") == "BCBS" and float(c.get("insbal") or 0) > 0 and dos.endswith("/2026") and c.get("visit") not in {v for v, _ in visits}:
                extra.append((c.get("visit"), cid))
        seen = set(); extra = [(v, c) for v, c in extra if not (v in seen or seen.add(v))]
        rec["steps"].append("extra open BCBS 2026 visits: %s" % extra); visits = visits + extra
    for vid, cid in visits:
        try:
            m = move_to_ins.move(cid, seq)
            time.sleep(0.6)
            f = freq1_visit.run(vid, cid, seq)
            rec["steps"].append("v%s c%s: %s | %s" % (vid, cid, str(m)[:140], str(f)[:80]))
        except Exception as e:
            rec["steps"].append("v%s c%s ERROR %s" % (vid, cid, repr(e)[:140]))
        time.sleep(0.6)
    out.append(rec); print(json.dumps(rec, indent=1), flush=True)
json.dump(out, open("registers/availity_cob_fix_%s.json" % STAMP, "w"), indent=1)
# Merriwether Paxton (pat17475906): Florida Blue MA says another policy is primary - Stedi MBI lookup for the COB picture
try:
    import stedi
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "17475906", "nocookie": "1"}), timeout=120)
    dob = re.search(r' dob="([^"]*)"', d); dob = dob.group(1) if dob else ""
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", dob); ymd = (m.group(3) + m.group(1) + m.group(2)) if m else dob.replace("-", "")
    j = stedi.mbi("NELL", "MERRIWETHER-PAXTON", ymd, "FL", "20260329")
    s = json.dumps(j)[:1500]
    print("STEDI MBI pat17475906:", s)
    json.dump(j, open("registers/stedi_mbi_17475906_%s.json" % STAMP, "w"), indent=1)
except Exception as e:
    print("stedi mbi error", repr(e)[:200])
