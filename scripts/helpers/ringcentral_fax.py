# PLAIN ENGLISH (faxes from RingCentral - William 11/11/2026: "integrate with ring central to receive faxes ... all the faxes for this
#   practice are there and could be downloaded into the database to support the ccm charges"; he chose the RingCentral API route).
# Decides: nothing. Copies the practice's RECEIVED faxes out of RingCentral into the workspace's fax inbox (inbox/faxes/), one PDF per
#   fax, each once. From there a fax is read like any other census input (census_inputs.py - nightly/census_inputs_step.md) and filed.
#   Why it cannot wait: RingCentral does not keep faxes for good - its developer guide (Message Store Exports, read 11/11/2026) says the
#   fax inbox holds the newest 200 messages, and 30 days on an account with its HIPAA setting on. What is not copied out is lost.
# How it signs in (RingCentral's JWT flow, developers.ringcentral.com/guide/authentication/jwt-flow): a private REST API app of the
#   practice's own RingCentral account with the "Read Messages" permission gives a client id, a client secret and a JWT. ONE POST to
#   https://platform.ringcentral.com/restapi/oauth/token (the id and secret as Basic, the JWT as the assertion of a jwt-bearer grant)
#   answers with a token that lasts about two hours. The three values come from the environment (RINGCENTRAL_CLIENT_ID,
#   RINGCENTRAL_CLIENT_SECRET, RINGCENTRAL_JWT) or from secrets/ringcentral.json in the workspace - never from the repository, and none of
#   them, nor the token, is ever printed or written anywhere.
# What it asks: GET /restapi/v1.0/account/~/extension/~/message-store?messageType=Fax&direction=Inbound&dateFrom=<day> page by page (the
#   list without a day answers for the last day only), then each fax's PDF attachment from the address the list gives (media.ringcentral.com).
# Never: changes anything in RingCentral - no delete, no "mark as read", no send; every request but the sign-in is a GET. Never talks to
#   AdvancedMD. A fax carries patient names: the PDFs stay in the workspace and Drive. GitHub gets registers/ringcentral_faxes.json -
#   message id, time received, pages, sha256, size - without a telephone number.
# NOT YET RUN AGAINST THE LIVE ACCOUNT (11/11/2026): written from RingCentral's guide and proven on a stand-in
#   (tools/selftest/test_census_inputs.py). The first real run is --list, which downloads nothing.
# Exit: 0 done, 2 usage, 4 no key, 5 sign-in refused, 6 RingCentral answered an error (its status in the line), 3 the network is closed.
# Usage (workspace = BILLING_WORKSPACE, else /home/claude/unbilled):
#   python3 ringcentral_fax.py --list  [--since YYYY-MM-DD]     what is there: id, time, pages - nothing downloaded
#   python3 ringcentral_fax.py --fetch [--since YYYY-MM-DD]     download every received fax not yet in the register
import os, sys, re, json, time, base64, hashlib, datetime
import urllib.request, urllib.parse, urllib.error
WS = os.environ.get("BILLING_WORKSPACE", "/home/claude/unbilled")
SERVER = "https://platform.ringcentral.com"
TOKEN_URL = SERVER + "/restapi/oauth/token"
LIST_URL = SERVER + "/restapi/v1.0/account/~/extension/~/message-store"
REGF = os.path.join("registers", "ringcentral_faxes.json"); INBOX = os.path.join("inbox", "faxes")
KEEP_DAYS = 30      # how far back the first run looks: what RingCentral itself keeps on an account with its HIPAA setting on
PAUSE = 1.6         # seconds between downloads (RingCentral limits requests per minute)

def _http(method, url, headers=None, body=None):
    """one request -> (status, headers, body bytes); the self-test gives a stand-in for this"""
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=120) as r: return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e: return e.code, dict(e.headers or {}), e.read()
def keys():
    """(client id, client secret, JWT) from the environment, else from secrets/ringcentral.json in the workspace; None when one is missing"""
    env = [os.environ.get(k, "").strip() for k in ("RINGCENTRAL_CLIENT_ID", "RINGCENTRAL_CLIENT_SECRET", "RINGCENTRAL_JWT")]
    if all(env): return tuple(env)
    try: j = json.load(open(os.path.join(WS, "secrets", "ringcentral.json")))
    except Exception: return None
    got = [str(j.get(k) or "").strip() for k in ("client_id", "client_secret", "jwt")]
    return tuple(got) if all(got) else None
def _get(http, sleep, url, token):
    """a GET with the token; a 'too many requests' answer is waited out, three times at most"""
    for _try in range(4):
        st, hd, body = http("GET", url, {"Authorization": "Bearer " + token, "Accept": "application/json, application/pdf"}, None)
        if st != 429: return st, hd, body
        sleep(min(120, int(re.sub(r"\D", "", str(hd.get("Retry-After") or "")) or 60)))
    return st, hd, body
