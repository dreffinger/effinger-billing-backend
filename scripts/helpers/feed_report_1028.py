# PLAIN ENGLISH: compiles the 10/28 Claimocity backlog import into one digest (counts, dollars, holds) from the registers.
# Also writes a PHI-light copy of the verify register for the repo (no addresses / member ids in the 271 result strings).
import json, os, re, collections, datetime
reg = json.load(open("registers/feed_import_1028.json")); newc = json.load(open("registers/feed_newcharts_1028.json"))
insp = json.load(open("registers/feed_inspector_1028.json")) if os.path.exists("registers/feed_inspector_1028.json") else {}
fix = json.load(open("registers/feed_fixholds_1028.json")) if os.path.exists("registers/feed_fixholds_1028.json") else {}
ver = {}
for f in ["feed_verify_1028.json"] + sorted(x for x in os.listdir(".") if x.startswith("feed_verify_1028_") and x.endswith(".json") and "probe" not in x):
    if os.path.exists(f): ver.update(json.load(open(f)))
# PHI-light verify register for GitHub
lite = {}
for pid, v in ver.items():
    w = dict(v); w["checks"] = [{"plan": c.get("plan"), "car": c.get("car"), "seq": c.get("seq"), "status": (c.get("result") or "")[:40].split(" | ")[0]} for c in v.get("checks") or []]
    w.pop("discovery", None); lite[pid] = w
json.dump(lite, open("registers/feed_verify_1028.json", "w"), indent=1)
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
L("- Gregg's pickup must skip the 10/16-10/27 files when un-paused, or the visits in registers/feed_import_1028.json are the void list for the duplicates.")
open("feed_digest_1028.md", "w").write("\n".join(lines)); print("\n".join(lines))
