# PLAIN ENGLISH (Claimocity backlog import 10/28/2026 - step 5, the cascade insurance check William asked for:
#   "use the nightly cascade insurance look up stedi tools as well to verify correct insurances and all on the claims").
# Decides, per chart with imported visits, which plan the claims bill FIRST and whether the visits may be released:
#   1. deceased guard (cache with real dates + AMD 'deceased' flag + any 271 date of death) - a DOS after death HOLDS.
#   2. AMD's free 271 (checkEligibility) on every open chart plan -> ACTIVE / INACTIVE / REJECTED, other payers, QMB, hospice.
#   3. lead plan: traditional Medicare (FLO02) ACTIVE and CMS lists no Medicare Advantage replacement -> Medicare first;
#      CMS lists an MA/other primary -> that carrier's ACTIVE chart plan first (none -> HOLD); no Medicare -> the first ACTIVE
#      commercial/MA plan; only Medicaid/LTC plans -> the ACTIVE one (FCC answers AAA at eligibility but pays - REJECTED kept).
#      Secondary = one more open plan of another carrier (the Medicaid/LTC plan for a QMB/dual). Medicaid/LTC never leads over Medicare.
#   4. the visits' insorder is set to that order (full-visit echo, no rebill - nothing is billed yet); the chart default order is left.
#   5. no ACTIVE plan at all -> Stedi insurance discovery -> add a found ACTIVE MEDICAL plan (never Part D / PDP) + order; else HOLD.
#   6. the feed's IN1 payers are mapped and reported next to the chart (the 271 decides, the feed only informs).
# Writes feed_verify_1028.json (+ registers copy). AMD writes: visit insorder resaves; addinsurance only from discovery.
# Usage: python3 feed_verify_1028.py [--no-stedi] [--limit N] [--only patNNN,...]
import amd, elig_amd, stedi, add_ins, ins_update, resave, re, json, sys, os, time, collections
os.environ.setdefault("DECEASED_CACHE", "/home/claude/unbilled/deceased_cache_local.json")
import deceased_guard
REG = json.load(open("registers/feed_import_1028.json"))
PARSED = {m["pid"]: m for m in json.load(open("feed_parsed_1028.json"))}
CARRIERS = json.load(open("carriers_rich.json"))            # carN -> [code, name]
CODE2CAR = {v[0]: k for k, v in CARRIERS.items()}
PAYER_MAP = [
    (r"MEDICARE A\b|FCSO|MEDICARE PART A|MEDICARE B\b|TRADITIONAL MEDICARE|^MEDICARE$|^MCA-|^MCB", "FLO02"),
    (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"WELLCARE", "WEL04"), (r"HUMANA", "HUM01"),
    (r"CAPITAL HEALTH", "CAP07"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY CARE|FCC\b", "FLO99"),
    (r"UNITED ?HEALTH|UHC|AARP MEDICARE ADV", "UNI20"), (r"AARP", "AAR01"), (r"AETNA", "AET07"),
    (r"CIGNA", "CIG09"), (r"FLORIDA BLUE|BCBS|BLUE CROSS|BC/BS", "BCBS"), (r"TRICARE FOR LIFE|TFL", "TRI05"),
    (r"TRICARE", "TRI00"), (r"CHAMPVA", "CHA03"), (r"VA COMMUNITY|VACCN|VETERAN", "VACCN"),
    (r"MEDICAID(?! MANAGED)|AHCA|FLORIDA MEDICAID|^MCD|-MCD\b", "MCAD"), (r"MOLINA", "MOL01"),
]
STEDI_NAME_MAP = [(r"HUMANA", "HUM01"), (r"UNITED ?HEALTH|UHC", "UNI20"), (r"AETNA", "AET07"), (r"CIGNA", "CIG09"),
                  (r"FLORIDA BLUE|BLUE CROSS|BCBS", "BCBS"), (r"SUNSHINE|CENTENE", "SUN01"), (r"WELLCARE", "WEL04"), (r"CAPITAL HEALTH", "CAP07"),
                  (r"SIMPLY", "SIM01"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY", "FLO99"), (r"^CMS$|MEDICARE", "FLO02"), (r"MEDICAI", "MCAD")]
LTC = {"FLO99", "MCAD", "SUN01", "SIM01"}
FAMILY = {"UNI20": "UHC", "UHCMA": "UHC", "AAR01": "UHC", "UMR": "UHC", "CIPSC": "UHC", "HUM01": "HUM", "HUMMA": "HUM", "CIG09": "CIG", "CIG13": "CIG",
          "AET07": "AET", "AET12": "AET", "BCBS": "BCBS", "FLO01": "BCBS", "WEL04": "WEL", "WEL07": "WEL"}          # Medicaid / LTC plans never lead over active Medicare
MA_WORDS = r"HUMANA|UNITED|UHC|AARP|WELLCARE|AETNA|CIGNA|CAPITAL HEALTH|FLORIDA BLUE|BLUE|DEVOTED|SIMPLY|CAREPLUS|FREEDOM|OPTIMUM|SUNSHINE|AMBETTER|EMPHESYS|OPTUM"
def map_payer(name, table):
    for pat, code in table:
        if re.search(pat, (name or "").upper()): return code
    return None
def ma_replacement(s):
    """From a Medicare (FLO02) 271 summary: the name of a Medicare Advantage / other-primary payer CMS reports, else None."""
    for o in s.get("other_payers") or []:
        if o.get("code") in ("R", "U") and (o.get("type") or "") != "OT":
            names = " ".join((e.get("name") or "") for e in o.get("entities") or [])
            ids = " ".join((e.get("id") or "") for e in o.get("entities") or [])
            if re.search(r"\bS\d{4}\b", ids): continue                      # S-contract = Part D, never a medical payer
            if re.search(MA_WORDS, names.upper()) and not re.search(r"PRESCRIPTION|PDP|PART D|RX", (names + " " + (o.get("plan") or "")).upper()):
                return names.strip()
    return None
def mma_plan(s):
    """From a Florida Medicaid (MCAD) 271 summary: the SMMC MMA (comprehensive) plan's carrier code, else None (= FFS)."""
    for o in s.get("other_payers") or []:
        if "MMA" in str(o.get("plan") or "").upper():
            names = " ".join((e.get("name") or "") for e in o.get("entities") or [])
            return map_payer(names, STEDI_NAME_MAP) or "?" + names[:30]
    return None
def fast_set_insorder(v, order):
    """Visit insorder by full echo of THIS import's charges (the register holds every charge id of the visit, so no
    gettxhistory paging): one getchargedetaildataicd10 per charge + one updvisitwithcharges force=1. -> (ok, msg)"""
    import xml.etree.ElementTree as ET
    charges = []; vis = pat = None
    for cid in v["charges"]:
        d = ET.fromstring(resave.detail(re.sub(r"\D", "", cid)))
        if vis is None: vis = d.find(".//visit"); pat = d.find(".//patient")
        for c in d.iter("charge"):
            if c.get("id") == cid and c.get("void") != "1": charges.append(c)
    if vis is None or len(charges) != len(v["charges"]):
        return False, "detail read mismatch (%d of %d charges live)" % (len(charges), len(v["charges"]))
    if (vis.get("insorder") or "").replace(" ", "") == order: return True, "already %s" % order
    chg = ""
    for c in charges:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, x) for k, x in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = order
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                 "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, x) for k, x in va.items()), chg)), timeout=180)
    if "Fault" in r: return False, "resave FAULT " + re.sub(r"\s+", " ", r[:200])
    d2 = ET.fromstring(resave.detail(re.sub(r"\D", "", v["charges"][0]))); v2 = d2.find(".//visit")
    live = [c for c in d2.iter("charge") if c.get("void") != "1"]
    got = (v2.get("insorder") or "").replace(" ", "") if v2 is not None else ""
    return got == order and len(live) >= 1, "insorder %s -> %s" % (vis.get("insorder"), got)
def main():
    a = sys.argv[1:]; use_stedi = "--no-stedi" not in a; limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 10 ** 9
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    amd.login_cached()
    by_chart = collections.defaultdict(list)
    for r in REG["created"]: by_chart[r["pid"]].append(r)
    OUTF = os.environ.get("VERIFY_OUT", "feed_verify_1028.json")
    prev = {}
    for f in ["feed_verify_1028.json"] + [x for x in os.listdir(".") if x.startswith("feed_verify_1028_p") and x.endswith(".json")]:
        if os.path.exists(f): prev.update(json.load(open(f)))
    out = dict(prev); stats = collections.Counter(); n = 0
    for pid, visits in by_chart.items():
        if only and pid not in only: continue
        if not only and pid in prev and prev[pid].get("decision") == "RELEASE" and prev[pid].get("v") == 3: continue
        if n >= limit: break
        n += 1
        num = re.sub(r"\D", "", pid)
        rec = {"v": 3, "visits": [v["visit"] for v in visits], "dos": sorted({v["dos"] for v in visits}), "cpts": sorted({c for v in visits for c in v["cpts"]}), "checks": [], "fixes": [], "hold": []}
        try:
            pa, plans = elig_amd.plans(num)
            rec["insorder"] = pa.get("insorder", ""); rec["deceased_flag"] = pa.get("deceased", "")
            openp = [p for p in plans if not p.get("enddate")]
            code_of = {p["id"]: CARRIERS.get(p.get("carrier"), [p.get("carrier")])[0] for p in plans}
            rec["plans"] = [{"id": p["id"], "car": code_of[p["id"]], "seq": p.get("sequence"), "end": p.get("enddate")} for p in plans]
            feed_codes = []
            for v in visits:
                for nm in PARSED.get(v["feed_id"], {}).get("IN1", []):
                    c = map_payer(nm, PAYER_MAP)
                    if c and c not in feed_codes: feed_codes.append(c)
            rec["feed_payers"] = feed_codes
            latest_dos = max(v["dos"] for v in visits)
            # 1. deceased
            blocked, why = deceased_guard.check(num, latest_dos, "FLO02" if any(code_of[p["id"]] == "FLO02" for p in openp) else None,
                                                 "99487" if "99487" in rec["cpts"] else None, allow_lookup=use_stedi)
            if pa.get("deceased"): rec["hold"].append("AMD chart flagged deceased %s" % pa.get("deceased"))
            if blocked: rec["hold"].append(why)
            # 2. 271 per open plan
            status = {}; summ = {}
            for p in openp:
                try:
                    s = elig_amd.run_plan(num, p["id"].replace("ins", "")); summ[p["id"]] = s
                    status[p["id"]] = (s.get("status") or "UNKNOWN").split()[0]
                    rec["checks"].append({"plan": p["id"], "car": code_of[p["id"]], "seq": p.get("sequence"), "result": elig_amd.one_line(s)[:300]})
                    if s.get("date_of_death"):
                        dod = s["date_of_death"]; dod_iso = "%s-%s-%s" % (dod[:4], dod[4:6], dod[6:8]) if re.match(r"\d{8}$", dod) else dod
                        deceased_guard.record(num, {"dateOfDeath": dod}, "amd-271")
                        after = [v["dos"] for v in visits if deceased_guard._iso(v["dos"]) > dod_iso]
                        if after: rec["hold"].append("271 reports date of death %s - visits dated after it: %s (never bill; void)" % (dod_iso, after))
                        else: rec["note_dod"] = "271 reports date of death %s; all imported visits are on/before it - billable" % dod_iso
                except Exception as e:
                    status[p["id"]] = "ERROR"; rec["checks"].append({"plan": p["id"], "car": code_of[p["id"]], "result": "271 error %s" % str(e)[:120]})
                time.sleep(0.3)
            # 3. choose the lead
            def active(p): return status.get(p["id"]) == "ACTIVE"
            med = [p for p in openp if code_of[p["id"]] == "FLO02"]
            med_active = next((p for p in med if active(p)), None)
            if med_active is None:
                for p in med:   # Medicare answers INACTIVE after a death; coverage was in force on DOS before the death date -> still the lead
                    sdod = (summ.get(p["id"]) or {}).get("date_of_death")
                    if sdod and all(deceased_guard._iso(v["dos"]) <= "%s-%s-%s" % (sdod[:4], sdod[4:6], sdod[6:8]) for v in visits):
                        med_active = p; rec["fixes"].append("Medicare INACTIVE after death %s; every imported DOS precedes it - Medicare leads" % sdod); break
            lead = None; reason = ""
            if med_active:
                ma = ma_replacement(summ[med_active["id"]])
                if ma:
                    ma_code = map_payer(ma, STEDI_NAME_MAP)
                    fam = FAMILY.get(ma_code, ma_code)
                    cand = sorted([p for p in openp if FAMILY.get(code_of[p["id"]], code_of[p["id"]]) == fam and active(p)], key=lambda p: int(p.get("sequence") or 99))
                    if cand: lead = cand[0]; reason = "CMS: %s is the Medicare Advantage/primary payer" % ma
                    else: rec["hold"].append("CMS reports MA/other primary '%s' (%s) but no ACTIVE %s plan on the chart" % (ma, ma_code, ma_code))
                else:
                    lead = med_active; reason = "traditional Medicare ACTIVE, no MA replacement on the CMS 271"
            if lead is None and not rec["hold"]:
                comm = [p for p in openp if active(p) and code_of[p["id"]] not in LTC and code_of[p["id"]] != "FLO02"]
                if comm: lead = sorted(comm, key=lambda p: int(p.get("sequence") or 99))[0]; reason = "%s ACTIVE (no traditional Medicare)" % code_of[lead["id"]]
            if lead is None and not rec["hold"]:
                ltc = [p for p in openp if code_of[p["id"]] in LTC and status.get(p["id"]) in ("ACTIVE", "REJECTED")]
                mcad = next((p for p in ltc if code_of[p["id"]] == "MCAD" and active(p)), None)
                mma = mma_plan(summ[mcad["id"]]) if mcad else None
                if mma and not mma.startswith("?"):
                    cand = [p for p in openp if code_of[p["id"]] == mma and status.get(p["id"]) in ("ACTIVE", "REJECTED")]
                    if cand: lead = cand[0]; reason = "Medicaid 271: SMMC MMA plan is %s - physician claims go to the MMA plan" % mma
                    else: rec["hold"].append("Medicaid 271 names SMMC MMA plan %s but the chart has no %s plan" % (mma, mma))
                elif mma: rec["hold"].append("Medicaid 271 names an SMMC MMA plan not mapped to a carrier: %s" % mma)
                elif ltc: lead = sorted(ltc, key=lambda p: int(p.get("sequence") or 99))[0]; reason = "Medicaid/LTC plan %s only (271 %s, no MMA plan)" % (code_of[lead["id"]], status[lead["id"]])
            # 5. discovery when nothing is active
            if lead is None and not rec["hold"]:
                if use_stedi:
                    msg = PARSED.get(visits[0]["feed_id"], {})
                    last, _, first = msg.get("name", "").partition(","); first = first.strip().split(" ")[0] if first else ""; last = last.strip()
                    try:
                        ds = stedi.disc_summ(stedi.disc(first, last, msg.get("dob", "")[:8], "FL")); rec["discovery"] = ds
                        for it in ds.get("items") or []:
                            txt = ((it.get("plan") or "") + " " + (it.get("payer") or "")).upper()
                            if re.search(r"PDP|PRESCRIPTION|PART D", txt) or not (it.get("status") or "").upper().startswith("ACTIVE") or not it.get("member"): continue
                            code = map_payer(it.get("payer"), STEDI_NAME_MAP)
                            if code and any(code_of[p["id"]] == code for p in plans):
                                rec["fixes"].append("discovery found %s but the chart already carries a %s plan (status %s) - not re-added" % (code, code, [status.get(p["id"]) for p in plans if code_of[p["id"]] == code])); continue
                            if code and code in CODE2CAR:
                                insid, seq = add_ins.add(num, CODE2CAR[code], it["member"])
                                rec["fixes"].append("discovery: added %s plan -> %s seq %s" % (code, insid, seq)); stats["plans added"] += 1
                                if insid and str(insid).startswith("ins"):
                                    ok, m2 = ins_update._set_order(num, {p["id"]: p for p in elig_amd.plans(num)[1]}, insid, str(seq)); rec["fixes"].append("chart order -> %s: %s" % (seq, m2[:100]))
                                    lead = {"id": insid, "sequence": str(seq)}; code_of[insid] = code; reason = "Stedi discovery %s ACTIVE" % code; status[insid] = "ACTIVE"
                                break
                        if lead is None: rec["hold"].append("no active plan: discovery found %s" % ([(i.get("payer"), i.get("status")) for i in ds.get("items") or []] or "nothing"))
                    except Exception as e:
                        rec["hold"].append("no active plan; discovery error %s" % str(e)[:120])
                else:
                    rec["hold"].append("no ACTIVE plan on the chart (Stedi off)")
            # order = lead + one secondary of another carrier (dual: the Medicaid/LTC plan; else the next open plan)
            order = None
            if lead is not None:
                sec = None
                others = [p for p in openp if p["id"] != lead["id"] and code_of[p["id"]] != code_of[lead["id"]] and status.get(p["id"]) in ("ACTIVE", "REJECTED")]
                ltc_sec = [p for p in others if code_of[p["id"]] in LTC or (code_of[p["id"]] == "HUM01" and re.match(r"\d{10}$", p.get("subscribernum") or ""))]
                qmb = bool(med_active and any((o.get("code") == "QM") or "QMB" in str(o.get("plan") or "").upper() for o in summ[med_active["id"]].get("other_payers") or []))
                if code_of[lead["id"]] == "FLO02" and ltc_sec: sec = sorted(ltc_sec, key=lambda p: int(p.get("sequence") or 99))[0]
                elif code_of[lead["id"]] not in LTC and code_of[lead["id"]] != "FLO02" and ltc_sec and med_active:
                    sec = sorted(ltc_sec, key=lambda p: int(p.get("sequence") or 99))[0]      # MA / D-SNP lead on a dual: Medicaid plan second
                elif code_of[lead["id"]] == "FLO02":
                    supp = [p for p in others if active(p) and code_of[p["id"]] not in LTC]
                    if supp: sec = sorted(supp, key=lambda p: int(p.get("sequence") or 99))[0]
                order = ",".join([lead["sequence"]] + ([sec["sequence"]] if sec else []))
                rec["lead"] = {"code": code_of[lead["id"]], "seq": lead["sequence"], "why": reason, "qmb": qmb}
                rec["order"] = order
                # 4. apply to the visits
                applied = (prev.get(pid) or {}).get("applied") or {}; rec["applied"] = dict(applied)
                # the import copied the chart's default order onto every visit: when that is already the target, nothing to resave
                same_as_default = (rec["insorder"] or "").replace(" ", "") == order
                for v in visits:
                    if applied.get(v["visit"]) == order: continue
                    if same_as_default: rec["applied"][v["visit"]] = order; continue
                    cid = v["charges"][0] if v.get("charges") else None
                    if not cid: rec["fixes"].append("%s: no charge id recorded" % v["visit"]); continue
                    try:
                        ok, m = fast_set_insorder(v, order)
                        rec["fixes"].append("%s insorder %s: %s" % (v["visit"], order, "ok" if ok else m[:140]))
                        if ok: rec["applied"][v["visit"]] = order
                        else: rec["hold"].append("insorder not applied on %s" % v["visit"])
                    except Exception as e:
                        rec["hold"].append("insorder error on %s: %s" % (v["visit"], str(e)[:100]))
                    time.sleep(0.4)
            if feed_codes and lead is not None and code_of[lead["id"]] not in feed_codes:
                rec["note"] = "feed IN1 says %s, chart bills %s first (%s)" % (feed_codes, code_of[lead["id"]], reason)
            rec["decision"] = "HOLD" if rec["hold"] else "RELEASE"
            stats[rec["decision"]] += 1
            print(rec["decision"], pid, rec.get("order"), rec.get("lead", {}).get("code"), "|", reason[:60], "| feed", feed_codes, "|", "; ".join(rec["hold"])[:140])
        except Exception as e:
            rec["decision"] = "HOLD"; rec["hold"].append("verify error %s" % str(e)[:160]); stats["error"] += 1; print("ERR", pid, str(e)[:160])
        out[pid] = rec
        json.dump({k: v for k, v in out.items() if k not in prev or v is not prev.get(k)} if OUTF != "feed_verify_1028.json" else out, open(OUTF, "w"), indent=1)
        if n % 25 == 0: print("progress", n, dict(stats))
    print("DONE", dict(stats))
if __name__ == "__main__": main()
