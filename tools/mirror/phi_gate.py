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
        "Cotterell", "Denholm", "Farrant", "Gillam", "Hexham", "Inchbold", "Kirkbride", "Lisle", "Marlow", "Oakes"]

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
    return "Patient%02d" % (h % 100)

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

def scrub(text, names):
    if names:
        keys = sorted(names, key=len, reverse=True)
        # exact case or ALL CAPS only - a lowercase common word ("bell") is never a name
        alts = [re.escape(k) for k in keys] + [re.escape(k.upper()) for k in keys]
        rx = re.compile(r"(?<![A-Za-z])(" + "|".join(alts) + r")(?![A-Za-z])")
        def rep(m):
            k = m.group(1)
            real = k if k in names else next(n for n in keys if n.upper() == k)
            fake = names[real]
            return fake.upper() if k.isupper() and len(k) > 1 else fake
        text = rx.sub(rep, text)
        # lowercase forms only inside slugs / filenames ("lepore-nicholas", "willis_rebill.py")
        lrx = re.compile(r"(?<=[-_./])(" + "|".join(re.escape(k.lower()) for k in keys) + r")(?![A-Za-z])|(?<![A-Za-z])(" + "|".join(re.escape(k.lower()) for k in keys) + r")(?=[-_][a-z])")
        def lrep(m):
            fake = names[next(n for n in keys if n.lower() == (m.group(1) or m.group(2)))].lower()
            s, e = m.span()
            if m.string[s - 1:s] == "_" or m.string[e:e + 1] == "_":   # inside an identifier / module name: a hyphenated pseudonym would break the code (10/6)
                fake = fake.replace("-", "_")
            return fake
        text = lrx.sub(lrep, text)
    return text

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
JSON_NAME = re.compile(r'("(?:patient|name|patname|patientname|pt|pat_name|patient_name|lastfirst)"\s*:\s*")([A-Z][A-Z\'\-]+,\s?[A-Z][A-Z\'\- ]*)(")')
PROSE_NAME = re.compile(r"\b([A-Z][A-Z'\-]{2,}),\s?([A-Z][A-Z'\-]{1,})((?: [A-Z]\.?)?)(?=\s*\((?:pat|chart|amd|id)\s*\d)")
DOB_SUB = re.compile(r"(\b(?:DOB|dob|birth|Birth|BIRTH)\b[^\n]{0,12}?)((?:19|20)\d{2}[-/]\d{2}[-/]\d{2}\b|\b\d{1,2}/\d{1,2}/(?:19|20)\d{2}\b)")
MEMBER_SUB = re.compile(r"(?i)((?:subscribernum|member\s*(?:id|#|number)|medicaid\s*(?:id|#|number)?|membernum)\W{0,4})\d{8,11}\b")
DRIVE_ONLY = re.compile(r"(?i)(digest|needs_facesheet|run[ _]report|facesheets?[ _]needed|_run report)")
TEXT_EXT = {".json", ".jsonl", ".md", ".txt", ".csv", ".py", ".sh", ".log", ".html", ".yaml", ".yml", ".xml"}
CODE_EXT = {".py", ".sh"}
SKIP_DIRS = {".git", "secrets", "__pycache__", "node_modules"}

# AMD's own LAST,FIRST form (no space after the comma) anywhere in a DATA file - a needs list, a digest, a CSV,
# a register note. Billing vocabulary that happens to look like it (DOS,CPT / WOINS,WOLATE) is allow-listed.
LASTFIRST_BARE = re.compile(r"\b([A-Z][A-Z'\-]{2,}),([A-Z][A-Z'\-]{1,})((?: [A-Z]\.?)?)%?(?![A-Za-z0-9=_])")
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
                 "REF", "ACK", "CLM", "CHK", "DD", "REJCTD", "RETURND", "ENCNTER", "ACCPTD", "PENDNG", "ADJ", "AMT", "QTY", "SVC", "NM", "DTP"}
CODE_HINT = re.compile(r"^(import |from \S+ import |def |class |#!/|#!)", re.M)
# in code only the comments and string literals are prose: a name list / search pattern lives in a string, never in a token
STR_OR_COMMENT = re.compile(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'|#[^\n]*)')
# board-row slugs built from real names ("last-first-<amdid>", the BOARD ACCESS RULE's id form)
SLUG_NAME = re.compile(r"\b[a-z][a-z']{1,}-[a-z][a-z']{1,}-(\d{6,9})\b")

def _bare(m, vals_up):
    last, first = m.group(1), m.group(2)
    if last in NOT_LASTFIRST or first in NOT_LASTFIRST or last in vals_up:
        return m.group(0)
    return "[name]"

def redact(text, names, code=None):
    """Scrub + substitute (never refuse): the transform the 10/6 history rewrite applied to every blob.
    code=None decides from the content (an import / def / shebang = code: the bare LAST,FIRST rule is skipped there)."""
    vals_up = {v.upper() for v in names.values()}
    if code is None:
        code = bool(CODE_HINT.search(text))
    t = scrub(text, names)
    t = JSON_NAME.sub(lambda m: m.group(1) + ("[name]" if m.group(2).split(",")[0].strip() not in vals_up else m.group(2)) + m.group(3), t)
    t = PROSE_NAME.sub(lambda m: m.group(0) if m.group(1) in vals_up else "[name]", t)
    if not code:
        t = LASTFIRST_BARE.sub(lambda m: _bare(m, vals_up), t)
        t = SLUG_NAME.sub(lambda m: m.group(0) if m.group(0).split("-")[0] in {v.lower() for v in names.values()} else "[name]-" + m.group(1), t)
    else:
        t = STR_OR_COMMENT.sub(lambda s: LASTFIRST_BARE.sub(lambda m: _bare(m, vals_up), s.group(0)), t)
    for label, rx in ID_PATTERNS:
        if label == "date of birth":
            continue
        t = rx.sub({"MBI": "[MBI]", "SSN": "[SSN]", "VA ICN": "[ICN]"}.get(label, "[secret]"), t)
    t = DOB_SUB.sub(lambda m: m.group(1) + "[DOB]", t)
    t = MEMBER_SUB.sub(lambda m: m.group(1) + "[member id]", t)
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
