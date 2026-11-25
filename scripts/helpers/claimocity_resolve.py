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
#  SINCE THE INDEPENDENT VERIFICATION OF 11/25/2026 (a rule without proof could put a visit on ANOTHER person's chart):
#  - THE WAIT covers every patient the same run would decide blind to a chart it is making. Until then only a patient the rule
#    gives a NEW chart waited for the new chart of the one before it. Now a patient whose own answer rests on what the same-name
#    charts look like (rules 5 to 8 - also where the patient map held that answer back) waits as well while a patient of the batch
#    it is related to (feed_identity.related: a name candidate, or rule 3's relation) gets a new chart in this run or waits for
#    one: no chart in this run, a plain line, its file is read again and the next run weighs it against every chart of the batch.
#    So does a patient that comes only under a key it shares - a chart is never made for such a patient, and it never counts as
#    the one whose chart is made. A patient with proof (rules 1 to 4) never waits, and a batch in which nobody gets a new chart
#    is decided as before. Each entry that waits names the Claimocity ids whose new chart it waits for ("waits_for" - the
#    new-chart step reads it and says so, for William, when that chart could not be made).
#  - TWO OF ONE BATCH ON ONE CHART: two patients of the batch whose real dates are far apart never both take one chart by the name
#    alone (feed_identity.same_chart_far: rule 6 twice put two people on one chart with no birth date) - none of them takes it,
#    for William, each with a line that names the Claimocity id and the chart.
#  - AN ID WITH PROOF KEEPS ITS CHART on a key several ids share: when the key itself gets no chart, the entry names the chart of
#    every id whose own answer is a chart by rules 1 to 4 ("by_proof": {Claimocity id: chart} - the import asks for the chart of
#    the message's OWN Claimocity id, and the driver takes these into the charts it names per id; "proof_rows": each such
#    patient's own answer in the fixed words, for a row of its own in the register on main). An id without proof stays
#    without a chart: "decided_for" then lists those ids, and the line for William names them and what each would get on its own.
#    When every id of the key has proof nothing is left to ask: the entry says so in fixed words and is no question for William.
#    A chart two ids claim by proof while the feed itself shows them to be two people ("apart") is nobody's by proof.
# Writes feed_match_<stamp>.json back, the same answer under EVERY name-and-date key the Claimocity id came with: "resolved" (the
# chart) and status FOUND (one chart) / AMBIGUOUS (the live one of several - or, with no "resolved", not decided) / MISSING with no
# "resolved" (= make a new chart: rule 9 only), and the fields the driver copies to the register on main, free of patient data:
# rule, why, flags, candidates, evidence, feed_dob, for_william. Refuses a match file this version's match step did not write.
# No AMD write. Prints Claimocity ids, chart ids, rule numbers and the fixed words of feed_identity.py - never a name, a date or a number;
# what is for William comes as lines that start "FOR WILLIAM: " (chart ids and Claimocity ids only - they belong at the top of the report).
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
count = collections.Counter(); answer = {}; said_for = {}; names_of = {}; real_of = {}
for ids, p in groups.items():
    keys = p["keys"]
    mine = [k for k, v in o.items() if set(v.get("feed_ids") or []) & set(ids)]      # every key this patient came with - also one it shares with another
    feed = {"ids": list(ids), "names": [FI.split_name(k.rpartition("|")[0]) for k in mine], "dobs": [k.rpartition("|")[2] for k in mine], "cut": p["cut"]}
    cands = [dict({"id": c["pid"], "name": c["name"], "dob": c["dob"], "ev": c["ev"], "contra": c["contra"]}, **{f: c[f] for f in ("owned", "also") if f in c}) for c in p["lookup"]]      # owned / also: what the match step read of the patient map and of the charts William called duplicates
    d = FI.decide(feed, cands, TODAY8)
    if d["needs_activity"]:      # the live chart of several: their activity is read, then the rule is asked again
        for c in cands:
            if c["id"] in d["needs_activity"]: c["last_dos"], c["charges"] = activity(c["id"]); time.sleep(0.3)
        d = FI.decide(feed, cands, TODAY8)
    bad = FI.problems(d)
    if bad or d["needs_activity"]:
        print("RESOLVE STOPPED: the answer for %s is not in the fixed words (%s) - nothing is written." % (FI.show_id(ids[0]), ", ".join(bad) or "activity still missing")); sys.exit(1)
    answer[ids] = d; names_of[ids] = feed["names"]; real_of[ids] = sorted({x for x in feed["dobs"] if FI.real_dob(x, TODAY8)})
