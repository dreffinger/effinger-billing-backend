#!/usr/bin/env python3
# PLAIN ENGLISH (PHI gate for everything that leaves the workspace for GitHub or Postman)
# Decides: Whether a file is safe to publish. Swaps patient names for stable pseudonyms using the
#   map in secrets/pseudonyms.json (real names live ONLY there and in Drive's "workspace mirror"),
#   then refuses - exit 2 - if anything that looks like an identifier survives: an MBI, an SSN,
#   a Medicaid/ICN-style number, a date of birth, a bearer token or key. Prints "possible name"
#   warnings for capitalized pairs it does not recognize so the run can add them to the map.
# Rules it uses: no PHI on GitHub (William 9/7). Names: pseudonymize. Numbers: never publish.
#   Fail closed: with no map at all it still runs the pattern checks but warns loudly.
# Never touches: AMD, Stedi, the workspace copies. It writes only the destination file you name -
#   except in `tree` mode (10/6/2026), which scrubs the changed files of a checkout in place before a commit.
# ---
import json, os, re, sys, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAP_CANDIDATES = [os.path.join(ROOT, "secrets", "pseudonyms.json"),
                  "/home/claude/unbilled/secrets/pseudonyms.json",
                  "/home/claude/unbilled/.pseudonyms.json"]

# A short, obviously-fake surname list so pseudonyms are stable per real name (hash-picked).
# (Dunmore, Thackeray, MacAllister, Bramwell, Fairbank, Ridgeway, Stanhope, Sterling, Wexford are already
#  taken by the 9/8 map and must never be reused for a different person.)
FAKE = ["Ashby", "Bexley", "Calder", "Ellery", "Fenwick", "Garrow", "Hollis", "Jarrell", "Kestrel", "Lowry",
        "Norcott", "Orme", "Pellam", "Quill", "Rowantree", "Selby", "Ulverston", "Varley", "Yardley", "Zell",
        "Abernathy", "Corvin", "Dalloway", "Eskdale", "Greaves", "Harlow", "Trent", "Winslow", "Bastable",
        "Cotterell", "Denholm", "Farrant", "Gillam", "Hexham", "Inchbold", "Kirkbride", "Lisle", "Marlow", "Oakes",
        # 10/6 afternoon: the first 40 were used up (nine names fell through to Patient%02d, two of them colliding)
        "Blakeney", "Carraway", "Elmsley", "Farrow", "Glenister", "Ivens", "Jessop", "Kendal", "Lydgate", "Nettleford",
        "Oswin", "Penrose", "Quarles", "Ransome", "Stillwater", "Thorney", "Wainfleet", "Yelverton", "Ashcombe", "Brackley",
        "Culverhouse", "Dovedale", "Everleigh", "Fairweather", "Gainsford", "Ingleby", "Kettering", "Langdale", "Moresby",
        "Northcote", "Overbury", "Rookwood", "Tavistock", "Underhill", "Wetherby", "Thistlewood", "Ravenscar", "Coldharbour",
        "Ambleside", "Buttermere", "Grasmere", "Haverthwaite"]

def load_map():
    env = os.environ.get("PHI_MAP")                       # a self-test's stand-in map; never set in a run
    for p in ([env] if env else []) + MAP_CANDIDATES:
        if os.path.exists(p):
            m = json.load(open(p))
            return m.get("names", m), p
    return {}, None

def pseudonym(real, taken):
    h = int(hashlib.sha256(real.lower().encode()).hexdigest(), 16)
    for i in range(len(FAKE)):
        cand = FAKE[(h + i) % len(FAKE)]
        if cand not in taken:
            return cand
    for i in range(1000):                                  # never two real names behind one pseudonym
        cand = "Patient%03d" % ((h + i) % 1000)
        if cand not in taken:
            return cand
    raise RuntimeError("pseudonym list exhausted")

