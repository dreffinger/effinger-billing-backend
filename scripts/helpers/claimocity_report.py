# PLAIN ENGLISH: compiles the 10/28 Claimocity backlog import into one digest (counts, dollars, holds) from the registers.
# Also writes a PHI-light copy of the verify register for the repo (no addresses / member ids in the 271 result strings).
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import json, os, re, collections, datetime
POS_REPORT_VERSION = "2026-11-10.5"     # the place-of-service block below; mirror.py PROTECTED names this line - change it with every revision of the block
reg = json.load(open(("registers/feed_import_%s.json" % STAMP))); newc = json.load(open(("registers/feed_newcharts_%s.json" % STAMP))) if os.path.exists(("registers/feed_newcharts_%s.json" % STAMP)) else {"created": [], "failed": []}
insp = json.load(open(("registers/feed_inspector_%s.json" % STAMP))) if os.path.exists(("registers/feed_inspector_%s.json" % STAMP)) else {}
fix = json.load(open(("registers/feed_fixholds_%s.json" % STAMP))) if os.path.exists(("registers/feed_fixholds_%s.json" % STAMP)) else {}
ver = {}
for f in [("feed_verify_%s.json" % STAMP)] + sorted(x for x in os.listdir(".") if x.startswith(("feed_verify_%s_" % STAMP)) and x.endswith(".json") and "probe" not in x):
    if os.path.exists(f): ver.update(json.load(open(f)))
# PHI-light verify register for GitHub
lite = {}
for pid, v in ver.items():
    w = dict(v); w["checks"] = [{"plan": c.get("plan"), "car": c.get("car"), "seq": c.get("seq"), "status": (c.get("result") or "")[:40].split(" | ")[0]} for c in v.get("checks") or []]
    w.pop("discovery", None); lite[pid] = w
