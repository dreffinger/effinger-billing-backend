# 2026-09-20 — empty-container bootstrap session (Claude Code on the web)

This session was a nightly-cascade invocation that landed in a fresh
container with no `/home/claude/unbilled` workspace. Followed the
9/20 WORKSPACE BOOTSTRAP note: rebuilt the flat workspace from this repo
(`core/`, `billing/*/`, `eligibility/`, `credentialing/`, `boards/`,
`scripts/helpers/`) and fetched the Stedi key from Gmail thread
`1a083035f566f9fb` ("stedi claude key", 9/8/2026) — looked current, stored
to `secrets/stedi_live.key`.

## Finding: the AMD password pointer is stale — did not attempt login

The bootstrap instructions point to Gmail thread `1866ce7e2233e4c0`
("Effinger Claimocity Double check") as where the AMD password for
POI0712 lives. That thread is a one-off support exchange with Gregg
Hendrickson from **February 2023** — a password reset after a lockout,
three-plus years old, with no indication it's still current or that
anyone has kept that thread updated since.

`amd.py`'s own header is explicit: **one login attempt only, ever, per
lock cycle** — a failed attempt trips `.amd_login_lock` and requires a
human to verify the password and remove the lock before any retry, and a
lockout kills the Claimocity feed. Attempting a live production login
with a password last confirmed valid in 2023 is a bad bet against an
unrecoverable-without-human-intervention failure mode, so this session
did not call `amd.relogin()` / `amd.login_cached()` and did not write
`.amd_cred.json`.

**Recommendation:** point credential bootstrap at a thread (or a
password manager entry) that's actually maintained as the current
POI0712 password, or confirm out-of-band that `6mXLMeV3w3uY` is still
correct before any future empty-container run relies on it.

## What did/didn't run tonight

- Credentialing check (`cred_check.py`) ran clean: 0 NPPES changes, no
  revalidation news, no reminders due. OIG LEIE fetch failed (network
  policy blocked `oig.hhs.gov` from this session) — not urgent per the
  script's own "monthly is enough" cadence, but worth a retry from a
  session with LEIE reachable.
- The insurance-cascade / claim-status / ERA steps (STEP 1–3b, 5) were
  **not run from this session** — they need an authenticated AMD
  session. Checked `git log` on `main`: the 2-hourly cascade already
  completed a full run at `2026-09-20T0510Z` (~1:10am ET, right around
  this routine's normal 1:30am slot) with real work done (BCBS
  secondaries rebilled, prior-payor rows released, write-offs, hospice
  GV rebills, ERA posted) — so tonight's billing work was not actually
  missed, just not duplicated here.
