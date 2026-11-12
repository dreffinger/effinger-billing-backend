# PLAIN ENGLISH: compiles the 10/28 Claimocity backlog import into one digest (counts, dollars, holds) from the registers.
# Also writes a PHI-light copy of the verify register for the repo (no addresses / member ids in the 271 result strings).
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import json, os, re, collections, datetime
POS_REPORT_VERSION = "2026-11-10.7"     # the place-of-service block below; mirror.py PROTECTED names this line - change it with every revision of the block
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
orders_changed = sum(len(v.get("saved") or []) for v in ver.values())      # 11/10/2026 (round 7): only saves really sent and accepted (the old count took every order that differed from the chart's, sent or not)
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
_qlines += sum(1 for x in reg["created"] if isinstance(x.get("mvp_codes"), list) and x.get("mvp_codes") and x.get("mvp_charge"))           # ... nor are the option code's (M0004) no-charge lines
_failed = [x for x in (reg.get("failed") or []) if isinstance(x, dict)]                      # 11/10/2026 (operations review N3): failed visits are counted and named, never "0 faults"
_finfo = lambda x: x.get("info") if isinstance(x.get("info"), dict) else {}
L("- %d visits / %d charge lines created, $%s at the fee schedule; %d encounters skipped as already in AMD; %s." % (len(reg["created"]), sum(len(x["charges"]) for x in reg["created"]) - _qlines, format(fees, ",.2f"), len(reg["skipped"]),
  ("%d visit(s) FAILED - not entered or not finished, see the import register's failed rows: %s" % (len(_failed), "; ".join("%s %s %s" % (x.get("pid") or "?", _finfo(x).get("dos") or "?", "+".join(str(c) for c in (_finfo(x).get("cpts") or [])))
   for x in _failed[:10]))) if _failed else "0 faults"))
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
        if x.get("msg_own") is False: _ps["notown"] += 1; _who["notown"].append(_tag(x) + ((" (%s)" % str(x["msg_fallback"])[:120]) if x.get("msg_fallback") else ""))      # msg_fallback: where each value its copies did not agree on came from
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
            (" (and %d kept at 31 by the back end's exception for that month - see pos_why - not held: they go out at 31 with the next claim run unless William changes them first)" % _ps["ccm31"]) if _ps["ccm31"] else "",
            _ps["nf32"], _ps["nf31"],
            (" (%d of them kept at 31 because the chart shows neither pattern - see pos_why)" % _ps["nfleft"]) if _ps["nfleft"] else "",
            (" (%d of them because the previous nursing visit was in another building)" % _ps["nfmoved"]) if _ps["nfmoved"] else "",
            ("; POS RULE NOT APPLIED on %d visit(s) - entered at the feed's place of service, see pos_err in the import register and rules.md 11/10/2026" % _ps["err"]) if _ps["err"] else "",
            ("; %d CCM / nursing-visit line(s) came from a building the facility table does not know - entered at 31 with no facility" % _ps["nofac"]) if _ps["nofac"] else "",
            ("; PLACE OF SERVICE RULE DID NOT RUN on %d visit(s) in the nursing buildings - the import helper in this workspace is an old copy (rules.md 11/10/2026)" % _ps["norule"]) if _ps["norule"] else ""))
        _names("err", "TOP OF THE REPORT - rule not applied, for William before the claim run; a routine changes nothing on these visits")
        _names("norule", "TOP OF THE REPORT - rule did not run (old helper)")
        _names("nofac", "TOP OF THE REPORT - building the facility table does not know")
        _names("ccm31", "for William, not held - CCM kept at 31 (pos_kind ccm-skilled-month)")
        _names("nfleft", "for William, not held - visits kept at 31, neither pattern shown (pos_kind extra / between)")
        if _ps["notkept"]:
            L("  - TOP OF THE REPORT - ADVANCEDMD DID NOT KEEP THE PLACE OF SERVICE on %d of %d visit(s) read back:" % (_ps["notkept"], _ps["readback"])); _names("notkept", "sent / stored")
        elif _ps["readback"]: L("  - AdvancedMD's own answer shows the place of service as sent on all %d visit(s) it echoed.%s" % (_ps["readback"], " The run still reads ONE 32 line back from the chart (runbook, 'EVERY RUN THAT ENTERS A 32 LINE')." if (_ps["ccm32"] or _ps["nf32"]) else ""))
        elif _ps["ccm32"] or _ps["nf32"]: L("  - AdvancedMD's answer did not echo the place of service: the run reads ONE 32 line back from the chart (runbook, 'EVERY RUN THAT ENTERS A 32 LINE').")
    if _ps["notown"]:
        L("- Clinician and building: %d visit(s) could not be matched to their own feed message - for what its copies do not agree on, the patient's last-read building or clinician and the admission date of the message's own last copy were used (each chart says which) - TOP OF THE REPORT, for William (a routine changes nothing on these visits):" % _ps["notown"]); _names("notown", "charts")
    if _ps["profdef"]:
        L("- Clinician: %d visit(s) whose feed message names no clinician id the profile table has were entered under the physician profile - TOP OF THE REPORT, for William (a routine changes nothing on these visits):" % _ps["profdef"]); _names("profdef", "charts")
    if _ps["nofacother"]:
        L("- Building: %d hospital / home / other visit(s) came from a building the facility table does not know and were entered with no facility at the feed's place of service - TOP OF THE REPORT, for William (a routine changes nothing on these visits):" % _ps["nofacother"]); _names("nofacother", "charts")