def main(argv, http=None, sleep=None):
    global WS
    WS = os.environ.get("BILLING_WORKSPACE", "/home/claude/unbilled")      # read at every start, not when the file is loaded
    http = http or _http; sleep = sleep or time.sleep
    if not ({"--list", "--fetch"} & set(argv)): print("usage: ringcentral_fax.py --list | --fetch [--since YYYY-MM-DD]"); return 2
    since = argv[argv.index("--since") + 1] if "--since" in argv and argv.index("--since") + 1 < len(argv) else (datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since): print("ringcentral: --since must be a day written YYYY-MM-DD"); return 2
    k = keys()
    if not k:
        print("ringcentral: no RingCentral key here (RINGCENTRAL_CLIENT_ID / RINGCENTRAL_CLIENT_SECRET / RINGCENTRAL_JWT, or secrets/ringcentral.json in the workspace) - no fax fetched; the other census inputs go on")
        return 4
    try:
        st, hd, body = http("POST", TOKEN_URL, {"Authorization": "Basic " + base64.b64encode(("%s:%s" % (k[0], k[1])).encode()).decode(), "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                            urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": k[2]}).encode())
    except Exception as e:
        print("ringcentral: the network did not let the sign-in through (%s) - platform.ringcentral.com and media.ringcentral.com must be allowed for this environment" % type(e).__name__); return 3
    try: ans = json.loads(body.decode("utf-8", "replace"))
    except Exception: ans = {}
    token = ans.get("access_token") if st == 200 else None
    if not token:
        print("ringcentral: sign-in refused (HTTP %s %s) - the app's id, secret or JWT is not accepted; no fax fetched" % (st, re.sub(r"[^A-Za-z0-9_\-]", "", str(ans.get("error") or ans.get("errorCode") or ""))[:40])); return 5
    faxes = []; page = 1
    while True:
        q = urllib.parse.urlencode({"messageType": "Fax", "direction": "Inbound", "dateFrom": since, "perPage": 100, "page": page})
        st, hd, body = _get(http, sleep, LIST_URL + "?" + q, token)
        if st != 200: print("ringcentral: the list of received faxes answered HTTP %s - stopped, nothing more fetched this run" % st); return 6
        j = json.loads(body.decode("utf-8", "replace"))
        faxes += [r for r in j.get("records") or [] if isinstance(r, dict) and r.get("id") is not None]
        if not (j.get("navigation") or {}).get("nextPage") or page >= 50: break
        page += 1
    faxes.sort(key=lambda r: str(r.get("creationTime") or ""))
    if "--list" in argv:
        for r in faxes: print("fax %s received %s pages %s" % (r["id"], r.get("creationTime") or "?", r.get("faxPageCount") if r.get("faxPageCount") is not None else "?"))
        print("ringcentral: %d received fax(es) since %s - nothing downloaded (--list)" % (len(faxes), since)); return 0
    regp = os.path.join(WS, REGF)
    try: reg = json.load(open(regp))
    except Exception: reg = {}
    if not isinstance(reg.get("faxes"), dict): reg = {"schema": "ringcentral-faxes/1", "faxes": {}}
    os.makedirs(os.path.join(WS, INBOX), exist_ok=True); os.makedirs(os.path.join(WS, "registers"), exist_ok=True); new = 0; failed = 0
    for r in faxes:
        mid = str(r["id"])
        if mid in reg["faxes"]: continue
        att = next((a for a in r.get("attachments") or [] if isinstance(a, dict) and a.get("uri") and "pdf" in str(a.get("contentType") or "").lower()), None)
        if not att: failed += 1; continue
        if new: sleep(PAUSE)
        st, hd, body = _get(http, sleep, att["uri"], token)
        if st != 200 or not body: failed += 1; continue
        t = re.sub(r"\D", "", str(r.get("creationTime") or ""))[:12]
        name = "%s_%s_%s.pdf" % (t[:8] or "00000000", t[8:12] or "0000", re.sub(r"\D", "", mid))
        open(os.path.join(WS, INBOX, name), "wb").write(body)
        reg["faxes"][mid] = {"received": r.get("creationTime"), "pages": r.get("faxPageCount"), "sha256": hashlib.sha256(body).hexdigest(), "size": len(body), "file": name}
        json.dump(reg, open(regp, "w"), indent=1, sort_keys=True); new += 1      # after EVERY fax: a run that is cut off keeps what it has
    print("ringcentral: %d new fax(es) saved to %s (%d received since %s, %d already here%s)" % (new, INBOX, len(faxes), since, len(faxes) - new - failed,
          (", %d could not be downloaded - tried again next run" % failed) if failed else ""))
    return 0
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
