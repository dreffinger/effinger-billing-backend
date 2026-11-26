# PLAIN ENGLISH: compiles the 10/28 Claimocity backlog import into one digest (counts, dollars, holds) from the registers.
# Also writes a PHI-light copy of the verify register for the repo (no addresses / member ids in the 271 result strings).
# Diagnosis codes AdvancedMD's own list does not have (William 11/25/2026: "for any diagnosis not in the master file yet change it to i10 and send me an
#   email with the codes needed to be added"): when created rows of the batch name such codes (missing_dx; dx_instead = what the import put in their place)
#   the digest gets ONE line - the visits, each code with its number of visits, 'EMAIL WILLIAM: <file>' - and this helper WRITES the text of that email to
#   outbox/dx_codes_needed_<STAMP>.txt: the codes, their visits, chart numbers and dates of service, no patient name. A row whose code was left off (an import
#   from before that day) is said to be entered WITHOUT the code, never with I10. No such code in the batch: no line, no file.
# Which chart, birth dates, the rehab unit (William 11/25/2026) - three parts near the end, each from a register, each chart ids and fixed words only:
#   'Which chart' from registers/feed_identity_<STAMP>.json (the ingest writes it): how many feed patients the map knew, how many were looked up and by
#   which rule, and - at the TOP OF THE REPORT - every line that is for William (a new chart beside same-name charts, a new chart with no birth date, a
#   patient nobody could decide, a new chart that could not be made, a file that stays unregistered). A word in that register that is not one of the
#   identity rule's fixed words is never printed. 'Birth dates': ONE line from the import's rows (dob_note) - where the feed's date and the chart's differ.
#   'Feed messages that could not be read': the parse step's register (feed_unreadable_<stamp>.json) - at the top, with what to do.
# No visit of the feed is lost without a word (11/25/2026, the independent verification - each line below was missing, or was wrong, at the top):
#   - every FAILED row of the import: a visit AdvancedMD refused at entry (nothing was made - its file stays unregistered and is tried again) and a visit
#     whose entry did not finish (for William; no routine sends it again). Until then a failed visit stood in a body line only.
#   - a message that could not be read: the file is NOT REGISTERED and every start reads it again - what ends it is said (the whole file in the bucket,
#     or William's word). The line no longer says 'the next ingest reads it when it arrives': a file sent again under its own name was never read.
#   - a name-and-date key several Claimocity ids share: EVERY id is named, with the chart it has through a key of its own (the line named the first id
#     alone - the one whose visit had gone in), and the count line counts patients, not rows.
#   - the driver's own lines (the identity register's notes), and what is for William about a new chart the identity register does not list.
#   The two lines from the insurance check's file (SAME PERSON? / NO BIRTH DATE ON EITHER SIDE) print a record only when its key is a chart id, and of
#   its list only what is a visit id.
#   'Inpatient rehab': the visits entered at HCA REHAB / place of service 61, the ones kept at 21, each new rehab stay by chart and date, and at the top
#   every rehab visit the Claim Inspector questions (the inspector step's own sentence, whole).
# Decides nothing and changes nothing in AdvancedMD; it sends no email itself - the line 'EMAIL WILLIAM: <file>' is the cue for the run that reads the digest.
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import json, os, re, collections, datetime
POS_REPORT_VERSION = "2026-11-25.5"     # the place-of-service block below; mirror.py PROTECTED names this line - change it with every revision of the block
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
_T = lambda s_: L("  - TOP OF THE REPORT - " + s_)
_pat_ok = lambda c_: c_ if isinstance(c_, str) and re.fullmatch(r"pat[0-9]+", c_) else ""
_fid_ok = lambda i_: i_ if isinstance(i_, str) and re.fullmatch(r"[0-9A-Fa-f]{24}", i_) else "(an id that is not 24 hex characters)"
_idf = "registers/feed_identity_%s.json" % STAMP      # the ingest's identity register: which chart, and the files it keeps unregistered
try:
    _IDR = json.load(open(_idf)) if os.path.isfile(_idf) else {}
    if not isinstance(_IDR, dict): _IDR = {}
except Exception: _IDR = {}      # (the 'Which chart' part below says when it cannot be read)
def _held(key):      # the file names of one of the register's lists - a name of another shape is never printed
    return [f_ for f_ in (_IDR.get(key) if isinstance(_IDR.get(key), list) else []) if isinstance(f_, str) and re.fullmatch(r"[0-9A-Za-z_.\-]{1,80}", f_)]
