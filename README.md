# effinger-billing-backend

Backend automation for the practice's AdvancedMD billing work — clearing the
Claims Center columns, chasing unpaid claims, and finding correct current
insurance, all through captured APIs instead of the browser UI.

> **Private repository. Read the [Data handling](#data-handling) section before
> committing anything.**

---

## What this is

AdvancedMD exposes no official API for most of this work. Every call in
`docs/captured_calls.md` was learned by capturing the UI's own network traffic,
by importing a Postman collection, or by probing. The documentation *is* the
product here: it is what makes the automation reproducible.

Two transports, one session token:

- **XML / ppmdmsg** — `POST .../practicemanager/xmlrpc/processrequest.aspx`
- **REST** — `https://pm-api-103.advancedmd.com/api/...` with a bearer token

Insurance verification runs against Stedi, since AMD's own eligibility module
has been unreliable.

---

## Repository state

**This repo currently contains documentation and browser scripts. The Python
helper modules are not here.**

The original workspace was lost with the container it lived in. This repo was
rebuilt from surviving reference notes. Rather than commit invented code,
`docs/script_inventory.md` records every module by name and responsibility so
a rebuild has a specification. **No stub or placeholder implementations were
committed** — a module listed there should be treated as unwritten until it is
written fresh against `docs/captured_calls.md` and validated on a live
account.

---

## Layout

```
docs/
  captured_calls.md            The registry — every captured AMD/Stedi call
  billing_rules.md             Standing practice rules that govern every pass
  workflows.md                 Claims Center pass, run alerts, lookup cascade,
                               facesheets, reporting, open items
  script_inventory.md          What the workspace held; what is missing here
  postman_effinger_amd.json    Postman v2.1 collection of the REST calls
scripts/browser/
  amdx-inject.js               AMD popup->tab shim + page macros
  advancedmd-tabs-and-macros.user.js
                               The same, packaged as a userscript
```

---

## Start here

1. **`docs/captured_calls.md`** — the call registry. Nothing gets called that
   is not in it. If a shape is not recorded, capture it; do not guess.
2. **`docs/billing_rules.md`** — the practice's standing decisions. These
   override generic coding instinct, and several exist because of a specific
   past mistake.
3. **`docs/workflows.md`** — how a pass actually runs.

### Three rules worth reading before writing any code

- **The void trap.** Any visit resave *replaces* the visit's charge list —
  every charge you omit is voided. Build resaves from a full visit fetch,
  never from a single-charge detail. This cost 30 charges once.
- **Modifier ids are not modifier codes.** Modifier 25 is `mcode7`. Writing
  `modcodes="25"` silently applies modifier 78.
- **Board counts lag.** `getclaimcenteroverview` is cached. The list calls are
  the truth.

---

## Postman collection

`docs/postman_effinger_amd.json` mirrors the REST calls so they can be run by
hand when the automation is unavailable. Import it and fill the collection
variables — `token`, `licensekey`, `username`, `stediKey` are intentionally
**empty in source control** and must be filled at run time.

Regenerate it whenever the registry changes.

---

## Data handling

This repository holds **code and call documentation only.**

Never commit:

- `.session.json`, `.amd_cred.json`, `secrets/`, any `*.key`
- `patient_db/`, `chat_history/`, facesheets, or any file containing patient
  names, member ids, MBIs, dates of birth, SSNs, diagnoses, or authorization
  numbers
- `*.log`, exported registers, or `*.json` data files

`.gitignore` covers all of these. It excludes `*.json` wholesale and
re-includes only `docs/postman_effinger_amd.json`.

The documentation in `docs/` was deliberately written with **no patient
identifiers** — call shapes, payer-level reference data, and rules are
described generically. Keep it that way. When a rule needs an example, describe
the pattern rather than naming the patient.

Bearer tokens, license keys, and usernames appear only as placeholders.

Real dates of service, patient names, and auth numbers belong in the
git-ignored working files, never in a commit.
