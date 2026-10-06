# PLAIN ENGLISH (AdvancedMD client)
# Decides: Nothing about billing. It logs in to AMD once, keeps the token in .session.json, and sends every XML message the other scripts build.
# Rules it uses: ONE login attempt per lock cycle - a second failed login locks the POI0712 user and kills the Claimocity feed. If the token expires mid-run it re-logs once and retries the message.
# Never touches: Patient data. It has no idea what a charge is; it only carries messages.
# ---
"""AdvancedMD API client — rebuilt 8/30/2026 from advancedmd-api-reference skill.
ONE login attempt rule: never retry a failed login (locks POI0712, kills Claimocity feed).
"""
import time, requests, datetime, re, json, os, sys, time
import xml.etree.ElementTree as ET

OFFICE = "152563"
USER = "POI0712"
ENTRY = "https://partnerlogin.advancedmd.com/practicemanager/xmlrpc/processrequest.aspx"
CACHE = "/home/claude/unbilled/.session.json"

def _msgtime():
    now = datetime.datetime.now()
    return now.strftime("%m/%d/%Y %I:%M:%S %p").lstrip("0")

def _login_xml(psw):
    return ('<ppmdmsg action="login" class="login" msgtime="%s" username="%s" psw="%s" officecode="%s" appname="TEMP"/>'
            % (_msgtime(), USER, psw, OFFICE))

def login(psw):
    """Two-step login. Returns (webserver_url, token). ONE ATTEMPT ONLY."""
    r1 = requests.post(ENTRY, data=_login_xml(psw), headers={"Content-Type": "text/xml"}, timeout=60)
    m = re.search(r'webserver="([^"]+)"', r1.text)
    if not m:
        raise RuntimeError("LOGIN STEP1 FAILED (no webserver redirect) — DO NOT RETRY:\n" + r1.text[:2000])
    web = m.group(1).rstrip("/")
    url = web + "/xmlrpc/processrequest.aspx"
    r2 = requests.post(url, data=_login_xml(psw), headers={"Content-Type": "text/xml"}, timeout=60)
    if 'success="1"' not in r2.text:
        raise RuntimeError("LOGIN STEP2 FAILED — DO NOT RETRY:\n" + r2.text[:2000])
    t = re.search(r"<usercontext[^>]*>([^<]+)</usercontext>", r2.text)
    if not t:
        raise RuntimeError("LOGIN ok but no token found:\n" + r2.text[:2000])
    tok = t.group(1).strip()
    json.dump({"web": web, "token": tok, "ts": time.time()}, open(CACHE, "w"))
    return web, tok

CRED = "/home/claude/unbilled/.amd_cred.json"
LOCK = "/home/claude/unbilled/.amd_login_lock"   # tripped after a failed login; blocks all retries

def _stored_psw():
    """The POI0712 password: the credential file first, else the AMD_PSW environment credential (9/30/2026)."""
    if os.path.exists(CRED):
        return json.load(open(CRED)).get("psw")
    return os.environ.get("AMD_PSW") or None

def relogin():
    """Get a fresh token using the stored password. ONE ATTEMPT, EVER, per lock cycle.
    On any failure this writes a lock file and refuses to try again until a human
    removes it (rm .amd_login_lock) -- protects POI0712 from lockout (Gregg's feed)."""
    if os.path.exists(LOCK):
        raise RuntimeError("AMD login LOCKED (prior attempt failed). A human must verify the "
                           "password and remove .amd_login_lock before any retry. NOT retrying.")
    psw = _stored_psw()
    if not psw:
        raise RuntimeError("no stored AMD password; cannot relogin")
    # trip the lock BEFORE attempting, so a crash mid-attempt still blocks the next run
    open(LOCK, "w").write("attempt in progress %s\n" % _msgtime())
    web, tok = login(psw)          # raises on failure -> lock stays, no second try
    os.remove(LOCK)                # success: clear the lock
    return web, tok