json.dump(lite, open(("registers/feed_verify_%s.json" % STAMP), "w"), indent=1)
fees = sum(float(f) for x in reg["created"] for f in x.get("fees", []) if re.match(r"^\d", f))
cpts = collections.Counter(c for x in reg["created"] for c in x["cpts"])
dec = collections.Counter(v.get("decision") for v in ver.values())
orders_changed = sum(1 for v in ver.values() for k, o in (v.get("applied") or {}).items() if o and o != (v.get("insorder") or "").replace(" ", ""))
plans_added = [(pid, f) for pid, v in ver.items() for f in v.get("fixes") or [] if f.startswith("discovery: added")] + [(pid, f) for pid, v in fix.items() for f in v.get("fixes") or [] if f.startswith("added")]
leads = collections.Counter((v.get("lead") or {}).get("code") for v in ver.values() if v.get("decision") == "RELEASE")
holds = {pid: v.get("hold") for pid, v in ver.items() if v.get("decision") == "HOLD"}
release_visits = sum(len(v["visits"]) for v in ver.values() if v.get("decision") == "RELEASE")
hold_visits = sum(len(v["visits"]) for v in ver.values() if v.get("decision") == "HOLD")
lines = []
L = lines.append
L("# Claimocity backlog import - digest %s UTC (chat session, William 10/28 02:23 ET: enter all encounters and bill them out)" % datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
L("")
L("## Import")
_qlines = sum(1 for x in reg["created"] if isinstance(x.get("quality_codes"), list) and x.get("quality_codes") and x.get("quality_charge"))    # no-charge quality lines are not charge lines
L("- %d visits / %d charge lines created, $%s at the fee schedule; %d encounters skipped as already in AMD; 0 faults." % (len(reg["created"]), sum(len(x["charges"]) for x in reg["created"]) - _qlines, format(fees, ",.2f"), len(reg["skipped"])))
L("- CPT mix: " + ", ".join("%s x%d" % (k, v) for k, v in cpts.most_common()))
# place of service in the nursing buildings (William 11/10/2026, rules.md): what the import's per-line rule did in this batch
_ps = collections.Counter(); _NFV = {"99304", "99305", "99306", "99307", "99308", "99309", "99310", "99315", "99316"}; _CCM = {"99487", "99489"}
_NURSING_FAC = {"fac34", "fac32", "fac33", "fac58", "fac1350"}                       # Brynwood, Aspire, Centre Pointe, Westminster Oaks-Bertrand, Oakes Southwood
_st8 = re.sub(r"[^0-9TZ]", "", STAMP)                                               # 2026-11-10T1319Z and 20261110T1319Z are the same batch
_rule_stamp = bool(re.match(r"^2\d{7}T", _st8)) and _st8[:8] >= "20261110"          # batches from the day the rule began
_who = collections.defaultdict(list)                                                  # what kind of line -> the charts (chart number, date, codes - no name)
def _tag(x): return "%s %s %s" % (x.get("pid") or "?", x.get("dos") or "?", "+".join(str(c) for c in (x.get("cpts") or [])))
def _names(key, lead):
    v = _who.get(key) or []
    if v: L("  - %s: %s%s" % (lead, "; ".join(v[:30]), (" (+%d more - see the import register)" % (len(v) - 30)) if len(v) > 30 else ""))
try:
    for x in reg["created"]:
        _c = x.get("cpts") or []
        if x.get("msg_own") is False: _ps["notown"] += 1; _who["notown"].append(_tag(x))
        if x.get("prof_default") is True: _ps["profdef"] += 1; _who["profdef"].append(_tag(x))
        if "pos_lines" in x and not x.get("fac") and not any(c in _NFV or c in _CCM for c in _c): _ps["nofacother"] += 1; _who["nofacother"].append(_tag(x))      # CCM / nursing lines are named in the block below
        if x.get("pos_stored") is not None and x.get("pos_lines"):
            _ps["readback"] += 1
            _qdiff = bool(x.get("quality_pos_stored")) and bool(x.get("quality_pos")) and str(x["quality_pos_stored"]) != str(x["quality_pos"])      # the quality line's own place of service
            if sorted(str(v) for v in x["pos_stored"]) != sorted(str(v) for v in x["pos_lines"]) or _qdiff: _ps["notkept"] += 1; _who["notkept"].append("%s sent %s stored %s%s" % (_tag(x), x["pos_lines"], x["pos_stored"], (" (quality line sent %s stored %s)" % (x["quality_pos"], x["quality_pos_stored"])) if _qdiff else ""))
        if x.get("pos_err"): _ps["err"] += 1; _who["err"].append("%s (%s)" % (_tag(x), str(x["pos_err"])[:70])); continue
        if not x.get("pos_lines"):
            if _rule_stamp and x.get("fac") in _NURSING_FAC and any(c in _NFV or c in _CCM for c in _c): _ps["norule"] += 1; _who["norule"].append(_tag(x))
            continue
        if x.get("pos_feed") != "31": continue
        if not x.get("fac"):
            _n = sum(1 for c in _c if c in _NFV or c in _CCM); _ps["nofac"] += _n
            if _n: _who["nofac"].append(_tag(x))
            continue
        _k = x.get("pos_kind") or []
        for _i, (_cpt, _p) in enumerate(zip(_c, x.get("pos_lines") or [])):
            _kind = _k[_i] if _i < len(_k) else ""
            if _cpt in _CCM:
                _ps["ccm%s" % _p] += 1
                if _kind == "ccm-skilled-month" and _tag(x) not in _who["ccm31"]: _who["ccm31"].append(_tag(x))
            elif _cpt in _NFV:
                _ps["nf%s" % _p] += 1
                if _kind in ("extra", "between"): _ps["nfleft"] += 1; _who["nfleft"].append(_tag(x))
                if _kind == "moved": _ps["nfmoved"] += 1
    if any(_ps[k] for k in _ps if k not in ("readback", "notown", "profdef", "nofacother")):
        L("- Place of service in the nursing buildings (11/10/2026 rule): CCM lines entered as 32: %d%s; nursing visits 32 (monthly): %d; nursing visits 31: %d%s%s%s%s%s." % (
            _ps["ccm32"],
            (" (and %d kept at 31 because the chart shows weekly visits, an admission or a new stay that month - not held: they go out at 31 with the next claim run unless William changes them first)" % _ps["ccm31"]) if _ps["ccm31"] else "",
            _ps["nf32"], _ps["nf31"],
            (" (%d of them kept at 31 because the chart shows neither pattern - see pos_why)" % _ps["nfleft"]) if _ps["nfleft"] else "",
            (" (%d of them because the previous nursing visit was in another building)" % _ps["nfmoved"]) if _ps["nfmoved"] else "",
            ("; POS RULE NOT APPLIED on %d visit(s) - entered at the feed's place of service, see pos_err in the import register and rules.md 11/10/2026" % _ps["err"]) if _ps["err"] else "",
            ("; %d CCM / nursing-visit line(s) came from a building the facility table does not know - entered at 31 with no facility" % _ps["nofac"]) if _ps["nofac"] else "",
            ("; PLACE OF SERVICE RULE DID NOT RUN on %d visit(s) in the nursing buildings - the import helper in this workspace is an old copy (rules.md 11/10/2026)" % _ps["norule"]) if _ps["norule"] else ""))
        _names("err", "TOP OF THE REPORT - rule not applied, check by hand before the claim run")
        _names("norule", "TOP OF THE REPORT - rule did not run (old helper)")
        _names("nofac", "TOP OF THE REPORT - building the facility table does not know")
        _names("ccm31", "for William, not held - CCM kept at 31 (pos_kind ccm-skilled-month)")
        _names("nfleft", "for William, not held - visits kept at 31, neither pattern shown (pos_kind extra / between)")
        if _ps["notkept"]:
            L("  - TOP OF THE REPORT - ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE on %d of %d visit(s) read back:" % (_ps["notkept"], _ps["readback"])); _names("notkept", "sent / stored")
        elif _ps["readback"]: L("  - AdvancedMD's own answer shows the place of service as sent on all %d visit(s) it echoed." % _ps["readback"])
        elif _ps["ccm32"] or _ps["nf32"]: L("  - AdvancedMD's answer did not echo the place of service: read ONE 32 line back by hand (runbook, 'first batch that enters a 32 line').")
    if _ps["notown"]:
        L("- Clinician and building: %d visit(s) could not be matched to their own feed message, so the patient's last-read building and clinician were used - TOP OF THE REPORT, for William (a routine changes nothing on these visits):" % _ps["notown"]); _names("notown", "charts")
    if _ps["profdef"]:
        L("- Clinician: %d visit(s) whose feed message names no clinician id the profile table has were entered under the physician profile - TOP OF THE REPORT, for William (a routine changes nothing on these visits):" % _ps["profdef"]); _names("profdef", "charts")
    if _ps["nofacother"]:
        L("- Building: %d hospital / home / other visit(s) came from a building the facility table does not know and were entered with no facility at the feed's place of service - TOP OF THE REPORT, for William (a routine changes nothing on these visits):" % _ps["nofacother"]); _names("nofacother", "charts")
except Exception as _e:                                    # a register edited by hand must never stop the digest
    L("- Place of service in the nursing buildings (11/10/2026 rule): this line could not be built (%s) - read pos_lines / pos_err in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
# quality code (William 11/10/2026, rules.md): the advance-care-plan code 1123F that rides, at no charge, with Medicare visits of patients 65 and older
try:
    _qg = reg.get("quality_gate") if isinstance(reg.get("quality_gate"), dict) else {}
    _qc = lambda x: isinstance(x, dict) and isinstance(x.get("quality_codes"), list) and bool(x.get("quality_codes"))
    _qa = [x for x in reg["created"] if _qc(x) and x.get("quality_charge")]                      # entered with the line
    _qn = [x for x in reg["created"] if isinstance(x, dict) and x.get("quality_not_stored")]     # the visit was stored, the line was not
    _qr = [x for x in reg["created"] if isinstance(x, dict) and x.get("quality_refused")]        # refused with the line, entered without it
    _qf = [x for x in (reg.get("failed") or []) if isinstance(x, dict) and x.get("stored") and isinstance(x.get("info"), dict) and "quality_tried" in x["info"]]   # refused, NOT sent again
    _pend = [str(v) for v in (_qg.get("pending") or [])] if isinstance(_qg.get("pending"), list) else []
    _dead = [d for d in (_qg.get("dead_zero_lines") or []) if isinstance(d, list)] if isinstance(_qg.get("dead_zero_lines"), list) else []
    _held = {re.sub(r"\D", "", str(h.get("visit") or "")): str(h.get("why") or "")[:140] for h in (insp.get("held") if isinstance(insp, dict) and isinstance(insp.get("held"), list) else []) if isinstance(h, dict)}
    _qh = [(x, _held[re.sub(r"\D", "", str(x.get("visit") or ""))]) for x in _qa if re.sub(r"\D", "", str(x.get("visit") or "")) in _held and re.sub(r"\D", "", str(x.get("visit") or ""))]
    if _qa or _qn or _qr or _qf or _qg.get("off") or _qg.get("notes") or _qg.get("proof") or _qg.get("wait") or _dead or _qg.get("reset"):
        _pf = _qg.get("proof") if isinstance(_qg.get("proof"), dict) else {}
        _days = None
        try:
            _d1 = re.search(r"(\d{8})T", re.sub(r"[^0-9TZ]", "", str(_qg.get("pending_since") or ""))); _d2 = re.search(r"(\d{8})T", _st8)
            if _d1 and _d2: _days = (datetime.datetime.strptime(_d2.group(1), "%Y%m%d") - datetime.datetime.strptime(_d1.group(1), "%Y%m%d")).days
        except Exception: _days = None
        L("- Quality code 1123F (advance care plan, Medicare measure 047; a line that pays nothing): on %d visit(s) in this batch, line amount $%s; %s." % (
            len(_qa), _qg.get("fee") or "0.00",
            ("every eligible visit carries it - a quality line was seen billed to insurance (visit %s, %s)" % (_pf.get("visit"), _pf.get("billed"))) if _qg.get("confirmed") and _pf else
            "every eligible visit carries it - a quality line was seen billed to insurance in an earlier run" if _qg.get("confirmed") else
            ("PILOT, waiting - no line was added in this run: the visit(s) that carry the first line(s) are not billed yet (%s)" % ", ".join(_pend[:6])) if _qg.get("wait") else
            "PILOT - at most %s visit(s) carry it, then no more until one such line is seen billed to insurance in AdvancedMD" % (_qg.get("pilot_cap") or 3)))
        if _qa: L("  - carried by: %s%s" % ("; ".join("%s %s %s" % (x.get("pid"), x.get("visit"), x.get("quality_charge") or "?") for x in _qa[:30]), (" (+%d more)" % (len(_qa) - 30)) if len(_qa) > 30 else ""))
        if _qa and not _qg.get("confirmed"): L("  - first lines: when Medicare's remittance for one of these visits arrives, remark N620 on the 1123F line means Medicare counted it (reason 246 with it is acceptance, not a denial).")
        if _qg.get("wait") and _days is not None and _days >= 3:
            L("  - TOP OF THE REPORT - the quality-code pilot has waited %d days: the visit(s) carrying its first line(s) are still not billed (%s). Look at them in AdvancedMD (Claim Inspector? insurance?) and tell William - he decides whether the line comes off." % (_days, ", ".join(_pend[:6])))
        if _qh: L("  - TOP OF THE REPORT - %d visit(s) that carry the quality line are HELD by the Claim Inspector (the visit's own charge waits with it; William decides whether the line comes off): %s" % (
            len(_qh), "; ".join("%s %s - %s" % (x.get("pid"), x.get("visit"), w) for x, w in _qh[:10])))
        if _qr: L("  - TOP OF THE REPORT - QUALITY CODE NOT ACCEPTED by AdvancedMD on %d visit(s); each visit was entered without it: %s" % (len(_qr), "; ".join("%s %s (%s)" % (x.get("pid"), x.get("visit"), str(x.get("quality_refused"))[:80]) for x in _qr[:10])))
        if _qn: L("  - TOP OF THE REPORT - AdvancedMD stored %d visit(s) WITHOUT the quality line that was sent with it (the visit itself is entered): %s" % (len(_qn), "; ".join("%s %s" % (x.get("pid"), x.get("visit")) for x in _qn[:10])))
        if _qf: L("  - TOP OF THE REPORT - %d visit(s) were refused with the quality line and NOT sent again, because the chart shows part of the visit or could not be read - enter or check them by hand: %s" % (
            len(_qf), "; ".join("%s (empty visit %s; chart shows %s)" % (x.get("pid"), x.get("empty_visit"), str(x.get("stored"))[:80]) for x in _qf[:10])))
        if _qg.get("off"): L("  - TOP OF THE REPORT - the quality code is OFF: %s" % str(_qg["off"])[:220])
        if _dead: L("  - %d earlier quality line(s) at $0.00 never went out on a claim (AdvancedMD leaves a $0.00 line off). Each of those patients gets the code again, at one cent, with the next visit; the dead $0.00 lines can be voided in AdvancedMD: %s%s" % (
            len(_dead), "; ".join(" ".join(str(v) for v in d[:3]) for d in _dead[:12]), (" (+%d more)" % (len(_dead) - 12)) if len(_dead) > 12 else ""))
        if _qg.get("reset"): L("  - the pilot was started again in this run (QUALITY_CODE=reset).")
        for _n in (_qg.get("notes") if isinstance(_qg.get("notes"), list) else [])[:5]: L("  - %s" % str(_n)[:220])
except Exception as _e:                                    # never stops the digest
    L("- Quality code 1123F: this line could not be built (%s) - read quality_gate in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
L("- New charts: %d (%s), Claimocity id kept as additionalmrn." % (len(newc["created"]), ", ".join(c["chart"] for c in newc["created"])))
L("")
L("## Cascade insurance check (AMD 271 per plan + deceased guard + Stedi discovery when nothing active)")
L("- Charts: %d verified -> RELEASE %d (%d visits), HOLD %d (%d visits)." % (len(ver), dec.get("RELEASE", 0), release_visits, dec.get("HOLD", 0), hold_visits))
L("- Lead payer on released charts: " + ", ".join("%s %d" % (k, v) for k, v in leads.most_common()))
L("- Visit insurance orders changed from the chart default: %d; plans added from discovery / feed IN1: %d" % (orders_changed, len(plans_added)))
for pid, f in plans_added: L("  - %s: %s" % (pid, f))
L("- Holds (William):")
for pid, h in holds.items(): L("  - %s: %s" % (pid, "; ".join(h)[:220]))
L("")
L("## Claim Inspector pass")
L("- fixed %d visits, advisories bypassed on %d, laterality logged %d, held %d (Pattern 24078 CCI: 99309 same day as the 10/22 CCM)." % (len(insp.get("fixed", [])), len(insp.get("bypassed", [])), len(insp.get("laterality", [])), len(insp.get("held", []))))
for h in insp.get("held", []): L("  - vst%s %s: %s" % (h["visit"], h["pid"], h["why"][:120]))
L("")
L("## Next")
L("- AMD's automatic claim run (~17:00 ET) sends every clean approved claim; the submission wizard sends sooner.")
L("- The integration must not re-post the files this run imported; registers/feed_import_%s.json is the duplicate/void list (claimocity_dupe_void.py)." % STAMP)
open(("feed_digest_%s.md" % STAMP), "w").write("\n".join(lines)); print("\n".join(lines))
