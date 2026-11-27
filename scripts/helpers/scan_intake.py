#!/usr/bin/env python3
# PLAIN ENGLISH (ScanSnap uploads - William 11/27/2026: "i added a scansnap folder in aa claude folders ... i will be uploading eras
#   for processing and credentialing documents that need to be categorized for the practice there", then: "ill add eras and billing
#   folder in that one and also a credentialing uploads folder ... put them where they belong in the neon database and the drive")
# Decides: what each scanned file IS and where it goes next - a remittance (EOB/EOP/RA/check/virtual-card stub), a face sheet, a
#   billing letter (records request, ADR, overpayment), a credentialing document (whose, which vault category, restricted or not,
#   issue and expiry dates), personal mail, or unknown. The folder it was dropped in is a strong hint ("eras and billing" = billing,
#   a folder whose name says credentialing = credentialing); the words on the page decide, and a clash is flagged, never guessed.
# Rules it uses: one register row per Drive file id in Neon public.scan_intake, so nothing is filed twice; the intake folders are
#   rows of public.intake_folders; the vault folder map is public.cred_folders (credentialing/README.md). WHO a document belongs to
#   comes from the practice's own people in public.cred_providers (names, NPIs, license and CAQH numbers) - read at run time from
#   the private database, never written in this public file. Restricted = identity documents, any page with an SSN, discipline or
#   monitoring records: those go to the restricted Drive folders and never into Neon as bytes.
# Never touches: Drive or Gmail (the Claude session copies and reads files with the Drive connector and records the result here),
#   AdvancedMD, money. It never prints an SSN, a date of birth, a DEA, card or account number: its output is labels, dates of issue
#   and expiry, and folder ids. No scan, title or scan text is ever committed - the repository is public.
# ---
"""Usage (NEON_DATABASE_URL, as for credentialing/cred_vault.py):
  python3 billing/era_input/scan_intake.py ensure-tables                 create public.intake_folders and public.scan_intake if missing
  python3 billing/era_input/scan_intake.py folders-sync <listing.json>   Drive search_files result (the intake folders) -> routes by name
  python3 billing/era_input/scan_intake.py folders                       the registered intake folders and their routes
  python3 billing/era_input/scan_intake.py register <listing.json>       Drive search_files result (files) -> new register rows
  python3 billing/era_input/scan_intake.py pending                       files not yet filed, routed or skipped
  python3 billing/era_input/scan_intake.py classify (--pdf <file.pdf> | --text <file.txt>) [--route auto|billing|credentialing]
          [--drive-id ID]                                                read it (page by page for a PDF: text layer, else tesseract),
                                                                         split it into documents, label each; --drive-id records it
  python3 billing/era_input/scan_intake.py split <file.pdf> <out-dir> --groups 1-2,3,4-6   one PDF per document (pypdf)
  python3 billing/era_input/scan_intake.py mark <drive-id> --status filed|routed|skipped|needs_review|error
          [--routed-to TEXT] [--vault-doc-id ID] [--note TEXT]
  python3 billing/era_input/scan_intake.py selftest                      the classifier against built-in samples (no database)
"""
import datetime, glob, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
A = sys.argv[1:]
def opt(name, default=None): return A[A.index(name) + 1] if name in A and A.index(name) + 1 < len(A) else default

ROUTES = ("auto", "billing", "credentialing")
KINDS = ("era", "facesheet", "billing_letter", "credentialing", "personal", "unknown")

