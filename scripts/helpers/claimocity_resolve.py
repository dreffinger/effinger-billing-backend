# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - step 2b, READ-ONLY):
# Decides, for every patient the match step gathered charts for, which chart is that person.
# THE CHART IS CHOSEN BY THE IDENTITY RULE (feed_identity.decide), ONCE PER CLAIMOCITY ID - NEVER BY A SINGLE SAME-NAME CHART ALONE
# (William 11/25/2026). Until then: several charts with the feed's date -> the most recent charge; no chart with the feed's date and
# exactly ONE chart of the same name -> that chart, without a word; two or more -> a NEW chart - which made a second chart on 11/8
# and on 11/17/2026 for a patient whose own chart carried the right date while the feed sent a wrong one.
#  Now rules 1 to 9 of feed_identity.py, the first that fits: the Claimocity id on the chart; the same date; the same date under
#  another first name; a Social Security or member number in common; a slip between the two dates; no date on one side or on both -
#  and only when none fits a new chart (rule 9; for William when same-name charts stood beside it). A patient nobody can decide
#  (rule 0) gets NO chart and none is made.
#  Where a rule leaves several charts the LIVE one is taken: a real date first, then the most recent non-void charge, then the most
#  charges, then the lowest chart id (gettxhistory through txh.fetch - read only for such a group, each chart once). A read that
#  fails or comes back as a fault is asked once more; failing again, the step STOPS with nothing decided - the live chart is never
#  guessed (until then a failed read counted as "no charges").
#  A name-and-date key that SEVERAL patients share (one name with no birth date under two Claimocity ids; the import reads the chart
#  by the key, so it can carry only one - 11/25/2026, review of the identity rule): each of them is decided on its own, like every
#  other patient, and the key gets a chart only when the rule gives every one of them the SAME chart (feed_identity.shared_answer -
#  then all their ids stand on the key, under the weaker of their answers). Otherwise nothing is written under it and no chart is
#  made for it (never one chart for two ids nobody knows to be one person): ONE line for William with the ids and what each would
#  get on its own. Until then such a key was decided for nobody before anything was weighed - neither visit was entered. (So "every
#  key the Claimocity id came with", below, means every key of its OWN.)
# Writes feed_match_<stamp>.json back, the same answer under EVERY name-and-date key the Claimocity id came with: "resolved" (the
# chart) and status FOUND (one chart) / AMBIGUOUS (the live one of several - or, with no "resolved", not decided) / MISSING with no
# "resolved" (= make a new chart: rule 9 only), and the fields the driver copies to the register on main, free of patient data:
# rule, why, flags, candidates, evidence, feed_dob, for_william. Refuses a match file this version's match step did not write.
# No AMD write. Prints Claimocity ids, chart ids, rule numbers and the fixed words of feed_identity.py - never a name, a date or a number;
# what is for William comes as lines that start "FOR WILLIAM: " (chart ids only - they belong at the top of the report).
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, json, sys, time, collections, datetime
import txh
try:
    import feed_identity as FI
except ImportError:      # a workspace that does not hold the rule yet: the repository clone's copy (the bootstrap and the driver's make_current copy the helpers from there)
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("feed_identity", "/home/claude/effinger-billing-backend/scripts/helpers/feed_identity.py"); FI = _iu.module_from_spec(_sp); _sp.loader.exec_module(FI)
MATCHF = "feed_match_%s.json" % STAMP
o = json.load(open(MATCHF))
TODAY8 = datetime.date.today().strftime("%Y%m%d")
older = [k for k, v in o.items() if not isinstance(v, dict) or v.get("identity_rule") != FI.IDENTITY_RULE_VERSION]
if older:      # an older claimocity_match.py chose by the date alone and marked the rest MISSING: nothing of it is taken over
    print("RESOLVE STOPPED: %d of the %d entries of %s were not written by this version's match step (identity rule %s). Nothing is decided and nothing is changed - copy the repository's feed helpers (claimocity_match.py, claimocity_resolve.py, claimocity_newcharts.py, feed_identity.py) and start the ingest again." % (len(older), len(o), MATCHF, FI.IDENTITY_RULE_VERSION))
    sys.exit(1)