_fnames = lambda fs_: ", ".join(fs_[:20]) + ((" +%d more" % (len(fs_) - 20)) if len(fs_) > 20 else "")
L("# Claimocity backlog import - digest %s UTC (chat session, William 10/28 02:23 ET: enter all encounters and bill them out)" % datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M"))
L("")
L("## Import")
_qlines = sum(1 for x in reg["created"] if isinstance(x.get("quality_codes"), list) and x.get("quality_codes") and x.get("quality_charge"))    # no-charge quality lines are not charge lines
_qlines += sum(1 for x in reg["created"] if isinstance(x.get("mvp_codes"), list) and x.get("mvp_codes") and x.get("mvp_charge"))           # ... nor are the option code's (M0004) no-charge lines
_failed = [x for x in (reg.get("failed") or []) if isinstance(x, dict)]                      # 11/10/2026 (operations review N3): failed visits are counted and named, never "0 faults"
_finfo = lambda x: x.get("info") if isinstance(x.get("info"), dict) else {}
# 11/25/2026 (the second verification of the death check): the visits the import kept out because a date of death is on record for the chart and nobody could name
# its day (claimocity_import.DEATH_DAY_WHY - the same line here; the self-test holds the two together). Chart ids and counts only.
# (The independent check of that round, finding 13: the count below called those visits 'skipped as already in AMD' - they are NOT in AdvancedMD, they are held. They
# are taken out of that count; the line for the top of the report, a few lines down, says what they are. The sentence's words are as they were.)
DEATH_DAY_WHY = "a date of death is on record for this chart but its day cannot be read - not entered"
# 11/25/2026 (the fourth round of the death check): the import's second fixed why (the same line there) - the record of a death for the chart was reset on the
# owner's word and Medicare has not answered the fresh question yet. Those visits are held too, not 'already in AMD': a line of their own for the top, below.
DEATH_RESET_WHY = "the record of a death for this chart was reset on the owner's word and Medicare has not answered yet - not entered"
_ddheld = sum(1 for x in (reg.get("skipped") or []) if isinstance(x, dict) and str(x.get("why") or "").startswith((DEATH_DAY_WHY, DEATH_RESET_WHY)))
L("- %d visits / %d charge lines created, $%s at the fee schedule; %d encounters skipped as already in AMD; %s." % (len(reg["created"]), sum(len(x["charges"]) for x in reg["created"]) - _qlines, format(fees, ",.2f"), len(reg["skipped"]) - _ddheld,
  ("%d visit(s) FAILED - not entered or not finished, see the import register's failed rows: %s" % (len(_failed), "; ".join("%s %s %s" % (x.get("pid") or "?", _finfo(x).get("dos") or "?", "+".join(str(c) for c in (_finfo(x).get("cpts") or [])))
   for x in _failed[:10]))) if _failed else "0 faults"))
# 11/25/2026 (the verification): every failed row stands at the TOP too. It was named in the line above only, its file was registered as done and the visit
# was never tried again. A visit AdvancedMD REFUSED at its first call (the import's row 'addvisit: ...' - no visit was made) keeps its file unregistered - the
# ingest says which in the identity register - and the next start tries again. Every other failed row (a visit was made and its charges were refused, an error,
# a call nobody saw the end of) is for William: no routine sends it again. Chart ids, dates of service, codes and visit ids only - AdvancedMD's own words stay
# in the import register.
try:
    if _failed:
        _dos_ok = lambda d_: d_ if isinstance(d_, str) and re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", d_) else ""
        _cpt_ok = lambda c_: [x_ for x_ in (c_ if isinstance(c_, list) else []) if isinstance(x_, str) and re.fullmatch(r"[A-Za-z0-9]{5}", x_)]
        def _fwhat(x):      # chart, date of service and codes of a failed row: from its info, else from the lines the feed showed
            _ln = [l_ for l_ in (x.get("lines") if isinstance(x.get("lines"), list) else []) if isinstance(l_, list) and len(l_) >= 2]
            _d = _dos_ok(_finfo(x).get("dos")) or next((_dos_ok(l_[1]) for l_ in _ln if _dos_ok(l_[1])), "") or "date ?"
            return "%s %s %s" % (_pat_ok(x.get("pid")) or "chart ?", _d, "+".join(_cpt_ok(_finfo(x).get("cpts")) or _cpt_ok([l_[0] for l_ in _ln])) or "code ?")
        _nomade = lambda x: isinstance(x.get("err"), str) and x["err"].startswith("addvisit:") and not x.get("empty_visit")
        _fa = [x for x in _failed if _nomade(x)]; _fo = [x for x in _failed if not _nomade(x)]
        _fsome = lambda it_: "; ".join(it_[:15]) + ((" +%d more" % (len(it_) - 15)) if len(it_) > 15 else "")
        if _fa:
            _hr, _ha = _held("not_registered_refused"), _held("registered_anyway_refused")      # the files kept back, and the files registered on William's word, FOR A REFUSED VISIT (the ingest keeps the two causes apart)
            _again = "the next start reads it again and the import tries once more (a visit entered by hand meanwhile answers 'already')"
            _T("%d visit(s) AdvancedMD REFUSED at entry are NOT on the chart: %s - nothing of them was made in AdvancedMD%s" % (len(_fa), _fsome([_fwhat(x) for x in _fa]),
               ("; of their files, NOT REGISTERED: %s - %s; REGISTERED ON WILLIAM'S WORD: %s - its refused visit is given up and not tried again" % (_fnames(_hr), _again, _fnames(_ha))) if _hr and _ha else
               ("; their file is NOT REGISTERED (%s): %s" % (_fnames(_hr), _again)) if _hr else
               ("; their file was REGISTERED ON WILLIAM'S WORD (%s): they are given up and not tried again" % _fnames(_ha)) if _ha else " (AdvancedMD's answer is in the failed rows of the import register)"))
        if _fo:
            _vmade = lambda x: ("visit vst%s was made" % re.sub(r"\D", "", str(x.get("empty_visit")))) if re.sub(r"\D", "", str(x.get("empty_visit") or "")) else "an error while it was entered"
            _T("%d visit(s) whose entry did NOT FINISH - for William, to look at in AdvancedMD (nobody knows what AdvancedMD kept of them; no routine sends them again): %s" % (len(_fo), _fsome(["%s (%s)" % (_fwhat(x), _vmade(x)) for x in _fo])))
except Exception as _e:                                    # never stops the digest
    L("  - TOP OF THE REPORT - the failed visits of this batch could not be listed (%s) - read the failed rows of registers/feed_import_%s.json" % (type(_e).__name__, STAMP))
L("- CPT mix: " + ", ".join("%s x%d" % (k, v) for k, v in cpts.most_common()))
try:      # (the register cannot say who was asked - a dry run asks nobody, a workspace may hold no guard - so the line says 'nobody named the day', as the import's own does)
    _ddr = [x for x in (reg.get("skipped") or []) if isinstance(x, dict) and str(x.get("why") or "").startswith(DEATH_DAY_WHY)]
    _ddc = sorted({x.get("pid") for x in _ddr if isinstance(x.get("pid"), str) and re.fullmatch(r"pat[0-9]+", x.get("pid"))})
    if _ddr: L("  - TOP OF THE REPORT - DEATH DAY UNKNOWN: %d visit(s) on %d chart(s) were NOT entered - a date of death is on record for the chart, its day cannot be read in this workspace and nobody named the day. Merge the deceased cache from Drive (the Button's step 0c); the retry step hands each visit to the import again once a run, until a register shows it entered or kept out for good: %s" % (
        len(_ddr), len(_ddc), ", ".join(_ddc) or "(no chart id in the rows)"))
except Exception: L("  - TOP OF THE REPORT - the line about visits kept out for a date of death nobody could read could not be built - read the skipped rows of the import register.")
try:      # (the fourth round) the visits held because the record of a death was reset on the owner's word and Medicare has not answered - chart ids and counts only
    _drr = [x for x in (reg.get("skipped") or []) if isinstance(x, dict) and str(x.get("why") or "").startswith(DEATH_RESET_WHY)]
    _drc = sorted({x.get("pid") for x in _drr if isinstance(x.get("pid"), str) and re.fullmatch(r"pat[0-9]+", x.get("pid"))})
    if _drr: L("  - TOP OF THE REPORT - DEATH RECORD RESET: %d visit(s) on %d chart(s) were NOT entered - the record of a death for the chart was reset on the owner's word (death_off_record.py) and Medicare has not answered yet. Medicare is asked again at the chart's next claim and its answer decides; the retry step hands each visit to the import again once a run, until a register shows it entered or kept out for good: %s" % (
        len(_drr), len(_drc), ", ".join(_drc) or "(no chart id in the rows)"))
except Exception: L("  - TOP OF THE REPORT - the line about visits kept out because the record of a death was reset could not be built - read the skipped rows of the import register.")
# place of service in the nursing buildings (William 11/10/2026, rules.md): what the import's per-line rule did in this batch
_ps = collections.Counter(); _NFV = {"99304", "99305", "99306", "99307", "99308", "99309", "99310", "99315", "99316"}; _CCM = {"99487", "99489"}
_NURSING_FAC = {"fac34", "fac32", "fac33", "fac58", "fac1350"}                       # Brynwood, Aspire, Centre Pointe, Westminster Oaks-Bertrand, Oakes Southwood
_st8 = re.sub(r"[^0-9TZ]", "", STAMP)                                               # 2026-11-10T1319Z and 20261110T1319Z are the same batch
_rule_stamp = bool(re.match(r"^2\d{7}T", _st8)) and _st8[:8] >= "20261110"          # batches from the day the rule began
_who = collections.defaultdict(list)                                                  # what kind of line -> the charts (chart number, date, codes - no name)
def _tag(x): return "%s %s %s" % (x.get("pid") or "?", x.get("dos") or "?", "+".join(str(c) for c in (x.get("cpts") or [])))
def _names(key, lead, cap=30):      # cap=None names EVERY chart (11/25/2026: the two CCM lists below); the other lists show the first 30 and say how many more the import register holds
    v = _who.get(key) or []
    if v: L("  - %s: %s%s" % (lead, "; ".join(v if cap is None else v[:cap]), (" (+%d more - see the import register)" % (len(v) - cap)) if (cap is not None and len(v) > cap) else ""))
_bld = collections.Counter()                                                           # the feed's own name of a building the facility table does not know -> visits (11/25/2026)
try:
    for x in reg["created"]:
        _c = x.get("cpts") or []
        if not x.get("fac") and isinstance(x.get("feed_building"), str) and x["feed_building"].strip(): _bld[x["feed_building"].strip()] += 1
        if x.get("msg_own") is False: _ps["notown"] += 1; _who["notown"].append(_tag(x) + ((" (%s)" % str(x["msg_fallback"])[:120]) if x.get("msg_fallback") else ""))      # msg_fallback: where each value its copies did not agree on came from
        if x.get("prof_default") is True: _ps["profdef"] += 1; _who["profdef"].append(_tag(x))
        if "pos_lines" in x and not x.get("fac") and not any(c in _NFV or c in _CCM for c in _c): _ps["nofacother"] += 1; _who["nofacother"].append(_tag(x))      # CCM / nursing lines are named in the block below
        if x.get("pos_stored") is not None and x.get("pos_lines"):
            _ps["readback"] += 1
            _qdiff = bool(x.get("quality_pos_stored")) and bool(x.get("quality_pos")) and str(x["quality_pos_stored"]) != str(x["quality_pos"])      # the quality line's own place of service
            if sorted(str(v) for v in x["pos_stored"]) != sorted(str(v) for v in x["pos_lines"]) or _qdiff: _ps["notkept"] += 1; _who["notkept"].append("%s sent %s stored %s%s" % (_tag(x), x["pos_lines"], x["pos_stored"], (" (quality line sent %s stored %s)" % (x["quality_pos"], x["quality_pos_stored"])) if _qdiff else ""))
        # 11/25/2026 (review of the CCM rule): a CCM line that stands AT 31 is looked for in EVERY row, before any row leaves this loop. A visit whose rule failed
        # (pos_err) and a visit with no facility used to leave before a CCM line was looked at, and fixed words then said "a CCM line at 32" about them - so of
        # the three ways an older copy of the rule put a CCM line in at 31 (its exception, a rule failure, an unknown building) only the first was shouted.
        _pl = x.get("pos_lines") if isinstance(x.get("pos_lines"), list) else []
        _cv = [str(_p) for _cpt, _p in zip(_c, _pl) if _cpt in _CCM]      # where each CCM line of this visit was entered
        if "31" in _cv:
            _ps["ccm31"] += _cv.count("31")
            if _tag(x) not in _who["ccm31"]: _who["ccm31"].append(_tag(x))
        if x.get("pos_err"):
            _ps["err"] += 1; _who["err"].append("%s (%s)" % (_tag(x), str(x["pos_err"])[:70])); _ps["err_ccm31"] += _cv.count("31"); _ps["err_ccm32"] += _cv.count("32"); continue
        if not x.get("pos_lines"):
            if _rule_stamp and x.get("fac") in _NURSING_FAC and any(c in _NFV or c in _CCM for c in _c): _ps["norule"] += 1; _who["norule"].append(_tag(x))
            continue
        if x.get("pos_feed") != "31": continue
        if not x.get("fac"):
            _n = sum(1 for c in _c if c in _NFV or c in _CCM); _ps["nofac"] += _n
            if _n: _who["nofac"].append(_tag(x))
            _ps["nofac_ccm31"] += _cv.count("31"); _ps["nofac_ccm32"] += _cv.count("32"); _ps["nofac_nf31"] += sum(1 for _cpt, _p in zip(_c, _pl) if _cpt in _NFV and str(_p) == "31")
            continue
        _k = x.get("pos_kind") or []
        for _i, (_cpt, _p) in enumerate(zip(_c, x.get("pos_lines") or [])):
            _kind = _k[_i] if _i < len(_k) else ""
            if _cpt in _CCM:      # William 11/25/2026: every CCM line is 32. pos_kind ccm-skilled-month = a 32 line LISTED for him; a CCM line at 31 = an older copy of the rule ran (or a batch from before that day)
                if str(_p) == "31": continue      # counted and named above, in whatever row it stands
                _ps["ccm%s" % _p] += 1
                if _kind == "ccm-skilled-month":
                    _ps["ccmlisted"] += 1
                    if _tag(x) not in _who["ccmlisted"]: _who["ccmlisted"].append(_tag(x))
            elif _cpt in _NFV:
                _ps["nf%s" % _p] += 1
                if _kind in ("extra", "between"): _ps["nfleft"] += 1; _who["nfleft"].append(_tag(x))
                if _kind == "moved": _ps["nfmoved"] += 1
    if any(_ps[k] for k in _ps if k not in ("readback", "notown", "profdef", "nofacother")):
        # 11/25/2026 (review): what the line says about the CCM lines of a rule-failed visit, or of a building the table does not know, is READ from the register - "at 32"
        # only when such a visit has a CCM line at 32 and none at 31; a CCM line at 31 there is pointed to the CCM ENTERED AT 31 list; no CCM line, no words about one
        _e_ccm = " (a CCM line among them AT 31 - see CCM ENTERED AT 31)" if _ps["err_ccm31"] else " (a CCM line among them at 32)" if _ps["err_ccm32"] else ""
        _n_ccm = [w_ for w_ in ("a nursing visit at the default 31" if _ps["nofac_nf31"] else "", "a CCM line AT 31 - see CCM ENTERED AT 31" if _ps["nofac_ccm31"] else "a CCM line at 32" if _ps["nofac_ccm32"] else "") if w_]
        L("- Place of service in the nursing buildings (11/10/2026 rule; CCM since 11/25/2026: every line 32): CCM lines entered as 32: %d%s%s; nursing visits 32 (monthly): %d; nursing visits 31: %d%s%s%s%s%s." % (
            _ps["ccm32"],
            (" (%d of them listed for William - the chart shows a skilled-looking month, see pos_why - not held and not changed)" % _ps["ccmlisted"]) if _ps["ccmlisted"] else "",
            (" - AND %d CCM LINE(S) ENTERED AT 31, which is not William's rule (11/25/2026: every CCM line is 32): an older copy of the rule ran, or the batch is from before that day - not held: they go out at 31 with the next claim run unless they are changed first" % _ps["ccm31"]) if _ps["ccm31"] else "",
            _ps["nf32"], _ps["nf31"],
            (" (%d of them kept at 31 because the chart shows neither pattern - see pos_why)" % _ps["nfleft"]) if _ps["nfleft"] else "",
            (" (%d of them because the previous nursing visit was in another building)" % _ps["nfmoved"]) if _ps["nfmoved"] else "",
            ("; POS RULE NOT APPLIED on %d visit(s) - entered at the feed's place of service%s, see pos_err in the import register and rules.md 11/10/2026" % (_ps["err"], _e_ccm)) if _ps["err"] else "",
            ("; %d CCM / nursing-visit line(s) came from a building the facility table does not know - entered with no facility%s" % (_ps["nofac"], (" (%s)" % ", ".join(_n_ccm)) if _n_ccm else "")) if _ps["nofac"] else "",
            ("; PLACE OF SERVICE RULE DID NOT RUN on %d visit(s) in the nursing buildings - the import helper in this workspace is an old copy (rules.md 11/10/2026)" % _ps["norule"]) if _ps["norule"] else ""))
        _names("err", "TOP OF THE REPORT - rule not applied, for William before the claim run; a routine changes nothing on these visits")
        _names("norule", "TOP OF THE REPORT - rule did not run (old helper)")
        _names("nofac", "TOP OF THE REPORT - building the facility table does not know")
        # 11/25/2026 (review): these two lists name EVERY chart, with no cut at 30. Since that day a CCM line of a skilled-looking month goes out at 32 the same day,
        # so the list is William's only cue for it (rules.md part 1: "he does not bill CCM on skilled residents, so a chart on that list is one for him to look at"); and a
        # CCM line at 31 goes out at 31 unless someone changes it first.
        _names("ccm31", "TOP OF THE REPORT - CCM ENTERED AT 31 (William 11/25/2026: every CCM line is 32) - for William before the claim run; a routine changes nothing on these visits", cap=None)
        _names("ccmlisted", "for William, not held - CCM entered at 32, the chart shows a skilled-looking month (pos_kind ccm-skilled-month)", cap=None)
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
    # 11/25/2026: the building is NAMED, in the feed's own words (the import writes them into the row as feed_building), whatever codes its visits carry - with the name
    # in hand the building can be added to the table (claimocity_import.py FAC: the feed's name -> AdvancedMD facility id and place of service) and its next visits go in with a facility
    if _bld: L("  - TOP OF THE REPORT - add to the facility table (claimocity_import.py FAC), the feed's own building name: %s" % "; ".join("'%s' x%d" % (n_, c_) for n_, c_ in sorted(_bld.items(), key=lambda t_: (-t_[1], t_[0]))))
except Exception as _e:                                    # a register edited by hand must never stop the digest
    L("- Place of service in the nursing buildings (11/10/2026 rule): this line could not be built (%s) - read pos_lines / pos_err in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
# initial nursing-facility visits (William 11/10/2026, rules.md): every one goes in under the physician whatever clinician the feed names - one plain line, not for the top
try:
    _ini = [x for x in reg["created"] if isinstance(x, dict) and x.get("prof_feed")]
    if _ini: L("- Initial visits entered under the physician although the feed named another clinician: %d (%s). William 11/10/2026: every initial nursing-facility visit is his." % (
        len(_ini), ", ".join("%s %s" % (x.get("pid") or "?", x.get("visit") or "?") for x in _ini[:30]) + (" +%d more" % (len(_ini) - 30) if len(_ini) > 30 else "")))
except Exception as _e:
    L("- Initial visits under the physician: this line could not be built (%s) - read prof_feed in the import register." % type(_e).__name__)
# diagnosis codes AdvancedMD's own list does not have (William 11/25/2026, STANDING: "for any diagnosis not in the master file yet change it to i10 and send me an email
# with the codes needed to be added"). The import names such codes in each created row (missing_dx) and, since that day, what it put in their place (dx_instead). ONE
# line here says how many visits, each code with its number of visits (most first) and where the text of William's email is; the text is written to
# outbox/dx_codes_needed_<STAMP>.txt - the codes, their visits, chart numbers and dates of service, never a name (a register row holds none; only pid and dos are read).
# A row with missing_dx and NO dx_instead had the code LEFT OFF (an import from before 11/25/2026, or a run in which I10 itself was not in the list): it is said to be
# entered WITHOUT the code, never with I10. No row with such a code: no line and no file. This block never stops the digest.
try:
    _dxc = {}; _dxn = [0, 0]; _dxi = set()      # code -> (its visits entered with the stand-in code, its visits entered without the code), each "chart date"; the visits of each kind; the stand-in code the rows name
    for x in reg["created"]:
        _m = x.get("missing_dx") if isinstance(x, dict) else None
        _m = sorted({c_.strip() for c_ in _m if isinstance(c_, str) and c_.strip()}) if isinstance(_m, list) else []
        if not _m: continue
        _in = isinstance(x.get("dx_instead"), str) and bool(x["dx_instead"].strip())
        _dxn[0 if _in else 1] += 1
        if _in: _dxi.add(x["dx_instead"].strip())
        for c_ in _m: _dxc.setdefault(c_, ([], []))[0 if _in else 1].append((str(x.get("pid") or "?"), str(x.get("dos") or "?")))
    if _dxc:
        _dkey = lambda t_: (t_[0], (t_[1][6:] + t_[1][:5]) if re.match(r"^\d\d/\d\d/\d{4}$", t_[1]) else t_[1])      # by chart, then by date of service
        _dxc = {c_: tuple(["%s %s" % t_ for t_ in sorted(v_, key=_dkey)] for v_ in pair_) for c_, pair_ in _dxc.items()}
        _i10 = "/".join(sorted(_dxi)) or "I10"
        _before = (bool(re.match(r"^2\d{7}T", _st8)) and _st8[:8] < "20261125") or STAMP == "1028"      # a batch from before William's word: its codes were left off by the import of that day
        _win = "entered with %s in its place" % _i10
        _wout = "entered without that code (before 11/25/2026)" if _before else "entered without that code (%s was not put in its place: an older copy of the import ran, %s itself is not in AdvancedMD's list, or the code stood past the 12 codes a charge line carries)" % (_i10, _i10)
        _nv = lambda c_: len(_dxc[c_][0]) + len(_dxc[c_][1])
        _order = sorted(_dxc, key=lambda c_: (-_nv(c_), c_))
        _kinds = "" if not _dxn[1] else (", all %s" % _wout) if not _dxn[0] else ", %d %s and %d %s" % (_dxn[0], _win, _dxn[1], _wout)
        _vis = lambda c_: "; ".join(_dxc[c_][0]) if not _dxn[1] else " - ".join(w_ for w_ in (("%s: %s" % (_win, "; ".join(_dxc[c_][0]))) if _dxc[c_][0] else "", ("%s: %s" % (_wout, "; ".join(_dxc[c_][1]))) if _dxc[c_][1] else "") if w_)
        _kept = "once a code is in the list, later visits use it; the visits already entered keep %s unless you say otherwise." % _i10
        _end = (("Each of these visits was entered with %s in the code's place on your word of 11/25/2026; " % _i10) + _kept) if not _dxn[1] else \
               (("The visits listed as %s went in with %s in the code's place on your word of 11/25/2026; " % (_win, _i10)) + _kept + " The visits listed as entered without that code went in with their other codes only: nothing stands in the code's place on them.") if _dxn[0] else \
               ("These visits were entered without that code: it was left off the charge and nothing stands in its place. Since 11/25/2026 a visit goes in with %s in the code's place on your word; once a code is in the list, later visits use it." % _i10) if _before else \
               ("These visits were entered without that code: it was left off the charge and nothing stands in its place - %s was not put there as your word of 11/25/2026 asks (an older copy of the import ran, %s itself is not in AdvancedMD's list, or the code stood past the 12 codes a charge line carries). Once a code is in the list, later visits use it." % (_i10, _i10))
        _file = "outbox/dx_codes_needed_%s.txt" % STAMP
        _mail = ["These diagnosis codes are not in AdvancedMD's diagnosis list (Master Files > Diagnosis Codes) and need to be added:", ""] + ["%s - %d visit(s): %s" % (c_, _nv(c_), _vis(c_)) for c_ in _order] + ["", _end]
        try:
            os.makedirs("outbox", exist_ok=True); open(_file, "w").write("\n".join(_mail) + "\n"); _where = _file
        except Exception as _ef:                           # the line is still said: the codes are in it and in the register
            _where = "the file %s could not be written (%s) - the codes are in this line and in missing_dx of the import register" % (_file, type(_ef).__name__)
        L("- Diagnosis codes not in AdvancedMD's list (William 11/25/2026: the visit goes in with %s in its place; he adds the codes): %d visit(s)%s - %s - EMAIL WILLIAM: %s" % (
            _i10, sum(_dxn), _kinds, ", ".join("%s x%d" % (c_, _nv(c_)) for c_ in _order), _where))
except Exception as _e:                                    # never stops the digest
    L("- Diagnosis codes not in AdvancedMD's list: this line could not be built (%s) - read missing_dx / dx_instead in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
# quality code (William 11/10/2026, rules.md): the advance-care-plan code 1123F that rides, at no charge, with Medicare visits of patients 65 and older.
# Everything that needs William is ONE line that starts "  - TOP OF THE REPORT - ", said in the run where it began; the state of the code is ONE
# top line in every batch ("QUALITY CODE: ...") - the previous import register's gate tells what is new in this run.
# 11/12/2026 (William 11/11/2026: "dont stop this dont let it stop make sure this suceeds"): the code never switches itself off. The state line says
# one of: stopped on William's word (his own QUALITY_CODE=stop) / paused this run / probing (one line a run) / going.
# November 12, 2026 - fix round 2 (K14-K17): a visit of a fault run held for its own reason (no 1123F line on it) is named in the state line for William
# but pauses nothing; after a cut or a fault the state line says what is known (a try cut off, a line that could not be looked for, a line found off
# already, what this run's inspector step found); a held visit this run's retry pass freed is said free under Claim Inspector pass.
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
    # 11/12/2026 - the code never switches itself off: why it probes, why this run is paused, the visits stuck held with their line, an older register's own OFF, what a person wrote about N620
    _probe = str(_qg.get("probe") or ""); _paused = str(_qg.get("paused") or ""); _stuck = [x for x in _lst("stuck") if isinstance(x, dict)]
    _stand = _qg.get("standing_restart") if isinstance(_qg.get("standing_restart"), dict) else None; _seen = str(_qg.get("n620_seen") or "")[:40]
    if (_qa or _qn or _qr or _qf or _off or _notes or _qg.get("proof") or _qg.get("wait") or _dead or _qg.get("reset") or _rem or _skip_h or _unread or _late or _nr
            or (_qg.get("confirmed") is True and (_ans or _mw)) or _qh or _moved or _qg):
        _pf = _qg.get("proof") if isinstance(_qg.get("proof"), dict) else {}
        _days = None
        try:
            _d1 = re.search(r"(\d{8})T", re.sub(r"[^0-9TZ]", "", str(_qg.get("pending_since") or ""))); _d2 = re.search(r"(\d{8})T", _st8)
            if _d1 and _d2: _days = (datetime.datetime.strptime(_d2.group(1), "%Y%m%d") - datetime.datetime.strptime(_d1.group(1), "%Y%m%d")).days
        except Exception: _days = None
        L("- Quality code 1123F (advance care plan, Medicare measure 047; a line that pays nothing): on %d visit(s) in this batch, line amount $%s; %s." % (
            len(_qa), _qg.get("fee") or "0.00",
            "stopped on William's word - no line is added until one run with QUALITY_CODE=reset" if _lasting else
            "paused this run - no line was added (the top line says why)" if _paused else
            "PROBING - one line a run until one such line is seen billed to insurance in AdvancedMD" if _probe else
            ("no line in this run (%s)" % _off[:120]) if _off else
            ("every eligible visit carries it - a quality line was seen billed to insurance (visit %s, %s)%s" % (_pf.get("visit"), _pf.get("billed"),
             "; no cap" if (_qg.get("n620") or _ans) else "; at most 10 a run until Medicare's own answer is on file")) if _qg.get("confirmed") is True and _pf else
            "every eligible visit carries it - a quality line was seen billed to insurance in an earlier run" if _qg.get("confirmed") is True else
            ("PILOT, waiting - no line was added in this run: the outcome of the first line(s) is not decided yet (%s) - the lines below say why" % ", ".join(_pend[:6])) if _qg.get("wait") else
            "PILOT - at most %s visit(s) carry it, then no more until one such line is seen billed to insurance in AdvancedMD" % (_qg.get("pilot_cap") or 3)))
        T = lambda s_: L("  - TOP OF THE REPORT - " + s_)
        if _qa: L("  - carried by: %s%s" % ("; ".join("%s %s %s" % (x.get("pid"), x.get("visit"), x.get("quality_charge") or "?") for x in _qa[:30]), (" (+%d more)" % (len(_qa) - 30)) if len(_qa) > 30 else ""))
        # ONCE, before the state line: Medicare's own answer (the first run whose gate carries it while the gate before carried neither), and the restart on William's standing word
        _acc_before = (isinstance(_pg.get("medicare_answer"), dict) and bool(_pg["medicare_answer"].get("charge"))) or _pg.get("n620") is True
        if (_ans or _qg.get("n620") is True) and not _acc_before:
            if _ans: T("QUALITY CODE ACCEPTED BY MEDICARE - Medicare's remittance shows the 1123F line on visit %s, a Medicare payment line of $%s posted %s: the code reached Medicare on the claim and came back on its remittance; whether the measure is met shows only in the feedback on the Medicare quality-program site. The cap of ten a run is lifted." % (
                _ans.get("visit"), _ans.get("amount"), _ans.get("date")))
            else: T("QUALITY CODE ACCEPTED BY MEDICARE - a person saw remark N620 on a 1123F line of a Medicare remittance (registers/quality_n620_seen.json%s): remark N620 on the 1123F line shows Medicare received the code and that it is valid for the year; whether the measure is met shows only in the feedback on the Medicare quality-program site. The cap of ten a run is lifted." % (
                (", seen %s" % _seen) if _seen else ""))
        if _stand: T("QUALITY CODE: restarted on William's standing word of November 11, 2026 (\"dont stop this dont let it stop make sure this suceeds\") - an earlier run had switched it off (%s). No restart by William is needed any more; the code goes on by itself." % str(_stand.get("was") or "")[:220])
        # THE STATE LINE (11/12/2026): ONE line in every batch - stopped on William's word / paused this run / probing (one line a run) / going. Copied to the top of the report word for word.
        _fee = str(_qg.get("fee") or "0.00"); _vst = lambda v: str(v) if str(v or "").startswith("vst") else "vst%s" % _num(v)
        if _lasting: T("QUALITY CODE: stopped on William's word (QUALITY_CODE=stop) - no line is added until one run with QUALITY_CODE=reset in front of the import's command.")
        # November 12, 2026 - fix round 2 (K15, K16): a visit of a fault run held for its own reason ("own": no 1123F line on it, or after the proof words that name
        # no line) pauses nothing - it is named in the state line for a person until it is free; what this run's step found is said from its NEWEST retry entry
        _stp = [x for x in _stuck if x.get("own") is not True]; _own = [x for x in _stuck if x.get("own") is True]
        def _newtry(x):
            _t = [e for e in _rem if e.get("retry_of") and _num(e.get("visit")) == _num(x.get("visit"))]; return _t[-1] if _t else None
        def _didof(_e, x):
            _nt = str((_e or {}).get("note") or ""); _flt = x.get("fault") is True
            return ("This run's inspector step recorded no new try for that visit; the next run %s again." % ("looks at it" if _flt else "tries the void and the re-save") if _e is None else
                    "This run found the visit free (%s): nothing was done to it, and the next run goes on by itself, probing." % (
                        "no longer listed by the Claim Inspector" if "no longer listed" in _nt else "only advisories remained - bypassed" if "only advisories" in _nt else "the visit was billed" if "was billed" in _nt else (_nt[:80] or "no longer held")) if _e.get("listed") is False else
                    "This run found it held for its own reason, not because of this code (%s) - a person fixes the visit; it does not pause the code." % (_nt[:140] or "its hold names no quality line") if _e.get("own_reason") is True else
                    "This run's step could not look for its quality line (%s); the next run looks again." % (_nt[:140] or "a read failed") if _e.get("looked") is False else
                    "This run's try was cut off before it ended; the next run's step looks again." if (_e.get("void_ok") is not True and not _nt) else
                    "This run tried again and could not take the line off (%s); every run tries again, and a person can take the line off that visit at any time." % (_nt[:120] or "the void failed") if _e.get("void_ok") is not True else
                    "This run found the line off already, re-saved the visit and it went out; the next run goes on by itself, probing." if (_e.get("released") is True and _e.get("was_void") is True) else
                    "This run took the line off, re-saved the visit and it went out; the next run goes on by itself, probing." if _e.get("released") is True else
                    "This run re-saved the visit again, but the listing after it failed, so the visit is not shown free; the next run lists it again." if "the listing after the re-save failed" in _nt else
                    "This run re-saved the visit again and it is still listed for the edit about the line%s; every run tries again." % ("; the re-save failed" if _e.get("resave_ok") is False else "") if (_e.get("still_named") is True or _e.get("resave_ok") is False) else
                    "This run took the line off; the visit is still held for its own reason (%s), which is not this code's; the next run goes on by itself, probing." % str(_e.get("why") or "")[:100])
        _ownsay = "".join((" Visit %s (chart %s) was found free by this run's inspector step." % (_vst(x.get("visit")), x.get("chart"))) if (_newtry(x) or {}).get("listed") is False else
                          " Visit %s (chart %s) came from a fault run and is held for its own reason, not because of this code: %s (%s: \"%s\") - it stays on this report until it is free; it does not pause the code." % (
                              _vst(x.get("visit")), x.get("chart"), x.get("what"), x.get("register"), str(x.get("why") or "")[:140]) for x in _own[:3])
        if _lasting: pass
        elif _paused and _stp:
            _s0 = _stp[0]; _e = _newtry(_s0); _did = _didof(_e, _s0)
            T("QUALITY CODE: paused this run - visit %s (chart %s) %s: %s (%s: \"%s\")%s. No new line was added. %s%s" % (
                _vst(_s0.get("visit")), _s0.get("chart"), "came from a fault run" if _s0.get("fault") is True else "may still be held with its quality line" if str(_s0.get("what") or "").startswith("the routine's last try was cut off") else "is held with its quality line",      # K11, K16: a visit of a fault run; a try that was cut off
                _s0.get("what"), _s0.get("register"), str(_s0.get("why") or "")[:140], ("; %d more visit(s) the same way" % (len(_stp) - 1)) if len(_stp) > 1 else "", _did, _ownsay))
        elif _paused.startswith("paused this run: AdvancedMD shows procedure id"):
            T("QUALITY CODE: paused this run - AdvancedMD shows procedure id pcode65441 as %s, not 1123F. No line is added while that is so; every run reads it again and goes on by itself when it reads 1123F. To end it: the code text of that procedure in AdvancedMD's procedure list must be 1123F (a person, or AdvancedMD's support).%s" % (_qg.get("wrong_code_text") or "another code", _ownsay))
        elif _paused or _off:
            _why = _paused or _off; _why = _why[len("paused this run: "):] if _why.startswith("paused this run: ") else _why[len("this run: "):] if _why.startswith("this run: ") else _why
            _fx = "".join(" Visit %s (chart %s) came from a fault run: %s. %s" % (_vst(x.get("visit")), x.get("chart"), str(x.get("what") or "")[:200], _didof(_newtry(x), x)) for x in _stp[:3] if x.get("fault") is True)      # K16 (fix round 2): what this run's step found
            T("QUALITY CODE: paused this run - %s.%s%s" % (_why[:300].rstrip("."), _fx.rstrip(), _ownsay))
        elif _probe:
            _kind = str(_qg.get("probe_kind") or ""); _pwords = str(_qg.get("probe_words") or ""); _cent = [str(v) for v in _lst("left_off_cent")]
            # November 12, 2026 - fix round 1 (K8): the newest cause is the move from $0.00 to one cent, or the one-cent fallback - no ONE-CENT line has been stopped
            # or refused yet, so nothing needs changing in AdvancedMD; the advice on what must change (or which bypass William must approve) comes only after that
            _fall = _probe.startswith("new lines carry $0.01 and no one-cent line is seen billed yet")
            _from_zero = _fall or (" at $0.00 (" in _probe and "new lines carry $0.01" in _probe and _kind in ("claim_check", "refused", "not_stored"))
            _adv = ("%s: ONE line of one cent a run is tried until one is billed, and nothing needs changing in AdvancedMD yet - if a one-cent line is stopped or refused too, this line will quote AdvancedMD's words and say what must change." % (
                        "No one-cent line has been stopped or refused" if _fall else "That stop was of the $0.00 line, not of a one-cent line") if _from_zero else
                    "To let the line pass, one of two things must change: in AdvancedMD the Claim Inspector edit quoted here is set so that it lets a 1123F line of $%s through (a person, or AdvancedMD's support), or William approves a standing bypass of exactly that edit for 1123F lines - no routine bypasses it without his word." % _fee if _kind == "claim_check" else
                    "To let the line pass, AdvancedMD's charge entry must take procedure 1123F at $%s on a visit - a person asks AdvancedMD's support why it does not." % _fee if _kind in ("refused", "not_stored") else
                    "AdvancedMD leaves the reporting line off the claim: %d one-cent line(s) sit unbilled (%s). This needs a setting in AdvancedMD - a person or AdvancedMD's support makes it send a line of one cent for procedure 1123F." % (len(_cent), ", ".join(_cent[:6])) if (_kind == "left_off" and _cent) else
                    "AdvancedMD left the $0.00 reporting line off the claim (%d line(s) sit unbilled); new lines carry one cent, which CMS allows. If it leaves a one-cent line off too, that needs a setting in AdvancedMD (a person or AdvancedMD's support)." % len(_dead) if _kind == "left_off" else
                    "Nothing to change in AdvancedMD is known; the visit named here is for a person to check, and the first probe line that is billed ends the probing." if _kind in ("fault", "order") else
                    "Nothing to change in AdvancedMD is known; the first probe line that is billed ends the probing.")
            _now = (" This run's probe line: visit %s (chart %s)." % (_qa[0].get("visit"), _qa[0].get("pid"))) if _qa else (" The probe line of visit %s is not decided yet - no new line in this run." % (_pend[0] if _pend else "an earlier run")) if _qg.get("wait") else ""
            T("QUALITY CODE: probing (one line a run) - %s%s. %s%s" % (
                ("AdvancedMD's own words: \"%s\" - %s" % (_pwords[:140], _probe[:400])) if _pwords else _probe[:400],
                "" if _from_zero else " (stopped %s time(s) since %s)" % (_qg.get("probe_tries") or 1, _qg.get("probe_since") or "an earlier run"), _adv, _now + _ownsay))      # K8: the move's own sentence names the register; a count of stops would mislead there
        else:
            _ansv = "; ".join(x for x in (("Medicare's payment line posted %s on visit %s" % (_ans.get("date"), _ans.get("visit"))) if _ans else "",
                                         ("remark N620 seen on %s" % _seen) if (_qg.get("n620") is True and _seen) else "remark N620 seen (registers/quality_n620_seen.json names no date)" if _qg.get("n620") is True else "") if x) or "not yet"
            _rd = _qg.get("round") if isinstance(_qg.get("round"), dict) else {}
            if _qg.get("confirmed") is True: T("QUALITY CODE: going - %d line(s) billed (read in AdvancedMD; lines added after the proof are not read back), Medicare's answer: %s.%s" % (len(_lst("billed_lines")), _ansv, _ownsay))
            else: T("QUALITY CODE: going - first round at $%s: %d line(s) entered, none billed yet (at most 3 until one is seen billed), Medicare's answer: %s.%s" % (
                _fee, max(0, (_rd.get("lines") if isinstance(_rd.get("lines"), int) else 0) - (_rd.get("void") if isinstance(_rd.get("void"), int) else 0)), _ansv, _ownsay))
        for u_ in (_unread if set(_unread) & set(str(u) for u in (_qg.get("unread_prev") or []) if isinstance(_qg.get("unread_prev"), list)) else []):
            T("the import register %s cannot be read - the quality code waits until it is restored from the repository (git checkout of practices/ehpa/registers/%s, then copy it to the workspace's registers/)." % (u_, u_))
        if any(n_.startswith("NOTHING TO RESTART") for n_ in _notes): T(next(n_ for n_ in _notes if n_.startswith("NOTHING TO RESTART"))[:220])
        if _qg.get("fee") == "0.01" and _pg.get("fee") != "0.01" and not _qg.get("reset"):
            # November 12, 2026 - fix round 1 (review note F5, with K8 and K12): the import's note is said whole, and who is due again follows from what moved the amount
            _mv = next((n_ for n_ in _notes if "$0.01" in n_ or "one cent" in n_), "")
            _who = (" The patients whose $0.00 line was left off are due again 30 days after it was called left off (AdvancedMD may still bill it until then); they get the code with a later visit of the same year" if "off its claim" in _mv else
                    " The patients whose visit was stored without its $0.00 line are due again; they get the code with a later visit of the same year" if "stored a visit without its quality line" in _mv else
                    " The patients whose $0.00 line was stopped get no line again this year (a patient whose visit the claim check or the charge entry stopped with the line is not tried again that year)" if _mv else "")
            T("new quality lines now carry ONE CENT ($0.01, which CMS allows): %s.%s%s - one line a run until a one-cent line is seen billed (at one cent the code probes)." % (
                (_mv or "AdvancedMD did not send a $0.00 line")[:400].rstrip("."), _who, " once William restarts the code (it is OFF)" if (_lasting and "due again" in _who) else ""))      # never a promise while the code is OFF, nor one for the next year (confirm review F2)
        if _qg.get("reset"): L("  - the pilot was started again in this run (QUALITY_CODE=reset): a new round at $0.00.")
        if _qa and _qg.get("confirmed") is not True: L("  - first lines: when Medicare's remittance for one of these visits arrives, remark N620 on the 1123F line shows Medicare received the code and that it is valid for the year; whether the measure is met shows only in the feedback on the Medicare quality-program site (reason 246 with it is not a denial: nothing to do, never bill the patient).")
        if _qg.get("wait") and _days is not None and _days >= 3:
            T("the quality-code pilot has waited %d days: the outcome of its first line(s) is still not decided (%s) - a visit not billed yet, a line not billed yet although its visit was, or a billed line whose code text AdvancedMD does not show (the lines below say which). Look at them in AdvancedMD and tell William - nobody takes a line off by hand (the patient of a line taken off by a person gets no line again this year)." % (_days, ", ".join(_pend[:6])))
        if _pw and isinstance(_pw.get("days"), int) and _pw["days"] >= 3:
            T("the quality line of visit %s is billed, but for %d days neither its charge detail nor the chart's history shows the code text 1123F - the pilot is not proven and waits; William looks whether AdvancedMD stores procedure id pcode65441 as 1123F." % (_pw.get("visit"), _pw["days"]))
        if _qh: T("%d visit(s) that carry the quality line are HELD by the Claim Inspector for a reason that does not name the line (the line stays on: after proof it comes off by itself only when the edit names it; the visit's own charge waits for its hold): %s" % (
            len(_qh), "; ".join("%s %s - %s" % (x.get("pid"), x.get("visit") if str(x.get("visit") or "").startswith("vst") else "vst%s" % x.get("visit"), w) for x, w in _qh[:10])))
        _stuckv = {_num(x.get("visit")) for x in _stuck}
        # November 12, 2026 - fix round 1 (K9; specification 2.5): in the digest too the NEWEST entry for a line decides. An entry that a later entry of the SAME
        # register replaces (same visit and code - e.g. the normal pass's void failed and this run's retry pass then took the line off) is not a top line of its
        # own: it is said once, with the newest one ("then freed by this run's retry pass"), or the newest entry's own words stand. The held row stays.
        _insids = {id(e) for e in (insp.get("quality_removed") if isinstance(insp, dict) and isinstance(insp.get("quality_removed"), list) else [])}
        _rkey = lambda e: (id(e) in _insids, _num(e.get("visit")), str(e.get("code") or "1123F").upper())
        _newest = {}
        for e in _rem: _newest[_rkey(e)] = e
        _older = {}
        for e in _rem:
            if _newest[_rkey(e)] is not e: _older.setdefault(_rkey(e), []).append(e)
        for e in _rem:      # William 11/10/2026: the routine takes the line off a held visit by itself
            if _newest[_rkey(e)] is not e: continue      # K9: replaced by a later entry of the same register - said once with that one
            _wv = "vst%s" % _num(e.get("visit")); _was = _older.get(_rkey(e)) or []
            _how = (str(_was[-1].get("note") or ("its try ended before the void reported back" if _was[-1].get("void_ok") is not True else "still listed for the edit about the line" if (_was[-1].get("still_named") is True or _was[-1].get("resave_ok") is False) else "held for its own reason"))[:100]) if _was else ""      # what the replaced entry said
            _then = (" - its first try in this run did not free it (%s), then freed by this run's retry pass" % _how) if _was else ""
            if e.get("retry_of") and (_num(e.get("visit")) in _stuckv or e.get("listed") is False):      # the step's retry of a stuck visit: the state line above says what this run did
                if _was and _num(e.get("visit")) not in _stuckv:      # ... unless the visit's first try was in THIS run, which the state line does not know: said once here
                    T("held visit %s (%s): the routine's first try in this run did not free it (%s), then freed by this run's retry pass (%s) - nothing more was done to it." % (_wv, e.get("pid"), _how, str(e.get("note") or "no longer held")[:100]))
                continue
            if e.get("void_ok") is not True: T("the routine could not take the quality line off held visit %s (%s: %s) - the visit is held WITH its line. No new line is added while that is so; every run tries the void and the re-save again, and a person can take the line off that visit at any time." % (_wv, e.get("pid"), str(e.get("note") or e.get("why") or "")[:120]))
            elif e.get("released") is True: T("the routine took the quality line %s off held visit %s (%s; the hold: %s) and the visit went through without it%s. That is one refusal of the line: %s" % (
                e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100], _then, ("after proof one changes nothing; a second in a row moves new lines to one cent" if _qg.get("fee") != "0.01" else "after proof one changes nothing; a second in a row sets the proof aside and the code probes: one line a run") if _qg.get("confirmed") is True else
                ("the next run moves new lines to one cent: one line a run until one is billed" if _qg.get("fee") != "0.01" else "the code goes on probing: one line a run until one is billed")))
            elif e.get("still_named") is True or e.get("resave_ok") is False: T("the routine took the quality line %s off held visit %s (%s), but the visit is still listed for the edit about the line (%s)%s - no new line is added while that is so; every run re-saves the visit again (one re-save should release it)." % (
                e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100], "; the re-save after the void failed" if e.get("resave_ok") is False else ""))      # not the visit's own reason (confirm review NH2-2)
            else: T("the routine took the quality line %s off held visit %s (%s)%s, but the visit is still held for its own reason (%s) - its place in the round is free and the patient is due again; the visit's own hold is listed under Claim Inspector pass." % (e.get("charge"), _wv, e.get("pid"), _then, str(e.get("why") or "")[:100]))
        if _qr: T("QUALITY CODE NOT ACCEPTED by AdvancedMD on %d visit(s); each visit was entered without it: %s - these patients are not tried again this year." % (len(_qr), "; ".join("%s %s (%s)" % (x.get("pid"), x.get("visit"), str(x.get("quality_refused"))[:80]) for x in _qr[:10])))
        if _qn: T("AdvancedMD stored %d visit(s) WITHOUT the quality line that was sent with it (the visit itself is entered): %s" % (len(_qn), "; ".join("%s %s" % (x.get("pid"), x.get("visit")) for x in _qn[:10])))
        if _qf: T("%d visit(s) were refused with the quality line and NOT sent again, because the chart shows part of the visit or could not be read - check that visit (for William; no routine sends it again): %s" % (
            len(_qf), "; ".join("%s %s %s (visit %s; the chart shows %s)" % (x.get("pid"), x["info"].get("dos") or "?", "+".join(str(c) for c in (x["info"].get("cpts") or [])), x.get("empty_visit"), str(x.get("stored"))[:80]) for x in _qf[:10]))
            + " - the insurance check did not look at these visits; the Claim Inspector step looks at each of them in every run until it is free (no new line while one is held - November 12, 2026).")      # never "empty": the chart shows what it holds (confirm review NH2-5); K11: the retry pass looks at them
        _qs = [x for x in (reg.get("failed") or []) if isinstance(x, dict) and x.get("quality_sent")]      # refused with the line, and the send WITHOUT it ended in an error (confirm review NH2-4)
        if _qs: T("%d visit(s) were refused with the quality line and the send without it ended in an error - such a visit may NOT be entered: William checks it (no routine sends it again): %s" % (
            len(_qs), "; ".join("%s %s %s (visit %s)" % (x.get("pid"), _finfo(x).get("dos") or "?", "+".join(str(c) for c in (_finfo(x).get("cpts") or [])), x.get("empty_visit")) for x in _qs[:10])))
        if _qg.get("history_shows_line") is False and _pg.get("history_shows_line") is not False:
            T("the chart history does NOT list the proven quality line: a 1123F or 1124F entered by hand is invisible to the import - William names such patients in registers/quality_exceptions.json.")
        for _y, _n in sorted(_nr.items()): T("the quality code is not added to %s visits until William renews it (%s visit(s) of this batch would otherwise carry it)." % (_y, _n))
        if _moved: L("  - %d quality line(s) of this batch rode on visits the insurance check moved to another payer than Medicare: %s - that line went to that payer; nothing to do (such a line is never the pilot's proof)." % (
            len(_moved), "; ".join("%s %s -> %s" % (x.get("pid"), x.get("visit"), c_) for x, c_ in _moved[:10])))
        if _qg.get("confirmed") is True and not _ans and not _qg.get("n620") and _mw:
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
# 11/12/2026: M0004 never switches itself off either - where it used to go off it probes (one M0004 line a run in all) or pauses for one run.
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
    _mprobe = str(_mg.get("probe") or ""); _mpaused = str(_mg.get("paused") or ""); _mstand = _mg.get("standing_restart") if isinstance(_mg.get("standing_restart"), dict) else None      # 11/12/2026: M0004 probes or pauses where it used to go off
    _mans = {k: v for k, v in (_mg.get("answer").items() if isinstance(_mg.get("answer"), dict) else ()) if isinstance(v, dict)}
    _mlo = [str(c) for c in _mlst("left_off_lines")]; _mlate = [r_ for r_ in _mlst("late_rows") if isinstance(r_, list) and len(r_) >= 5]
    _WHO = {"prof13": "prof13 (the physician)", "prof15": "prof15 (the nurse practitioner)"}
    _st = lambda p_: str((_mcl.get(p_) or {}).get("state") or "not yet")
    _dec = bool(re.match(r"^\d{8}T", _st8)) and _st8[4:6] == "12"      # a batch of December: the registration year ends on the 31st
    if _mg and (_ma or _mr or _mns or _mrem or _mlast or _moff or _mnotes or _mlo or _mlate or _mprobe or _mstand or _qg2.get("confirmed") is True or any(_st(p_) != "not yet" for p_ in _mcl)):
        L("- Option code M0004 (Quality Care for Patients with Neurological Conditions - the option the group and both clinicians are registered for; William 11/10/2026: \"use it\"; a line that pays nothing, once per clinician, on a claim that carries 1123F): on %d visit(s) in this batch; %s; %s." % (
            len(_ma), "; ".join("%s: %s" % (_WHO.get(p_, p_), _st(p_)) for p_ in sorted(_mcl)) or "no clinician known yet",
            "paused this run - no M0004 line was added" if _mpaused else "probing - one M0004 line a run in all until one is billed" if _mprobe else ("no M0004 line in this run (%s)" % _moff[:120]) if _moff else
            "it rides with the next eligible visit of a clinician who has none" if _qg2.get("confirmed") is True else "it rides only once the quality code is proven"))
        T2 = lambda s_: L("  - TOP OF THE REPORT - " + s_)
        if _ma: L("  - M0004 carried by: %s" % "; ".join("%s %s %s (%s)" % (x.get("pid"), x.get("visit"), x.get("mvp_charge"), x.get("mvp_prof") or "?") for x in _ma[:10]))
        if _mstand: T2("the option code M0004: restarted on William's standing word of November 11, 2026 - an earlier run had switched it off (%s)." % str(_mstand.get("was") or "")[:220])
        if _mpaused: T2("the option code M0004 is paused this run: %s." % (_mpaused[len("paused this run: "):] if _mpaused.startswith("paused this run: ") else _mpaused)[:300].rstrip("."))
        if _mprobe and not str(_mpg.get("probe") or ""): T2("the option code M0004 probes (one M0004 line a run in all until one is billed): %s. The 1123F line goes on as before." % _mprobe[:260].rstrip("."))
        elif _mprobe: L("  - the option code M0004 still probes (since an earlier run): %s." % _mprobe[:240].rstrip("."))
        if _moff.startswith("this run: switched off (MVP_CODE=off)"): L("  - M0004 switched off for this run by William's MVP_CODE=off - no M0004 line was added.")
        elif "MVP_CODE=" in _moff: T2("the option code M0004 is off in this run: %s" % _moff[:220])
        if any(n_.startswith("NOTHING TO RESTART") for n_ in _mnotes): T2(next(n_ for n_ in _mnotes if n_.startswith("NOTHING TO RESTART"))[:220])
        if _mg.get("reset") is True: L("  - the option code M0004 was started again in this run (MVP_CODE=reset).")
        if _mr: T2("AdvancedMD refused %d visit(s) that carried M0004; each was entered with the 1123F line only: %s - M0004 goes on probing: one M0004 line a run in all until one is billed." % (len(_mr), "; ".join("%s %s (%s)" % (x.get("pid"), x.get("visit"), str(x.get("mvp_refused"))[:80]) for x in _mr[:5])))
        if _mns: T2("AdvancedMD stored %d visit(s) WITHOUT the M0004 line that was sent with it (the visit itself is entered): %s - M0004 goes on probing." % (len(_mns), "; ".join("%s %s" % (x.get("pid"), x.get("visit")) for x in _mns[:5])))
        for e in _mrem:      # William 11/10/2026: the routine takes a no-charge line off a held visit by itself (11.6)
            _wv = "vst%s" % _mnum(e.get("visit"))
            if e.get("listed") is False: L("  - visit %s (%s), which was held with its M0004 line, is free again (%s) - nothing was done to it; M0004 goes on by itself, probing." % (_wv, e.get("pid"), str(e.get("note") or "no longer held")[:100]))      # the inspector step's retry (11/12/2026)
            elif e.get("void_ok") is not True: T2("the routine could not take the M0004 line off held visit %s (%s: %s) - the visit is held WITH that line. No new M0004 line is added while that is so; every run tries the void and the re-save again." % (_wv, e.get("pid"), str(e.get("note") or e.get("why") or "")[:120]))
            elif e.get("with") == "1123F": L("  - the M0004 line %s of visit %s (%s) came off together with its 1123F line (M0004 never rides without it) - that clinician may get M0004 again." % (e.get("charge"), _wv, e.get("pid")))      # confirm review NH2-1
            elif e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False): T2("the routine took the M0004 line %s off held visit %s (%s), but the visit is still listed for the edit about the line (%s)%s - no new M0004 line is added while that is so; every run re-saves the visit again (one re-save should release it)." % (
                e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100], "; the re-save after the void failed" if e.get("resave_ok") is False else ""))      # confirm review NH2-2, the same for M0004 (8.6)
            elif e.get("released") is True: T2("the routine took the M0004 line %s off held visit %s (%s; the hold: %s) and the visit went through without it: M0004 probes: one M0004 line a run in all until one is billed; this does not count against the 1123F line." % (e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100]))
            else: T2("the routine took the M0004 line %s off held visit %s (%s), but the visit is still held for its own reason (%s) - its clinician may get M0004 again; the visit's own hold is listed under Claim Inspector pass." % (e.get("charge"), _wv, e.get("pid"), str(e.get("why") or "")[:100]))
        _billed = [p_ for p_ in sorted(_mcl) if _st(p_) == "billed"]
        if _billed: L("  - Medicare's answer for M0004: %s (a posted Medicare payment line on the M0004 line shows the code reached Medicare on the claim; whether the measure is met shows only in the feedback on the Medicare quality-program site)." % "; ".join(
            ("Medicare's remittance shows the M0004 line for %s (visit %s, $%s on %s)" % (p_, (_mans[p_].get("visit") or "?"), _mans[p_].get("amount") or "?", _mans[p_].get("date") or "?")) if p_ in _mans else ("not yet for %s (its line billed %s)" % (p_, (_mcl.get(p_) or {}).get("billed") or "?")) for p_ in _billed))
        if _mlo: L("  - %d M0004 line(s) were read as left off their claims (each visit went out without it, still so three days later; such a line is read again for 30 days): %s - listed for William; no routine voids them. That clinician gets M0004 once more; after a second left-off line M0004 probes: AdvancedMD leaves the line off the claim, which needs a setting in AdvancedMD (a person or AdvancedMD's support)." % (len(_mlo), ", ".join(_mlo[:6])))
        for r_ in _mlate: L("  - an M0004 line read as left off on %s was billed later: %s counts as done for %s%s." % (r_[4], r_[0], r_[6] if len(r_) > 6 else "the year", ("; %s carries two billed M0004 lines (the later one on %s); nothing to do" % (r_[0], r_[5])) if len(r_) > 5 and r_[5] else ""))
        if _dec:
            for p_ in sorted(_mcl):
                if _st(p_) not in ("billed", "waiting"): T2("%s has no M0004 line billed or waiting for %s - the year ends December 31 (M0004 must be on at least one of that clinician's Medicare claims that carries 1123F)%s." % (
                    _WHO.get(p_, p_), (_mcl.get(p_) or {}).get("year") or "the year", (": M0004 probes - " + _mprobe[:120]) if _mprobe else ""))
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
    # 11/25/2026 (review of the birth-date change): the two holds the insurance check sets BEFORE it buys a look-up (claimocity_verify.py lookup_hold) -
    # record keys same_person / no_birth_date, each the chart's visits. Chart ids and visit ids only; the hold line in the list below has the fixed words.
    # (11/25/2026, the verification: the record's key and every string of its list were printed as they were - a hand-made or odd record with a name in it
    # reached the top of the report. Now a record is printed only when its key is a chart id, and of its list only what is a visit id; what is left out is counted.)
    def _byc(key):
        rows = []; odd = 0
        for p_, v_ in ver.items():
            if not (isinstance(v_, dict) and isinstance(v_.get(key), list) and v_.get(key)): continue
            vis = [x_ for x_ in v_[key] if isinstance(x_, str) and re.fullmatch(r"(?:vst)?[0-9]+", x_)]
            if _pat_ok(p_) and vis: rows.append((p_, vis))
            else: odd += 1
        return rows, odd
    _whoc = lambda rows, odd: (", ".join("%s (%s)" % (p_, " ".join(x_)) for p_, x_ in rows[:20]) + (" +%d more" % (len(rows) - 20) if len(rows) > 20 else "")
                               + ((" (+%d record(s) not shown: its key is no chart id, or its list holds no visit id - see the insurance-check register)" % odd) if odd else ""))
    (_sam, _samx), (_nbd, _nbdx) = _byc("same_person"), _byc("no_birth_date")
    # 11/25/2026 (round 2 of the second review): the insurance check holds under no_birth_date also a chart whose feed patient came with two DIFFERENT real birth dates
    # while the chart carries none - and the sentence below, 'neither Claimocity nor the chart carries a real birth date', was untrue of it: Claimocity had sent two. The
    # record now says which case it is (no_birth_date_case, a fixed word) and such a chart has a sentence of its own. A record without the word - an older one - or with
    # anything else in its place reads as before; the word is only compared, never printed.
    _nbt = [r_ for r_ in _nbd if ver[r_[0]].get("no_birth_date_case") == "two dates"]; _nbd = [r_ for r_ in _nbd if r_ not in _nbt]
    if _sam or _samx: L("  - TOP OF THE REPORT - SAME PERSON? %d chart(s) whose name or birth date is not what Claimocity sent for the visits on it: no paid look-up was bought and no plan was added (the look-up would be asked about the CHART's person) - for William: is the visit on the right chart? On his yes the insurance check is run again for that chart with --same-person; on his no the visit belongs on the proper chart (William 11/9/2026): %s" % (len(_sam), _whoc(_sam, _samx)))
    if _nbd or _nbdx: L("  - TOP OF THE REPORT - NO BIRTH DATE ON EITHER SIDE: %d chart(s) with no active plan where neither Claimocity nor the chart carries a real birth date - no paid look-up can be asked without one; a face sheet is needed: %s" % (len(_nbd), _whoc(_nbd, _nbdx)))
    if _nbt: L("  - TOP OF THE REPORT - TWO BIRTH DATES FROM CLAIMOCITY, NONE ON THE CHART: %d chart(s) with no active plan where Claimocity sent two different real birth dates for one patient and the chart carries none of its own - nobody knows which of the two to ask with, so no paid look-up was bought; a face sheet is needed: %s" % (len(_nbt), _whoc(_nbt, 0)))
    if _svp: L("  - TOP OF THE REPORT - SAVE NOT AS ASKED: %d visit(s) on %d chart(s) - the order reads right but the save lost a charge or the admission date (see the hold line): %s" % (len(_svp), len({p_ for p_, _x in _svp}), _who2(_svp)))