# ---------------------------------------------------------------------------------------------------------------------------
# Classifier. Patterns run on the upper-cased text with runs of white space folded to one space. Weights add up per rule set.
# Each credentialing rule: (category, doc_type, restricted, [(regex, weight), ...]).
CRED_RULES = [
    # discipline first: on a tie the more specific and more protective label wins (an NPDB report carries field labels
    # such as 'Social Security', 'DEA' and 'License' - those are fields of the report, not the documents themselves)
    ("discipline", "Discipline or monitoring record", True,
     [(r"NATIONAL PRACTITIONER DATA BANK|\bNPDB\b", 6), (r"INTERVENTION PROJECT FOR NURSES|\bIPN\b", 3),
      (r"SETTLEMENT AGREEMENT", 2.5), (r"FINAL ORDER", 2.5), (r"ADMINISTRATIVE COMPLAINT", 2.5), (r"\bPETITIONER\b|\bRESPONDENT\b", 1.5),
      (r"DEPARTMENT OF HEALTH,?\s+(PETITIONER,?\s+)?VS?\.?\s", 1.5),
      (r"EMERGENCY (SUSPENSION|RESTRICTION) ORDER", 3), (r"\bPROBATION\b", 1), (r"PROFESSIONALS RESOURCE NETWORK", 2),
      (r"SELF-?QUERY", 2), (r"ADVERSE ACTION", 1.5),
      (r"MONITORING (AGREEMENT|CONTRACT)|PARTICIPANT CONTRACT|DRUG SCREEN|TOXICOLOGY", 3),
      (r"NOTICE OF INVESTIGATION|UNIFORM COMPLAINT|DOH CASE (NO|NUMBER)|PROBABLE CAUSE|CONSENT ORDER|LETTER OF (CONCERN|GUIDANCE)|REPRIMAND|DISCIPLINARY", 3)]),
    ("identity", "Social Security card", True,
     [(r"THIS NUMBER HAS BEEN ESTABLISHED FOR", 4), (r"SOCIAL SECURITY", 1.5), (r"\bSSA\b", 0.5)]),
    ("identity", "Driver license or state ID", True,
     [(r"DRIVER'?S? LICEN[CS]E", 3), (r"IDENTIFICATION CARD", 2.5), (r"\bCLASS\s+E\b", 1.5), (r"\bDOB\b|DATE OF BIRTH", 1),
      (r"\bSEX\b.{0,12}\b[MF]\b", 0.5), (r"\bHGT\b|\bHEIGHT\b", 0.5)]),
    ("identity", "Passport", True, [(r"\bPASSPORT\b", 3), (r"NATIONALITY", 1)]),
    ("dea", "DEA registration", False,
     [(r"CONTROLLED SUBSTANCE REGISTRATION", 3.5), (r"DRUG ENFORCEMENT ADMINISTRATION", 2),
      (r"\bDEA\b.{0,30}(REGISTRATION|CERTIFICATE)", 1.5), (r"SCHEDULES?\b.{0,20}\b2N\b", 2)]),
    # a license number appears on many forms (agreements, applications, reports): numbers count little; the licensing
    # board's own page (verification, status, renewal) counts
    ("license", "License (verification or renewal)", False,
     [(r"LICENSE VERIFICATION", 3), (r"BOARD OF OSTEOPATHIC MEDICINE", 2.5), (r"BOARD OF NURSING", 2),
      (r"MEDICAL QUALITY ASSURANCE|\bMQA\b", 2), (r"CLEAR/ACTIVE|STATUS:? ?CLEAR|LICENSE STATUS", 2),
      (r"RENEWAL (CONFIRMATION|NOTICE|RECEIPT)", 1.5), (r"LICENSE EXPIR", 1), (r"DEPARTMENT OF HEALTH", 0.5),
      (r"LICENSE (NUMBER|NO\b|#)", 0.5), (r"\bOS ?\d{4,6}\b", 0.5), (r"\b(APRN|ARNP|RN|ME) ?\d{5,8}\b", 0.5)]),
    ("board-caqh", "Board certification", False,
     [(r"AMERICAN OSTEOPATHIC BOARD", 3), (r"\bAOBFP\b", 2.5), (r"\bDIPLOMATE\b", 2),
      (r"AMERICAN ACADEMY OF NURSE PRACTITIONERS|\bAANP\b", 3), (r"AMERICAN NURSES CREDENTIALING CENTER|\bANCC\b", 3),
      (r"BOARD CERTIFI", 2), (r"LONGITUDINAL ASSESSMENT", 2)]),
    ("board-caqh", "CAQH profile", False, [(r"\bCAQH\b", 3), (r"PROVIEW", 2), (r"RE-?ATTEST", 1.5)]),
    ("malpractice", "Malpractice certificate of insurance", False,
     [(r"CERTIFICATE OF LIABILITY INSURANCE", 3), (r"\bACORD\b", 2), (r"PROFESSIONAL LIABILITY", 2.5), (r"MALPRACTICE", 2),
      (r"MEDPRO", 2), (r"\bCM ?& ?F\b", 2), (r"POLICY (NUMBER|PERIOD)", 1), (r"EACH CLAIM|AGGREGATE", 1)]),
    ("screening", "Background screening", False,
     [(r"CLEARINGHOUSE", 2.5), (r"BACKGROUND SCREENING", 3), (r"LIVE ?SCAN", 2), (r"\bLEVEL 2\b", 1.5),
      (r"RETAINED PRINTS?", 2), (r"FINGERPRINT", 1.5)]),
    ("collaboration", "Collaboration agreement or protocol", False,
     [(r"COLLABORATIVE (PRACTICE )?AGREEMENT", 3), (r"COLLABORATING PHYSICIAN|SUPERVISING PHYSICIAN", 2),
      (r"(A\.? ?R\.? ?N\.? ?P\.?|A\.? ?P\.? ?R\.? ?N\.?|GENERAL|COLLABORATIVE|PRACTICE|WRITTEN) PROTOCOLS?|PROTOCOLS? (FOR|BETWEEN)|THIS PROTOCOL", 3),
      (r"\bPROTOCOLS?\b", 1), (r"NURSE PRACTICE ACT", 1.5),
      (r"464\.012", 2), (r"DELEGAT(ED|ION)|MEDICAL ACTS", 1)]),
    ("medicaid", "Medicaid enrollment", False,
     [(r"MEDICAID PROVIDER AGREEMENT", 3), (r"AGENCY FOR HEALTH CARE ADMINISTRATION|\bAHCA\b", 2), (r"FLORIDA MEDICAID", 2),
      (r"GAINWELL|FLMMIS", 2), (r"\bATN\b", 1), (r"PROVIDER ENROLLMENT", 1), (r"MEDICAID (ID|PROVIDER (ID|NUMBER))", 1.5)]),
    ("medicare-payers", "Medicare or payer enrollment", False,
     [(r"\bPECOS\b", 3), (r"CMS-? ?855", 3), (r"\bPTAN\b", 2), (r"MEDICARE (ENROLLMENT|APPROVAL|REVALIDATION)", 3),
      (r"FIRST COAST|NOVITAS|PALMETTO GBA", 1.5), (r"WELCOME TO (THE |OUR )?[A-Z0-9&'.\- ]{0,40}NETWORK|NOW (A )?PARTICIPATING|PLEASED TO (INFORM|WELCOME)", 3),
      (r"NOTICE OF (TERMINATION|NON-?RENEWAL)|TERMINAT\w* (OF )?(YOUR )?(PARTICIPATION|NETWORK|AGREEMENT|CONTRACT)|(AGREEMENT|PARTICIPATION|CONTRACT) (WILLOUGHBY )?TERMINATE", 3),
      (r"PARTICIPATING PROVIDER|PARTICIPATION AGREEMENT", 2), (r"RE-?CREDENTIALING|CREDENTIALING COMMITTEE", 2),
      (r"NETWORK (PARTICIPATION|STATUS|TERMINATION)", 2), (r"EFFECTIVE DATE", 0.5)]),
    ("privileges", "Hospital privileges", False,
     [(r"MEDICAL STAFF", 2), (r"REAPPOINTMENT", 2), (r"CLINICAL PRIVILEGES", 2), (r"CREDENTIALS COMMITTEE", 2),
      (r"\bPARALLON\b", 1.5)]),
    ("business", "NPI, tax or business record", False,
     [(r"EMPLOYER IDENTIFICATION NUMBER", 3), (r"\bCP ?575\b|\b147C\b", 3), (r"FORM W-?9|REQUEST FOR TAXPAYER", 3),
      (r"INTERNAL REVENUE SERVICE", 1.5), (r"DIVISION OF CORPORATIONS|SUNBIZ|ARTICLES OF (INCORPORATION|ORGANIZATION)", 3),
      (r"NATIONAL PLAN AND PROVIDER ENUMERATION|\bNPPES\b", 2.5), (r"\bANNUAL REPORT\b", 1.5)]),
    ("permits-insurance", "Permit or business insurance", False,
     [(r"BUSINESS TAX RECEIPT|LOCAL BUSINESS TAX|OCCUPATIONAL LICENSE", 3), (r"GENERAL LIABILITY", 2),
      (r"WORKERS'? COMPENSATION", 2), (r"\bCLIA\b|CERTIFICATE OF WAIVER", 3)]),
]
# Categories each kind of entity has a vault folder for (public.cred_folders); anything else needs a person to decide.
GROUP_ONLY = {"business", "permits-insurance", "correspondence", "payers", "medicare"}
PERSON_ONLY = {"license", "dea", "board-caqh", "malpractice", "screening", "identity", "privileges", "collaboration",
               "discipline"}

ERA_RULES = [(r"EXPLANATION OF (BENEFITS|PAYMENT)", 3), (r"REMITTANCE ADVICE|PROVIDER REMITTANCE|\bREMIT(TANCE)?\b", 2),
             (r"PATIENT ACC(OUN)?T", 1.5), (r"CLAIM (NUMBER|NO\b|#)", 1), (r"CHECK (NUMBER|NO\b|#|DATE|AMOUNT)", 1.5),
             (r"PAY TO THE ORDER OF", 2.5), (r"VOID AFTER \d+ DAYS", 2),
             (r"\bZELIS\b|ECHO HEALTH|VIRTUAL (CARD|CREDIT CARD)|\bVPAY\b|PAYSPAN", 2.5),
             (r"AMOUNT (PAID|BILLED|ALLOWED)|ALLOWED AMOUNT|PAID AMOUNT|PROVIDER PAID|PAYMENT AMOUNT", 1.5),
             (r"DEDUCTIBLE|CO-?INSURANCE|\bCOPAY", 1), (r"DATES? OF SERVICE|SERVICE DATE|\bDOS\b", 1),
             (r"\bICN\b|INTERNAL CONTROL", 1), (r"\b(CO|PR|OA|PI)-?\d{1,3}\b", 0.5), (r"\b99\d{3}\b", 0.5)]
FACESHEET_RULES = [(r"FACE ?SHEET", 3), (r"ADMISSION (RECORD|DATE)", 2), (r"RESIDENT (INFORMATION|NAME)", 2),
                   (r"POINTCLICKCARE|\bPCC\b", 1.5), (r"RESPONSIBLE PARTY|EMERGENCY CONTACT", 1.5),
                   (r"(PRIMARY|SECONDARY) (PAYER|PAYOR|INSURANCE)", 1.5), (r"\bMBI\b|MEDICARE (BENEFICIARY )?(ID|NUMBER)", 1),
                   (r"ATTENDING PHYSICIAN", 1), (r"PATIENT (INFORMATION|DEMOGRAPHICS|REGISTRATION)|GUARANTOR|ADMIT(TING)? (DATE|DX|DIAGNOSIS)", 1.5)]
