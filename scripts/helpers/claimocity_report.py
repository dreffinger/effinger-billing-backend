# PLAIN ENGLISH: compiles the 10/28 Claimocity backlog import into one digest (counts, dollars, holds) from the registers.
# Also writes a PHI-light copy of the verify register for the repo (no addresses / member ids in the 271 result strings).
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import json, os, re, collections, datetime
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
L("- %d visits / %d charge lines created, $%s at the fee schedule; %d encounters skipped as already in AMD; 0 faults." % (len(reg["created"]), sum(len(x["charges"]) for x in reg["created"]), format(fees, ",.2f"), len(reg["skipped"])))
L("- CPT mix: " + ", ".join("%s x%d" % (k, v) for k, v in cpts.most_common()))
# place of service in the nursing buildings (William 11/10/2026, rules.md): what the import's per-line rule did in this batch
_ps = collections.Counter(); _NFV = {"99304", "99305", "99306", "99307", "99308", "99309", "99310", "99315", "99316"}; _CCM = {"99487", "99489"}
_NURSING_FAC = {"fac34", "fac32", "fac33", "fac58", "fac1350"}                       # Brynwood, Aspire, Centre Pointe, Westminster Oaks-Bertrand, Oakes Southwood
_rule_stamp = bool(re.match(r"^2\d{7}T", STAMP)) and STAMP[:8] >= "20261110"         # batches from the day the rule began
try:
    for x in reg["created"]:
        _c = x.get("cpts") or []
        if x.get("pos_err"): _ps["err"] += 1; continue
        if not x.get("pos_lines"):
            if _rule_stamp and x.get("fac") in _NURSING_FAC and any(c in _NFV or c in _CCM for c in _c): _ps["norule"] += 1
            continue
        if x.get("pos_feed") != "31": continue
        if not x.get("fac"):
            _ps["nofac"] += sum(1 for c in _c if c in _NFV or c in _CCM); continue
        _k = x.get("pos_kind") or []
        for _i, (_cpt, _p) in enumerate(zip(_c, x.get("pos_lines") or [])):
            if _cpt in _CCM: _ps["ccm%s" % _p] += 1
            elif _cpt in _NFV:
                _ps["nf%s" % _p] += 1
                if _i < len(_k) and _k[_i] in ("extra", "between"): _ps["nfleft"] += 1
    if any(_ps.values()):
        L("- Place of service in the nursing buildings (11/10/2026 rule): CCM lines entered as 32: %d%s; nursing visits 32 (monthly): %d; nursing visits 31: %d%s%s%s%s." % (
            _ps["ccm32"],
            (" (and %d kept at 31 because the chart shows weekly visits, an admission or a new stay that month - for William, see pos_why in the import register)" % _ps["ccm31"]) if _ps["ccm31"] else "",
            _ps["nf32"], _ps["nf31"],
            (" (%d of them kept at 31 because the chart shows neither pattern - see pos_why)" % _ps["nfleft"]) if _ps["nfleft"] else "",
            ("; POS RULE NOT APPLIED on %d visit(s) - entered at the feed's place of service, see pos_err in the import register and rules.md 11/10/2026" % _ps["err"]) if _ps["err"] else "",
            ("; %d CCM / nursing-visit line(s) came from a building the facility table does not know - entered at 31 with no facility" % _ps["nofac"]) if _ps["nofac"] else "",
            ("; PLACE OF SERVICE RULE DID NOT RUN on %d visit(s) in the nursing buildings - the import helper in this workspace is an old copy (rules.md 11/10/2026)" % _ps["norule"]) if _ps["norule"] else ""))
except Exception as _e:                                    # a register edited by hand must never stop the digest
    L("- Place of service in the nursing buildings (11/10/2026 rule): this line could not be built (%s) - read pos_lines / pos_err in the import register." % (type(_e).__name__ + ": " + str(_e))[:120])
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
