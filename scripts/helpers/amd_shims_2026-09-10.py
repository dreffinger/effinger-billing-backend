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