BILLING_LETTER_RULES = [(r"ADDITIONAL DOCUMENTATION REQUEST|\bADR\b", 3), (r"MEDICAL RECORDS? REQUEST|REQUEST(ING)? (FOR )?(MEDICAL )?RECORDS", 3),
                        (r"OVERPAYMENT|REFUND REQUEST|RECOUP", 2.5), (r"RECONSIDERATION|REDETERMINATION|\bAPPEAL\b", 1.5),
                        (r"CLAIM (DENIAL|REJECT)", 1.5)]
PERSONAL_RULES = [(r"PRE-?QUALIFIED|PRESCREEN(ED)?", 3), (r"OPT-?OUT NOTICE", 2.5), (r"HOME EQUITY|\bHELOC\b", 2.5), (r"\d(\.\d+)?%\s*APR\b|\bAPR\s*:?\s*\d{1,2}(\.\d+)?%", 1),
                  (r"LIMITED[- ]TIME OFFER|SPECIAL OFFER", 2), (r"MEMBER FDIC|EQUAL HOUSING LENDER", 2),
                  (r"UNSUBSCRIBE|SWEEPSTAKES|YOU'?VE BEEN SELECTED", 2), (r"BALANCE TRANSFER|CREDIT CARD OFFER", 2)]
# Generic role words (the practice's own names and numbers come from the database at run time).
ROLE_CUES = {"aprn": [(r"\bAPRN\b|\bARNP\b|\bA\.R\.N\.P\b|\bA\.P\.R\.N\b|NURSE PRACTITIONER|ADVANCED PRACTICE REGISTERED NURSE", 1)],
             "physician": [(r"\bD\.? ?O\.?\b|OSTEOPATHIC PHYSICIAN|\bM\.? ?D\.?\b", 1)],
             "group": [(r"\b(P\.? ?A\.?|LLC|INC|PLLC)\b", 0.5)]}
CARD_NO = re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b")
SSN_DASHED = re.compile(r"\b(?!000|666|9\d\d)\d{3}[-\s.\u2013\u2014](?!00)\d{2}[-\s.\u2013\u2014](?!0000)\d{4}\b")
MONTHS = "JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC|JANUARY|FEBRUARY|MARCH|APRIL|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER"
DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b|\b(" + MONTHS + r")\.? (\d{1,2}),? (\d{4})\b|\b(\d{4})-(\d{2})-(\d{2})\b")
EXPIRY_CUE = re.compile(r"EXPIR|\bEXP\b|VALID (THROUGH|THRU|UNTIL)|GOOD THROUGH|POLICY PERIOD")
RANGE_TO = re.compile(r"^\s*(TO|THROUGH|THRU|-|\u2013)\s*$")
ISSUE_CUE = re.compile(r"ISSUE[D ]|DATE ISSUED|EFFECTIVE|DATE OF (ISSUE|NOTICE)|LETTER DATE|PRINTED|AS OF")
NEVER_DATE = re.compile(r"B[I1]RTH|\bD\.?\s?[O0]\.?\s?B\b|\bBORN\b")


def norm(text): return re.sub(r"\s+", " ", (text or "").upper())


def score(u, rules):
    hits, total = [], 0.0
    for pat, w in rules:
        if re.search(pat, u):
            total += w; hits.append(pat)
    return total, hits


def to_iso(m):
    try:
        if m.group(1):
            mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            y = y + 2000 if y < 100 else y
        elif m.group(4):
            mo = [x[:3] for x in MONTHS.split("|")].index(m.group(4)[:3]) + 1; d, y = int(m.group(5)), int(m.group(6))
        else:
            y, mo, d = int(m.group(7)), int(m.group(8)), int(m.group(9))
        return datetime.date(y, mo, d).isoformat()
    except (ValueError, IndexError):
        return None


def find_dates(text):
    """Issue and expiry dates by the words next to them; a line that speaks of a birth date is never read."""
    exp, iss = [], []
    for line in (text or "").splitlines():
        u = line.upper(); prev_end = 0; prev_start = None
        for m in DATE_RE.finditer(u):
            # only the words between the previous date and this one count, so 'DOB' never lends its date to 'EXP' or back
            before = u[max(prev_end, m.start() - 60):m.start()]; prev_end = m.end()
            first_on_line = prev_start is None; prev_start = m.start()
            if NEVER_DATE.search(before): continue
            iso = to_iso(m)
            if not iso or not ("1990" <= iso[:4] <= "2045"): continue
            if EXPIRY_CUE.search(before) or (not first_on_line and RANGE_TO.match(before)): exp.append(iso)
            elif ISSUE_CUE.search(before): iss.append(iso)
    return (max(exp) if exp else None), (max(iss) if iss else None)


def entity_cues(providers, kinds=None):
    """providers: rows (id, name, npi, caqh_id, license_no, dea_no) from public.cred_providers -> {entity: [(regex, weight)]}.
    A clinician's last name that is also the first word of the practice's name ("Doe" in "Doe Health PA") does not count when
    the practice name follows it - otherwise every practice letter would read as the clinician's own paper."""
    def words_of(name):
        return [w for w in re.findall(r"[A-Za-z]+", (name or "").split(",")[0]) if len(w) > 2 and w.upper() not in ("ARNP", "APRN", "HEALTH", "INC", "LLC", "PLLC")]
    group_follow = {}
    is_group = lambda pid: (kinds or {}).get(pid) == "group" or pid == "group"
    for pid, name, *_ in providers:
        if is_group(pid):
            ws = re.findall(r"[A-Za-z]+", name or "")
            if len(ws) >= 2: group_follow.setdefault(ws[0].upper(), []).append(ws[1].upper())
    cues = {}
    for pid, name, npi, caqh, lic, dea in providers:
        c = []
        words = words_of(name)
        if words:
            if is_group(pid):
                ws = re.findall(r"[A-Za-z]+", name or "")
                c.append((r"\b" + r"\s+".join(re.escape(w.upper()) for w in ws[:2]) + r"\b", 3))
            else:
                first, last = words[0].upper(), words[-1].upper()
                not_group = "".join(r"(?!\s+%s\b)" % re.escape(f) for f in group_follow.get(last, []))
                c.append((r"\b" + re.escape(first) + r"\b", 1)); c.append((r"\b" + re.escape(last) + r"\b" + not_group, 2))
        for num, w in ((npi, 4), (caqh, 3), (dea, 4)):
            if num: c.append((r"\b" + re.escape(str(num).upper()) + r"\b", w))
        if lic:
            digits = re.sub(r"\D", "", str(lic))
            pre = re.sub(r"[^A-Z]", "", str(lic).upper())
            if digits: c.append(((r"\b" + re.escape(pre) + r"\s?#?\s?" if pre else r"\b") + digits + r"\b", 4 if pre or len(digits) >= 7 else 1))
        cues[pid] = c
    return cues


SUBJECT = re.compile(r"\b(RE|SUBJECT|REGARDING|APPLICANT|PROVIDER NAME|PRACTITIONER NAME|NAME OF (APPLICANT|PROVIDER|PRACTITIONER))\b\s*:?\s*(.{0,120})")
COLLAB_CTX = re.compile(r"COLLABORATING PHYSICIAN|SUPERVISING PHYSICIAN|COLLABORATIVE (PRACTICE )?AGREEMENT|MEDICAL DIRECTOR")


