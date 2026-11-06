#!/usr/bin/env python3
# PLAIN ENGLISH (the nightly insurance cascade's one-line record for the ehpa Practice Database - William 11/6/2026: "this section
#   on ehpa practice database does not appear to be updating like it should ... I would like it to update when the scheduled
#   nightly cascade runs").
# Decides: nothing. At the end of the nightly cascade the run states, in one command, what it checked and changed: pairs checked,
#   rows flagged, Stedi lookups, visits re-pointed / re-routed / re-sent, dollars re-sent, ERA dollars posted, write-offs, and a
#   one-line "what was done". This script writes that as practices/ehpa/registers/cascade_runs/<stamp>.json - the PHI-light
#   record main keeps - in exactly the shape the page's "Nightly insurance cascade" chart reads (collection cascade_runs: at, date,
#   checked, changed, dollars, done, note ...). tools/db/practice_db.py build --run <stamp> then turns it into the cascade_runs
#   document and the ArtifactData batch call; any later billing run's sweep picks the night up if that call was refused.
# Rules it uses: chart ids and dollars only. It REFUSES (exit 2) a --done / --note that the mirror's own PHI gate
#   (tools/mirror/phi_gate.py - the same rules every mirror commit applies: LAST,FIRST and Last, First names, pseudonym-map names,
#   MBIs, SSNs, member / Medicaid numbers, dates of birth or death) would rewrite or refuse, plus its own floor of patterns when the
#   gate cannot be imported - because the register is committed to GitHub main and the document is read by the page.
#   Numbers are whole counts and whole dollars (the chart draws counts). A stamp is the run stamp 2026-11-06T0535Z (also accepted
#   as 20261106T0535Z - it is written back in the dashed form the four backfilled nights of 11/4/2026 use).
#   SHELL RULE: the routine runs this as ONE bash command, so write NO dollar sign ANYWHERE in it - not in the bare numbers
#   (--dollars 160, --stedi-cost 8.40; "$160" reaches this script as "60", "$8.40" as ".40") and not inside the double quotes of
#   --done / --note (bash swallows "$1" out of "$160" and "(60, chart ...)" would be recorded). Write "160 dollars" in the text;
#   the page's Re-sent column comes from --dollars anyway. A value that looks swallowed (".40", "04", "(60, chart") is refused.
# Never touches: AdvancedMD, Stedi, the database itself (the model makes the ArtifactData call through practice_db.py).
# Usage (one plain command at the end of the run, after the money ledger and before the mirror):
#   python3 tools/db/cascade_record.py --stamp 2026-11-06T0535Z --checked 15 --flagged 2 --lookups 14 --changed 1 --dollars 160 \
#       --era-posted 0 --writeoffs 0 --stedi-cost 8.40 --commit 87c7fbd \
#       --done "1 hospital visit re-pointed to the BCBS Medicare Advantage plan (160 dollars, chart 17473090)" --note "15 visit-and-plan pairs checked, 2 flagged"
#   Options: --finished <ISO UTC> (default now)  --repo /home/claude/effinger-billing-backend  --kind "nightly cascade"
#            --session <url> (default $CLAUDE_SESSION_URL)  --dry (print the document, write nothing)
import os, sys, re, json, datetime

a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a else default
def usage(msg=""):
    sys.exit((msg + "\n" if msg else "") + "usage: cascade_record.py --stamp <run stamp> --checked N --changed N --dollars N --done \"...\" [--flagged N --lookups N "
             "--era-posted N --writeoffs N --stedi-cost X --commit <sha> --finished <ISO> --note \"...\" --repo <path> --dry]")

REPO = opt("--repo", "/home/claude/effinger-billing-backend")
NOW = datetime.datetime.now(datetime.timezone.utc)
stamp = opt("--stamp")
if not stamp: usage("--stamp is required")
m = re.match(r"^(\d{4})-?(\d{2})-?(\d{2})T(\d{2})(\d{2})Z$", stamp.strip())
if not m: usage("--stamp must look like 2026-11-06T0535Z")
y, mo, d, hh, mm = m.groups()
stamp = "%s-%s-%sT%s%sZ" % (y, mo, d, hh, mm)                      # the dashed form the existing cascade_runs documents use
at = "%s-%s-%sT%s:%s:00Z" % (y, mo, d, hh, mm)
date = "%s-%s-%s" % (y, mo, d)                                      # the night's date: 05:35Z is 12:35 AM EST / 1:35 AM EDT, the same calendar day