except Exception as _e:                                    # a register edited by hand must never stop the digest
    L("- Place of service in the nursing buildings (11/10/2026 rule): this line could not be built (%s) - read pos_lines / pos_err in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
# initial nursing-facility visits (William 11/10/2026, rules.md): every one goes in under the physician whatever clinician the feed names - one plain line, not for the top
try:
    _ini = [x for x in reg["created"] if isinstance(x, dict) and x.get("prof_feed")]
    if _ini: L("- Initial visits entered under the physician although the feed named another clinician: %d (%s). William 11/10/2026: every initial nursing-facility visit is his." % (
        len(_ini), ", ".join("%s %s" % (x.get("pid") or "?", x.get("visit") or "?") for x in _ini[:30]) + (" +%d more" % (len(_ini) - 30) if len(_ini) > 30 else "")))
except Exception as _e:
    L("- Initial visits under the physician: this line could not be built (%s) - read prof_feed in the import register." % type(_e).__name__)
# quality code (William 11/10/2026, rules.md): the advance-care-plan code 1123F that rides, at no charge, with Medicare visits of patients 65 and older.
# Everything that needs William is ONE line that starts "  - TOP OF THE REPORT - ", said in the run where it began; a state that only still
# stands (the code still OFF, a fact already reported) is a plain line - the previous import register's gate tells the two apart.
try:
    _qg = reg.get("quality_gate") if isinstance(reg.get("quality_gate"), dict) else {}
    _qc = lambda x: isinstance(x, dict) and isinstance(x.get("quality_codes"), list) and bool(x.get("quality_codes"))
    _num = lambda x: re.sub(r"\D", "", str(x or ""))
    _qa = [x for x in reg["created"] if _qc(x) and x.get("quality_charge")]                      # entered with the line
    _qn = [x for x in reg["created"] if isinstance(x, dict) and x.get("quality_not_stored")]     # the visit was stored, the line was not
    _qr = [x for x in reg["created"] if isinstance(x, dict) and x.get("quality_refused")]        # refused with the line, entered without it
    _qf = [x for x in (reg.get("failed") or []) if isinstance(x, dict) and x.get("stored") and isinstance(x.get("info"), dict) and "quality_tried" in x["info"]]   # refused, NOT sent again
    _lst = lambda k: [v for v in _qg.get(k)] if isinstance(_qg.get(k), list) else []
    _pend = [str(v) for v in _lst("pending")]; _dead = [d for d in _lst("dead_zero_lines") if isinstance(d, list)]
    _pg = {}                                                                                      # the gate of the newest import register BEFORE this batch
    try:
        _older = sorted(f for f in os.listdir("registers") if f.startswith("feed_import_") and f.endswith(".json") and not f.endswith("_decisions.json") and f < "feed_import_%s.json" % STAMP)
        _pr = json.load(open(os.path.join("registers", _older[-1]))) if _older else {}
        _pg = _pr.get("quality_gate") if isinstance(_pr, dict) and isinstance(_pr.get("quality_gate"), dict) else {}
    except Exception: _pg = {}
    _insp_rows = insp.get("held") if isinstance(insp, dict) and isinstance(insp.get("held"), list) else []
    _rem = [e for e in (insp.get("quality_removed") if isinstance(insp, dict) and isinstance(insp.get("quality_removed"), list) else []) if isinstance(e, dict)]
    _rem += [e for v in ver.values() if isinstance(v, dict) for e in (v.get("quality_removed") if isinstance(v.get("quality_removed"), list) else []) if isinstance(e, dict)]
    _rem = [e for e in _rem if str(e.get("code") or "").upper() != "M0004"]      # an entry for the option code's M0004 line is said in its own block below
    _gone = {_num(e.get("visit")) for e in _rem if e.get("void_ok") is True}
    _legacy = not (isinstance(insp, dict) and "quality_removed" in insp)                           # an inspector step older than 11/10/2026 writes no such key and marks no row
    _qvis = {_num(x.get("visit")): x for x in _qa if _num(x.get("visit"))}
    _qh = [(_qvis.get(_num(h.get("visit"))) or h, str(h.get("why") or "")[:140]) for h in _insp_rows if isinstance(h, dict) and _num(h.get("visit")) not in _gone
           and not any(_num(e.get("visit")) == _num(h.get("visit")) for e in _rem) and (h.get("quality") is True or (_legacy and _num(h.get("visit")) in _qvis))]
    _moved = [(x, (ver.get(x.get("pid")) or {}).get("lead", {}).get("code")) for x in _qa if isinstance(ver.get(x.get("pid")), dict) and ver[x.get("pid")].get("decision") == "RELEASE"
              and isinstance(ver[x.get("pid")].get("lead"), dict) and ver[x.get("pid")]["lead"].get("code") not in (None, "", "FLO02") and _num(x.get("visit")) not in _gone]
    _off = str(_qg.get("off") or ""); _lasting = str(_qg.get("off_until_reset") or ""); _notes = [str(n) for n in _lst("notes")]
    _skip_h = _qg.get("quality_skipped_hospital") if isinstance(_qg.get("quality_skipped_hospital"), int) and not isinstance(_qg.get("quality_skipped_hospital"), bool) else 0
    _unread = [str(u) for u in _lst("unread")]; _late = [r_ for r_ in _lst("late_rows") if isinstance(r_, list) and len(r_) >= 4]
    _ans = _qg.get("medicare_answer") if isinstance(_qg.get("medicare_answer"), dict) else None; _mw = _qg.get("medicare_wait") if isinstance(_qg.get("medicare_wait"), dict) else None
    _pw = _qg.get("proof_wait") if isinstance(_qg.get("proof_wait"), dict) else None; _nr = _qg.get("not_renewed") if isinstance(_qg.get("not_renewed"), dict) else {}
    if (_qa or _qn or _qr or _qf or _off or _notes or _qg.get("proof") or _qg.get("wait") or _dead or _qg.get("reset") or _rem or _skip_h or _unread or _late or _nr
            or (_qg.get("confirmed") is True and (_ans or _mw)) or _qh or _moved):
        _pf = _qg.get("proof") if isinstance(_qg.get("proof"), dict) else {}
        _days = None
        try:
            _d1 = re.search(r"(\d{8})T", re.sub(r"[^0-9TZ]", "", str(_qg.get("pending_since") or ""))); _d2 = re.search(r"(\d{8})T", _st8)
            if _d1 and _d2: _days = (datetime.datetime.strptime(_d2.group(1), "%Y%m%d") - datetime.datetime.strptime(_d1.group(1), "%Y%m%d")).days
        except Exception: _days = None
        L("- Quality code 1123F (advance care plan, Medicare measure 047; a line that pays nothing): on %d visit(s) in this batch, line amount $%s; %s." % (
            len(_qa), _qg.get("fee") or "0.00",
            "OFF until William restarts it (one run with QUALITY_CODE=reset, once the cause is fixed)" if _lasting else
            ("no line in this run (%s)" % _off[:120]) if _off else
            ("every eligible visit carries it - a quality line was seen billed to insurance (visit %s, %s)%s" % (_pf.get("visit"), _pf.get("billed"),
             "; no cap" if (_qg.get("n620") or _ans) else "; at most 10 a run until Medicare's own answer is on file")) if _qg.get("confirmed") is True and _pf else
            "every eligible visit carries it - a quality line was seen billed to insurance in an earlier run" if _qg.get("confirmed") is True else
            ("PILOT, waiting - no line was added in this run: the outcome of the first line(s) is not decided yet (%s) - the lines below say why" % ", ".join(_pend[:6])) if _qg.get("wait") else
            "PILOT - at most %s visit(s) carry it, then no more until one such line is seen billed to insurance in AdvancedMD" % (_qg.get("pilot_cap") or 3)))
        T = lambda s_: L("  - TOP OF THE REPORT - " + s_)
        if _qa: L("  - carried by: %s%s" % ("; ".join("%s %s %s" % (x.get("pid"), x.get("visit"), x.get("quality_charge") or "?") for x in _qa[:30]), (" (+%d more)" % (len(_qa) - 30)) if len(_qa) > 30 else ""))
        # OFF: in the run where it began at the top, afterwards a plain line; William's own switch is a plain line
        if _lasting and _lasting != str(_pg.get("off_until_reset") or ""): T("the quality code is OFF until William restarts it: %s. To start again (once the cause is fixed): one run with QUALITY_CODE=reset in front of the import's command." % _lasting[:220])
        elif _lasting: L("  - the quality code is still OFF (since an earlier run): %s - to start again: one run with QUALITY_CODE=reset." % _lasting[:200])
        elif _off.startswith("this run: switched off"): L("  - switched off for this run by William's QUALITY_CODE=off - no line was added.")
        elif "cannot be read - the state of the quality code is not known" in _off and _unread and not (set(_unread) & set(str(u) for u in (_qg.get("unread_prev") or []) if isinstance(_qg.get("unread_prev"), list))):
            L("  - no line in this run: the import register %s cannot be read (the visits went in as always) - if the next run says the same, it goes to the top." % ", ".join(_unread[:3]))
        elif _off and not ("cannot be read - the state of the quality code is not known" in _off and _unread): T("the quality code is OFF: %s" % _off[:220])
        for u_ in (_unread if set(_unread) & set(str(u) for u in (_qg.get("unread_prev") or []) if isinstance(_qg.get("unread_prev"), list)) else []):
            T("the import register %s cannot be read - the quality code waits until it is restored from the repository (git checkout of practices/ehpa/registers/%s, then copy it to the workspace's registers/)." % (u_, u_))
        if any(n_.startswith("NOTHING TO RESTART") for n_ in _notes): T(next(n_ for n_ in _notes if n_.startswith("NOTHING TO RESTART"))[:220])
        if _qg.get("fee") == "0.01" and _pg.get("fee") != "0.01" and not _qg.get("reset"):
            T("new quality lines now carry ONE CENT ($0.01, which CMS allows): %s. The patients whose $0.00 line was left off are due again; they get the code with a later visit of the same year%s, once the one-cent round has room (a pilot of three)." % (
                next((n_ for n_ in _notes if "$0.01" in n_ or "one cent" in n_), "AdvancedMD did not send a $0.00 line")[:180], " once William restarts the code (it is OFF)" if _lasting else ""))      # never a promise while the code is OFF, nor one for the next year (confirm review F2)
        if _qg.get("reset"): L("  - the pilot was started again in this run (QUALITY_CODE=reset): a new round at $0.00.")
        if _qa and _qg.get("confirmed") is not True: L("  - first lines: when Medicare's remittance for one of these visits arrives, remark N620 on the 1123F line shows Medicare received the code and that it is valid for the year; whether the measure is met shows only in the feedback on the Medicare quality-program site (reason 246 with it is not a denial: nothing to do, never bill the patient).")
        if _qg.get("wait") and _days is not None and _days >= 3:
            T("the quality-code pilot has waited %d days: the outcome of its first line(s) is still not decided (%s) - a visit not billed yet, a line not billed yet although its visit was, or a billed line whose code text AdvancedMD does not show (the lines below say which). Look at them in AdvancedMD and tell William - nobody takes a line off by hand (a line taken off by a person switches the code off until William restarts it)." % (_days, ", ".join(_pend[:6])))
        if _pw and isinstance(_pw.get("days"), int) and _pw["days"] >= 3:
            T("the quality line of visit %s is billed, but for %d days neither its charge detail nor the chart's history shows the code text 1123F - the pilot is not proven and waits; William looks whether AdvancedMD stores procedure id pcode65441 as 1123F." % (_pw.get("visit"), _pw["days"]))
        if _qh: T("%d visit(s) that carry the quality line are HELD by the Claim Inspector for a reason that does not name the line (the line stays on: after proof it comes off by itself only when the edit names it; the visit's own charge waits for its hold): %s" % (
            len(_qh), "; ".join("%s %s - %s" % (x.get("pid"), x.get("visit") if str(x.get("visit") or "").startswith("vst") else "vst%s" % x.get("visit"), w) for x, w in _qh[:10])))
        for e in _rem:      # William 11/10/2026: the routine takes the line off a held visit by itself
            _wv = "vst%s" % _num(e.get("visit"))
            if e.get("void_ok") is not True: T("the routine could not take the quality line off held visit %s (%s: %s) - the visit is held WITH its line; William looks. The next run switches the code off until he restarts it." % (_wv, e.get("pid"), str(e.get("note") or e.get("why") or "")[:120]))
            elif e.get("released") is True: T("the routine took the quality line %s off held visit %s (%s; the hold: %s) and the visit went through without it. That is one refusal of the line: %s" % (
                e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100], ("after proof one changes nothing; a second in a row moves new lines to one cent" if _qg.get("fee") != "0.01" else "after proof one changes nothing; a second in a row switches the code off until William restarts it") if _qg.get("confirmed") is True else
                ("the next run moves new lines to one cent and starts a new round" if _qg.get("fee") != "0.01" else "the next run switches the code off until William restarts it")))
            elif e.get("still_named") is True or e.get("resave_ok") is False: T("the routine took the quality line %s off held visit %s (%s), but the visit is still listed for the edit about the line (%s)%s - William looks: one re-save of the visit should release it. The next run switches the code off until he restarts it." % (
                e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100], "; the re-save after the void failed" if e.get("resave_ok") is False else ""))      # not the visit's own reason (confirm review NH2-2)
            else: T("the routine took the quality line %s off held visit %s (%s), but the visit is still held for its own reason (%s) - its place in the round is free and the patient is due again; the visit's own hold is listed under Claim Inspector pass." % (e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100]))
        if _qr: T("QUALITY CODE NOT ACCEPTED by AdvancedMD on %d visit(s); each visit was entered without it: %s - these patients are not tried again this year." % (len(_qr), "; ".join("%s %s (%s)" % (x.get("pid"), x.get("visit"), str(x.get("quality_refused"))[:80]) for x in _qr[:10])))
        if _qn: T("AdvancedMD stored %d visit(s) WITHOUT the quality line that was sent with it (the visit itself is entered): %s" % (len(_qn), "; ".join("%s %s" % (x.get("pid"), x.get("visit")) for x in _qn[:10])))
        if _qf: T("%d visit(s) were refused with the quality line and NOT sent again, because the chart shows part of the visit or could not be read - check that visit (for William; no routine sends it again): %s" % (
            len(_qf), "; ".join("%s %s %s (visit %s; the chart shows %s)" % (x.get("pid"), x["info"].get("dos") or "?", "+".join(str(c) for c in (x["info"].get("cpts") or [])), x.get("empty_visit"), str(x.get("stored"))[:80]) for x in _qf[:10]))
            + " - the insurance check and the Claim Inspector step did not look at these visits.")      # never "empty": the chart shows what it holds (confirm review NH2-5)
        _qs = [x for x in (reg.get("failed") or []) if isinstance(x, dict) and x.get("quality_sent")]      # refused with the line, and the send WITHOUT it ended in an error (confirm review NH2-4)
        if _qs: T("%d visit(s) were refused with the quality line and the send without it ended in an error - such a visit may NOT be entered: William checks it (no routine sends it again): %s" % (
            len(_qs), "; ".join("%s %s %s (visit %s)" % (x.get("pid"), _finfo(x).get("dos") or "?", "+".join(str(c) for c in (_finfo(x).get("cpts") or [])), x.get("empty_visit")) for x in _qs[:10])))
        if _qg.get("history_shows_line") is False and _pg.get("history_shows_line") is not False:
            T("the chart history does NOT list the proven quality line: a 1123F or 1124F entered by hand is invisible to the import - William names such patients in registers/quality_exceptions.json.")
        for _y, _n in sorted(_nr.items()): T("the quality code is not added to %s visits until William renews it (%s visit(s) of this batch would otherwise carry it)." % (_y, _n))
        if _moved: L("  - %d quality line(s) of this batch rode on visits the insurance check moved to another payer than Medicare: %s - that line went to that payer; nothing to do (such a line is never the pilot's proof)." % (
            len(_moved), "; ".join("%s %s -> %s" % (x.get("pid"), x.get("visit"), c_) for x, c_ in _moved[:10])))
        if _ans and not (isinstance(_pg.get("medicare_answer"), dict) and _pg["medicare_answer"].get("charge") == _ans.get("charge")):
            L("  - Medicare's remittance shows the 1123F line on visit %s, paid $%s on %s: the code reached Medicare on the claim and came back on its remittance (whether the measure is met shows only in the feedback on the Medicare quality-program site); the daily cap is lifted." % (_ans.get("visit"), _ans.get("amount"), _ans.get("date")))
        elif _qg.get("confirmed") is True and not _ans and not _qg.get("n620") and _mw:
            # say exactly what is known (confirm reviews F6, W-3): only the pilot's lines are read back, and the import sees Medicare's answer only as a payment line AdvancedMD posts on such a line
            _t = "%s of the pilot's quality lines are read as billed (lines added after proof are not read back); no Medicare payment line is posted on them yet (the oldest billed %s, %s day(s) ago) - the import reads up to six of them each run for a Medicare payment line and lifts the cap of ten a run when one shows. A second way: when a Medicare remittance for one of these visits shows the 1123F line (reason 246, remark N620), tell William, then: echo '{\"seen\": \"<date>\"}' > registers/quality_n620_seen.json" % (
                _mw.get("lines"), _mw.get("oldest") or "?", _mw.get("days") if _mw.get("days") is not None else "?")
            if isinstance(_mw.get("days"), int) and _mw["days"] >= 45: T("no Medicare payment line is posted on the pilot's billed 1123F lines after 45 days - William looks at one remittance. " + _t)
            else: L("  - " + _t)
        if _dead: L("  - %d quality line(s) were read as left off their claims (each visit went out without its line, still so three days later; such a line is read again for 30 days): %s%s - listed for William; no routine voids them. Their patients are due again: %s." % (
            len(_dead), "; ".join(" ".join(str(v) for v in d[:3]) for d in _dead[:12]), (" (+%d more)" % (len(_dead) - 12)) if len(_dead) > 12 else "",
            # never a promise while the code is OFF, nor one that falls into the next year (confirm reviews F2, W-1)
            "the code is OFF until William restarts it - no line is added before then; after the restart a later eligible visit of the same year carries the code" if _lasting else
            "a later eligible visit of the same year carries the code (a line of an earlier year is not replaced by a visit of the new year)"))
        for r_ in _late: L("  - a quality line read as left off on %s was billed later: %s counts as coded%s." % (r_[3], r_[0], ("; %s carries two billed quality lines for %s (the later one on %s); nothing to do" % (r_[0], r_[5] if len(r_) > 5 else "the year", r_[4])) if len(r_) > 4 and r_[4] else ""))
        if _skip_h: L("  - %d hospital visit(s) of Medicare patients 65 and older did not get the quality line: hospital visits are not coded in this version (William decides for 2027)." % _skip_h)
        for _n in [n_ for n_ in _notes if not n_.startswith("NOTHING TO RESTART") and "started again in this run" not in n_][:5]: L("  - %s" % _n[:220])