except Exception as _e:                                    # never stops the digest
    L("  - TOP OF THE REPORT - the insurance-order lines could not be built (%s) - read no_order_list / order_differs / order_unread / save_problem / same_person / no_birth_date in the insurance-check register." % type(_e).__name__)
L("- Lead payer on released charts: " + ", ".join("%s %d" % (k, v) for k, v in leads.most_common()))
L("- Visit insurance orders changed (saves sent and accepted by AdvancedMD): %d; plans added from discovery / feed IN1: %d" % (orders_changed, len(plans_added)))
for pid, f in plans_added: L("  - %s: %s" % (pid, f))
L("- Holds (William) - %s (a visit whose insurance order is empty bills nothing until it is saved again):" % _HELD)
for pid, h in holds.items(): L("  - %s: %s%s%s" % (pid, "; ".join(str(x).replace(" - " + _HELD, "").replace(" - " + _NOCLAIM, "") for x in h)[:400], (" - " + _HELD) if any(_HELD in str(x) for x in h) else "",
                                (" - " + _NOCLAIM) if any(_NOCLAIM in str(x) for x in h) else ""))      # each ending said once; a chart with no plan (empty insurance orders) gets the NO CLAIM words
L("")
L("## Claim Inspector pass")
L("- fixed %d visits, advisories bypassed on %d, laterality logged %d, held %d (Pattern 24078 CCI: 99309 same day as the 10/22 CCM)." % (len(insp.get("fixed", [])), len(insp.get("bypassed", [])), len(insp.get("laterality", [])), len(insp.get("held", []))))
# November 12, 2026 - fix round 2 (K17, review note G5): a held row whose visit a LATER retry entry of the same register freed (no longer listed, or the line
# came off and the visit went out) is said to be free; the held row itself stays in the register (the import's never-held proof rule reads it)
_freedv = {}
try:
    for _e2 in (insp.get("quality_removed") if isinstance(insp, dict) and isinstance(insp.get("quality_removed"), list) else []):
        if isinstance(_e2, dict) and re.sub(r"\D", "", str(_e2.get("visit") or "")): _freedv[re.sub(r"\D", "", str(_e2["visit"]))] = bool(_e2.get("retry_of")) and (_e2.get("listed") is False or (_e2.get("void_ok") is True and _e2.get("released") is True))