def swallowed(name, v):
    """"$704" reaches a bash-run script as "04", "$8.40" as ".40", "$1,234.56" as ",234.56" - the $ and the digit behind it are gone"""
    if re.match(r"^\s*(?:0\d|[.,])", str(v)): usage("%s = %r looks like a figure bash swallowed a $ from (write 704, never $704; no dollar sign anywhere in the command)" % (name, v))
def whole(name, required=False):
    v = opt(name)
    if v is None:
        if required: usage("%s is required" % name)
        return 0
    swallowed(name, v)
    try: n = int(round(float(str(v).replace("$", "").replace(",", ""))))
    except ValueError: usage("%s must be a number, got %r" % (name, v))
    if n < 0: usage("%s cannot be negative" % name)
    return n
def money(name):
    v = opt(name)
    if v is None: return 0.0
    swallowed(name, v)
    try: x = round(float(str(v).replace("$", "").replace(",", "")), 2)
    except ValueError: usage("%s must be a number, got %r" % (name, v))
    if x < 0: usage("%s cannot be negative" % name)
    return x

checked = whole("--checked", True); changed = whole("--changed", True); dollars = whole("--dollars", True)
flagged = whole("--flagged"); lookups = whole("--lookups"); era_posted = money("--era-posted"); writeoffs = money("--writeoffs")
stedi_cost = money("--stedi-cost")
done = (opt("--done") or "").strip(); note = (opt("--note") or "").strip()
if not done: usage("--done is required (one line: what was done, chart ids and dollars only)")
if not note: note = "%d visit-and-plan pair%s checked%s" % (checked, "" if checked == 1 else "s", (", %d flagged" % flagged) if flagged else "")
if len(done) > 300 or len(note) > 300: usage("--done and --note are one line each, 300 characters at most")
if "\n" in done or "\n" in note: usage("--done and --note are one line each")

# ---- the privacy check: the mirror's own gate first, this script's floor always ---------------------------------------------------------
NAME_RE = re.compile(r"\b([A-Z][A-Za-z'\-]+)(?: (?:JR|SR|II|III|IV))?,\s?([A-Z][A-Za-z'\-]+)\b")        # LAST,FIRST / Last, First / SMYTHE,Mary
TITLE_RE = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+){1,2})\b")                                          # First Last / First Middle Last
VOCAB = {"MEDICARE", "MEDICAID", "ADVANTAGE", "HUMANA", "SUNSHINE", "FLORIDA", "BLUE", "CROSS", "SHIELD", "STEDI", "CENTENE", "AETNA", "CIGNA",
         "UNITED", "UNITEDHEALTHCARE", "WELLCARE", "SIMPLY", "CAPITAL", "HEALTH", "PLAN", "PLANS", "PART", "MEDIGAP", "TRICARE", "CHAMPVA",
         "AMBETTER", "COMMUNITY", "CARE", "ORIGINAL", "DUAL", "COMPLETE", "AARP", "UHC", "BCBS", "OPTUM", "AVAILITY", "CLAIMOCITY",
         "ADVANCEDMD", "CHART", "CHARTS", "VISIT", "VISITS", "CLAIM", "CLAIMS", "ERA", "ERAS", "EASTERN", "STEP", "NO", "NONE", "OK",
         "ACTIVE", "INACTIVE", "CCM", "AWV", "ACP", "SNF", "ALF", "HCA", "TMH", "VA", "MA", "PPO", "HMO", "DOS", "CPT", "FCC", "LTC",
         "SMMC", "MMA", "DRIVE", "GMAIL", "WOINS", "WOLATE", "WONCS", "WOCAID2ND", "CR", "CI", "UNBILLED", "EXCLUSIONS", "AMD", "MBI",
         "HOSPICE", "CENTER", "BUTTON", "WILLIAM", "RE-SENT", "RE-POINTED", "RE-ROUTED",
         # carrier, facility and billing words a night's line may carry (the files below add every carrier and facility name on main)
         "HEALTHCARE", "HEALTHSPRING", "HCSC", "GOLD", "PLUS", "OPTIONS", "CHOICE", "HUMANACHOICE", "PREFERRED", "PARTNERS", "IMPROVEMENT",
         "SERVICE", "CORPORATION", "INSURANCE", "COMPANY", "LIFE", "NATIONAL", "SENIOR", "SUPPLEMENTAL", "HORIZONS", "HEALTHY", "EMPLOYEES",
         "HOSPITAL", "ASSOCIATION", "FIRST", "COAST", "RAILROAD", "BANKERS", "MUTUAL", "OMAHA", "AMERICAN", "GLOBE", "PHYSICIANS", "USAA",
         "ZELIS", "ECHO", "REGIONS", "DEVOTED", "CAREPLUS", "CHP", "AVMED", "MOLINA", "STAYWELL", "MAGELLAN", "TEXAS", "WASHINGTON",
         "PENDING", "INVESTIGATION", "DISCOVERY", "ELIGIBILITY", "LOOKUP", "LOOKUPS", "TIMELY", "FILING", "ANNUAL", "WELLNESS", "ADVANCE",
         "PLANNING", "CHRONIC", "MANAGEMENT", "INSPECTOR", "CHARGE", "CHARGES", "REVIEW", "REFRESH", "BOARD", "WORKING", "DENIALS",
         "MANDATORY", "APPROVALS", "MONEY", "LEDGER", "OUTSTANDING", "PRACTICE", "DATABASE", "FEED", "CENTER", "CHECK", "CHECKS", "LINE",
         "LINES", "NIGHT", "RUN", "PAIR", "PAIRS", "FLAG", "FLAGS", "DOLLARS", "POSTED", "DISMISSED", "WRITTEN", "VOIDED", "ENTERED",
         "ADDED", "CORRECTED", "FIXED", "CLEARED", "SENT", "ROUTED", "POINTED", "QUIET", "NOTHING", "CHANGE", "NEEDED", "FALSE", "TRUE",
         "HELD", "HOLD", "HOLDS", "ROW", "ROWS", "TURN", "FACESHEET", "FACESHEETS", "DROP", "DROPS", "INBOX", "GITHUB", "MAIN", "MIRROR",
         "SYNC", "PUSH", "COMMIT", "BUNDLE", "PACKAGE", "CARD", "CARDS", "APPROVED", "WAITING", "DONE", "NURSING", "ASSISTED", "LIVING",
         "REHAB", "REHABILITATION", "HOME", "BIG", "BEND", "AND", "OR", "OF", "THE", "TO", "ON", "IN", "FOR", "WITH", "AT", "BY", "FROM",
         "AS", "A", "AN", "RE", "ALL", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "NEW", "OLD", "NOT",
         "QMB", "SLMB", "FFS", "MCD", "CMS", "NPPES", "OIG", "LEIE", "EOB", "CARC", "RARC", "ICD", "DX", "POS", "PCC", "CCN",
         "EFFINGER", "GARLAND", "GARCIA", "PAMELA", "GREGG", "CLAUDE"}