def put(ids, d):      # an answer that takes the place of a patient's own (a wait; a chart that does not stand): in the fixed words, or nothing is written
    if FI.problems(d): print("RESOLVE STOPPED: the answer for %s is not in the fixed words - nothing is written." % FI.show_id(ids[0])); sys.exit(1)
    answer[ids] = d
# 11/25/2026 (review of the identity rule): one person under two NEW Claimocity ids in one batch (the second birth date a digit off, or none) got two
# new charts - the same two messages in two batches got one. Of the patients rule 9 gives a new chart, one the rule would weigh against another's
# new chart waits (feed_identity.new_chart_waits): no chart in this run, its file is read again, and the next run weighs it against the chart made now.
# 11/25/2026 (the independent verification): the same holds for every patient this run would otherwise decide BLIND to such a chart - one whose own
# answer rests on what the same-name charts look like (rules 5 to 8; also where the patient map held that answer back), and one that comes only
# under a key it shares (a chart is never made for it). Of three new ids of one name the one without a birth date went, by rule 7, on the chart of
# whichever dated id sorted first; a newcomer's second id went on a long-time namesake's chart in the run that made the newcomer a chart of her own.
def who(i): return {"names": names_of[i], "dobs": real_of[i], "real": answer[i]["feed_dob"] == "real"}
_new = [ids for ids, p in groups.items() if p["keys"] and answer[ids]["new_chart"]]      # a chart is made only for a patient with a key of its own: one that comes only under a shared key never counts as the one whose chart is made
_late = {_new[n] for n in FI.new_chart_waits([who(i) for i in _new])}; _made = [i for i in _new if i not in _late]
behind = collections.OrderedDict((i, [m for m in _made if FI.related(who(i), who(m))]) for i in _new if i in _late)      # a patient that waits -> the patients whose new chart it waits for (charts of this run)
for ids, p in groups.items():
    d = answer[ids]
    if ids in _new or not ((d["chart"] and d["rule"] in FI.RULES_BY_CHARTS) or d["why"] == FI.WHY_OWNED or (d["new_chart"] and not p["keys"])): continue      # (a patient with proof never waits)
    near = [j for j in _new if FI.related(who(ids), who(j))]      # the patients of the batch that get a new chart, or wait for one, and whose chart the rule would weigh this one against
    if near: behind[ids] = [m for m in _made if m in near or any(m in behind[j] for j in near if j in _late)]
for ids in behind: put(ids, FI.waits(answer[ids]))
def waits_for(i): return sorted({x for m in behind.get(i, []) for x in m})      # the Claimocity ids whose new chart a waiting patient waits for - written to its entries, for the new-chart step
# 11/25/2026 (the independent verification): two patients of one batch with far-apart real birth dates were both put on ONE chart that has no birth
# date (rule 6 twice) - the second one's visit on the first one's chart and plan. None of them takes a chart by the name alone that another patient
# of the batch, far apart from it, was given too: no chart, none made, for William - the chart named. One with proof of the chart keeps it.
_all = list(groups)
for n in FI.same_chart_far([{"chart": answer[i]["chart"], "rule": answer[i]["rule"], "dobs": real_of[i]} for i in _all]):
    put(_all[n], FI.undecided(answer[_all[n]], FI.WHY_FAR_PAIR, [answer[_all[n]]["chart"]]))