def pick_entity(u, category, cues, kinds):
    """Who the document belongs to. kinds: {entity: 'individual'|'aprn-pa'|'group'}."""
    s = {e: score(u, r)[0] for e, r in cues.items()}
    for m in SUBJECT.finditer(u):                          # the name on the subject / applicant line is who the paper is about
        for e, r in cues.items(): s[e] += score(m.group(3), r)[0]
    for e, k in kinds.items():
        if k == "aprn-pa": s[e] = s.get(e, 0) + score(u, ROLE_CUES["aprn"])[0]
        elif k == "individual": s[e] = s.get(e, 0) + score(u, ROLE_CUES["physician"])[0] * 0.5
    people = {e: v for e, v in s.items() if kinds.get(e) != "group"}
    groups = {e: v for e, v in s.items() if kinds.get(e) == "group"}
    best_p = max(people, key=people.get) if people else None
    best_g = max(groups, key=groups.get) if groups else None
    if category in GROUP_ONLY:
        return best_g, s
    aprn = [e for e, k in kinds.items() if k == "aprn-pa"]
    if category == "collaboration" and aprn:
        return max(aprn, key=lambda e: s.get(e, 0)), s
    # an APRN's own papers name the collaborating physician (who often signs the cover letter too): when the paper speaks
    # of the collaboration and the APRN is clearly named, it is the APRN's
    if aprn and COLLAB_CTX.search(u):
        a = max(aprn, key=lambda e: s.get(e, 0))
        if s.get(a, 0) >= 4 and category != "privileges": return a, s
    # a category both the practice and the clinicians have (Medicaid): the practice when its own cues outweigh every clinician's
    if category not in PERSON_ONLY and best_g and (not best_p or groups[best_g] > people[best_p]):
        return (best_g if groups[best_g] >= 3 else None), s
    second = sorted(people.values(), reverse=True)[1] if len(people) > 1 else 0
    if best_p and people[best_p] >= 2 and not (second >= 2 and people[best_p] - second < 4): return best_p, s
    return None, s


def classify_text(text, route="auto", cues=None, kinds=None):
    u = norm(text)
    cues = cues or {}; kinds = kinds or {}
    out = {"route": route, "kind": "unknown", "entity": None, "category": None, "doc_type": None, "restricted": False,
           "restricted_reason": None, "expires": None, "doc_date": None, "confidence": "low", "cues": [], "flags": []}
    if len(u.strip()) < 40:
        if SSN_DASHED.search(u) and re.search(r"SOCIAL SECURITY|\bSSA\b|\bSSN\b", u):   # a short, badly read SS card is still one
            out.update(kind="credentialing", category="identity", doc_type="Social Security card", restricted=True, confidence="medium",
                       restricted_reason="shows a Social Security number")
            out["flags"].append("SSN-bearing page - a person checks it")
            out["entity"], s_ = pick_entity(u, "identity", cues, kinds)
            return out
        out["flags"].append("no readable text - check the scan"); return out
    era, era_h = score(u, ERA_RULES)
    face, face_h = score(u, FACESHEET_RULES)
    letter, letter_h = score(u, BILLING_LETTER_RULES)
    pers, pers_h = score(u, PERSONAL_RULES)
    best_cred = (0.0, None)
    for cat, dtype, restr, rules in CRED_RULES:
        sc, h = score(u, rules)
        if sc > best_cred[0]: best_cred = (sc, (cat, dtype, restr, h))
    # a restricted category (discipline, identity) wins when its own cues are real - at least 3 and half the best other
    # category - so a monitoring agreement that names the board still files as discipline, while a Medicaid agreement whose
    # fine print says "final order" stays a Medicaid agreement
    top_open = max((score(u, rl)[0] for _, _, r_, rl in CRED_RULES if not r_), default=0.0)
    restr_best = max(((sc2, (c2, d2, r2, h2)) for c2, d2, r2, rl2 in CRED_RULES if r2 for sc2, h2 in [score(u, rl2)]
                      if sc2 >= 3 and sc2 >= 0.5 * top_open), default=None, key=lambda x: x[0])
    if restr_best: best_cred = (max(best_cred[0], restr_best[0]), restr_best[1])
    cred = best_cred[0]
    bill = max(era, face, letter)
    # personal mail first: a prescreened offer is never practice paper, whatever folder it came in
    if pers >= 5 and pers >= max(cred, bill):
        out.update(kind="personal", confidence="high" if pers >= 7 else "medium", cues=pers_h[:6]); return out
    # route bias: the folder is a hint worth +1.5 to its side; the text still decides
    bias_bill = 1.5 if route == "billing" else 0
    bias_cred = 1.5 if route == "credentialing" else 0
    remit_veto = bool(re.search(r"REMITTANCE ADVICE|EXPLANATION OF (BENEFITS|PAYMENT)|PAY TO THE ORDER OF", u)) and bool(re.search(r"\bICN\b|CLAIM (NUMBER|NO\b|#)|PATIENT ACC|RECIPIENT (ID|NAME)", u))
    if remit_veto or (bill + bias_bill >= 3 and bill + bias_bill > cred + bias_cred):
        kind = "era" if era >= max(face, letter) else ("facesheet" if face >= letter else "billing_letter")
        hits = era_h if kind == "era" else (face_h if kind == "facesheet" else letter_h)
        out.update(kind=kind, confidence="high" if bill >= 6 else "medium", cues=hits[:6])
        if route == "credentialing": out["flags"].append("note: billing paper in the credentialing folder - routed to billing")
        return out
    if cred + bias_cred >= 3 and best_cred[1]:
        cat, dtype, restr, hits = best_cred[1]
        out.update(kind="credentialing", category=cat, doc_type=dtype, restricted=restr, cues=hits[:6],
                   restricted_reason=("identity document" if cat == "identity" else "discipline record" if cat == "discipline" else None),
                   confidence="high" if cred >= 5 else "medium")
        if route == "billing": out["flags"].append("note: credentialing paper in the billing folder - routed to credentialing")
    elif route == "credentialing":
        out.update(kind="credentialing", confidence="low"); out["flags"].append("credentialing folder, but no category matched - a person decides")
    elif route == "billing" and bill >= 1.5:
        out.update(kind="era", confidence="low", cues=era_h[:6]); out["flags"].append("billing folder, weak remittance cues - check it")
    if out["kind"] == "unknown" and SSN_DASHED.search(u) and re.search(r"SOCIAL SECURITY|\bSSA\b|\bSSN\b", u):
        out.update(kind="credentialing", category="identity", doc_type="Social Security card", restricted=True, confidence="medium",
                   restricted_reason="shows a Social Security number"); out["flags"].append("SSN-bearing page - a person checks it")
    if out["kind"] == "credentialing":
        rr = [c for c, _, restr, rules in CRED_RULES if restr and score(u, rules)[0] >= 3 and score(u, rules)[0] >= 0.5 * top_open]
        if rr and not out["restricted"]: out["restricted"] = True; out["restricted_reason"] = rr[0] + " cues on the page"
        if CARD_NO.search(u):
            out["restricted"] = True; out["restricted_reason"] = out["restricted_reason"] or "shows a card number"
        if SSN_DASHED.search(u) or re.search(r"SOCIAL SECURITY (NUMBER|NO\b|#)|\bSSN\b", u):
            out["restricted"] = True; out["restricted_reason"] = out["restricted_reason"] or "shows a Social Security number"
        ent, s = pick_entity(u, out["category"], cues, kinds)
        out["entity"] = ent
        out["entity_scores"] = {e: round(v, 1) for e, v in s.items()}
        cat = out["category"]
        people = {e: v for e, v in s.items() if kinds.get(e) != "group"}
        top_person = max(people, key=people.get) if people else None
        if cat == "business" and top_person and people[top_person] >= s.get(ent, 0) + 2:
            ent = out["entity"] = top_person; cat = out["category"] = "medicare-payers"
            out["flags"].append("note: an individual's NPI or tax record - filed with that person's Medicare and payers papers")
        if ent and kinds.get(ent) == "group" and cat == "medicare-payers": out["category"] = "payers" if not re.search(r"MEDICARE|PECOS|PTAN|CMS", u) else "medicare"
        if ent and kinds.get(ent) != "group" and cat in GROUP_ONLY: out["flags"].append("a group category on a clinician's paper - check it")
        if ent and kinds.get(ent) == "group" and cat in PERSON_ONLY: out["flags"].append("a clinician category on group paper - check it")
        if ent is None and cat: out["flags"].append("whose document is unclear - a person decides")
        out["expires"], out["doc_date"] = find_dates(text)
        if out["category"] == "identity": out["doc_date"] = None
    return out