except Exception: _freedv = {}
for h in insp.get("held", []): L("  - vst%s %s: %s%s" % (h["visit"], h["pid"], h["why"][:120], " - then freed by this run's retry pass: the visit is free" if _freedv.get(re.sub(r"\D", "", str(h.get("visit") or ""))) else ""))
# A new admission (William 11/25/2026: a 99223 after follow-up hospital visits is valid - inpatient hospital, then inpatient rehab): the step bypasses the Claim
# Inspector's Pattern 692. Said AFTER the held rows (they belong to the 'held N' line above), by visit - a visit once, whatever the number of its entries; a visit
# that is on the held list for another edit and a bypass AdvancedMD did not accept are named as such
try:
    _n9 = lambda x: re.sub(r"\D", "", str(x or ""))
    _byp = [b for b in (insp.get("bypassed") if isinstance(insp, dict) and isinstance(insp.get("bypassed"), list) else []) if isinstance(b, dict) and "692" in [str(x) for x in (b.get("patterns") or [])] and _n9(b.get("visit"))]
    _heldv = {_n9(h.get("visit")) for h in (insp.get("held") if isinstance(insp.get("held"), list) else []) if isinstance(h, dict)}
    _okv = sorted({_n9(b.get("visit")) for b in _byp if b.get("ok") is not False}); _refv = sorted({_n9(b.get("visit")) for b in _byp if b.get("ok") is False} - set(_okv))
    if _okv:
        _free = [v for v in _okv if v not in _heldv]; _also = [v for v in _okv if v in _heldv]
        _who = {}      # visit -> " (chart, service date)" from the import register of this batch, where it has the visit
        try:
            for _c in (reg.get("created") if isinstance(reg, dict) and isinstance(reg.get("created"), list) else []):
                if isinstance(_c, dict) and _n9(_c.get("visit")): _who[_n9(_c.get("visit"))] = " (%s, %s)" % (_c.get("pid") or "chart ?", _c.get("dos") or "date ?")
        except Exception: _who = {}
        _nm = lambda v: "vst" + v + _who.get(v, "")
        L("- New admission (William 11/25/2026: a 99223 after follow-up hospital visits is valid - inpatient hospital, then inpatient rehab): the Pattern 692 edit was bypassed on %d visit(s)%s%s." % (
            len(_okv), (" - %s: not held, nothing for William" % ", ".join(_nm(v) for v in _free)) if _free else "", ("%s %s: on the held list above for another edit" % (";" if _free else " -", ", ".join(_nm(v) for v in _also))) if _also else ""))
    if _refv: L("- New admission: AdvancedMD did not accept the bypass of the Pattern 692 edit on %s - the edit is still listed; the next columns pass bypasses it again." % ", ".join("vst" + v for v in _refv))