def login_cached(psw=None):
    if os.path.exists(CACHE):
        c = json.load(open(CACHE))
        return c["web"], c["token"]
    if psw is not None:
        return login(psw)
    return relogin()

def _inject(body_xml, tok):
    if "<usercontext" in body_xml:
        return body_xml
    uc = '<usercontext>%s</usercontext>' % tok
    if body_xml.rstrip().endswith("/>"):
        i = body_xml.rstrip().rfind("/>")
        return body_xml.rstrip()[:i] + ">" + uc + "</ppmdmsg>"
    i = body_xml.index(">") + 1
    return body_xml[:i] + uc + body_xml[i:]

def _expired(text):
    """Only a genuine auth failure counts. 'Action X not found' faults must NEVER trigger a relogin
    (9/2/2026: a probe fault tripped this, dropped a valid token and hit AMD's 429 login limit)."""
    t = text.lower()
    if "not found" in t and "action" in t:
        return False
    return ("session has expired" in t or "session expired" in t or "invalid session" in t
            or "not logged in" in t or "invalid usercontext" in t or "usercontext is invalid" in t
            or "user context attached to your request is invalid" in t)

def post(body_xml, timeout=180, _retried=False):
    """POST a ppmdmsg; injects <usercontext> token. If the token is expired, relogin
    ONCE (via the one-attempt-locked relogin) and resend. Never more than one relogin."""
    web, tok = login_cached()
    url = web + "/xmlrpc/processrequest.aspx"
    body = _inject(body_xml, tok)
    for _attempt in range(4):   # transient SSL/connection errors: retry with backoff (added 9/4/2026)
        try:
            r = requests.post(url, data=body, headers={"Content-Type": "text/xml"},
                              cookies={"token": tok}, timeout=timeout)
            break
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if _attempt == 3: raise
            time.sleep(3 * (_attempt + 1))
    if not _retried and _expired(r.text):
        # token stale: drop cache and relogin exactly once (relogin itself is one-attempt-safe)
        try:
            if os.path.exists(CACHE):
                os.remove(CACHE)
        except OSError:
            pass
        relogin()
        return post(body_xml, timeout=timeout, _retried=True)
    return r.text

def msg(action, cls, attrs=None, children=""):
    a = ' '.join('%s="%s"' % (k, v) for k, v in (attrs or {}).items())
    return '<ppmdmsg action="%s" class="%s" msgtime="%s" %s>%s</ppmdmsg>' % (
        action, cls, _msgtime(), a, children)

# ONE REBILL PER VISIT (William 10/6/2026: "make this fix to the routine permanent so it doesn't delay billing").
# chargerebill rebills the WHOLE claim (rebillentireclaim=True), so the guard is per VISIT + plan sequence, and per script run
# (this process): a second rebill of a visit this run already rebilled successfully is NOT sent - it answers 204 with text
# "SKIPPED ..." (the claim IS queued, so callers that test for 204 keep working). That stops the move_to_ins.move(cid, seq) +
# freq1_visit.run double (act_1710_1005, 10/5) and per-charge loops over one visit, and it can never block a LATER run's
# corrected rebill (after a claim-run rejection is fixed). allow_repeat=True forces a second one. Every 2xx rebill is appended to
# registers/rebill_log.jsonl - an audit trail only, it never blocks. Fails open: an unreadable visit falls back to the charge id.
WS_DIR = os.environ.get("BILLING_WORKSPACE", "/home/claude/unbilled")
REBILL_LOG = os.path.join(WS_DIR, "registers", "rebill_log.jsonl")
_REBILLED = {}

def _visit_of(chargeid):
    try:
        x = post(msg("getchargedetaildataicd10", "demographics", {"chargeid": re.sub(r"\D", "", str(chargeid)), "nocookie": "1"}))
        m = re.search(r'<visit\s(?:[^>]*?\s)?id="(?:vst)?(\d+)"', x)
        return m.group(1) if m else None
    except Exception:
        return None

