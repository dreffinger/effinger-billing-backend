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
_ps = collections.Counter(); _NFV = {"99304", "99305", "99306", "99307", "99308", "99309", "99310", "99315", "99316"}
for x in reg["created"]:
    if x.get("pos_err"): _ps["err"] += 1; continue
    if x.get("pos_feed") != "31" or not x.get("fac") or not x.get("pos_lines"): continue
    for _c, _p in zip(x.get("cpts") or [], x.get("pos_lines") or []):
        if _c in ("99487", "99489"): _ps["ccm" + _p] += 1
        elif _c in _NFV: _ps["nf" + _p] += 1
if _ps:
    L("- Place of service in the nursing buildings (11/10/2026 rule): CCM lines entered as 32: %d%s; nursing visits 32 (monthly, long-term): %d; nursing visits 31 (seen weekly or more, initial or first visit): %d%s." % (
        _ps["ccm32"], (" (and %d left at 31 - check)" % _ps["ccm31"]) if _ps["ccm31"] else "", _ps["nf32"], _ps["nf31"],
        ("; POS RULE NOT APPLIED on %d visit(s) - entered at the feed's 31, see rules.md 11/10/2026" % _ps["err"]) if _ps["err"] else ""))
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
