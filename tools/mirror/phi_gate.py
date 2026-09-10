#!/usr/bin/env python3
# PLAIN ENGLISH (PHI gate for everything that leaves the workspace for GitHub or Postman)
# Decides: Whether a file is safe to publish. Swaps patient names for stable pseudonyms using the
#   map in secrets/pseudonyms.json (real names live ONLY there and in Drive's "workspace mirror"),
#   then refuses - exit 2 - if anything that looks like an identifier survives: an MBI, an SSN,
#   a Medicaid/ICN-style number, a date of birth, a bearer token or key. Prints "possible name"
#   warnings for capitalized pairs it does not recognize so the run can add them to the map.
# Rules it uses: no PHI on GitHub (William 9/7). Names: pseudonymize. Numbers: never publish.
#   Fail closed: with no map at all it still runs the pattern checks but warns loudly.
# Never touches: AMD, Stedi, the workspace copies. It writes only the destination file you name.
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
    for p in MAP_CANDIDATES:
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
        text = lrx.sub(lambda m: names[next(n for n in keys if n.lower() == (m.group(1) or m.group(2)))].lower(), text)
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

def main():
    if len(sys.argv) < 3:
        sys.exit("usage: phi_gate.py <source> <destination>   (exit 0 clean, 2 blocked)")
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