except Exception: pass
# ---- which chart, birth dates, the rehab unit (William 11/25/2026) ---------------------------------------------------------------------------------------
# Each part reads ONE register and stands alone: a part that cannot be built says so in one line and the digest goes on. Nothing here is taken from the match
# file (names and dates - it never leaves the workspace); the identity register holds chart ids, Claimocity ids, rule numbers and the fixed words of
# feed_identity.py, and a value that is NOT one of those words is not printed (this digest goes to Drive).
# (_T, _pat_ok and _fid_ok - a top line, a chart id or nothing, a Claimocity id or a word in its place - stand at the top of this file since 11/25/2026)
# feed messages that could not be read (feed_parse_dft_1028.py, 11/25/2026: one broken message no longer stops the feed - it is passed over and counted in
# registers/feed_unreadable_<stamp>.json). Said at the top: nothing of such a message was entered. Only a file date (8 digits), a message number and the
# parse's two fixed sentences are printed; a row that is anything else is counted and not copied.
# 11/25/2026 (the verification): the line said 'ask Claimocity to send the file again; the next ingest reads it when it arrives' - but the file had been
# registered as done, every feed file is named by its day, and the copy job never copies a name the bucket already holds: the file sent again was never
# read. The ingest now keeps such a file UNREGISTERED and says which in the identity register; this line says so, and what ends it.
_UW = ("no patient line", "a line of the message is cut short", "a charge line carries no whole procedure code", "no charge line", "the patient line carries no Claimocity id")      # the parse step's five fixed sentences (the self-test holds the two lists together)
_unf = "registers/feed_unreadable_%s.json" % STAMP
_hu, _hw = _held("not_registered_unreadable"), _held("registered_anyway_unreadable")      # the files kept back, and the files registered on William's word, FOR A MESSAGE THAT COULD NOT BE READ (a file registered on his word for a refused visit is not one of them)
_kept_ = ("every start reads it again (a visit already in AdvancedMD is not entered twice), enters what is missing as soon as the file it reads carries these messages whole, and says this again until then. What ends it: "
          "Claimocity's whole file in the bucket - the copy job does not replace a file the bucket already holds, so the object download__<file name> has to be deleted there first (a run's key cannot) - "
          "or William's word that the message is lost, and then ONE ingest with --register-anyway <file name>")