def _file_words():
    """every word of every carrier and facility name on main, so a payer or home named in a line is never read as a patient"""
    out = set()
    for path in (os.path.join(REPO, "practices", "ehpa", "carriers.json"), os.path.join(REPO, "practices", "ehpa", "facilities.json")):
        try: j = json.load(open(path, encoding="utf-8"))
        except Exception: continue
        vals = []
        for v in (j.values() if isinstance(j, dict) else j):
            if isinstance(v, list): vals += [str(x) for x in v]
            elif isinstance(v, dict): vals += [str(x) for x in v.values()]
            else: vals.append(str(v))
        for s in vals: out.update(w for w in re.findall(r"[A-Za-z][A-Za-z'\-]+", s) if len(w) >= 2)
    return {w.upper() for w in out}
VOCAB |= _file_words()
MBI_RE = re.compile(r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d{2}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b|(?i:\b(?:ssn|social security)\b\W{0,12}\d{9}\b)")
MEMBER_RE = re.compile(r"(?i)\b(?:subscriber|member|medicaid|policy|insured|beneficiary)\b(?:\s*(?:id|no\.?|num(?:ber)?|#|:))?\W{0,8}\d{8,11}\b")
# any bare 9-11 digit number, or a letter + 8-10 digits (H10208880), is a member / Medicaid / policy number until proven otherwise:
# chart, visit and charge ids are 5-8 digits, run stamps carry a T, CPT codes are 5 characters; an ERA check number is written "check 349717623"
BARE_ID_RE = re.compile(r"(?<![Cc]heck )(?<!NPI )(?<![Rr]un )(?<![Tt]race )\b(?:\d{9,11}|[A-Z]\d{8,10})\b")
# a date of birth or death in any of the house styles, the year-less "10/12" included (DOS 11/02 is not a birth or death)
DATE_RE = re.compile(r"(?i)\b(?:dob|dod|date of birth|born|birth ?date|date of death|died|deceased|death)\b[^\n\[\]]{0,16}?(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|(?:19|20)\d{6}|\d{1,2}/\d{1,2}(?![\d/]))\b")
def floor_offence(text):
    for mm_ in NAME_RE.finditer(text):
        last, first = mm_.group(1).upper(), mm_.group(2).upper()
        if last in VOCAB or first in VOCAB: continue                        # "Medicare, Medicaid" / "Simply Healthcare, Humana" is vocabulary, not a person
        return "a name (%r)" % mm_.group(0)
    for mm_ in TITLE_RE.finditer(text):                                     # "John Smith" - every word outside the vocabulary
        words = [w.upper() for w in mm_.group(1).split()]
        if all(w not in VOCAB for w in words): return "a name (%r)" % mm_.group(1)
    if MBI_RE.search(text) or MBI_RE.search(re.sub(r"(?<=[A-Z0-9])[- ](?=[A-Z0-9]{3}\b)", "", re.sub(r"(?<=[A-Z0-9])-(?=[A-Z0-9])", "", text))): return "an MBI"   # 1EG4TE5MK73, the card's 1EG4-TE5-MK73 and 1EG4 TE5 MK73
    if SSN_RE.search(text): return "an SSN"
    if MEMBER_RE.search(text): return "a member / policy number"
    mm_ = BARE_ID_RE.search(text)
    if mm_: return "a 9-11 digit number (%s - a member or Medicaid number? chart, visit and charge ids are 5-8 digits; an ERA check number is written 'check 349717623')" % mm_.group(0)
    if DATE_RE.search(re.sub(r"(?i)\bDOS\s*\d{1,2}/\d{1,2}(?:/\d{2,4})?", "DOS", text)): return "a date of birth or death"   # a DOS is a service date, never a birth or death
    return None
def gate_offence(text):
    """what tools/mirror/phi_gate.py would do to this text at the next mirror commit: rewrite it (a name, an identifier, a DOB)
    or refuse it; None when the gate leaves it alone or cannot be imported here"""
    try:
        sys.path.insert(0, os.path.join(REPO, "tools", "mirror")); import phi_gate
    except Exception: return None
    try:
        names, _ = phi_gate.load_map()
        red = phi_gate.redact(text, names, code=False)
        if red != text: return "text the mirror's PHI gate would rewrite (-> %r)" % red[:80]
        hits = phi_gate.check(red)
        if hits: return "an identifier the PHI gate refuses (%s)" % ", ".join(h[0] for h in hits[:3])
    except Exception as ex: return "text the PHI gate could not clear (%s)" % str(ex)[:60]
    return None
for label, text in (("--done", done), ("--note", note)):
    bad = floor_offence(text) or gate_offence(text)
    if bad:
        print("cascade_record: %s carries %s - chart ids and dollars only; nothing written" % (label, bad)); sys.exit(2)
    sw = re.search(r"\(\d{1,2},\s*charts?\b[^)]{0,40}\)?", text)
    if sw:
        print("cascade_record: %s reads %r - that looks like a dollar figure bash swallowed (\"$160\" -> \"60\"); write \"160 dollars\" with no $ sign anywhere in the command; nothing written" % (label, sw.group(0))); sys.exit(2)

finished = opt("--finished") or NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
body = {"schema": "practice-cascade-run/1", "kind": opt("--kind", "nightly cascade"), "stamp": stamp, "at": at, "date": date, "finished": finished,
        "checked": checked, "flagged": flagged, "lookups": lookups, "changed": changed, "dollars": dollars,
        "era_posted": era_posted, "writeoffs": writeoffs, "stedi_cost": stedi_cost, "done": done, "note": note,
        "commit": (opt("--commit") or "")[:12], "routine": "trig_01XVrVN9dpSdvAbB1ZrsAzFU",
        "session": opt("--session", os.environ.get("CLAUDE_SESSION_URL", "")) or "",
        "source": "practices/ehpa/registers/cascade_runs/%s.json" % stamp, "_recorded": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")}
if "--dry" in a:
    print(json.dumps(body, indent=1)); sys.exit(0)
folder = os.path.join(REPO, "practices", "ehpa", "registers", "cascade_runs")
os.makedirs(folder, exist_ok=True)
path = os.path.join(folder, stamp + ".json")
replaced = os.path.exists(path)
with open(path, "w", encoding="utf-8") as f: json.dump(body, f, indent=1, sort_keys=True)
print("cascade_record %s: checked %d, flagged %d, changed %d, %d dollars re-sent%s -> %s%s (practice_db.py build --run %s writes it to the page's database)" % (
    stamp, checked, flagged, changed, dollars, (", ERA %.2f posted" % era_posted) if era_posted else "", os.path.relpath(path, REPO).replace(os.sep, "/"),
    " (replaced tonight's earlier record)" if replaced else "", stamp))