amd.login_cached()
ACT = {}
def activity(pid):
    """(the date of the most recent charge that is not void, YYYYMMDD - how many such charges) of one chart, read once."""
    if pid in ACT: return ACT[pid]
    why = ""
    for n in (1, 2):
        try:
            root = txh.fetch(pid)
            if not any(e.tag == "Fault" or (isinstance(e.tag, str) and e.tag.endswith("}Fault")) for e in root.iter()):      # a fault brings no charge row: it is not "no charges"
                last = ""; cnt = 0
                for c in root.iter("charge"):
                    if c.attrib.get("void") == "1": continue
                    cnt += 1
                    last = max(last, FI.amd_dob(c.attrib.get("dos") or c.attrib.get("dateofservice") or ""))
                ACT[pid] = (last, cnt); return ACT[pid]
            why = "a fault"
        except Exception as e: why = type(e).__name__
        time.sleep(2)
    print("RESOLVE STOPPED: the charges of %s could not be read (asked twice: %s). The live chart of a group is never guessed: nothing is decided and nothing is changed - the next run reads the files again." % (pid, why))
    sys.exit(1)
groups = collections.OrderedDict()      # the Claimocity id(s) of one patient -> its own keys (its answer is written under them), the keys it shares with another patient, what the match step gathered for it
def patient(ids, src): return groups.setdefault(tuple(ids), {"keys": [], "shared": [], "lookup": src.get("lookup") or [], "cut": src.get("cut") or ""})
for k, v in o.items():
    if v.get("sharers"):
        for s in v["sharers"]: patient(s["ids"], s)["shared"].append(k)
    elif v.get("decided_for"): patient(v["decided_for"], v)["keys"].append(k)
count = collections.Counter(); answer = {}; said_for = {}; names_of = {}
for ids, p in groups.items():
    keys = p["keys"]
    mine = [k for k, v in o.items() if set(v.get("feed_ids") or []) & set(ids)]      # every key this patient came with - also one it shares with another
    feed = {"ids": list(ids), "names": [FI.split_name(k.rpartition("|")[0]) for k in mine], "dobs": [k.rpartition("|")[2] for k in mine], "cut": p["cut"]}
    cands = [{"id": c["pid"], "name": c["name"], "dob": c["dob"], "ev": c["ev"], "contra": c["contra"]} for c in p["lookup"]]
    d = FI.decide(feed, cands, TODAY8)
    if d["needs_activity"]:      # the live chart of several: their activity is read, then the rule is asked again
        for c in cands:
            if c["id"] in d["needs_activity"]: c["last_dos"], c["charges"] = activity(c["id"]); time.sleep(0.3)
        d = FI.decide(feed, cands, TODAY8)
    bad = FI.problems(d)
    if bad or d["needs_activity"]:
        print("RESOLVE STOPPED: the answer for %s is not in the fixed words (%s) - nothing is written." % (FI.show_id(ids[0]), ", ".join(bad) or "activity still missing")); sys.exit(1)
    answer[ids] = d; names_of[ids] = feed["names"]
# 11/25/2026 (review of the identity rule): one person under two NEW Claimocity ids in one batch (the second birth date a digit off, or none) got two
# new charts - the same two messages in two batches got one. Of the patients rule 9 gives a new chart, one whose name is a name candidate of another's
# waits (feed_identity.new_chart_waits): no chart in this run, its file is read again, and the next run weighs it against the chart made now.
_new = [ids for ids, p in groups.items() if p["keys"] and answer[ids]["new_chart"]]
for n in FI.new_chart_waits([{"names": names_of[i], "real": answer[i]["feed_dob"] == "real"} for i in _new]):
    answer[_new[n]] = FI.waits(answer[_new[n]])
    if FI.problems(answer[_new[n]]): print("RESOLVE STOPPED: the answer for %s is not in the fixed words - nothing is written." % FI.show_id(_new[n][0])); sys.exit(1)
for ids, p in groups.items():
    keys = p["keys"]; d = answer[ids]; more = " (+%d more id(s))" % (len(ids) - 1) if len(ids) > 1 else ""
    if not keys:      # a patient that comes ONLY under a key it shares: its answer is written (below) only when the rule gives every patient of that key the same chart - no chart is made on it, no line for William said from it
        print("%s%s on its own -> %s | rule %d | %s%s | under a key it shares with another Claimocity id: see below" % (FI.show_id(ids[0]), more, d["chart"] or ("a new chart" if d["new_chart"] else "no chart"), d["rule"], d["why"], " | " + "; ".join(d["flags"]) if d["flags"] else ""))
        continue
    if d["chart"]: status, said = ("FOUND" if len(d["group"]) == 1 else "AMBIGUOUS"), "rule %d: %s -> %s%s" % (d["rule"], d["why"], d["chart"], " (the live chart of %d)" % len(d["group"]) if len(d["group"]) > 1 else "")
    elif d["new_chart"]: status, said = "MISSING", "rule 9: %s - NEW CHART NEEDED" % d["why"]
    else: status, said = "AMBIGUOUS", "not decided: %s - no chart chosen, none made" % d["why"]
    for k in keys:
        v = o[k]; v.update({f: d[f] for f in FI.PHI_FREE_FIELDS}); v["status"] = status; v["pids"] = d["group"]; v["resolution"] = said
        if d["chart"]: v["resolved"] = d["chart"]
        else: v.pop("resolved", None)
    count["rule %d" % d["rule"]] += 1
    print("%s%s -> %s | rule %d | %s%s%s" % (FI.show_id(ids[0]), more, d["chart"] or ("NEW CHART" if d["new_chart"] else "NO CHART - it waits for the next run" if d["why"] == FI.WHY_SAME_RUN else "NO CHART"), d["rule"], d["why"],
                                           " | " + "; ".join(d["flags"]) if d["flags"] else "", " | FOR WILLIAM" if d["for_william"] else ""))
    said_for[ids] = FI.william_lines(d, d["chart"] or "", ids[0])
    for line in said_for[ids]: print("FOR WILLIAM: " + line)      # (for a new chart claimocity_newcharts.py says them again, with the chart's id)
