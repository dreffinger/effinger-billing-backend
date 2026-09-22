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
    if os.path.exists(CRED):
        return json.load(open(CRED)).get("psw")
    return None

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

def rebill_charge(chargeid, sequencenumber, dod_guard=True):
    """REST rebill — the dialog's Submit. HTTP 204 = success.
    DECEASED GUARD (William [DOB]): refuses (HTTP-style 409, nothing sent) when the date of service is after the
    patient's date of death - see core/deceased_guard.py. dod_guard=False only for an explicit, logged override."""
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
# RESTORE RECIPE (9/10/2026 nightly): the workspace amd.py = repo core/amd.py (GitHub main) with this
# block APPENDED. It reconciles the two helper generations (repo scripts use amd.post/amd.msg; the
# 9/8-9/9 mirror scripts amdw/precheck use amd.call/amd.rest_post). Also patch precheck.py:
#   1) CARIDS = {v[0]: k for k, v in json.load(open(...'carriers.json')).items()}   # rich carN->[code,name] format
#   2) its AMD eligibility call -> amd.check_eligibility_xml(...)                    # raw 271 text
# carriers.json in the workspace = the RICH practices/ehpa/carriers.json from the repo.

# --- compat shims for the 9/8-9/10 mirror-generation helpers (amdw, precheck, wo_reversal_post) ---
def esc(s):
    return str(s or '').replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;')

def call(attrs, children=''):
    """Mirror-style call: attrs string + children; token injected by post()."""
    t = post('<ppmdmsg %s msgtime="%s">%s</ppmdmsg>' % (attrs, _msgtime(), children))
    time.sleep(0.3)
    return t

def wfe_call(attrs, children=''):
    """Collections-module calls on the pm-wfe gateway. Same token."""
    web, tok = login_cached()
    body = _inject('<ppmdmsg %s msgtime="%s">%s</ppmdmsg>' % (attrs, _msgtime(), children), tok)
    r = requests.post('https://pm-wfe-103.advancedmd.com/practicemanager/xmlrpc/processrequest.aspx',
                      data=body, headers={'Content-Type': 'text/xml'}, cookies={'token': tok}, timeout=90)
    time.sleep(0.3)
    return r.text

def rest_get(path, accept='application/json'):
    web, tok = login_cached()
    r = requests.get('https://pm-api-103.advancedmd.com' + path,
                     headers={'Accept': accept, 'Authorization': 'Bearer ' + tok}, timeout=60)
    time.sleep(0.3)
    return r.text

def rest_post(path, payload, accept='application/json'):
    web, tok = login_cached()
    r = requests.post('https://pm-api-103.advancedmd.com' + path, json=payload,
                      headers={'Accept': accept, 'Authorization': 'Bearer ' + tok}, timeout=90)
    time.sleep(0.3)
    return r.status_code, r.text

def check_eligibility_xml(insplan_id, stc="30", timeout=120):
    """Raw-text variant of check_eligibility (the mirror precheck expects XML text)."""
    web, tok = login_cached()
    body = {"licensekey": "152563", "username": "POI0712",
            "patientinsurancecoverageid": str(insplan_id).replace("ins", ""), "servicetypecode": stc}
    r = requests.post("https://pm-api-103.advancedmd.com/api/eligibility/EligibilityDetailsLegacy/checkEligibility",
                      headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json",
                               "Accept": "application/xml",
                               "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"},
                      json=body, timeout=timeout)
    time.sleep(0.4)
    return r.text