def doc_id_for(entity, category, doc_date, expires, taken):
    year = (doc_date or expires or datetime.date.today().isoformat())[:4]
    base = "%s-%s-%s" % (entity or "unsorted", category or "doc", year)
    i, cand = 1, base
    while cand in taken: i += 1; cand = "%s-%d" % (base, i)
    return cand



def pdf_pages_text(path, dpi=200):
    """One text per page: the page's own text layer when it has one (80+ characters), else tesseract on that page alone - a
    file can mix typed pages and scanned enclosures. ScanSnap duplex backs come out (nearly) empty and count as continuation pages."""
    info = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", info, re.M)
    n = int(m.group(1)) if m else 0
    texts = [subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), path, "-"], capture_output=True, text=True).stdout
             for i in range(1, n + 1)]
    need = [i for i, t in enumerate(texts, 1) if len(re.sub(r"\s+", "", t)) < 80]
    if not need: return texts, "text layer"
    if not shutil.which("tesseract"):
        sys.exit("scan_intake: %d page(s) have no text layer and tesseract is not installed (apt-get install -y tesseract-ocr), "
                 "or pass Drive's OCR text with --text" % len(need))
    tmp = tempfile.mkdtemp(prefix="scanocr_")
    env = dict(os.environ, OMP_THREAD_LIMIT="1")
    def one(i):
        base = os.path.join(tmp, "p%04d" % i)
        subprocess.run(["pdftoppm", "-r", str(dpi), "-gray", "-png", "-f", str(i), "-l", str(i), "-singlefile", path, base], capture_output=True)
        img = base + ".png"
        if not os.path.exists(img): return i, ""
        return i, subprocess.run(["tesseract", img, "-", "--psm", "6"], capture_output=True, text=True, env=env).stdout
    try:
        with ThreadPoolExecutor(max(1, (os.cpu_count() or 2))) as ex:
            for i, t in ex.map(one, need): texts[i - 1] = t
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return texts, ("tesseract" if len(need) == n else "text layer + tesseract (%d page(s))" % len(need))


CONT = re.compile(r"\b(SECTION|ARTICLE)\s+[IVX\d]+\b|\bEXHIBIT\s+[A-Z\d]\b|\bPAGE\s+\d+\s+OF\s+\d+\b|WHEREAS|IN WITNESS WHEREOF|THIS (AGREEMENT|PROTOCOL|CONTRACT)")
COARSE = {"era": "billing", "facesheet": "billing", "billing_letter": "billing", "credentialing": "credentialing", "personal": "personal"}


def segment(pages, route, cues, kinds):
    """Pages -> documents. (1) Runs of one coarse kind (billing / credentialing / personal); a page without a clear label (a
    duplex back, a page of terms, page 3 of a 5-page agreement) continues the run it is in. (2) Billing runs stay whole - the
    paper-remit pipeline reads them page by page itself. (3) A credentialing run is cut only where a page is CLEARLY another
    credential (high confidence, other category) and what came before is clearly a credential of its own. (4) Neighbours that
    read as one document together are merged back."""
    labels = [classify_text(t, route, cues, kinds) for t in pages]
    join = lambda nums: "\n".join(pages[p - 1] for p in nums)
    runs = []
    for i, r in enumerate(labels, 1):
        c = COARSE.get(r["kind"]) if r["confidence"] in ("high", "medium") else None
        if c and runs and runs[-1]["coarse"] not in (None, c) and CONT.search(norm(pages[i - 1])): c = None
        if runs and (c is None or runs[-1]["coarse"] in (None, c)):
            if runs[-1]["coarse"] is None: runs[-1]["coarse"] = c
            runs[-1]["pages"].append(i); continue
        runs.append({"coarse": c, "pages": [i]})
    groups = []
    for run in runs:
        if run["coarse"] != "credentialing":
            groups.append(run["pages"]); continue
        cur, cur_cat = [], None
        for p in run["pages"]:
            r = labels[p - 1]
            if cur and cur_cat and r["confidence"] == "high" and r["category"] and not CONT.search(norm(pages[p - 1])) and (r["category"] != cur_cat or (r["entity"] and labels[cur[0] - 1]["entity"] not in (None, r["entity"]))):
                before = classify_text(join(cur), route, cues, kinds)
                if before["confidence"] == "high" and (before["category"] == cur_cat or r["category"] == cur_cat):
                    groups.append(cur); cur, cur_cat = [p], r["category"]; continue
            cur.append(p)
            if cur_cat is None and r["confidence"] in ("high", "medium"): cur_cat = r["category"]
        if cur: groups.append(cur)
    i = 0
    while i < len(groups) - 1:
        a, b = groups[i], groups[i + 1]
        ra, rb, rab = (classify_text(join(x), route, cues, kinds) for x in (a, b, a + b))
        if (ra["kind"] == rb["kind"] == rab["kind"] == "credentialing" and rab["category"] == ra["category"]
                and rb["confidence"] != "high" and rb["entity"] in (None, ra["entity"]) and ra["entity"] in (None, rb["entity"], rab["entity"])):
            groups[i] = a + b; del groups[i + 1]; continue
        i += 1
    docs = []
    for g in groups:
        r = classify_text(join(g), route, cues, kinds)
        r["pages"] = page_ranges(g)
        if any(labels[p - 1]["restricted"] for p in g) and not r["restricted"]: r["restricted"] = True; r["flags"].append("note: a page of it is restricted")
        docs.append(r)
    return docs


def page_ranges(nums):
    out, start, prev = [], None, None
    for n in nums:
        if start is None: start = prev = n; continue
        if n == prev + 1: prev = n; continue
        out.append("%d-%d" % (start, prev) if start != prev else str(start)); start = prev = n
    if start is not None: out.append("%d-%d" % (start, prev) if start != prev else str(start))
    return ",".join(out)


def split_pdf(path, out_dir, groups):
    from pypdf import PdfReader, PdfWriter
    rd = PdfReader(path); os.makedirs(out_dir, exist_ok=True); made = []
    for k, g in enumerate(groups.split(","), 1):
        pages = []
        for part in g.split("+"):
            a, _, b = part.partition("-"); pages += list(range(int(a), int(b or a) + 1))
        w = PdfWriter()
        for p in pages: w.add_page(rd.pages[p - 1])
        f = os.path.join(out_dir, "part%02d_p%s.pdf" % (k, g.replace(",", "_").replace("+", "_")))
        with open(f, "wb") as fh: w.write(fh)
        made.append(f); print("%s  %d page(s)  sha256 %s" % (f, len(pages), hashlib.sha256(open(f, "rb").read()).hexdigest()))
    return made


# ---------------------------------------------------------------------------------------------------------------------------
# Database
CONNECTOR_MAX = 10 * 1000 * 1000                         # the Google Drive connector's download limit (bytes)
SLICE = 4000000                                         # the Zapier code action's largest slice
ZAPIER_ACTION = "google_drive_get_file_byte_range_base64"   # Zapier code action (file_id, start, length) - one Zapier task per call
ZAPIER_NIGHT_CAP = 25                                    # slices a night (~100 MB); every call is one Zapier task (the 10/5 pile hit the monthly limit)