_ends = ("of their files, NOT REGISTERED: %s - %s; REGISTERED ON WILLIAM'S WORD: %s - its messages are given up and it is not read again" % (_fnames(_hu), _kept_, _fnames(_hw))) if _hu and _hw else \
        ("their file is NOT REGISTERED (%s): %s" % (_fnames(_hu), _kept_)) if _hu else \
        ("their file was REGISTERED ON WILLIAM'S WORD (%s): the messages are given up and not read again" % _fnames(_hw)) if _hw else \
        "whether their file was registered is in the ingest's own log (this batch has no identity register that says so) - ask Claimocity whether its file is whole"
if os.path.exists(_unf):
    try:
        _unr_ = json.load(open(_unf)); _um = _unr_.get("messages") if isinstance(_unr_, dict) else None
        if not isinstance(_um, list): raise ValueError("no list of messages")
        _uok = ["%s message %d (%s)" % (u_["file"], u_["message"], u_["why"]) for u_ in _um if isinstance(u_, dict) and isinstance(u_.get("file"), str) and re.fullmatch(r"\d{8}|\?", u_["file"])
                and isinstance(u_.get("message"), int) and not isinstance(u_.get("message"), bool) and u_.get("why") in _UW]
        if _um:
            L(""); L("## Feed messages that could not be read")
            _T("%d feed message(s) could not be read and their visits are NOT entered%s%s - %s (the register: %s)." % (
                len(_um), (": file " + "; file ".join(_uok[:20]) + (" +%d more" % (len(_uok) - 20) if len(_uok) > 20 else "")) if _uok else "",
                (" (%d row(s) of the register are not a file date, a message number and the fixed words - not shown)" % (len(_um) - len(_uok))) if len(_um) > len(_uok) else "", _ends, _unf))
    except Exception as _e:
        L(""); L("## Feed messages that could not be read"); _T("%s could not be read (%s) - the parse step counted feed messages it could not read; see logs/claimocity_%s_parse.log%s" % (
            _unf, type(_e).__name__, STAMP, (" - every file of the batch is kept unregistered and read again by the next start (%s)" % _fnames(_hu)) if _hu else ""))