except Exception as _e:                                    # never stops the digest
    L("- Quality code 1123F: this line could not be built (%s) - read quality_gate in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
# the option code M0004 (William 11/10/2026, about M0004: "use it"; rules.md): its own no-charge line, once per clinician per year, on a visit that carries the
# 1123F line once that line is proven. Its ledger is the import register's "mvp_gate". Everything that needs William is ONE line "  - TOP OF THE REPORT - ",
# said in the run where it began (the previous import register's mvp_gate tells); from December 1 a clinician without an M0004 line is at the top every run.
try:
    _mg = reg.get("mvp_gate") if isinstance(reg.get("mvp_gate"), dict) else {}
    _qg2 = reg.get("quality_gate") if isinstance(reg.get("quality_gate"), dict) else {}
    _mpg = {}
    try:
        _mold = sorted(f for f in os.listdir("registers") if f.startswith("feed_import_") and f.endswith(".json") and not f.endswith("_decisions.json") and f < "feed_import_%s.json" % STAMP)
        _mpr = json.load(open(os.path.join("registers", _mold[-1]))) if _mold else {}
        _mpg = _mpr.get("mvp_gate") if isinstance(_mpr, dict) and isinstance(_mpr.get("mvp_gate"), dict) else {}
    except Exception: _mpg = {}
    _mnum = lambda x: re.sub(r"\D", "", str(x or ""))
    _mlst = lambda k: [v for v in _mg.get(k)] if isinstance(_mg.get(k), list) else []
    _ma = [x for x in reg["created"] if isinstance(x, dict) and isinstance(x.get("mvp_codes"), list) and x.get("mvp_codes") and x.get("mvp_charge")]      # entered with the M0004 line
    _mr = [x for x in reg["created"] if isinstance(x, dict) and x.get("mvp_refused")]                                                                   # refused with it, entered with the 1123F line only
    _mns = [x for x in reg["created"] if isinstance(x, dict) and x.get("mvp_not_stored")]                                                               # stored without it
    _mrem = [e for e in (insp.get("quality_removed") if isinstance(insp, dict) and isinstance(insp.get("quality_removed"), list) else []) if isinstance(e, dict) and str(e.get("code") or "").upper() == "M0004"]
    _mrem += [e for v in ver.values() if isinstance(v, dict) for e in (v.get("quality_removed") if isinstance(v.get("quality_removed"), list) else []) if isinstance(e, dict) and str(e.get("code") or "").upper() == "M0004"]
    _mcl = {k: v for k, v in (_mg.get("clinicians").items() if isinstance(_mg.get("clinicians"), dict) else ()) if isinstance(v, dict)}
    _moff = str(_mg.get("off") or ""); _mlast = str(_mg.get("off_until_reset") or ""); _mnotes = [str(n) for n in _mlst("notes")]
    _mans = {k: v for k, v in (_mg.get("answer").items() if isinstance(_mg.get("answer"), dict) else ()) if isinstance(v, dict)}
    _mlo = [str(c) for c in _mlst("left_off_lines")]; _mlate = [r_ for r_ in _mlst("late_rows") if isinstance(r_, list) and len(r_) >= 5]
    _WHO = {"prof13": "prof13 (the physician)", "prof15": "prof15 (the nurse practitioner)"}
    _st = lambda p_: str((_mcl.get(p_) or {}).get("state") or "not yet")
    _dec = bool(re.match(r"^\d{8}T", _st8)) and _st8[4:6] == "12"      # a batch of December: the registration year ends on the 31st
    if _mg and (_ma or _mr or _mns or _mrem or _mlast or _moff or _mnotes or _mlo or _mlate or _qg2.get("confirmed") is True or any(_st(p_) != "not yet" for p_ in _mcl)):
        L("- Option code M0004 (Quality Care for Patients with Neurological Conditions - the option the group and both clinicians are registered for; William 11/10/2026: \"use it\"; a line that pays nothing, once per clinician, on a claim that carries 1123F): on %d visit(s) in this batch; %s; %s." % (
            len(_ma), "; ".join("%s: %s" % (_WHO.get(p_, p_), _st(p_)) for p_ in sorted(_mcl)) or "no clinician known yet",
            "OFF until William restarts it (one run with MVP_CODE=reset, once the cause is fixed)" if _mlast else ("no M0004 line in this run (%s)" % _moff[:120]) if _moff else
            "it rides with the next eligible visit of a clinician who has none" if _qg2.get("confirmed") is True else "it rides only once the quality code is proven"))
        T2 = lambda s_: L("  - TOP OF THE REPORT - " + s_)
        if _ma: L("  - M0004 carried by: %s" % "; ".join("%s %s %s (%s)" % (x.get("pid"), x.get("visit"), x.get("mvp_charge"), x.get("mvp_prof") or "?") for x in _ma[:10]))
        if _mlast and _mlast != str(_mpg.get("off_until_reset") or ""): T2("the option code M0004 is OFF until William restarts it: %s. The 1123F line goes on as before. To start M0004 again (once the cause is fixed): one run with MVP_CODE=reset in front of the import's command." % _mlast[:220])
        elif _mlast: L("  - the option code M0004 is still OFF (since an earlier run): %s - to start it again: one run with MVP_CODE=reset." % _mlast[:200])
        elif _moff.startswith("this run: switched off (MVP_CODE=off)"): L("  - M0004 switched off for this run by William's MVP_CODE=off - no M0004 line was added.")
        elif "MVP_CODE=" in _moff: T2("the option code M0004 is off in this run: %s" % _moff[:220])
        if any(n_.startswith("NOTHING TO RESTART") for n_ in _mnotes): T2(next(n_ for n_ in _mnotes if n_.startswith("NOTHING TO RESTART"))[:220])
        if _mg.get("reset") is True: L("  - the option code M0004 was started again in this run (MVP_CODE=reset).")
        if _mr: T2("AdvancedMD refused %d visit(s) that carried M0004; each was entered with the 1123F line only: %s - M0004 is OFF until William restarts it (no second try)." % (len(_mr), "; ".join("%s %s (%s)" % (x.get("pid"), x.get("visit"), str(x.get("mvp_refused"))[:80]) for x in _mr[:5])))
        if _mns: T2("AdvancedMD stored %d visit(s) WITHOUT the M0004 line that was sent with it (the visit itself is entered): %s - M0004 is OFF until William restarts it." % (len(_mns), "; ".join("%s %s" % (x.get("pid"), x.get("visit")) for x in _mns[:5])))
        for e in _mrem:      # William 11/10/2026: the routine takes a no-charge line off a held visit by itself (11.6)
            _wv = "vst%s" % _mnum(e.get("visit"))
            if e.get("void_ok") is not True: T2("the routine could not take the M0004 line off held visit %s (%s: %s) - the visit is held WITH that line; William looks. The next run switches M0004 off until he restarts it." % (_wv, e.get("pid"), str(e.get("note") or e.get("why") or "")[:120]))
            elif e.get("with") == "1123F": L("  - the M0004 line %s of visit %s (%s) came off together with its 1123F line (M0004 never rides without it) - that clinician may get M0004 again." % (e.get("charge"), _wv, e.get("pid")))      # confirm review NH2-1
            elif e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False): T2("the routine took the M0004 line %s off held visit %s (%s), but the visit is still listed for the edit about the line (%s)%s - William looks: one re-save of the visit should release it. The next run switches M0004 off until he restarts it." % (
                e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100], "; the re-save after the void failed" if e.get("resave_ok") is False else ""))      # confirm review NH2-2, the same for M0004 (8.6)
            elif e.get("released") is True: T2("the routine took the M0004 line %s off held visit %s (%s; the hold: %s) and the visit went through without it: M0004 is OFF until William restarts it (no second try); this does not count against the 1123F line." % (e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100]))
            else: T2("the routine took the M0004 line %s off held visit %s (%s), but the visit is still held for its own reason (%s) - its clinician may get M0004 again; the visit's own hold is listed under Claim Inspector pass." % (e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100]))
        _billed = [p_ for p_ in sorted(_mcl) if _st(p_) == "billed"]
        if _billed: L("  - Medicare's answer for M0004: %s (a posted Medicare payment line on the M0004 line shows the code reached Medicare on the claim; whether the measure is met shows only in the feedback on the Medicare quality-program site)." % "; ".join(
            ("Medicare's remittance shows the M0004 line for %s (visit %s, $%s on %s)" % (p_, (_mans[p_].get("visit") or "?"), _mans[p_].get("amount") or "?", _mans[p_].get("date") or "?")) if p_ in _mans else ("not yet for %s (its line billed %s)" % (p_, (_mcl.get(p_) or {}).get("billed") or "?")) for p_ in _billed))
        if _mlo: L("  - %d M0004 line(s) were read as left off their claims (each visit went out without it, still so three days later; such a line is read again for 30 days): %s - listed for William; no routine voids them. That clinician gets M0004 once more; a second left-off line switches M0004 off until William restarts it." % (len(_mlo), ", ".join(_mlo[:6])))
        for r_ in _mlate: L("  - an M0004 line read as left off on %s was billed later: %s counts as done for %s%s." % (r_[4], r_[0], r_[6] if len(r_) > 6 else "the year", ("; %s carries two billed M0004 lines (the later one on %s); nothing to do" % (r_[0], r_[5])) if len(r_) > 5 and r_[5] else ""))
        if _dec:
            for p_ in sorted(_mcl):
                if _st(p_) not in ("billed", "waiting"): T2("%s has no M0004 line billed or waiting for %s - the year ends December 31 (M0004 must be on at least one of that clinician's Medicare claims that carries 1123F)%s." % (
                    _WHO.get(p_, p_), (_mcl.get(p_) or {}).get("year") or "the year", (": M0004 is OFF until William restarts it - " + _mlast[:120]) if _mlast else ""))
        for _n in [n_ for n_ in _mnotes if not n_.startswith("NOTHING TO RESTART") and "started again in this run" not in n_][:5]: L("  - %s" % _n[:220])