for ids, p in groups.items():
    keys = p["keys"]; d = answer[ids]; more = " (+%d more id(s))" % (len(ids) - 1) if len(ids) > 1 else ""
    if not keys:      # a patient that comes ONLY under a key it shares: its answer is written (below) only when the rule gives every patient of that key the same chart, or its own proof names its chart - no chart is made on it, no line for William said from it
        print("%s%s on its own -> %s | rule %d | %s%s | under a key it shares with another Claimocity id: see below" % (FI.show_id(ids[0]), more, d["chart"] or ("a new chart" if d["new_chart"] else "no chart"), d["rule"], d["why"], " | " + "; ".join(d["flags"]) if d["flags"] else ""))
        continue
    if d["chart"]: status, said = ("FOUND" if len(d["group"]) == 1 else "AMBIGUOUS"), "rule %d: %s -> %s%s" % (d["rule"], d["why"], d["chart"], " (the live chart of %d)" % len(d["group"]) if len(d["group"]) > 1 else "")
    elif d["new_chart"]: status, said = "MISSING", "rule 9: %s - NEW CHART NEEDED" % d["why"]
    else: status, said = "AMBIGUOUS", "not decided: %s - no chart chosen, none made" % d["why"]
    for k in keys:
        v = o[k]; v.update({f: d[f] for f in FI.PHI_FREE_FIELDS}); v["status"] = status; v["pids"] = d["group"]; v["resolution"] = said
        if d["chart"]: v["resolved"] = d["chart"]
        else: v.pop("resolved", None)
        if ids in behind: v["waits_for"] = waits_for(ids)
        else: v.pop("waits_for", None)
    count["rule %d" % d["rule"]] += 1
    print("%s%s -> %s | rule %d | %s%s%s" % (FI.show_id(ids[0]), more, d["chart"] or ("NEW CHART" if d["new_chart"] else "NO CHART - it waits for the next run" if d["why"] == FI.WHY_SAME_RUN else "NO CHART"), d["rule"], d["why"],
                                           " | " + "; ".join(d["flags"]) if d["flags"] else "", " | FOR WILLIAM" if d["for_william"] else ""))
    said_for[ids] = FI.william_lines(d, d["chart"] or "", list(ids))
    for line in said_for[ids]: print("FOR WILLIAM: " + line)      # (for a new chart claimocity_newcharts.py says them again, with the chart's id)