elif _hu or _hw:      # the ingest itself counted a message with a charge line and no Claimocity id (the parse step that ran did not): its log names it
    L(""); L("## Feed messages that could not be read"); _T("a feed message carries a charge line and no Claimocity id and its visit is NOT entered - %s (the ingest's log names the file date)." % _ends)
_chart_section = False      # the birth-date line stands under 'Which chart' when that section is there, else under a heading of its own
if os.path.exists(_idf):
    try:
        _idr = json.load(open(_idf))
        if not isinstance(_idr, dict): raise ValueError("no JSON object")
        try: import feed_identity as _FI
        except Exception: _FI = None
        _pats = [p_ for p_ in (_idr.get("patients") if isinstance(_idr.get("patients"), list) else []) if isinstance(p_, dict)]
        _cn = _idr.get("counts") if isinstance(_idr.get("counts"), dict) else {}
        _num = lambda k_: _cn.get(k_) if isinstance(_cn.get(k_), int) and not isinstance(_cn.get(k_), bool) else "?"
        _rules = collections.Counter(p_.get("rule") for p_ in _pats if isinstance(p_.get("rule"), int) and not isinstance(p_.get("rule"), bool) and 0 <= p_.get("rule") <= 9)
        # 11/25/2026 (the verification): a key several Claimocity ids share that got no chart is ONE row with every id (the resolve step's answer 'several Claimocity ids under
        # one name are not known to be one person'). The line named the first id alone - which can be the id that HAS a chart through a key of its own, its visit entered - and the
        # id without a chart stood nowhere in the digest; two patients waited where the count said one. Now every id of such a row is named, each with the chart it has through a
        # row of its own, the count line counts patients, and - when the driver carried it ("each") - the line says what the rule gives each id on its own.
        _own = {}      # Claimocity id -> the chart it has through a row of its own
        for p_ in _pats:
            for i_ in (p_.get("feed_ids") if isinstance(p_.get("feed_ids"), list) else []):
                if isinstance(i_, str) and _pat_ok(p_.get("chart")): _own.setdefault(i_, p_["chart"])
        _WSH = getattr(_FI, "WHY_SHARED", "several Claimocity ids under one name are not known to be one person")
        def _sharers(p_):      # the ids of a shared key that got no chart, else []
            _i = [i_ for i_ in (p_.get("feed_ids") if isinstance(p_.get("feed_ids"), list) else []) if isinstance(i_, str)]
            return _i if (len(_i) > 1 and not _pat_ok(p_.get("chart")) and p_.get("rule") == 0 and p_.get("why") == _WSH) else []
        _waits = [i_ for p_ in _pats for i_ in _sharers(p_) if i_ not in _own]      # each id of a shared key that has no chart anywhere is a patient of its own
        _single = [p_ for p_ in _pats if not _sharers(p_)]
        L(""); L("## Which chart (William 11/25/2026: a feed patient goes to the chart that patient already has - also when Claimocity sends a wrong birth date or none)"); _chart_section = True
        L("- %s feed patient(s) known from the patient map; %d looked up%s; %d new chart(s) made; %d with NO chart." % (
            _num("known from the patient map"), len(_single) + len(_waits), (" - " + ", ".join("rule %d x%d" % (k_, _rules[k_]) for k_ in sorted(_rules, key=lambda r_: (r_ == 0, r_)))) if _rules else "",
            sum(1 for p_ in _pats if p_.get("new_chart") is True and _pat_ok(p_.get("chart"))), sum(1 for p_ in _single if not _pat_ok(p_.get("chart"))) + len(_waits)))
        for p_ in _pats:
            _ids = [i_ for i_ in (p_.get("feed_ids") if isinstance(p_.get("feed_ids"), list) else []) if isinstance(i_, str)]; _fid = _fid_ok(_ids[0] if _ids else ""); _ch = _pat_ok(p_.get("chart"))
            _left = sorted(str(x_) for x_ in p_["withheld"] if x_ in ("rule", "why", "flags", "candidates", "evidence", "feed_dob", "for_william")) if isinstance(p_.get("withheld"), list) else []
            _badw = _left or (_FI.problems(p_) if _FI else ["why", "flags"])       # words that are not the rule's own are never printed
            if _badw:
                _T("Claimocity id %s -> %s: what the identity rule said was NOT copied to the register (%s not in its fixed words) - read logs/claimocity_%s_resolve.log in the workspace" % (_fid, _ch or "no chart", ", ".join(_badw), STAMP))
                continue
            if _sharers(p_):      # ONE line that names every id of the row
                _each = p_.get("each") if isinstance(p_.get("each"), list) else []
                _each = _each if _each and all(isinstance(e_, list) and len(e_) == 2 and e_[0] in _ids and re.fullmatch(r"[0-9A-Fa-f]{24}", str(e_[0])) and isinstance(e_[1], str) and re.fullmatch(r"pat[0-9]+|a new chart|no chart", e_[1]) for e_ in _each) else []
                _T("no chart chosen and none made for Claimocity id(s) %s: %s (%s)%s" % (", ".join(_fid_ok(i_) for i_ in _ids), p_["why"],
                   "; ".join(["%s has %s through a name-and-date key of its own" % (_fid_ok(i_), _own[i_]) for i_ in _ids if i_ in _own] + ["%s has no chart" % _fid_ok(i_) for i_ in _ids if i_ not in _own]) if any(i_ in _own for i_ in _ids) else "none of them has a chart",
                   (" - each on its own: %s" % "; ".join("%s -> %s" % (e_[0], e_[1]) for e_ in _each)) if _each else ""))
                continue
            _tops = _FI.william_lines(p_, _ch, [i_ for i_ in _ids if re.fullmatch(r"[0-9A-Fa-f]{24}", i_)] or "")      # every Claimocity id of the row is named (the rule's lines take a list since 11/25/2026 - a row can stand for several ids)
            for t_ in _tops: _T(t_)
            if not _tops and not _ch and p_.get("rule") == 0: L("  - no chart yet for Claimocity id %s: %s" % (_fid, p_["why"]))      # a wait for the next run (feed_identity.new_chart_waits): said, no question for William
            elif not _tops and p_.get("flags"): L("  - %s: %s (%s)" % (_ch or "no chart", p_["why"], "; ".join(p_["flags"])))      # a match the rule had to explain (a slip in the date, no date from Claimocity): said here, not at the top
        for n_ in (_idr.get("notes") if isinstance(_idr.get("notes"), list) else []):      # the driver's own lines (11/25/2026: the ingest fills them now) - Claimocity ids, chart ids and fixed words
            # a line that looks like it holds a date or a LAST, FIRST name is left out - looked for with the Claimocity ids and chart ids taken out (an id that begins with capital letters behind a comma was taken for a name)
            if isinstance(n_, str) and not re.search(r"[0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4}|,\s*[A-Z]{2,}", re.sub(r"\b[0-9A-Fa-f]{24}\b|\bpat[0-9]+\b", " ", n_)): _T(n_[:700])
        _nr = [f_ for f_ in (_idr.get("not_registered") if isinstance(_idr.get("not_registered"), list) else []) if isinstance(f_, str) and re.fullmatch(r"[0-9A-Za-z_.\-]{1,80}", f_)]
        if _nr: _T("NOT REGISTERED: %d feed file(s) hold a patient with no chart (%s) - the next start reads them again; a visit already in AdvancedMD is not entered twice" % (len(_nr), ", ".join(_nr[:20]) + (" +%d more" % (len(_nr) - 20) if len(_nr) > 20 else "")))
        _rp = [(r_.get("feed_id"), _pat_ok(r_.get("was")), _pat_ok(r_.get("now"))) for r_ in (_idr.get("repointed") if isinstance(_idr.get("repointed"), list) else []) if isinstance(r_, dict) and _pat_ok(r_.get("now"))]
        if _rp: L("- Patient map: %d feed patient(s) now go to the repository's chart - %s. Visits the feed entered on the earlier chart belong on the new one (William 11/9/2026)." % (
            len(_rp), ", ".join("%s (was %s, now %s)" % (_fid_ok(f_), w_ or "?", n2_) for f_, w_, n2_ in _rp[:20]) + (" +%d more" % (len(_rp) - 20) if len(_rp) > 20 else "")))
    except Exception as _e:
        _T("the which-chart lines could not be built (%s) - read registers/feed_identity_%s.json and logs/claimocity_%s_resolve.log" % (type(_e).__name__, STAMP, STAMP))
