# PLAIN ENGLISH (the feed helpers are the repository's on every run - 11/10/2026, reviewers C2 and W1)
# Decides: whether the feed helpers in the workspace are the repository's copies, before the ingest or the retry starts any of them.
#   With the repository clone there (its claimocity_import.py carries the rule version the driver names), every file the runbook's step (c)
#   copies is compared byte for byte with the clone's copy and replaced when it differs - the same as step (c), now also on a run that
#   skipped that line, and not only when the import helper itself is old (C2: an older report or inspector ran with no word; W1: the
#   retry warned about an old import helper but entered visits with it). Without a usable clone, or for a file the clone lacks, a helper
#   that carries a version line (the lines tools/mirror/mirror.py protects - VERSION_LINES below) is checked by that line.
#   Whatever could not be replaced, compared or found is named in ONE warning that the driver puts at the end of its RESULT line.
# Never: holds or delays a visit (an old helper is said, never a reason to stop - rules.md part 6); touches anything but these files in the
#   workspace; talks to AdvancedMD.
# Used by claimocity_ingest.py and claimocity_retry_dx.py: make_current(their folder, the clone's scripts/helpers, their POS_RULE line).
import os, shutil
REPO_HELPERS = "/home/claude/effinger-billing-backend/scripts/helpers"
# the files the runbook's step (c) copies before every ingest, and this file itself
FEED_HELPERS = ("claimocity_import.py", "claimocity_report.py", "claimocity_inspector.py", "claimocity_verify.py", "claimocity_ingest.py",
                "claimocity_retry_dx.py", "feed_parse_dft_1028.py", "claimocity_helpers_current.py")
# the version lines mirror.py protects (the self-test checks that the two lists agree); the import helper and the two drivers carry the
# driver's own POS_RULE line. Since 11/11/2026 the parser carries a sentence too: a parser from before that day stops a whole batch at one
# message it cannot read (no PV1 segment, a short FT1 line), so without a clone it is checked like the others.
VERSION_LINES = {"claimocity_report.py": 'POS_REPORT_VERSION = "2026-11-12.2"', "claimocity_inspector.py": "every run tries the void and the re-save again for a visit stuck with its no-charge line",
                 "claimocity_verify.py": "the save is skipped only when the visit's insurance-order LIST",      # 11/10/2026 (round 7): a sentence only the list-aware version has
                 "feed_parse_dft_1028.py": "a message this parser cannot read is skipped and named"}                                       # 11/11/2026: a sentence only the parser that skips and names an unreadable message has
RULE_HELPERS = ("claimocity_import.py", "claimocity_ingest.py", "claimocity_retry_dx.py")
def _read(p):
    try: return open(p, "rb").read()
    except OSError: return None
def make_current(here, repo=REPO_HELPERS, rule=""):
    """-> (lines for the console, the warning for the RESULT line - "" when every helper is the repository's or carries its version line).
    here = the folder the driver runs from (the workspace); repo = the clone's scripts/helpers; rule = the driver's POS_RULE line."""
    marks = dict(VERSION_LINES, **{f: rule for f in RULE_HELPERS})
    def lacks(f):      # the workspace copy is missing or does not carry its version line
        h = _read(os.path.join(here, f)); return bool(marks.get(f)) and (h is None or marks[f].encode() not in h)
    clone = _read(os.path.join(repo, "claimocity_import.py"))
    usable = clone is not None and bool(rule) and rule.encode() in clone          # a clone of an OLDER rule never replaces newer workspace copies
    replaced = []; failed = {}; older = []
    for f in FEED_HELPERS:
        new = _read(os.path.join(repo, f)) if usable else None
        if new is not None:                                                       # the clone has it: the workspace copy must be the same bytes
            if _read(os.path.join(here, f)) == new: continue
            try: shutil.copy2(os.path.join(repo, f), os.path.join(here, f)); replaced.append(f)
            except Exception as e: failed[f] = type(e).__name__
        elif usable and not marks.get(f): failed[f] = "not in the repository copy"  # the clone lacks a file that has no version line to check it by
        elif lacks(f): older.append(f)                                            # no usable clone, or the clone lacks it: its version line decides
    lines = ["FEED HELPERS: %s differed from the repository copy - replaced by it before anything ran" % ", ".join(replaced)] if replaced else []
    warn = ""
    if lacks("claimocity_import.py"):                                             # judged after any replacement: the copy that will run
        warn += (" | PLACE OF SERVICE RULE NOT CURRENT: claimocity_import.py here is missing, an old copy or an earlier version of the rule and %s - for William to check: the place of "
                 "service of every nursing-building line this run entered, and the clinician and building of every visit whose patient has another message in the batch (a routine changes nothing on these visits)"
                 % (("could not be replaced (%s)" % failed.get("claimocity_import.py", "not in the repository copy")) if usable else "no repository copy was found"))
    nf = ["%s (%s)" % (f, w) for f, w in failed.items() if not (f == "claimocity_import.py" and warn)]
    no = ["%s%s" % (f, " (missing)" if _read(os.path.join(here, f)) is None else "") for f in older if f != "claimocity_import.py"]
    if nf: warn += " | FEED HELPERS NOT ALL CURRENT: %s could not be replaced by the repository copy - this run's digest, insurance check or inspector step may be an older version" % ", ".join(nf)
    if no: warn += " | FEED HELPERS NOT ALL CURRENT: %s %s no version line of this rule%s - this run's digest, insurance check or inspector step may be an older version" % (
        ", ".join(no), "has" if len(no) == 1 else "have", "" if usable else " and no repository copy was found")
    if warn: lines.append("FEED HELPERS: not all current - the RESULT line says which; it goes to the top of the report")
    return lines, warn