except Exception as _e:                                    # never stops the digest
    L("- Option code M0004: this line could not be built (%s) - read mvp_gate in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
L("- New charts: %d (%s), Claimocity id kept as additionalmrn." % (len(newc["created"]), ", ".join(c["chart"] for c in newc["created"])))
L("")
L("## Cascade insurance check (AMD 271 per plan + deceased guard + Stedi discovery when nothing active)")
L("- Charts: %d verified -> RELEASE %d (%d visits), HOLD %d (%d visits)." % (len(ver), dec.get("RELEASE", 0), release_visits, dec.get("HOLD", 0), hold_visits))
# 11/10/2026 (round 7): what the insurance check could not confirm on a visit's insurance-order LIST (a claim is built from the list; a visit entered
# while its chart had no plan reads insorder "1" over an EMPTY list and is never billed). Each is ONE line that starts "  - TOP OF THE REPORT - ".
_HELD = "HELD in this report only - AdvancedMD will still bill this visit to its insurance order at the next claim run unless someone stops it"
_NOCLAIM = "HELD in this report only - AdvancedMD makes no claim for this visit until it is saved again with its plan in place"      # the ending of a chart whose visits have an empty insurance order
try:
    _ov = lambda key: [(p_, x_) for p_, v_ in ver.items() if isinstance(v_, dict) for x_ in (v_.get(key) if isinstance(v_.get(key), list) else [])]
    _who2 = lambda rows: ", ".join("%s %s" % (p_, x_) for p_, x_ in rows[:40]) + (" +%d more" % (len(rows) - 40) if len(rows) > 40 else "")
    _nol, _dif, _unr, _svp = _ov("no_order_list"), _ov("order_differs"), _ov("order_unread"), _ov("save_problem")
    _nop = [(p_, v_) for p_, v_ in ver.items() if isinstance(v_, dict) and v_.get("decision") == "HOLD" and any(str(h_).startswith("no open plan on this chart") for h_ in v_.get("hold") or [])]
    if _nol: L("  - TOP OF THE REPORT - NO CLAIM CAN BE MADE: %d visit(s) on %d chart(s) have no insurance order: %s" % (len(_nol), len({p_ for p_, _x in _nol}), _who2(_nol)))
    if _nop: L("  - TOP OF THE REPORT - %d chart(s) held with NO plan: each visit of such a chart must be saved again after a plan is added (a plan alone builds no insurance order): %s" % (
        len(_nop), ", ".join("%s (%s)" % (p_, " ".join(v_.get("visits") or [])) for p_, v_ in _nop[:20]) + (" +%d more" % (len(_nop) - 20) if len(_nop) > 20 else "")))
    if _dif: L("  - TOP OF THE REPORT - OLD INSURANCE ORDER: %d visit(s) on %d chart(s) still bill to their old insurance order (or are already billed) - %s: %s" % (len(_dif), len({p_ for p_, _x in _dif}), _HELD, _who2(_dif)))
    if _unr: L("  - TOP OF THE REPORT - INSURANCE ORDER NOT READ: %d visit(s) on %d chart(s) - %s: %s" % (len(_unr), len({p_ for p_, _x in _unr}), _HELD, _who2(_unr)))
    if _svp: L("  - TOP OF THE REPORT - SAVE NOT AS ASKED: %d visit(s) on %d chart(s) - the order reads right but the save lost a charge or the admission date (see the hold line): %s" % (len(_svp), len({p_ for p_, _x in _svp}), _who2(_svp)))
except Exception as _e:                                    # never stops the digest
    L("  - TOP OF THE REPORT - the insurance-order lines could not be built (%s) - read no_order_list / order_differs / order_unread / save_problem in the insurance-check register." % type(_e).__name__)
L("- Lead payer on released charts: " + ", ".join("%s %d" % (k, v) for k, v in leads.most_common()))
L("- Visit insurance orders changed (saves sent and accepted by AdvancedMD): %d; plans added from discovery / feed IN1: %d" % (orders_changed, len(plans_added)))
for pid, f in plans_added: L("  - %s: %s" % (pid, f))
L("- Holds (William) - %s (a visit whose insurance order is empty bills nothing until it is saved again):" % _HELD)
for pid, h in holds.items(): L("  - %s: %s%s%s" % (pid, "; ".join(str(x).replace(" - " + _HELD, "").replace(" - " + _NOCLAIM, "") for x in h)[:400], (" - " + _HELD) if any(_HELD in str(x) for x in h) else "",
                                (" - " + _NOCLAIM) if any(_NOCLAIM in str(x) for x in h) else ""))      # each ending said once; a chart with no plan (empty insurance orders) gets the NO CLAIM words
L("")
L("## Claim Inspector pass")
L("- fixed %d visits, advisories bypassed on %d, laterality logged %d, held %d (Pattern 24078 CCI: 99309 same day as the 10/22 CCM)." % (len(insp.get("fixed", [])), len(insp.get("bypassed", [])), len(insp.get("laterality", [])), len(insp.get("held", []))))
for h in insp.get("held", []): L("  - vst%s %s: %s" % (h["visit"], h["pid"], h["why"][:120]))
L("")
L("## Next")
L("- AMD's automatic claim run (~17:00 ET) sends every clean approved claim; the submission wizard sends sooner.")
L("- The integration must not re-post the files this run imported; registers/feed_import_%s.json is the duplicate/void list (claimocity_dupe_void.py)." % STAMP)
open(("feed_digest_%s.md" % STAMP), "w").write("\n".join(lines)); print("\n".join(lines))