ID_PATTERNS = [
    ("MBI", re.compile(r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d{2}\b")),
    ("SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("VA ICN", re.compile(r"\b\d{10}V\d{6}\b")),
    ("date of birth", re.compile(r"\b(DOB|dob|birth)\b[^\n]{0,12}\b(19|20)\d{2}[-/]\d{2}[-/]\d{2}\b|\b(DOB|dob)\b[^\n]{0,8}\b\d{1,2}/\d{1,2}/(19|20)\d{2}\b")),
    ("bearer token", re.compile(r"Bearer\s+[A-Za-z0-9\-_\.]{40,}")),
    ("usercontext token", re.compile(r"usercontext>[A-Za-z0-9\-_\.=]{40,}<")),
    ("GitHub PAT", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("Stedi key", re.compile(r"\b[A-Za-z0-9]{2,6}\.[A-Za-z0-9]{40,}\b")),
    ("AMD password", re.compile(r"psw=\"(?!\{\{)[^\"]{4,}\"")),
]
# Medicaid ids / member numbers: 9-10 digits right after a member/subscriber/medicaid word.
MEMBER_RE = re.compile(r"(?i)(subscribernum|member\s*(id|#|number)|medicaid\s*(id|#|number)?|membernum)\W{0,4}\d{8,11}\b")

# Candidate names: "(Firstname Lastname" / "Lastname Firstname ×" style tokens in registry prose.
NAME_HINT = re.compile(r"\(([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})[,;:/ )]")
NOT_NAMES = {"Charge Review", "Claim Inspector", "Claims Center", "Mass Rebill", "Mass Write", "Master Files",
             "Payment Entry", "Process Accepted", "Florida Blue", "Cigna Health", "William", "Pam Garcia",
             "Report Center", "Edit address", "Post button"}

# Surnames that are ordinary English words: in lowercase they are words, never names ("--short", "white_list",
# "spring"), so the lowercase rules below skip them; the exact-case and ALL-CAPS forms are still mapped.
COMMON_WORDS = set("""
able abbot active alley amber apple arch archer arms ash ashes bacon badger bail baker ball band bank banks bar bare
barn barrow bass bay beach beam bean bear beck bell bells belt bench bend berry best bill bills bird bishop black blake
blank bland bliss block bloom blood blue blunt board bold bolt bond bone book boon booth bound bow bowl box boyd branch
brand brass bray bread bridge bright brook brooks broom brown buck bull bunch burn burns bush butler cable cage cake
camp cane cannon cap cape card carpenter carr carter case cash castle catch cave chalk chance chapel chase cheek cherry
chief child chin church city clay clear cliff clock close cloud club coach coal coat cobb cock coin cole cook cooper
cope copper corn cost court cox crane crew crisp crook cross crow crown cup curry cut dale dance dark date day deal
dean deer dice dike dock dodge dole door dove down drake draper drew drum dry duke dunn dust dyer earl early east
edge elder ember end even fair faith fall fare farmer fast fawn fay fear fee fell fern few field fields finch fine
fire fish fisher flag flat fleet flint flood flower fly foot ford forest fork fox frame frank free freeze friend frost
fry full fuller gain gale gall game garden gate gay gentle gill glass glen glove gold golden good goose gore grace
grant grass gray graves green greene grey grill grove guest gum gun hail hair hale hall ham hand hard hare harp
hart hatch hawk hay hays head heart heath hedge herring hill hills hind hogg hold holiday holland holly home hood hook
hope horn house howl hunt hunter hurst ice ink iron ivy jack jay jewel joy judge jump just keen keep kemp key kid
kind king kirk kitchen knight lace lake lamb lamp lance land lane large lark last late law lawn lay leaf lean lee
light lily lime line link lion little lock lodge long lord love low lowe lucky lynch mace main major mallet man
manly march mark marks marsh mason masters match may mead meadow meek merry mild mill miller mills mine mint miss
monk moody moon moore moss moth mount mud myrtle nail nash neal new newman nice night noble noon north nurse oak oaks
oat odd oil olive orange order organ otter oven over owen owl pace pack page paine pale palm park parker parks parr
parrot parsons part pass pate patch pay peach peacock pearl peck peel pell penny pepper perry pike pine pink pitt
place plant plum pool pope port post pound powell power price pride prince prior pure quick quill rain ram rand
ray read reed reel rhodes rice rich ride ridge ring rivers road robin rock roe rose rowe royal rudd rush rust rye
sage sail salt sand sands savage saw scott screws seal seed self sharp shaw sheen shelley sheppard shield shore short
silver simple sing skinner slate slick slow small smart smith snow snyder song south spark sparks spear speed spring
square stack stalk stamp star stark steel stern still stock stone storm stout street string strong sugar summer
sun swan sweet swift tailor tall tan tate taylor temple thorn tidy till toll tower town trade trent trim true
trust tuck tune turner twig vale vane vest vine wade wages wall walker ward ware warren water waters way weaver
web weed weeks well wells west wheeler white wild will winter wise wolf wood woods wool wren wright yard yates young
""".split())

def _ident_safe(fake, m, ident):
    """A hyphenated pseudonym (Garland-G) next to an identifier character, or anywhere in code outside a
    string / comment, is written with an underscore: GARLAND-G_RPROV / GARLAND-G = "prof15" do not compile
    (the 9/24 and 10/6 breakage of the two re-render helpers on main)."""
    s, e = m.span()
    before, after = m.string[s - 1:s], m.string[e:e + 1]
    if ident or before == "_" or after == "_" or before.isdigit() or after.isdigit():
        return fake.replace("-", "_")
    return fake

def scrub(text, names, code=False):
    """Map every real name to its pseudonym. Exact case or ALL CAPS anywhere; lowercase only (a) inside slugs and
    file names ("<surname>-<first>-<amdid>", "<surname>_rebill.py" - never after "--", a CLI flag) and (b) as a
    whole word (a dict key "<surname>", a lowercase note) - both skipped for a surname that is an ordinary word.
    code=True: tokens outside string literals / comments are identifiers and get an underscore-safe pseudonym."""
    if not names:
        return text
    keys = sorted(names, key=len, reverse=True)
    alts = [re.escape(k) for k in keys] + [re.escape(k.upper()) for k in keys]
    rx = re.compile(r"(?<![A-Za-z])(" + "|".join(alts) + r")(?![A-Za-z])")
    lows = [re.escape(k.lower()) for k in keys if k.lower() not in COMMON_WORDS and len(k) >= 4]
    lrx = re.compile(r"(?<![A-Za-z])(?<!--)(" + "|".join(lows) + r")(?![A-Za-z])") if lows else None
    # an ordinary-word surname is still a name as a scanned-sheet file name ("savage.pdf") or a helper stem ("short_1002.py")
    commons = [re.escape(k.lower()) for k in keys if k.lower() in COMMON_WORDS]
    crx = re.compile(r"(?<![A-Za-z])(" + "|".join(commons) + r")(?=\.(?:pdf|jpe?g|png|json|txt)\b|_\d{3,})") if commons else None
    def run(seg, ident):
        def rep(m):
            k = m.group(1)
            real = k if k in names else next(n for n in keys if n.upper() == k)
            fake = names[real]
            fake = fake.upper() if k.isupper() and len(k) > 1 else fake
            return _ident_safe(fake, m, ident)
        seg = rx.sub(rep, seg)
        for low_rx in (lrx, crx):
            if low_rx:
                seg = low_rx.sub(lambda m: _ident_safe(names[next(n for n in keys if n.lower() == m.group(1))].lower(), m, ident), seg)
        return seg
    if not code:
        return run(text, False)
    lowmap = {k.lower(): v.lower() for k, v in names.items()}
    def literal(s):
        # a string literal that IS a lowercase surname ("short": item_x, the 10/4 chat script's dict keys) is a
        # name key even when the word is ordinary - paired with a pseudonymized function it would be a real ->
        # pseudonym table; an identifier-safe form keeps a dict key and its function name consistent
        m = re.fullmatch(r"(['\"])([a-z]+)\1", s)
        if m and m.group(2) in lowmap:
            return m.group(1) + lowmap[m.group(2)].replace("-", "_") + m.group(1)
        return run(s, False)
    out, pos = [], 0
    for s in STR_OR_COMMENT.finditer(text):      # code: identifiers between the literals, prose inside them
        out.append(run(text[pos:s.start()], True)); out.append(literal(s.group(0))); pos = s.end()
    out.append(run(text[pos:], True))
    return "".join(out)

def check(text):
    hits = []
    for label, rx in ID_PATTERNS:
        for m in rx.finditer(text):
            hits.append((label, m.group(0)[:24]))
    for m in MEMBER_RE.finditer(text):
        hits.append(("member/medicaid number", m.group(0)[:30]))
    return hits

def warn_names(text, names):
    fakes = set(v.lower() for v in names.values())
    out = set()
    for m in NAME_HINT.finditer(text):
        cand = m.group(1)
        if cand in NOT_NAMES or any(w.lower() in fakes for w in cand.split()):
            continue
        out.add(cand)
    return sorted(out)

# ---- tree mode (10/6/2026) -----------------------------------------------------------------------
# `phi_gate.py tree <path>... [--all]` scrubs files IN PLACE before a commit: every changed / untracked
# text file under the paths (--all = every file) gets the pseudonym map, then any LAST,FIRST value or
# LAST,FIRST (pat NNN) token not in the map -> "[name]", identifiers -> "[MBI]" / "[SSN]" / "[member id]"
# / "[DOB]". Run artifacts that are prose about patients (a run digest, the needs list / needs section,
# a run report) are Drive-only: a new or changed one is taken out of the tree (a tracked one is put back
# to HEAD) and named in the output. mirror.py runs this on "." before `git add -A`; the 10/6 lesson:
# the 9/30 payreason registers and the 10/3 digest reached GitHub with patient names in them.
# ---- the name / identifier rules (10/6/2026 afternoon: rewritten after the history-rewrite hunt) ------------
# a name part: letters, with ' or - only BETWEEN letters (O'BRIEN, SMITH-JONES) - never a closing quote (10/6:
# 'CHADWICK,SELINA' lost its quote and the file no longer compiled); a suffix (JR/SR/II/III/IV) may follow the last name
_NP = r"[A-Z](?:[A-Z]|['\-](?=[A-Z]))"
_FP = r"[A-Z](?:[A-Za-z]|['\-](?=[A-Za-z]))"                      # a first name may be mixed case (SMYTHE,Mary)
_SUF = r"(?: (?:JR|SR|II|III|IV))?"
SUFFIX_RE = re.compile(r" (?:JR|SR|II|III|IV)$")
NAME_KEYS = r"(?:patient|name|patname|patientname|pt|pat_name|patient_name|lastfirst|responsibleparty|respparty|guarantor|subscribername|subscriber_name|insuredname|insured_name|patientfullname)"
PART_KEYS = r"(?:firstname|lastname|first_name|last_name|patfname|patlname|subscriberfirstname|subscriberlastname|insuredfirstname|insuredlastname|first|last)"
JSON_NAME = re.compile(r'("' + NAME_KEYS + r'"\s*:\s*")([^"\n]*)(")', re.I)
JSON_PART = re.compile(r'("' + PART_KEYS + r'"\s*:\s*")([^"\n]*)(")', re.I)
PROSE_NAME = re.compile(r"\b(" + _NP + r"{2,}" + _SUF + r"),\s?(" + _FP + r"{1,})((?: [A-Z]\.?)?)(?=\s*\((?:pat|chart|amd|id)\s*\d)")
# AMD's own LAST,FIRST form (no space after the comma) anywhere in a DATA file - a needs list, a digest, a CSV,
# a register note. Billing vocabulary that happens to look like it (DOS,CPT / WOINS,WOLATE) is allow-listed.
# (the AMD lookup wildcard "%" after the name is left where it is: "[name]%" and "[name]%%" keep a %-format valid)
LASTFIRST_BARE = re.compile(r"\b(" + _NP + r"{2,}" + _SUF + r"),(" + _FP + r"{1,})((?: [A-Z]\.?)?)(?![A-Za-z0-9=_])")
NOT_LASTFIRST = {"DOS", "CPT", "CO", "PR", "OA", "PI", "CR", "WOINS", "WOLATE", "WONCS", "WOPAT", "ERA", "ICN", "MBI", "NPI", "SSN",
                 "DOB", "UNI", "BCBS", "HUM", "AET", "SUN", "WEL", "CAP", "SIM", "TRI", "VACCN", "CCN", "RARC", "CARC", "JSON", "CSV",
                 "PDF", "XML", "API", "AMD", "UHC", "AARP", "HMO", "PPO", "POS", "FFS", "LTC", "SNF", "ALF", "HCA", "CCM", "TCM", "PAID",
                 "DENIED", "PENDING", "NOT", "ON", "FILE", "RUN", "COMPLETE", "START", "UTC", "ET", "GV", "GW", "TRUE", "FALSE", "NULL",
                 "GET", "POST", "PUT", "PATCH", "REBILL", "VOID", "HOLD", "READ", "WRITE", "OK", "NO", "NA", "YES", "FIX", "TRAP", "WATCH",
                 "RULE", "AND", "OR", "THE", "FOR", "CLAIM", "VISIT", "CHARGE", "PAYER", "PLAN", "ORDER", "FINALIZED", "DUPLICATE",
                 "REVERSAL", "DENIAL", "ACTIVE", "INACTIVE", "MISMATCH", "DEATH", "ADVANTAGE", "MEDICARE", "MEDICAID", "HOSPICE",
                 "BLOCKED", "SKIPPED", "APPLIED", "DONE", "WAITING", "APPROVED", "DECLINED", "STEDI", "CMS", "PECOS", "NPPES", "OIG",
                 "LEIE", "CAQH", "DEA", "SELECT", "FROM", "WHERE", "DRY", "LIVE", "ALL", "NONE", "MA", "PDP", "EFT", "TRN", "ERR", "ID",
                 "LAST", "FIRST", "NAME", "PID", "VID", "CID", "SEQ", "ICD", "HCPCS", "DX", "NDC", "VA", "UC", "USA", "FL", "GA", "AL",
                 "REF", "ACK", "CLM", "CHK", "DD", "REJCTD", "RETURND", "ENCNTER", "ACCPTD", "PENDNG", "ADJ", "AMT", "QTY", "SVC", "NM", "DTP",
                 "THEN", "ELSE", "WITH", "WITHOUT", "ONLY", "NEW", "OLD", "MAX", "MIN", "SUM", "AVG", "TODO", "NOTE", "WARN", "INFO", "DEBUG"}
CODE_HINT = re.compile(r"^(import |from \S+ import |def |class |#!/|#!)", re.M)
# in code only the comments and string literals are prose: a name list / search pattern lives in a string, never in a token
STR_OR_COMMENT = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|#[^\n]*)')
# board-row slugs built from real names ("last-first-<amdid>", the BOARD ACCESS RULE's id form, with an optional initial)
SLUG_NAME = re.compile(r"\b([a-z][a-z']+)-([a-z][a-z']+)((?:-[a-z])?)-(\d{5,9})\b")
# file names built from a name and a date of birth (patient_db/pending_admits/<last>_<first>_<yyyymmdd>.json)
FILE_SLUG = re.compile(r"\b([a-z][a-z']+)_([a-z][a-z']+)_((?:19|20)\d{6})\b")
# identifiers the rewrite hunt found the first rules missing
MBI_FRAG = re.compile(r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d?\b")   # 9-10 chars of an MBI
DOB_SUB = re.compile(r"(?i)((?:\bdob\b|\bdod\b|date\s*of\s*(?:birth|death)|dateofbirth|dateofdeath|birth\s*date|birthdate|birthday|\bbirth\b|\bdeath\b|deceased|\bdied\b|\bborn\b)[^\n]{0,16}?)"
                     r"((?:19|20)\d{2}[-/]\d{2}[-/]\d{2}(?:T[\d:.]*Z?)?|\b\d{1,2}/\d{1,2}/(?:19|20)\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2}\b|\b(?:19|20)\d{6}\b)")
MEMBER_JSON = re.compile(r'("(?:subscribernum|subscriberid|subscriber_id|memberid|member_id|membernum|member|insid|insuredid|policynum|policynumber|policy_number|hicnum|hicn|medicaidid|medicaid_id|medicaidnum)"\s*:\s*")([A-Za-z0-9][A-Za-z0-9\-]{4,})(")', re.I)
MEMBER_PROSE = re.compile(r"(?i)\b(member|subscriber|policy|insured|recipient|medicaid|hic|hicn)((?:\s*(?:id|#|number|no\.?|num))?\s*[:=#]?\s*)(?=[A-Za-z0-9\-]*\d)([A-Za-z0-9][A-Za-z0-9\-]{5,})\b")
MEMBER_SUB = MEMBER_PROSE                                       # older name, kept for callers
PHONE_JSON = re.compile(r'("(?:phone|homephone|cellphone|mobilephone|workphone|phone1|phone2|phonenumber|phone_number|homephone1|cell|mobile)"\s*:\s*")(\+?[\d\-\(\) .]{7,})(")', re.I)
PHONE_PROSE = re.compile(r"(?i)((?:home|cell|mobile|patient|pt|resident|her|his|their)\s*phone[\s:#=-]{0,3}|\bcell[\s:#=-]{0,3}|\bmobile[\s:#=-]{0,3}|\bphone\s+)((?:\+?1[ -.]?)?\(?\d{3}\)?[ -.]?\d{3}[ -.]?\d{4})\b")
ADDR_JSON = re.compile(r'("(?:address|address1|address2|addr1|addr2|street|streetaddress|address_1|address_2|homeaddress|mailingaddress)"\s*:\s*")([^"\n]{4,})(")', re.I)
# case matters here: "2 else None st" is code, "2677 Old Bainbridge Rd" is an address
ADDR_PROSE = re.compile(r"\b\d{1,5}\s+(?:[A-Z][A-Za-z'.]*\s+){1,4}(?:ST|St|STREET|Street|AVE|Ave|AVENUE|Avenue|RD|Rd|ROAD|Road|DR|Dr|DRIVE|Drive|LN|Ln|LANE|Lane|BLVD|Blvd|BOULEVARD|Boulevard|COURT|Court|CIRCLE|Circle|TRAIL|Trail|PARKWAY|Parkway|HWY|Hwy|HIGHWAY|Highway|TERRACE|Terrace|PLACE|Place)\b\.?(?:\s+(?:APT|Apt|UNIT|Unit|STE|Ste|SUITE|Suite|#)\s*[A-Za-z0-9\-]+)?")
DRIVE_ONLY = re.compile(r"(?i)(digest|needs_facesheet|run[ _]report|facesheets?[ _]needed|_run report)")
TEXT_EXT = {".json", ".jsonl", ".md", ".txt", ".csv", ".py", ".sh", ".log", ".html", ".yaml", ".yml", ".xml"}
CODE_EXT = {".py", ".sh"}
SKIP_DIRS = {".git", "secrets", "__pycache__", "node_modules"}

def _name_token(last, first, mid, vals_up):
    """LAST[,FIRST] decision: a last name that is not a pseudonym -> "[name]"; a pseudonym last name keeps a pseudonym
    first name and hides any other ("DASHWOOD,[first]" - the real first name beside a mapped surname was the most
    common survivor of the first history rewrite)."""
    lastkey = SUFFIX_RE.sub("", last)
    if lastkey in NOT_LASTFIRST or (first and first.upper() in NOT_LASTFIRST):
        return None                                            # vocabulary, leave it
    if lastkey not in vals_up:
        return "[name]"
    if first and first.upper() not in vals_up:
        return last + ",[first]" + (mid or "")
    return None

def _bare(m, vals_up):
    r = _name_token(m.group(1), m.group(2), m.group(3), vals_up)
    return m.group(0) if r is None else r

_VALUE = re.compile(r"^(" + _NP + r"{2,}(?: " + _NP + r"{2,})?" + _SUF + r"),\s?(" + _FP + r"{1,})((?: [A-Z]\.?)?)$")
def _json_value(v, vals_up, single):
    if not v or v.startswith("[") or not re.search(r"[A-Za-z]", v):
        return v
    m = _VALUE.match(v)
    if m:
        last = m.group(1)
        if " " in SUFFIX_RE.sub("", last):                     # two-word last name: every word must be a pseudonym
            if not all(w in vals_up for w in SUFFIX_RE.sub("", last).split()):
                return "[name]"
            r = _name_token(last.split()[-1] if SUFFIX_RE.search(last) else last.split()[-1], m.group(2), m.group(3), vals_up)
            return v if r is None else (("[name]") if r == "[name]" else last + ",[first]" + (m.group(3) or ""))
        r = _name_token(last, m.group(2), m.group(3), vals_up)
        return v if r is None else r
    if single or re.fullmatch(r"[A-Z][A-Z'\- ]{1,}", v):      # one name part (a firstname field, a bare surname)
        words = [w for w in re.split(r"[ ,]+", v) if w]
        if all(w.upper() in vals_up or w.upper() in NOT_LASTFIRST or SUFFIX_RE.match(" " + w) for w in words):
            return v
        return "[name]"
    return v

def redact(text, names, code=None):
    """Scrub + substitute (never refuse): the transform the 10/6 history rewrite applied to every blob.
    code=None decides from the content (an import / def / shebang = code: the bare LAST,FIRST rule is skipped there)."""
    vals_up = {v.upper() for v in names.values()}
    vals_lo = {v.lower() for v in names.values()}
    if code is None:
        code = bool(CODE_HINT.search(text))
    t = scrub(text, names, code=code)
    t = JSON_NAME.sub(lambda m: m.group(1) + _json_value(m.group(2), vals_up, False) + m.group(3), t)
    t = JSON_PART.sub(lambda m: m.group(1) + _json_value(m.group(2), vals_up, True) + m.group(3), t)
    t = PROSE_NAME.sub(lambda m: _bare(m, vals_up), t)
    def slug(m):
        last, first, ini, pid = m.group(1), m.group(2), m.group(3), m.group(4)
        if last not in vals_lo:
            return "[name]-" + pid
        if first not in vals_lo:
            return last + "-[first]" + ini + "-" + pid
        return m.group(0)
    def fslug(m):
        if m.group(1) in vals_lo and m.group(2) in vals_lo:
            return m.group(1) + "_" + m.group(2) + "_[DOB]"
        return "[name]_[DOB]"
    def prose_rules(s):
        s = LASTFIRST_BARE.sub(lambda m: _bare(m, vals_up), s)
        s = SLUG_NAME.sub(slug, s)
        s = FILE_SLUG.sub(fslug, s)
        return s
    if not code:
        t = prose_rules(t)
    else:
        t = STR_OR_COMMENT.sub(lambda s: prose_rules(s.group(0)), t)
    for label, rx in ID_PATTERNS:
        if label == "date of birth":
            continue
        t = rx.sub({"MBI": "[MBI]", "SSN": "[SSN]", "VA ICN": "[ICN]"}.get(label, "[secret]"), t)
    t = MBI_FRAG.sub("[MBI]", t)
    t = DOB_SUB.sub(lambda m: m.group(1) + "[DOB]", t)
    t = MEMBER_JSON.sub(lambda m: m.group(1) + "[member id]" + m.group(3), t)
    t = MEMBER_PROSE.sub(lambda m: m.group(1) + m.group(2) + "[member id]", t)
    t = PHONE_JSON.sub(lambda m: m.group(1) + "[phone]" + m.group(3), t)
    t = PHONE_PROSE.sub(lambda m: m.group(1) + "[phone]", t)
    t = ADDR_JSON.sub(lambda m: m.group(1) + "[address]" + m.group(3), t)
    t = ADDR_PROSE.sub("[address]", t)
    return t

def _git(args, cwd):
    import subprocess
    r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout

def _changed_files(root, paths):
    """Files git would commit with `git add -A` under the paths: modified, added, renamed, untracked."""
    rc, out = _git(["status", "--porcelain", "--untracked-files=all", "--"] + paths, root)
    if rc:
        return None
    files = []
    for line in out.splitlines():
        if not line.strip() or line[:2] == " D" or line[:2] == "D ":
            continue
        p = line[3:]
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        files.append(p.strip().strip('"'))
    return files

def _all_files(root, paths):
    files = []
    for p in paths:
        base = os.path.join(root, p)
        if os.path.isfile(base):
            files.append(os.path.relpath(base, root)); continue
        for d, dirs, fs in os.walk(base):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            for f in fs:
                files.append(os.path.relpath(os.path.join(d, f), root))
    return files

def tree(paths, all_files=False, root=None):
    root = os.path.abspath(root or ROOT)
    names, mpath = load_map()
    if mpath is None:
        print("WARN: no pseudonym map found - names NOT scrubbed beyond the LAST,FIRST / identifier rules")
    files = _all_files(root, paths) if all_files else _changed_files(root, paths)
    if files is None:
        print("tree: not a git checkout - gating every file under the paths instead")
        files = _all_files(root, paths)
    removed, changed, warned, seen = [], [], [], 0
    for rel in files:
        if any(part in SKIP_DIRS for part in rel.split(os.sep)):
            continue
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(rel)[1].lower()
        if ext not in TEXT_EXT:
            continue
        seen += 1
        base = os.path.basename(rel)
        if ext not in CODE_EXT and DRIVE_ONLY.search(base) and not all_files:
            rc, _ = _git(["ls-files", "--error-unmatch", "--", rel], root)
            if rc == 0:
                _git(["checkout", "--", rel], root)   # tracked: back to the committed copy
            else:
                os.remove(path)                       # untracked: never enters the tree
            removed.append(rel)
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if "PLAIN ENGLISH (PHI gate for everything" in text:
            continue
        new = redact(text, names, code=(ext in CODE_EXT) or None)
        if new != text:
            open(path, "w", encoding="utf-8").write(new)
            changed.append(rel)
        for w in warn_names(new, names):
            warned.append((rel, w))
    for rel in removed:
        print("DRIVE ONLY (not committed): %s" % rel)
    for rel in changed:
        print("scrubbed in place: %s" % rel)
    for rel, w in warned:
        print("possible patient name (add to the map if it is one): %s  [%s]" % (w, rel))
    print("tree: %d text file(s) checked, %d scrubbed, %d kept out of the tree, %d name warning(s)" % (seen, len(changed), len(removed), len(warned)))
    return 0

def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "tree":
        args = [a for a in sys.argv[2:] if not a.startswith("--")]
        return sys.exit(tree(args or ["."], all_files="--all" in sys.argv, root=os.getcwd() if "--cwd" in sys.argv else None))
    if len(sys.argv) < 3:
        sys.exit("usage: phi_gate.py <source> <destination>   (exit 0 clean, 2 blocked)\n       phi_gate.py tree <path>... [--all] [--cwd]   (scrub in place before a commit)")
    src, dst = sys.argv[1], sys.argv[2]
    names, mpath = load_map()
    text = open(src, errors="replace").read()
    text = scrub(text, names)
    hits = check(text)
    warns = warn_names(text, names)
    if mpath is None:
        print("WARN: no pseudonym map found (%s) - names NOT scrubbed, only identifier patterns checked" % MAP_CANDIDATES[0])
    for w in warns:
        print("possible patient name (add to the map if it is one): %s" % w)
    if hits:
        for h in hits:
            print("BLOCKED %s: %s" % h)
        sys.exit(2)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    open(dst, "w").write(text)
    print("clean -> %s (%d names mapped, %d warnings)" % (dst, len(names), len(warns)))

if __name__ == "__main__":
    main()
