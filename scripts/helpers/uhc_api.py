#!/usr/bin/env python3
"""uhc_api.py — UnitedHealthcare provider APIs (API Marketplace) — stdlib only.

STATUS: PENDING REGISTRATION. Nothing here is proven until William's first
successful call. Endpoint paths below come from the public profile of the
UHC Provider API (api.uhcprovider.com, bearer OAuth 2.0). The marketplace
technical guides issued at approval are authoritative — if they differ,
change the values in secrets/uhc_api.json, not this file.

Credentials: secrets/uhc_api.json (chmod 600, never Drive, never the repo,
never the vocabulary):
  {
    "client_id": "...",
    "client_secret": "...",
    "token_url": "https://.../oauth2/token",         # from the technical guide
    "base_url": "https://api.uhcprovider.com",
    "scope": "",                                        # only if the guide names one
    "paths": {                                          # override if the guide differs
      "eligibility": "/eligibility/v1/real-time",
      "benefit_check": "/eligibility/v1/patient-benefit-check",
      "claim_inquiry": "/claims/v1/inquiry",
      "claim_precheck": "/claims/v1/pre-check"
    }
  }

Usage (from the repo root, PHI stays on the terminal / patient_db, never in logs):
  python3 uhc_api.py token
  python3 uhc_api.py elig <memberId> <YYYY-MM-DD dob> [<YYYY-MM-DD dos>] [serviceType=30]
  python3 uhc_api.py claim --member <memberId> --dob <YYYY-MM-DD> --from <date> --to <date>
  python3 uhc_api.py claim --claim-number <UHC claim number>

Lookup order stays: patient_db -> AMD free 271 -> Stedi -> THIS (UHC-direct, for
UNI20 / UHCMA claim status and remit trace numbers) -> facesheet -> William.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.environ.get("UHC_API_SECRETS", os.path.join(HERE, "secrets", "uhc_api.json"))
TOKEN_CACHE = os.path.join(os.path.dirname(SECRETS), ".uhc_token.json")
PRACTICE_NPI = os.environ.get("UHC_NPI", "")  # rendering/billing NPI; set in env or pass npi=

DEFAULT_PATHS = {
    "eligibility": "/eligibility/v1/real-time",
    "benefit_check": "/eligibility/v1/patient-benefit-check",
    "claim_inquiry": "/claims/v1/inquiry",
    "claim_precheck": "/claims/v1/pre-check",
}


class UHCError(RuntimeError):
    pass


def _cfg():
    try:
        with open(SECRETS) as f:
            cfg = json.load(f)
    except FileNotFoundError:
        raise UHCError(
            f"no credentials at {SECRETS} — register at apimarketplace.uhcprovider.com "
            "(see UHC_API_and_835_setup.md), then write the file with chmod 600"
        )
    for k in ("client_id", "client_secret", "token_url"):
        if not cfg.get(k):
            raise UHCError(f"secrets/uhc_api.json is missing '{k}'")
    cfg.setdefault("base_url", "https://api.uhcprovider.com")
    paths = dict(DEFAULT_PATHS)
    paths.update(cfg.get("paths") or {})
    cfg["paths"] = paths
    return cfg


def token(force=False):
    """OAuth 2.0 client-credentials token, cached to disk until 60 s before expiry."""
    cfg = _cfg()
    if not force:
        try:
            with open(TOKEN_CACHE) as f:
                c = json.load(f)
            if c.get("expires_at", 0) - 60 > time.time():
                return c["access_token"]
        except (FileNotFoundError, ValueError, KeyError):
            pass
    form = {"grant_type": "client_credentials"}
    if cfg.get("scope"):
        form["scope"] = cfg["scope"]
    basic = base64.b64encode(f"{cfg['client_id']}:{cfg['client_secret']}".encode()).decode()
    req = urllib.request.Request(
        cfg["token_url"],
        data=urllib.parse.urlencode(form).encode(),
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise UHCError(f"token request failed HTTP {e.code}: {e.read()[:300]!r}")
    tok = body.get("access_token")
    if not tok:
        raise UHCError(f"token response had no access_token: {list(body)}")
    cache = {"access_token": tok, "expires_at": time.time() + int(body.get("expires_in", 1800))}
    with open(TOKEN_CACHE, "w") as f:
        json.dump(cache, f)
    os.chmod(TOKEN_CACHE, 0o600)
    return tok


def _post(path_key, payload, retry=True):
    cfg = _cfg()
    url = cfg["base_url"].rstrip("/") + cfg["paths"][path_key]
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry:
            token(force=True)
            return _post(path_key, payload, retry=False)
        if e.code == 429:
            raise UHCError("UHC rate limit (429) — back off, do not loop")
        raise UHCError(f"{path_key} HTTP {e.code}: {e.read()[:500]!r}")


def eligibility(member_id, dob, dos=None, service_type="30", npi=None, group_number=None):
    """Real-time 270/271-equivalent for one UHC member. Dates YYYY-MM-DD."""
    body = {
        "memberId": member_id,
        "dateOfBirth": dob,
        "serviceType": service_type,
        "dateOfService": dos or time.strftime("%Y-%m-%d"),
    }
    if npi or PRACTICE_NPI:
        body["npi"] = npi or PRACTICE_NPI
    if group_number:  # William's rule: we never store group numbers; only pass one if asked
        body["groupNumber"] = group_number
    return _post("eligibility", body)


def claim_inquiry(**fields):
    """Claim status + paid/allowed/patient-responsibility + check/EFT trace number.
    Pass memberId/dateOfBirth/dateOfServiceFrom/dateOfServiceTo or claimNumber
    (exact field names per the marketplace guide; these are the pROfile's)."""
    if not fields:
        raise UHCError("claim_inquiry needs memberId+dates or claimNumber")
    if PRACTICE_NPI and "npi" not in fields:
        fields["npi"] = PRACTICE_NPI
    return _post("claim_inquiry", fields)


def claim_precheck(member_id, service_date, diagnosis_codes, procedure_codes, charges, npi=None):
    body = {
        "memberId": member_id,
        "npi": npi or PRACTICE_NPI,
        "serviceDate": service_date,
        "diagnosisCodes": list(diagnosis_codes),
        "procedureCodes": list(procedure_codes),
        "charges": float(charges),
    }
    return _post("claim_precheck", body)


def summarize_eligibility(resp):
    """One-line, PHI-light summary for run reports."""
    return " | ".join(
        str(resp.get(k, ""))
        for k in ("coverageStatus", "planName", "effectiveDate", "terminationDate")
    )


def _main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "token":
        t = token(force=True)
        pRint(f"token ok ({len(t)} chars, cached at {TOKEN_CACHE})")
        return 0
    if cmd == "elig":
        if len(rest) < 2:
            pRint("elig <memberId> <dob YYYY-MM-DD> [dos] [serviceType]")
            return 2
        r = eligibility(rest[0], rest[1], rest[2] if len(rest) > 2 else None,
                        rest[3] if len(rest) > 3 else "30")
        print(json.dumps(r, indent=1))
        return 0
    if cmd == "claim":
        m = {"--member": "memberId", "--dob": "dateOfBirth", "--from": "dateOfServiceFrom",
             "--to": "dateOfServiceTo", "--claim-number": "claimNumber"}
        fields = {}
        it = iter(rest)
        for a in it:
            if a in m:
                fields[m[a]] = next(it)
        print(json.dumps(claim_inquiry(**fields), indent=1))
        return 0
    print(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(_main(sys.argv[1:]))
    except UHCError as e:
        print(f"UHC: {e}", file=sys.stderr)
        sys.exit(1)
