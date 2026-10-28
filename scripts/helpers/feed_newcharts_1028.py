# PLAIN ENGLISH (Claimocity backlog import 10/28/2026 - new charts for feed patients with no AMD chart).
# Creates the chart from the DFT PID segment (name, DOB, sex, address, phone; Claimocity id kept as additionalmrn like the
# integration does), chart number F1028-NN (its own series so Gregg's numeric series cannot collide), address line 2 = line 1
# (the 9/14 rule for feed charts), then adds the feed's IN1 payers that map to an AMD carrier (member id from IN1-36) so the
# cascade check has something to verify. Writes registers/feed_newcharts_1028.json and updates feed_match_1028.json (resolved).
# Proven 10/28/2026 on pat17478199 (chart F1028-01). Never touches existing charts.
import amd, add_ins, re, json, glob, time, collections
amd.login_cached()
MATCH = json.load(open("feed_match_1028.json"))
CARRIERS = json.load(open("carriers_rich.json")); CODE2CAR = {v[0]: k for k, v in CARRIERS.items()}
PAYER_MAP = [
    (r"MEDICARE A\b|FCSO|MEDICARE PART A|MEDICARE B\b|TRADITIONAL MEDICARE|^MEDICARE$|^MCA-|^MCB", "FLO02"),
    (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"WELLCARE", "WEL04"), (r"HUMANA", "HUM01"),
    (r"CAPITAL HEALTH", "CAP07"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY CARE|FCC\b", "FLO99"),
    (r"UNITED ?HEALTH|UHC|AARP MEDICARE ADV", "UNI20"), (r"AARP", "AAR01"), (r"AETNA", "AET07"),
    (r"CIGNA", "CIG09"), (r"FLORIDA BLUE|BCBS|BLUE CROSS|BC/BS", "BCBS"), (r"TRICARE FOR LIFE|TFL", "TRI05"),
    (r"TRICARE", "TRI00"), (r"CHAMPVA", "CHA03"), (r"VA COMMUNITY|VACCN|VETERAN", "VACCN"),
    (r"MEDICAID(?! MANAGED)|AHCA|FLORIDA MEDICAID|^MCD|-MCD\b|^MCD-", "MCAD"), (r"MOLINA", "MOL01"),
]
SKIP_IN1 = r"LIABILITY|SELF PAY|PRIVATE PAY|PENDING|COINS|CO-INS|THERAPY|VACCINE|LAB\b|PART D|PDP|PRESCRIPTION|HOSPICE"
PID = {}; IN1 = collections.defaultdict(list)
for f in glob.glob("/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct/*.hl7"):
    raw = open(f, errors="replace").read().replace("\r", "\n"); cur = None
    for line in raw.split("\n"):
        s = line.split("|")
        if s[0] == "PID": cur = s[3]; PID.setdefault(cur, s)
        elif s[0] == "IN1" and cur:
            payer = s[4].split("^")[0] if len(s) > 4 else ""; member = s[36] if len(s) > 36 else ""
            if payer and (payer, member) not in IN1[cur]: IN1[cur].append((payer, member))
REGF = "registers/feed_newcharts_1028.json"
import os
reg = json.load(open(REGF)) if os.path.exists(REGF) else {"created": [], "failed": []}
n = len(reg["created"]) + 1
for k, v in MATCH.items():
    if v["status"] != "MISSING" or v.get("resolved"): continue
    name, dob = k.split("|"); last, _, first = name.partition(","); last = last.strip(); first = first.strip()
    seg = PID.get(v["feed_ids"][0])
    if not seg: reg["failed"].append({"key": k[:6], "why": "no PID segment"}); continue
    sex = seg[8] or "U"; addr = (seg[11] or "^^^^^").split("^"); phone = re.sub(r"\D", "", seg[14] or "")[-10:]
    mdy = "%s/%s/%s" % (dob[4:6], dob[6:8], dob[:4]); chart = "F1028-%02d" % (n + 1)
    street = addr[0] or "HCA"; city = addr[2] or "TALLAHASSEE"; st = addr[3] or "FL"; zipc = (addr[4] or "32308-4486")[:10]
    xml = ('<patient id="" name="%s,%s" dob="%s" sex="%s" chart="%s" profile="prof13" finclasscode="CC" relationship="1" hipaarelationship="18" '
           'additionalmrn="%s" respparty=""><address zip="%s" city="%s" state="%s" address1="%s" address2="%s" areacode="%s" countrycode="USA"/>'
           '<contactinfo homephone="%s"/></patient>') % (last, first, mdy, sex, chart, v["feed_ids"][0].upper()[:24], zipc, city, st, street, street, phone[:3], phone)
    r = amd.post(amd.msg("addpatient", "demographics", {"nocookie": "1"}, xml), timeout=90)
    m = re.search(r'<patient id="(pat\d+)"', r)
    if not m or 'success="1"' not in r:
        d = re.search(r"<description>(.*?)</description>", r, re.S)
        reg["failed"].append({"key": k[:6], "chart": chart, "err": (d.group(1) if d else r[:200])[:200]}); print("FAIL", last[:5] + "*", (d.group(1) if d else r[:120])[:120]); continue
    pid = m.group(1); n += 1
    rec = {"pid": pid, "chart": chart, "feed_ids": v["feed_ids"], "plans": []}
    # insurance from IN1 (every message of this patient), first mappable payers, no group numbers (William's rule)
    seen = set()
    for fid in v["feed_ids"]:
        for payer, member in IN1.get(fid, []):
            up = payer.upper()
            if re.search(SKIP_IN1, up): continue
            code = next((c for pat, c in PAYER_MAP if re.search(pat, up)), None)
            if not code or code in seen or code not in CODE2CAR or not member: continue
            seen.add(code)
            try:
                insid, seq = add_ins.add(pid, CODE2CAR[code], member, finclass="CC")
                rec["plans"].append({"code": code, "ins": insid, "seq": seq, "from": payer[:30]})
            except Exception as e:
                rec["plans"].append({"code": code, "err": str(e)[:100]})
            time.sleep(0.3)
    v["resolved"] = pid; v["resolution"] = "NEW CHART created 10/28 (%s)" % chart
    reg["created"].append(rec); print("OK", pid, chart, last[:5] + "*", [(p["code"], p.get("seq")) for p in rec["plans"]])
    json.dump(reg, open(REGF, "w"), indent=1); json.dump(MATCH, open("feed_match_1028.json", "w"), indent=1)
    time.sleep(0.5)
print("DONE created", len(reg["created"]), "failed", len(reg["failed"]))