# 11/25/2026 (review of the identity rule): a name-and-date key several patients share (one name, no real birth date - not known to be one person; the
# import can give the key only ONE chart). Each of them was decided on its own above; the key gets a chart only when the rule gave every one of them
# the SAME chart (feed_identity.shared_answer). Until then such a key was decided for nobody before anything was weighed: no chart, neither visit entered.
each = {}; counted = set()
for k, v in o.items():
    if not v.get("sharers"): continue
    them = [tuple(s["ids"]) for s in v["sharers"]]; d = FI.shared_answer([answer[i] for i in them]); ids = sorted(i for t in them for i in t); bad = FI.problems(d)
    if bad:
        print("RESOLVE STOPPED: the answer for %s is not in the fixed words (%s) - nothing is written." % (FI.show_id(ids[0]), ", ".join(bad))); sys.exit(1)
    each[k] = "; ".join("%s -> %s" % (FI.show_id(i[0]), answer[i]["chart"] or ("a new chart" if answer[i]["new_chart"] else "no chart")) for i in them)
    v.update({f: d[f] for f in FI.PHI_FREE_FIELDS}); v["pids"] = d["group"]; v["status"] = "FOUND" if len(d["group"]) == 1 else "AMBIGUOUS"
    if d["chart"]:
        v["resolved"] = d["chart"]; v["decided_for"] = ids; v["resolution"] = "rule %d: %s -> %s (the chart the rule gives each of the %d patients under this name, each on its own)" % (d["rule"], d["why"], d["chart"], len(them))
        print("%d Claimocity ids under one name with no birth date (%s) -> %s | each decided on its own, the rule gives them all this chart | rule %d | %s%s%s" % (
            len(ids), ", ".join(FI.show_id(i) for i in ids), d["chart"], d["rule"], d["why"], " | " + "; ".join(d["flags"]) if d["flags"] else "", " | FOR WILLIAM" if d["for_william"] else ""))
        for line in FI.william_lines(d, d["chart"], ids[0]):
            if not any(line in said_for.get(i, []) for i in them): print("FOR WILLIAM: " + line)      # (not twice, when one of them has said it under a key of its own)
    else: v.pop("resolved", None); v["decided_for"] = []; v["resolution"] = "not decided: %s - no chart chosen, none made (each on its own: %s)" % (d["why"], each[k])
    for i in them:
        if not groups[i]["keys"] and i not in counted: counted.add(i); count["rule %d" % (answer[i]["rule"] if d["chart"] else 0)] += 1      # a patient that has no key of its own is counted once, by the key it shares
for k, v in o.items():
    if not v.get("decided_for"): print("FOR WILLIAM: " + ("no chart chosen and none made for Claimocity id(s) %s: %s%s" % (", ".join(FI.show_id(i) for i in v.get("feed_ids") or []) or "(none)", v.get("why") if v.get("why") in FI.WHY_WORDS else "",
                                                                                                                         " (each on its own: %s)" % each[k] if k in each else "")))
json.dump(o, open(MATCHF + ".tmp", "w"), indent=1); _os.replace(MATCHF + ".tmp", MATCHF)      # written once, whole: a step that stopped above has changed nothing
print(collections.Counter(("resolved" in v, v["status"]) for v in o.values()))
william = len({tuple(v.get("decided_for") or v.get("feed_ids") or [k]) for k, v in o.items() if v.get("for_william")})      # the patients - or keys nobody could decide - with something for William
print("RESOLVE %d Claimocity patient(s): %s; new charts needed %d; for William %d." % (len(groups), ", ".join("%s x%d" % kv for kv in sorted(count.items())) or "none", count["rule 9"], william))
