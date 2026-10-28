# PLAIN ENGLISH (Claimocity backlog import 10/28/2026 - step 5b, the cascade's chart fixes for the HOLD charts):
#   'CMS reports MA/other primary X but no ACTIVE X plan'  -> add X with the member id from the feed's IN1, else from Stedi
#                                                              insurance discovery's X coverage (medical only, never PDP)
#   'Medicaid 271 names SMMC MMA plan X but the chart has no X plan' -> add X (FLO99/HUM01/SUN01/SIM01...) with the Medicaid id
#   'no active plan: discovery found nothing'              -> add the feed's IN1 payers that carry a member id (Medicare/Medicaid/
#                                                              commercial), so the 271 can judge them
#   Then the chart is re-verified by feed_verify_1028.py (which sets the visits' order). Writes registers/feed_fixholds_1028.json.
#   Begin date = one year back (add_ins default) so every imported DOS falls inside the plan. No group numbers (William's rule).
import amd, add_ins, stedi, elig_amd, re, json, os, glob, time, collections
CARRIERS = json.load(open("carriers_rich.json")); CODE2CAR = {v[0]: k for k, v in CARRIERS.items()}
NAME_MAP = [(r"HUMANA", "HUM01"), (r"UNITED ?HEALTH|UHC|AARP MEDICARE", "UNI20"), (r"AETNA", "AET07"), (r"CIGNA", "CIG09"),
            (r"FLORIDA BLUE|BLUE CROSS|BC/BS|BCBS", "BCBS"), (r"SUNSHINE|CENTENE", "SUN01"), (r"WELLCARE", "WEL04"), (r"CAPITAL HEALTH", "CAP07"),
            (r"SIMPLY", "SIM01"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY", "FLO99"), (r"^CMS$|MEDICARE", "FLO02"), (r"MEDICAI", "MCAD"),
            (r"TRICARE FOR LIFE", "TRI05"), (r"TRICARE", "TRI00"), (r"CHAMPVA", "CHA03")]
SKIP_IN1 = r"LIABILITY|SELF PAY|PRIVATE PAY|PENDING|COINS|CO-INS|THERAPY|VACCINE|LAB\b|PART D|PDP|PRESCRIPTION|HOSPICE"
def map_name(n):
    for pat, c in NAME_MAP:
        if re.search(pat, (n or "").upper()): return c
    return None
# feed IN1 (payer, member) per Claimocity patient id
IN1 = collections.defaultdict(list); SSN = {}
for f in glob.glob("/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct/*.hl7"):
    cur = None
    for line in open(f, errors="replace").read().replace("\r", "\n").split("\n"):
        s = line.split("|")
        if s[0] == "PID":
            cur = s[3]; ssn = re.sub(r"\D", "", s[19]) if len(s) > 19 else ""
            if len(ssn) == 9: SSN[cur] = ssn
        elif s[0] == "IN1" and cur:
            payer = s[4].split("^")[0] if len(s) > 4 else ""; member = s[36].strip() if len(s) > 36 else ""
            if payer and not re.search(SKIP_IN1, payer.upper()) and (payer, member) not in IN1[cur]: IN1[cur].append((payer, member))
REG = json.load(open("registers/feed_import_1028.json")); PARSED = {m["pid"]: m for m in json.load(open("feed_parsed_1028.json"))}
prev = {}
for f in ["feed_verify_1028.json"] + [x for x in os.listdir(".") if x.startswith("feed_verify_1028_") and x.endswith(".json") and "probe" not in x]:
    prev.update(json.load(open(f)))
amd.login_cached()
out = {}
for pid, rec in prev.items():
    if rec.get("decision") != "HOLD": continue
    num = re.sub(r"\D", "", pid); holds = " | ".join(rec.get("hold") or []); fixes = []
    visits = [v for v in REG["created"] if v["pid"] == pid]
    feed_ids = {v["feed_id"] for v in visits}
    msg = PARSED.get(next(iter(feed_ids)), {}) if feed_ids else {}
    last, _, first = msg.get("name", "").partition(","); first = first.strip().split(" ")[0] if first else ""; last = last.strip()
    chart_codes = {p["car"] for p in rec.get("plans") or [] if not p.get("end")}
    def add(code, member, why):
        if code not in CODE2CAR or not member: fixes.append("cannot add %s (%s)" % (code, "no carrier" if code not in CODE2CAR else "no member id")); return
        insid, seq = add_ins.add(num, CODE2CAR[code], member)
        fixes.append("added %s seq %s (%s) - %s" % (code, seq, insid, why)); time.sleep(0.4)
    try:
        m = re.search(r"CMS reports MA/other primary '([^']+)' \((\w+)\)", holds)
        if m:
            code = m.group(2); member = next((mem for fid in feed_ids for payer, mem in IN1.get(fid, []) if map_name(payer) == code and mem), None)
            src = "feed IN1"
            if not member:
                ds = stedi.disc_summ(stedi.disc(first, last, msg.get("dob", "")[:8], "FL")); src = "Stedi discovery"
                for it in ds.get("items") or []:
                    txt = ((it.get("plan") or "") + " " + (it.get("payer") or "")).upper()
                    if re.search(r"PDP|PRESCRIPTION|PART D", txt): continue
                    if map_name(it.get("payer")) == code and it.get("member"): member = it["member"]; break
            add(code, member, "CMS names it the MA/primary payer; member id from %s" % src)
        m = re.search(r"Medicaid 271 names SMMC MMA plan (\w+) but the chart has no", holds)
        if m:
            code = m.group(1); pa, pl = elig_amd.plans(num)
            mcad = next((p for p in pl if CARRIERS.get(p.get("carrier"), ["?"])[0] == "MCAD" and not p.get("enddate")), None)
            add(code, (mcad or {}).get("subscribernum"), "SMMC MMA plan per the Medicaid 271; Medicaid id from the MCAD plan")
        if "no active plan" in holds or "no ACTIVE plan" in holds:
            added = False
            for fid in feed_ids:
                for payer, mem in IN1.get(fid, []):
                    code = map_name(payer)
                    if code and mem and code not in chart_codes:
                        add(code, mem, "feed IN1 '%s'" % payer[:30]); chart_codes.add(code); added = True
            if not added:
                # Medicare MBI lookup with the feed's SSN (MBILU) - the SSN is used in the call only, never stored or printed
                ssn = next((SSN[fid] for fid in feed_ids if fid in SSN), None)
                if ssn and "FLO02" not in chart_codes:
                    try:
                        j = stedi.mbi(first, last, msg.get("dob", "")[:8], None, None, ssn, pid=num)
                        ms = stedi.med_summ(j)
                        if ms.get("mbi") and (ms.get("partB") or ms.get("partA")) and not ms.get("death"):
                            add("FLO02", ms["mbi"], "Stedi MBI lookup (SSN) - Medicare Part A %s / B %s" % (ms.get("partA"), ms.get("partB"))); chart_codes.add("FLO02"); added = True
                            oth = [o for o in ms.get("other") or [] if o.get("code") in ("R", "U")]
                            if oth: fixes.append("CMS also lists other payer(s): %s" % [(o.get("typeName"), o.get("entity")) for o in oth][:2])
                        else:
                            fixes.append("MBI lookup: %s" % (ms.get("errors") or "no Medicare record")[:1])
                    except Exception as e:
                        fixes.append("MBI lookup error %s" % str(e)[:100])
            if not added and "discovery found [" in holds:
                ds = stedi.disc_summ(stedi.disc(first, last, msg.get("dob", "")[:8], "FL"))
                for it in ds.get("items") or []:
                    txt = ((it.get("plan") or "") + " " + (it.get("payer") or "")).upper()
                    if re.search(r"PDP|PRESCRIPTION|PART D", txt) or not (it.get("status") or "").upper().startswith("ACTIVE") or not it.get("member"): continue
                    code = map_name(it.get("payer"))
                    if code and code not in chart_codes:
                        add(code, it["member"], "Stedi discovery '%s' %s" % ((it.get("payer") or "")[:25], it.get("plan") or "")); chart_codes.add(code); added = True
            if not added: fixes.append("no mappable IN1 payer with a member id in the feed - William (facesheet)")
        if "date of death" in holds and "void" not in holds:
            fixes.append("date-of-death hold re-evaluated by the verifier (visits before the death date are billable)")
    except Exception as e:
        fixes.append("error %s" % str(e)[:160])
    out[pid] = {"holds": rec.get("hold"), "fixes": fixes}
    print(pid, "|", holds[:90], "|", "; ".join(fixes)[:200])
json.dump(out, open("registers/feed_fixholds_1028.json", "w"), indent=1)
print("TO RE-VERIFY:", ",".join(out))