def _rebill_log(entry):
    try:
        os.makedirs(os.path.dirname(REBILL_LOG), exist_ok=True)
        with open(REBILL_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def rebill_charge(chargeid, sequencenumber, dod_guard=True, allow_repeat=False, visitid=None):
    """REST rebill — the dialog's Submit. HTTP 204 = success.
    ONE REBILL PER VISIT (William 10/6/2026): a second rebill of the same VISIT + sequence in this script run is not sent - it
    answers 204 "SKIPPED ..." (see the note above); pass visitid= when the caller knows it (saves a read); allow_repeat=True forces it.
    DECEASED GUARD (William 9/22/2026): refuses (HTTP-style 409, nothing sent) when the date of service is after the
    patient's date of death - see core/deceased_guard.py. dod_guard=False only for an explicit, logged override."""
    cidn = re.sub(r"\D", "", str(chargeid))
    vid = re.sub(r"\D", "", str(visitid)) if visitid else _visit_of(cidn)
    key = ("v%s" % vid if vid else "c%s" % cidn) + ":%s" % int(sequencenumber)
    if key in _REBILLED and not allow_repeat:
        e = _REBILLED[key]
        return 204, ("SKIPPED - visit %s already rebilled to seq %s in this run at %s (charge %s, HTTP %s); one rebill per visit - "
                     "nothing sent (allow_repeat=True forces a second)" % (vid or "?", sequencenumber, e["at"], e["charge"], e["status"]))
    if dod_guard:
        try:
            import deceased_guard
            blocked, why = deceased_guard.check_charge(chargeid, sequencenumber)
            if blocked: return 409, "BLOCKED by deceased guard: " + why
        except Exception as e:                      # fail CLOSED: an unreadable charge is held, never sent blind
            return 409, f"BLOCKED by deceased guard: could not verify ({str(e)[:100]}) - retry next run"
    web, tok = login_cached()
    host = re.sub(r"providerapi", "pm-api-103", web)  # not reliable; use fixed host
    url = "https://pm-api-103.advancedmd.com/api/claim/chargerebill"
    cid = int(re.sub(r"\D", "", str(chargeid)))  # strip 'charge' prefix -> numeric fid
    r = requests.post(url, json={"licensekey": OFFICE, "username": USER,
                                 "chargedetailfid": cid,
                                 "sequencenumber": int(sequencenumber),
                                 "rebillentireclaim": True, "reason": ""},
                      headers={"Authorization": "Bearer " + tok}, timeout=60)
    if 200 <= r.status_code < 300:
        e = {"at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "visit": vid, "charge": cidn,
             "seq": int(sequencenumber), "status": r.status_code, "by": os.path.basename(sys.argv[0] or "") or "interactive"}
        _REBILLED[key] = e; _rebill_log(e)
    return r.status_code, r.text[:500]

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        psw = sys.stdin.read().strip()
        web, tok = login(psw)
        print("LOGIN OK", web, "token_len", len(tok))

def check_eligibility(insplan_id, stc="30", timeout=120):
    """AMD's own eligibility check (William's capture, re-pasted 9/7/2026): POST
    /api/eligibility/EligibilityDetailsLegacy/checkEligibility with the numeric insplan id.
    Returns (status_code, parsed json or text). The full 271 is in the response; no AAA = active."""
    web, tok = login_cached()
    body = {"licensekey": "152563", "username": "POI0712", "patientinsurancecoverageid": str(insplan_id).replace("ins", ""), "servicetypecode": stc}
    r = requests.post("https://pm-api-103.advancedmd.com/api/eligibility/EligibilityDetailsLegacy/checkEligibility",
                      headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json", "Accept": "application/json",
                               "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"},
                      json=body, timeout=timeout)
    try: return r.status_code, r.json()
    except Exception: return r.status_code, r.text