# 11/25/2026 (review of the identity rule): a name-and-date key several patients share (one name, no real birth date - not known to be one person; the
# import can give the key only ONE chart). Each of them was decided on its own above; the key gets a chart only when the rule gave every one of them
# the SAME chart (feed_identity.shared_answer). Until then such a key was decided for nobody before anything was weighed: no chart, neither visit entered.
# 11/25/2026 (the independent verification): when the key itself gets no chart, an id whose OWN answer is a chart by proof (rules 1 to 4) keeps that
# chart - "by_proof" names it; the import asks by the message's own Claimocity id - and only the ids without proof stay without one. Until then none
# of them was entered, run after run, also when each id stood on a chart of its own with its Claimocity id on it.
def own(i): return answer[i]["chart"] or ("a new chart" if answer[i]["new_chart"] else "no chart")      # what a patient would get on its own
each = {}; counted = set()
for k, v in o.items():
    if not v.get("sharers"): continue
    them = [tuple(s["ids"]) for s in v["sharers"]]; d = FI.shared_answer([answer[i] for i in them], apart=bool(v.get("apart"))); ids = sorted(i for t in them for i in t); proof = {}
    if not d["chart"]:
        proof = {i: answer[i]["chart"] for i in them if answer[i]["chart"] and answer[i]["rule"] in FI.RULES_BY_PROOF}
        if v.get("apart"): proof = {i: c for i, c in proof.items() if list(proof.values()).count(c) == 1}      # the feed itself shows them to be two people: a chart two of them claim is nobody's by proof
        if proof and len(proof) == len(them): d = FI.undecided(d, FI.WHY_EACH_PROOF); d["for_william"] = False      # every id of the key has a chart of its own: nothing is left to ask
        d["feed_dob"] = "real" if FI.real_dob(k.rpartition("|")[2], TODAY8) else "none"      # (what the key itself came with)
    left = [i for i in them if i not in proof]; bad = FI.problems(d)      # left: the patients of the key that get no chart through it
    if bad:
        print("RESOLVE STOPPED: the answer for %s is not in the fixed words (%s) - nothing is written." % (FI.show_id(ids[0]), ", ".join(bad))); sys.exit(1)
    each[k] = "; ".join("%s -> %s%s" % (FI.show_id(i[0]), own(i), " by proof (rule %d)" % answer[i]["rule"] if i in proof else "") for i in them) + ("; the Social Security numbers Claimocity sent for them differ - two people" if v.get("apart") else "")
    v.update({f: d[f] for f in FI.PHI_FREE_FIELDS}); v["pids"] = d["group"]; v["status"] = "FOUND" if len(d["group"]) == 1 else "AMBIGUOUS"
    for f in ("resolved", "by_proof", "proof_rows", "waits_for"): v.pop(f, None)
    under = "%d Claimocity ids under one name %s (%s)" % (len(ids), "and one birth date" if FI.real_dob(k.rpartition("|")[2], TODAY8) else "with no birth date", ", ".join(FI.show_id(i) for i in ids))
    if d["chart"]:
        v["resolved"] = d["chart"]; v["decided_for"] = ids; v["resolution"] = "rule %d: %s -> %s (the chart the rule gives each of the %d patients under this name, each on its own)" % (d["rule"], d["why"], d["chart"], len(them))
        print("%s -> %s | each decided on its own, the rule gives them all this chart | rule %d | %s%s%s" % (under, d["chart"], d["rule"], d["why"], " | " + "; ".join(d["flags"]) if d["flags"] else "", " | FOR WILLIAM" if d["for_william"] else ""))
        quiet = collections.OrderedDict()      # what is for William is said once for each Claimocity id: by the patients that have not said it under a key of their own, in one line where they say the same
        for i in them:
            if i not in said_for: quiet.setdefault((answer[i]["rule"], answer[i]["why"], tuple(answer[i]["flags"])), []).append(i)
        for same in quiet.values():
            for line in FI.william_lines(answer[same[0]], d["chart"], [x for i in same for x in i]): print("FOR WILLIAM: " + line)
    else:
        v["by_proof"] = {x: c for i, c in sorted(proof.items()) for x in i}      # the chart of each Claimocity id that has proof of its own chart (the driver takes it into the charts it names per id)
        v["proof_rows"] = [dict({"feed_ids": list(i), "chart": c}, **{f: answer[i][f] for f in FI.PHI_FREE_FIELDS}) for i, c in sorted(proof.items())]      # ... and each such patient's own answer in the fixed words, for a row of its own in the register on main (the entry's own fields are about the ids left without a chart)
        v["decided_for"] = sorted(x for i in (left if proof and left else them if proof else []) for x in i)      # the ids this entry's own words are about: those left without a chart (none listed, as before, when no id has proof)
        v["resolution"] = ("not decided: %s - no chart chosen, none made (each on its own: %s)" if left else "%s (%s)") % (d["why"], each[k])
        if d["why"] == FI.WHY_SAME_RUN: v["waits_for"] = sorted({x for i in left for x in waits_for(i)})
        print("%s -> no chart for the key itself | rule 0 | %s | each on its own: %s%s" % (under, d["why"], each[k], " | FOR WILLIAM" if d["for_william"] else ""))
        for line in FI.william_lines(d, "", [x for i in left for x in i]): print("FOR WILLIAM: %s%s" % (line, " (each on its own: %s)" % each[k] if d["why"] == FI.WHY_SHARED else ""))
        for i in proof:      # an id that goes to its chart by proof says its own (the FYI of rule 3) - unless it has said it under a key of its own
            if i not in said_for:
                for line in FI.william_lines(answer[i], answer[i]["chart"], list(i)): print("FOR WILLIAM: " + line)
    for i in them:
        if not groups[i]["keys"] and i not in counted: counted.add(i); count["rule %d" % (answer[i]["rule"] if (d["chart"] or i in proof) else 0)] += 1      # a patient that has no key of its own is counted once, by the key it shares
for k, v in o.items():      # a key nobody could weigh (no Claimocity id carries it; a message without an id shares it with one)
    if not v.get("decided_for") and not v.get("sharers"): print("FOR WILLIAM: " + ("no chart chosen and none made for Claimocity id(s) %s: %s" % (", ".join(FI.show_id(i) for i in v.get("feed_ids") or []) or "(none)", v.get("why") if v.get("why") in FI.WHY_WORDS else "")))
json.dump(o, open(MATCHF + ".tmp", "w"), indent=1); _os.replace(MATCHF + ".tmp", MATCHF)      # written once, whole: a step that stopped above has changed nothing
print(collections.Counter(("resolved" in v, v["status"]) for v in o.values()))
william = len({tuple(v.get("decided_for") or v.get("feed_ids") or [k]) for k, v in o.items() if v.get("for_william")})      # the patients - or keys nobody could decide - with something for William
print("RESOLVE %d Claimocity patient(s): %s; new charts needed %d; for William %d." % (len(groups), ", ".join("%s x%d" % kv for kv in sorted(count.items())) or "none", count["rule 9"], william))