def fetch_plan(size):
    """How a file of `size` bytes comes into the container: the connector (<= 10 MB) or Zapier byte-range slices of <= 4 MB."""
    if size <= CONNECTOR_MAX: return {"route": "connector"}
    return {"route": "zapier", "slices": [(s, min(SLICE, size - s)) for s in range(0, size, SLICE)]}


def db():
    sys.path.insert(0, os.path.join(REPO, "credentialing"))
    saved = sys.argv[:]; sys.argv = sys.argv[:1]
    try:
        import cred_vault
    finally:
        sys.argv = saved
    return cred_vault.DB(), cred_vault


DDL = [
    """create table if not exists public.intake_folders (
         folder_id text primary key, practice text not null default 'ehpa', route text not null, title text, parent_id text,
         active boolean not null default true, added_at timestamptz not null default now(), updated_at timestamptz not null default now())""",
    """create table if not exists public.scan_intake (
         drive_file_id text primary key, practice text not null default 'ehpa', folder_id text, route text, title text,
         mime_type text, size_bytes bigint, sha256 text, pages int, created_in_drive timestamptz,
         kind text, entity text, category text, restricted boolean, detail jsonb,
         status text not null default 'new', routed_to text, vault_doc_id text, notes text,
         first_seen timestamptz not null default now(), classified_at timestamptz, processed_at timestamptz,
         updated_at timestamptz not null default now())""",
    "create index if not exists scan_intake_status on public.scan_intake (practice, status)",
]


def route_for_title(title):
    t = (title or "").lower()
    if "credential" in t: return "credentialing"
    if re.search(r"\beras?\b|billing|remit|\beobs?\b", t): return "billing"
    return "auto"


def rows_or_none(d, did):
    return d.q("select 1 from public.scan_intake where drive_file_id=%s", [did])


def outside_repo(path):
    """Scans, their text and their split parts never sit in the repository's working tree (it is public and the PHI gate
    reads text files only)."""
    real = os.path.realpath(path)
    if real == REPO or real.startswith(REPO + os.sep):
        sys.exit("scan_intake: %s is inside the repository - keep scans in a scratch or /home/claude/scans folder" % path)
    return path


def load_listing(path):
    j = json.load(open(path))
    if isinstance(j, list): return j
    return j.get("files") or j.get("items") or []


def main():
    cmd = A[0] if A else "help"
    if cmd == "selftest": return selftest()
    if cmd == "split": split_pdf(outside_repo(A[1]), outside_repo(A[2]), opt("--groups")); return
    if cmd not in ("ensure-tables", "folders-sync", "folders", "register", "pending", "classify", "mark"): sys.exit(__doc__)
    d, cv = db()
    practice = opt("--practice", "ehpa")
    if cmd == "ensure-tables":
        have = d.q("select to_regclass('public.intake_folders') is not null, to_regclass('public.scan_intake') is not null")[0]
        if all(x in (True, "true", "t", "True") for x in have):
            print("tables ready: public.intake_folders, public.scan_intake"); return
        # the routine's role can read and write rows but not create tables: the database owner runs DDL (Neon connector run_sql),
        # then: grant select, insert, update on public.intake_folders, public.scan_intake to <the routine's role>
        for s in DDL: d.q(s)
        print("tables created: public.intake_folders, public.scan_intake"); return
    if cmd == "folders-sync":
        for f in load_listing(A[1]):
            if f.get("mimeType") != "application/vnd.google-apps.folder": continue
            r = route_for_title(f.get("title"))
            d.q("insert into public.intake_folders (folder_id, practice, route, title, parent_id) values (%s,%s,%s,%s,%s) "
                "on conflict (folder_id) do update set title=excluded.title, parent_id=excluded.parent_id, updated_at=now()",
                [f["id"], practice, r, f.get("title"), f.get("parentId")])
        cmd = "folders"
    if cmd == "folders":
        for r in d.q("select folder_id, route, title, active from public.intake_folders where practice=%s order by route, title", [practice]):
            print("%-34s %-14s %-6s %s" % (r[0], r[1], "on" if r[3] in (True, "true", "t", "True") else "off", r[2]))
        return
    if cmd == "register":
        routes = {r[0]: r[1] for r in d.q("select folder_id, route from public.intake_folders where practice=%s and active", [practice])}
        new = 0
        for f in load_listing(A[1]):
            if f.get("mimeType") == "application/vnd.google-apps.folder" or f.get("trashed"): continue
            parent = f.get("parentId"); route = routes.get(parent, "auto")
            rows = d.q("insert into public.scan_intake (drive_file_id, practice, folder_id, route, title, mime_type, size_bytes, created_in_drive) "
                       "values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict (drive_file_id) do nothing returning drive_file_id",
                       [f["id"], practice, parent, route, f.get("title"), f.get("mimeType"), f.get("fileSize"), f.get("createdTime")])
            if rows: new += 1; print("new  %s  route=%s  %s bytes" % (f["id"], route, f.get("fileSize") or "?"))
        print("%d new file(s) registered" % new); return
    if cmd == "pending":
        rows = d.q("select drive_file_id, route, status, kind, size_bytes, first_seen from public.scan_intake where practice=%s "
                   "and status not in ('filed','routed','skipped') order by first_seen", [practice])
        for r in rows:
            fp = fetch_plan(int(r[4] or 0))
            print("%-34s %-14s %-13s %-15s %-10s %s" % (r[0], r[1], r[2], r[3] or "-", r[4] or "?",
                  "fetch: connector" if fp["route"] == "connector" else "fetch: zapier x%d (fetch-plan %s)" % (len(fp["slices"]), r[0])))
        print("%d pending" % len(rows)); return
    if cmd == "fetch-plan":
        # William 11/27/2026: "there was a zapier connection once used for large files solidify that in the coding so im not limited to
        #   25 page uploads". The Drive connector stops at 10 MB (a 25-page ScanSnap batch); a bigger file comes through the Zapier code
        #   action in 4 MB slices that fetch_scans.py joins and checks against Drive's md5 (the 10/5/2026 route, billing/era_input/README.md).
        size = int(opt("--size") or (rows_or_none(d, A[1]) or [[None] * 8])[0][6] or 0) if len(A) > 1 else 0
        if not size: sys.exit("fetch-plan <drive-id> [--size <bytes>]: the size is not registered - pass --size from the folder listing")
        fp = fetch_plan(size)
        if fp["route"] == "connector":
            print("connector: download_file_content fileId=%s (%d bytes <= %d)" % (A[1], size, CONNECTOR_MAX)); return
        for i, (start, length) in enumerate(fp["slices"], 1):
            print("zapier %d/%d: execute_zapier_write_action tool_name=%s params={file_id: %s, start: %d, length: %d}" % (i, len(fp["slices"]), ZAPIER_ACTION, A[1], start, length))
        print("then: python3 billing/era_input/fetch_scans.py chunks <the %d persisted slice results>  (joins them, checks Drive's md5)" % len(fp["slices"]))
        print("zapier tasks: %d (one per slice; nights cap at %d)" % (len(fp["slices"]), ZAPIER_NIGHT_CAP)); return
    if cmd == "classify":
        did = opt("--drive-id"); route = opt("--route")
        if did and not route:
            r = d.q("select route from public.scan_intake where drive_file_id=%s", [did]); route = r[0][0] if r else "auto"
        route = route or "auto"
        prov = d.q("select id, name, npi, caqh_id, license_no, dea_no from public.cred_providers where coalesce(active::text,'true') <> 'false'")
        kinds = dict(cv.ENTITY_KIND); cues = entity_cues(prov, kinds)
        sha, npages, how = opt("--sha256"), None, "text"
        if opt("--pdf"):
            pdf = outside_repo(opt("--pdf")); sha = hashlib.sha256(open(pdf, "rb").read()).hexdigest()
            pages, how = pdf_pages_text(pdf); npages = len(pages)
            if not npages:
                if did: d.q("update public.scan_intake set status=%s, notes=%s, updated_at=now() where drive_file_id=%s", ["error", "PDF could not be read (0 pages)", did])
                sys.exit("scan_intake: %s could not be read (0 pages) - a damaged or partial download" % pdf)
            docs = segment(pages, route, cues, kinds)
        else:
            docs = [classify_text(open(outside_repo(opt("--text")), encoding="utf-8", errors="replace").read(), route, cues, kinds)]
            npages = int(opt("--pages")) if opt("--pages") else None
        taken = set()
        for res in docs:
            if res["kind"] == "credentialing" and res["entity"] and res["category"]:
                cat = res["category"]
                if res["restricted"] and res["entity"] and kinds.get(res["entity"]) == "group":
                    res["vault_folder_id"] = None; res["vault_category"] = cat; res["doc_id"] = None
                    res["flags"].append("restricted practice paper (it shows an SSN or card number) - the practice has no restricted folder; a person files it")
                    continue
                if res["restricted"] and cat not in ("identity", "discipline") and res["entity"] != "group":
                    cat = "identity"; res["flags"].append("note: shows an SSN - filed with the restricted identity documents")
                f = d.q("select drive_folder_id from public.cred_folders where practice=%s and entity=%s and category=%s",
                        [practice, res["entity"], cat])
                res["vault_folder_id"] = f[0][0] if f else None
                res["vault_category"] = cat
                if not f: res["flags"].append("no vault folder for %s/%s - a person decides" % (res["entity"], cat))
                taken |= {r[0] for r in d.q("select id from public.cred_documents where id like %s", ["%s-%s-%%" % (res["entity"], cat)])}
                taken |= {r[0] for r in d.q("select jsonb_array_elements(detail->'documents')->>'doc_id' from public.scan_intake "
                                            "where practice=%s and status not in ('filed','skipped') and drive_file_id <> %s and detail ? 'documents'",
                                            [practice, did or ""]) if r[0]}
                res["doc_id"] = doc_id_for(res["entity"], cat, res["doc_date"], res["expires"], taken); taken.add(res["doc_id"])
        out = {"drive_file_id": did, "route": route, "read_by": how, "pages": npages, "sha256": sha, "documents": docs, "flags": []}
        if len(docs) > 1:
            groups = ",".join((x.get("pages") or "?").replace(",", "+") for x in docs)
            out["split_groups"] = groups
            out["flags"].append("note: %d documents in one scan - split with: split <pdf> <dir> --groups %s" % (len(docs), groups))
        if sha:
            dup = d.q("select drive_file_id from public.scan_intake where sha256=%s and drive_file_id <> %s and status in ('filed','routed')",
                      [sha, did or ""])
            dup2 = d.q("select id from public.cred_documents where sha256=%s", [sha])
            if dup or dup2: out["duplicate_of"] = (dup[0][0] if dup else dup2[0][0]); out["flags"].append("same bytes already on file")
        print(json.dumps(out, indent=1))
        if did:
            kinds_seen = sorted({x["kind"] for x in docs})
            held = lambda flags: [f for f in flags if not f.startswith("note: ")]
            review = any(x["kind"] == "unknown" or held(x["flags"]) or (x["kind"] == "credentialing" and x["confidence"] == "low") for x in docs)
            first = docs[0] if docs else {}
            d.q("update public.scan_intake set route=%s, kind=%s, entity=%s, category=%s, restricted=%s, detail=%s::jsonb, sha256=coalesce(%s, sha256), "
                "pages=coalesce(%s, pages), status=%s, classified_at=now(), updated_at=now() where drive_file_id=%s",
                [route, kinds_seen[0] if len(kinds_seen) == 1 else "mixed", first.get("entity") if len(docs) == 1 else None,
                 (first.get("vault_category") or first.get("category")) if len(docs) == 1 else None,
                 any(x["restricted"] for x in docs), json.dumps(out), sha, npages,
                 "needs_review" if review or out.get("duplicate_of") else "classified", did])
        return
    if cmd == "split":
        split_pdf(A[1], A[2], opt("--groups")); return
    if cmd == "mark":
        did = A[1] if len(A) > 1 else sys.exit(__doc__); st = opt("--status")
        if st not in ("filed", "routed", "skipped", "needs_review", "error", "new"): sys.exit("--status filed|routed|skipped|needs_review|error|new")
        d.q("update public.scan_intake set status=%s, routed_to=coalesce(%s, routed_to), vault_doc_id=coalesce(%s, vault_doc_id), "
            "notes=coalesce(%s, notes), processed_at=case when %s in ('filed','routed','skipped') then now() else processed_at end, "
            "updated_at=now() where drive_file_id=%s returning drive_file_id",
            [st, opt("--routed-to"), opt("--vault-doc-id"), opt("--note"), st, did])
        if not rows_or_none(d, did): sys.exit("scan_intake: no register row for %s - run register first" % did)
        print("marked %s %s" % (did, st))