# the new-chart step's failed rows (a patient who got no chart): said once here when the identity register did not already say it
try:
    _nf = [f_ for f_ in (newc.get("failed") if isinstance(newc, dict) and isinstance(newc.get("failed"), list) else []) if isinstance(f_, dict)]
    if _nf and not os.path.exists(_idf): _T("NEW CHART NOT MADE for %d feed patient(s) (Claimocity id %s) - their visits are not entered; see registers/feed_newcharts_%s.json" % (len(_nf), ", ".join(_fid_ok(f_.get("feed_id")) for f_ in _nf[:10]), STAMP))
except Exception: pass
# 11/25/2026 (the verification): what is for William about a NEW CHART of this batch that the identity register does not list - the register could not be written
# (the ingest says 'IDENTITY REGISTER NOT WRITTEN') or holds no row for it. Until then the question about a possible duplicate chart, and the face sheet for a chart
# made with no birth date, stood in no digest. From the new-chart register's own rows: rule 9, the identity rule's fixed flags, real / none - chart ids only.
try:
    _listed = {p_.get("chart") for p_ in (_IDR.get("patients") if isinstance(_IDR.get("patients"), list) else []) if isinstance(p_, dict)}
    _nfrom = " (from the new-chart register - the identity register of this batch does not list this chart)"
    for c_ in (newc.get("created") if isinstance(newc, dict) and isinstance(newc.get("created"), list) else []):
        if not (isinstance(c_, dict) and c_.get("rule") == 9 and c_.get("for_william") is True and _pat_ok(c_.get("pid")) and c_["pid"] not in _listed): continue
        _fl = [f_ for f_ in (c_.get("flags") if isinstance(c_.get("flags"), list) else []) if isinstance(f_, str)]
        if "same-name charts not used" in _fl: _T("new chart %s was made beside same-name charts with other birth dates and no number in common - same person or not? The charts are named in logs/claimocity_%s_resolve.log%s" % (c_["pid"], STAMP, _nfrom))
        elif "list of same-name charts may be incomplete" in _fl: _T("new chart %s was made although AdvancedMD's list of same-name charts may be incomplete - is there a chart of this patient already?%s" % (c_["pid"], _nfrom))
        if c_.get("dob") == "none": _T("new chart %s was made: Claimocity sent %s - face sheet needed%s" % (c_["pid"], "two different birth dates" if "Claimocity sent two birth dates" in _fl else "no birth date", _nfrom))
except Exception as _e: _T("what is for William about this batch's new charts could not be read from registers/feed_newcharts_%s.json (%s)" % (STAMP, type(_e).__name__))
# birth dates: what the import's rows say about the feed's date and the chart's (dob_note - fixed words, never a date). The words are the import's own line
# 'BIRTH DATES:' (claimocity_import.py birth_dates_line), built here from the register so that the digest has it without a run copying a log line.
try:
    _dn = collections.defaultdict(set)
    for x in reg["created"]:
        if isinstance(x, dict) and isinstance(x.get("dob_note"), str) and _pat_ok(x.get("pid")): _dn[x["pid"]].add(x["dob_note"])
    _ord = lambda p_: (int(re.sub(r"\D", "", p_) or 0), p_); _charts = sorted(_dn, key=_ord)
    _some = lambda it_: ", ".join(it_[:12]) + ((" +%d more" % (len(it_) - 12)) if len(it_) > 12 else "")
    _KINDS = ("one digit", "two digits swapped", "month and day swapped", "one day apart", "far")
    _differ = ["%s %s" % (p_, " / ".join(k_ for k_ in _KINDS if "differs: " + k_ in _dn[p_])) for p_ in _charts if any("differs: " + k_ in _dn[p_] for k_ in _KINDS)]
    _grp = lambda w_: [p_ for p_ in _charts if w_ in _dn[p_]]
    _nofeed, _nochart, _neither = _grp("no birth date from Claimocity"), _grp("chart has no birth date"), _grp("no birth date on either side"); _unread = _grp("chart not read")      # (11/25/2026, review: not read is not 'no birth date' - until then such a row fell out of this line)
    _parts = (["feed and chart differ on %d chart(s) (%s)" % (len(_differ), _some(_differ))] if _differ else []) + (["Claimocity sent no birth date for %d chart(s) (%s)" % (len(_nofeed), _some(_nofeed))] if _nofeed else []) \
        + (["%d chart(s) carry no birth date themselves (%s)" % (len(_nochart), _some(_nochart))] if _nochart else []) + (["no birth date on either side for %d chart(s) (%s)" % (len(_neither), _some(_neither))] if _neither else []) \
        + (["%d chart(s) could not be read (%s) - nobody knows their birth date for this batch" % (len(_unread), _some(_unread))] if _unread else [])
    if _parts:
        if not _chart_section: L(""); L("## Birth dates (Claimocity's and the chart's)")
        L("- Birth dates: %s. Each visit went on the chart as it stands; the chart's own date is the one used for the quality code and for every insurance look-up (William 11/25/2026: where the chart's date is right and Claimocity's is wrong, the chart's stays)." % "; ".join(_parts))
except Exception as _e: L("- Birth dates: the line could not be built (%s) - the import register's rows carry dob_note." % type(_e).__name__)
# inpatient rehab (William 11/25/2026: the visits of the hospital's rehab unit go out at place of service 61; a rehab stay whose first visit went in at 21
# keeps 21 - no look-back, no mixing). The import's rows say it: stay.kind 'rehab', pos '61' (HCA REHAB) or kept at 21 (pos_kind 'rehab-stay-kept-21').
# 11/25/2026 (the second round of the verification - its finding about the counters, the digest's side): WHERE A VISIT STANDS is what AdvancedMD STORED where the import
# read it back (the row's pos_stored, one per charge line), read as pos61_monitor.py reads it (group_of): the stored places count when the read-back holds one for every
# line that was sent; with no read-back - none, an empty one, one of another length - what was sent counts. Until then the lines below went by what was SENT: a rehab visit
# AdvancedMD stored at 21 stood here as 'entered at HCA REHAB, place of service 61' and its stay was named as a new rehab stay at 61, while the import ('rehab 61 x0', POS
# NOT KEPT) and the monitor of the same run said that no visit is at 61. Such a visit now has its own words - 'sent at 61, stored at <place>', at the top of the report -
# is not counted as entered at 61 and names no new rehab stay.
try:
    _stay = lambda x: x.get("stay") if isinstance(x.get("stay"), dict) else {}
    _rh = [x for x in reg["created"] if isinstance(x, dict) and _stay(x).get("kind") == "rehab"]
    def _r61_sent(x):      # the place of service of every charge line as it was SENT
        _pl = x.get("pos_lines"); return [str(v_) for v_ in (_pl if isinstance(_pl, list) and _pl else [x.get("pos")]) if v_ not in (None, "")]
    def _r61_at(x):        # ... and where the visit STANDS: what AdvancedMD stored where the import read it back, else what was sent
        _ps = x.get("pos_stored"); _sn = _r61_sent(x)
        return [str(v_) for v_ in _ps] if isinstance(_ps, list) and _ps and len(_ps) == len(_sn) and all(v_ not in (None, "") for v_ in _ps) else _sn
    _a61 = [x for x in _rh if "61" in _r61_at(x)]                                      # a line of the visit stands at 61
    _n61 = [x for x in _rh if "61" in _r61_sent(x) and "61" not in _r61_at(x)]         # sent at 61, stored at another place: NOT at 61
    _k21 = [x for x in _rh if "61" not in _r61_sent(x) and "61" not in _r61_at(x)]     # a visit of a rehab stay that was kept at 21
    _held = [h for h in (insp.get("held") if isinstance(insp, dict) and isinstance(insp.get("held"), list) else []) if isinstance(h, dict)]
    _q61 = [h for h in _held if h.get("pos61") is True]; _qnf = [h for h in _held if str(h.get("why") or "").startswith("nursing-facility code under the hospital building")]
    if _rh or _q61:
        L(""); L("## Inpatient rehab (William 11/25/2026: the rehab unit's visits go out at place of service 61 and are watched until they are paid)")
        L("- %d visit(s) of a rehab stay entered at HCA REHAB, place of service 61 (%d chart(s)); %d visit(s) of a rehab stay that began at 21 kept at 21 - the comparison group (%d chart(s))%s." % (
            len(_a61), len({x.get("pid") for x in _a61}), len(_k21), len({x.get("pid") for x in _k21}),
            ("; %d visit(s) sent at 61 and stored at another place of service - NOT at 61, see the line at the top" % len(_n61)) if _n61 else ""))
        if _n61:      # chart, date of service, codes, visit and the stored place of each - ids, codes and dates of service only
            _r61_vst = lambda x: ("vst" + re.sub(r"\D", "", str(x.get("visit")))) if re.sub(r"\D", "", str(x.get("visit") or "")) else "visit ?"
            _r61_day = lambda x: x.get("dos") if isinstance(x.get("dos"), str) and re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", x.get("dos")) else "date ?"
            _r61_cds = lambda x: "+".join(c_ for c_ in (x.get("cpts") if isinstance(x.get("cpts"), list) else []) if isinstance(c_, str) and re.fullmatch(r"[A-Za-z0-9]{5}", c_)) or "code ?"
            _r61_plc = lambda x: "/".join(sorted({v_ for v_ in _r61_at(x) if re.fullmatch(r"[0-9]{1,2}", v_)})) or "?"
            _T("PLACE OF SERVICE 61 NOT KEPT: %d visit(s) of a rehab stay were sent at 61 and AdvancedMD stored another place of service - they are NOT at place of service 61, are not counted above as entered at HCA REHAB and name no new rehab stay: %s. For William before the claim run; a routine changes nothing on these visits (the import says the same in its line POS NOT KEPT; the payment monitor goes by what was stored too - a visit stored at 21 stands in its comparison group with the visits kept at 21, never among the visits at 61)" % (
                len(_n61), "; ".join("%s %s %s (%s) sent at 61, stored at %s" % (_pat_ok(x.get("pid")) or "chart ?", _r61_day(x), _r61_cds(x), _r61_vst(x), _r61_plc(x)) for x in _n61[:30]) + ((" +%d more - see the import register" % (len(_n61) - 30)) if len(_n61) > 30 else "")))
        _INIT = {"99221", "99222", "99223"}; _SIGNS = ("facility number", "new admission 1-2 days after an acute stay")
        _new = []
        for x in _a61:
            if _INIT & {str(c_) for c_ in (x.get("cpts") or [])} and _pat_ok(x.get("pid")):
                _sg = _stay(x).get("sign"); _d = str(x.get("dos") or ""); _new.append("%s %s (%s)" % (x["pid"], _d if re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", _d) else "date ?", _sg if _sg in _SIGNS else "its stay began at HCA REHAB"))
        if _new: L("- New rehab stay(s) at 61, by chart and date of the first visit: %s. A patient who went HOME and came back to the ACUTE hospital one or two days later reads the same way - say so on the board and that stay's visits go back to 21." % "; ".join(_new))
        for h in _q61: _T(str(h.get("why") or "")[:600] if str(h.get("why") or "").startswith("PLACE OF SERVICE 61:") else "PLACE OF SERVICE 61: AdvancedMD's Claim Inspector questions rehab visit vst%s (%s) - for William; nothing was changed" % (re.sub(r"\D", "", str(h.get("visit") or "")), _pat_ok(h.get("pid")) or "chart ?"))
    for h in _qnf: _T("vst%s %s: nursing-facility code under the hospital building - which building was the patient in? The visit is held, not moved (William 10/31/2026: such a visit was not in the rehab unit)" % (re.sub(r"\D", "", str(h.get("visit") or "")), _pat_ok(h.get("pid")) or "chart ?"))
except Exception as _e: _T("the inpatient-rehab lines could not be built (%s) - read stay / pos_kind in the import register and the held rows of the inspector register" % type(_e).__name__)
L("")
L("## Next")
L("- AMD's automatic claim run (~17:00 ET) sends every clean approved claim; the submission wizard sends sooner.")
L("- The integration must not re-post the files this run imported; registers/feed_import_%s.json is the duplicate/void list (claimocity_dupe_void.py)." % STAMP)
open(("feed_digest_%s.md" % STAMP), "w").write("\n".join(lines)); print("\n".join(lines))