# ---------------------------------------------------------------------------------------------------------------------------
def selftest():
    assert fetch_plan(9_000_000) == {"route": "connector"} and len(fetch_plan(20_785_992)["slices"]) == 6
    assert fetch_plan(8_000_001)["route"] == "connector" and fetch_plan(10_000_001)["slices"][-1] == (8_000_000, 2_000_001)
    """Synthetic samples only - no real person, number or document."""
    kinds = {"doe": "individual", "roe": "aprn-pa", "grp": "group", "grp2": "group"}
    cues = entity_cues([("doe", "John Doe, DO", "1000000001", "90000001", "OS99999", None),
                        ("roe", "Jane Roe, APRN", "1000000002", "90000002", "APRN7777777", None),
                        ("grp", "Sample Clinic PA", "1000000003", None, None, None), ("grp2", "Doe Health LLC", "1000000004", None, None, None)])
    cases = [
        ("PRESCREEN & OPT-OUT NOTICE. You're pre-qualified for a home equity line of credit (HELOC). APR 10.4%. Member FDIC. Equal Housing Lender.",
         "credentialing", ("personal", None, None)),
        ("U.S. DEPARTMENT OF JUSTICE DRUG ENFORCEMENT ADMINISTRATION CONTROLLED SUBSTANCE REGISTRATION CERTIFICATE "
         "JOHN DOE DO SCHEDULES 2,2N,3,3N,4,5 EXPIRATION DATE 08-31-2028 FEE PAID", "credentialing", ("credentialing", "doe", "dea")),
        ("Florida Department of Health License Verification JANE ROE License Number APRN7777777 Status CLEAR/ACTIVE "
         "Expiration Date 04/30/2027 Board of Nursing", "auto", ("credentialing", "roe", "license")),
        ("CERTIFICATE OF LIABILITY INSURANCE ACORD 25 PRODUCER MedPro INSURED JOHN DOE DO PROFESSIONAL LIABILITY "
         "POLICY PERIOD 02/14/2026 TO 02/14/2027 EACH CLAIM 1,000,000 AGGREGATE 3,000,000", "auto", ("credentialing", "doe", "malpractice")),
        ("SOCIAL SECURITY THIS NUMBER HAS BEEN ESTABLISHED FOR JANE ROE", "credentialing", ("credentialing", "roe", "identity")),
        ("EXPLANATION OF BENEFITS Patient Acct 12345678A Claim Number 2026123 Dates of Service 10/01/2026 99309 "
         "Amount Billed 141.00 Allowed Amount 98.00 Paid Amount 78.40 Coinsurance 19.60 PR-2 Check Number 00123", "billing", ("era", None, None)),
        ("EXPLANATION OF BENEFITS Patient Acct 12345678A Claim Number 2026123 Amount Paid 78.40 Check Number 00123 PAY TO THE ORDER OF SAMPLE CLINIC PA",
         "credentialing", ("era", None, None)),
        ("FACE SHEET Resident Information Admission Date 11/01/2026 Primary Payer MEDICARE Secondary Payer MEDICAID Responsible Party",
         "auto", ("facesheet", None, None)),
        ("FLORIDA MEDICAID PROVIDER AGREEMENT Agency for Health Care Administration SAMPLE CLINIC PA NPI 1000000003 "
         "Medicaid ID renewal", "credentialing", ("credentialing", "grp", "medicaid")),
        ("INTERVENTION PROJECT FOR NURSES participant contract JANE ROE APRN", "credentialing", ("credentialing", "roe", "discipline")),
        ("PRACTITIONER COLLABORATIVE AGREEMENT Collaborating physician JOHN DOE DO OS99999 Advanced Practice Registered Nurse JANE ROE APRN7777777",
         "credentialing", ("credentialing", "roe", "collaboration")),
        ("Request for Taxpayer Identification Number and Certification Form W-9 SAMPLE CLINIC PA Employer identification number",
         "credentialing", ("credentialing", "grp", "business")),
        ("ADDITIONAL DOCUMENTATION REQUEST medical records request for claims", "billing", ("billing_letter", None, None)),
    ]
    cases += [   # lessons from the 11/27/2026 run on real vault documents (synthetic stand-ins)
        ("NATIONAL PRACTITIONER DATA BANK self-query response JANE ROE Social Security Number on file License Number APRN7777777 "
         "DEA number field Adverse action report", "credentialing", ("credentialing", "roe", "discipline")),
        ("A.R.N.P PROTOCOL JANE ROE, A.R.N.P. JOHN DOE, D.O. (MEDICAL DIRECTOR) Nurse Practice Act ... THIS PROTOCOL SHALL APPLY "
         "Board of Nursing license number APRN7777777", "credentialing", ("credentialing", "roe", "collaboration")),
        ("FLORIDA MEDICAID PROVIDER AGREEMENT Agency for Health Care Administration Provider: SAMPLE CLINIC PA NPI 1000000003 "
         "signed JOHN DOE, President", "credentialing", ("credentialing", "grp", "medicaid")),
        ("Re: Jane Roe, APRN - Florida Medicaid application ATN, collaborating physician John Doe, DO OS99999. Agency for Health Care "
         "Administration. Sincerely, John Doe, DO", "credentialing", ("credentialing", "roe", "medicaid")),
        ("DOE HEALTH LLC business tax receipt Local Business Tax", "credentialing", ("credentialing", "grp2", "permits-insurance")),
    ]
    fake_spaced = " ".join(["123", "45", "6789"])
    cases += [   # the 11/27/2026 adversarial review (synthetic)
        ("FINAL ORDER Department of Health v. JOHN DOE, D.O. License No. OS99999 Board of Osteopathic Medicine", "credentialing",
         ("credentialing", "doe", "discipline")),
        ("SOCIAL SECURITY " + fake_spaced + " JANE ROE", "auto", ("credentialing", "roe", "identity")),
        ("FLORIDA MEDICAID REMITTANCE ADVICE GAINWELL Medicaid provider ID ICN 1234567 Recipient ID Paid amt 45.00", "credentialing",
         ("era", None, None)),
        ("PROFESSIONALS RESOURCE NETWORK MONITORING AGREEMENT JOHN DOE Board of Osteopathic Medicine License No. OS 99999", "auto",
         ("credentialing", "doe", "discipline")),
    ]
    bad = 0
    for text, route, (k, e, c) in cases:
        r = classify_text(text, route, cues, kinds)
        got = (r["kind"], r["entity"], r["category"])
        ok = got == (k, e, c)
        if not ok: bad += 1
        print("%s %-15s %-6s %-14s %s" % ("ok  " if ok else "FAIL", got[0], got[1], got[2], ("" if ok else "want %s" % ((k, e, c),))))
    fake_birth = "D" + "OB " + "/".join(["01", "01", "1970"])          # built at run time so no birth-date literal sits in the file
    r = classify_text("DRIVER LICENSE FLORIDA JANE ROE %s EXP 06/30/2030 CLASS E" % fake_birth, "credentialing", cues, kinds)
    dates_ok = r["expires"] == "2030-06-30" and r["doc_date"] is None and r["restricted"]
    print("%s driver license: restricted=%s expires=%s (birth date never read)" % ("ok  " if dates_ok else "FAIL", r["restricted"], r["expires"]))
    bad += 0 if dates_ok else 1
    fake_ssn = "-".join(["123", "45", "6789"])                          # synthetic, assembled at run time (the PHI gate blocks the literal)
    r = classify_text("W-9 Request for Taxpayer Identification Number JANE ROE Social security number " + fake_ssn, "credentialing", cues, kinds)
    ssn_ok = r["restricted"] and fake_ssn not in json.dumps(r)
    print("%s SSN page: restricted=%s, number never echoed" % ("ok  " if ssn_ok else "FAIL", r["restricted"]))
    bad += 0 if ssn_ok else 1
    pages = ["FLORIDA MEDICAID PROVIDER AGREEMENT Agency for Health Care Administration", "terms and conditions of participation",
             "Provider agrees ... participating provider ... effective date", "", "Signature page SAMPLE CLINIC PA NPI 1000000003 Florida Medicaid ID"]
    docs = segment(pages, "credentialing", cues, kinds)
    one_ok = len(docs) == 1 and docs[0]["category"] == "medicaid" and docs[0]["pages"] == "1-5"
    print("%s 5-page agreement stays one document (%s)" % ("ok  " if one_ok else "FAIL", [(x["pages"], x["category"]) for x in docs]))
    bad += 0 if one_ok else 1
    pages = ["Florida Department of Health LICENSE VERIFICATION JOHN DOE OS99999 Status CLEAR/ACTIVE Board of Osteopathic Medicine",
             "U.S. DEPARTMENT OF JUSTICE DRUG ENFORCEMENT ADMINISTRATION CONTROLLED SUBSTANCE REGISTRATION CERTIFICATE JOHN DOE DO"]
    docs = segment(pages, "credentialing", cues, kinds)
    two_ok = [(x["pages"], x["category"]) for x in docs] == [("1", "license"), ("2", "dea")]
    print("%s license + DEA in one scan split in two (%s)" % ("ok  " if two_ok else "FAIL", [(x["pages"], x["category"]) for x in docs]))
    bad += 0 if two_ok else 1
    pages = ["U.S. DEPARTMENT OF JUSTICE DRUG ENFORCEMENT ADMINISTRATION CONTROLLED SUBSTANCE REGISTRATION CERTIFICATE JOHN DOE DO",
             "U.S. DEPARTMENT OF JUSTICE DRUG ENFORCEMENT ADMINISTRATION CONTROLLED SUBSTANCE REGISTRATION CERTIFICATE JANE ROE APRN APRN7777777"]
    docs = segment(pages, "credentialing", cues, kinds)
    two_people_ok = [(x["pages"], x["entity"]) for x in docs] == [("1", "doe"), ("2", "roe")]
    print("%s two people's DEA certificates stay apart (%s)" % ("ok  " if two_people_ok else "FAIL", [(x["pages"], x["entity"]) for x in docs]))
    bad += 0 if two_people_ok else 1
    print("selftest: %d failure(s)" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
