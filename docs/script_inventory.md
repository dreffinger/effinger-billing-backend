# Script inventory — what the workspace holds, and what is missing here

## Status

**The Python helper scripts are NOT in this repository.**

The original mirror was assembled in a workspace at `/home/claude/unbilled`
that no longer exists in any reachable environment. This repo was rebuilt from
the surviving documentation (the AMD/billing reference notes) plus the two
browser scripts that were stored alongside them.

What that means:

- Everything under `docs/` is real, recovered documentation — call shapes,
  payloads, and standing rules that were captured from live traffic.
- Everything under `scripts/browser/` is real, recovered code.
- **The Python modules below are named and described but their source is
  gone.** They are listed so the gap is explicit and so a rebuild has a
  specification to work from. Nothing here is a stub or a placeholder
  implementation — no fabricated code was committed.

Rebuilding a module means writing it fresh against `docs/captured_calls.md`
and validating it against a live account. Treat every one as unwritten until
that happens.

---

## Core session / transport

| Module | Responsibility |
|---|---|
| `amd.py` | Session + transport. `login_cached`, the ONE-login-attempt rule, auto-relogin from `.amd_cred.json`, XML `processrequest.aspx` POSTs, REST calls with the bearer token. Also `check_eligibility(insplan_id)` and `rebill_charge(chargeid, insorder_first_digit)`. Everything else imports this. |

## Visit / charge editing

| Module | Responsibility |
|---|---|
| `resave.py` | The void-trap guard. `detail(cid)`, `visit_charges(cid)`, `CHG_FIELDS`. Every resave must be built from `visit_charges`, never from a single-charge detail. |
| `recode.py` | `_save(cid, fn)` — edit a charge's `diagcodes` list and resave. The visit detail's `<diagcode id="dcode..." name="..." code="...">` map; the parsing regex must allow `name=` between `id` and `code`. |
| `void_scan.py` | Post-batch scan for charges voided by an incomplete echo. Run after every resave batch. |
| `restore_charge.py` | `<voided> <surviving>` — restore a wrongly voided charge. Sign-off required. |

## Rebilling

| Module | Responsibility |
|---|---|
| `freq1_visit.py` | `run(vid, cid, seq)` — reset the corrected-claim flag to frequency 1, then rebill. The standard per-visit rebill. |
| `reset_freq_rebill.py` | The whole unpaid list, resumable via `reset_freq_rebill.log`. |
| `fix_freq7_exclusions.py` | Same for the Exclusions column. |
| `rebill_patient_year.py` | `run(pid, order, days)` — one patient, filtered by DOS window. |
| `move_to_ins.py` | `move(cid, seq)` — move a patient balance back to insurance, set insorder, rebill. |
| `co24_restore.py` | `run(pid, seq, first, last)` — the CO24 (Advantage-plan-responsible) path. |

## Insurance

| Module | Responsibility |
|---|---|
| `add_ins.py` | `add(pid, car, num, begindate, finclass)` — `addinsurance`. Never sends a group number. |
| `ins_update.py` | `update(pid, insid, **fields)` — `updateinsurance` with the required `o_<field>` originals. |
| `patient_patch.py` | `family_address(pid, address1, address2, zipcode, city, state)` — the PATCH with the `familyupdate` block. |
| `elig_amd.py` | `<patientid> [--all]` — run eligibility across plans, parse the 271 (status, AAA codes, plan dates, Part A/B, other payers, hospice, date of death, payer address), save raw + summary. |
| `txh.py` | `fetch` — `gettxhistory` wrapper. |

## Payments / ERA

| Module | Responsibility |
|---|---|
| `manual_post.py` | `post(cid, carrier, pay, wo, wocode, checknumber, depositdate, note)` — `addpayments`. |
| `era_manual_post.py` | Manual post against an unvalidated ERA line. |
| `era_post.py` | `post_check` — the ERA Center Post button. |
| `era_clear.py` | `zero_post` — Process Accepted ($0.00). |
| `void_tx.py` | `void_writeoff(pid, cid, woid)` / `void_payment(pid, cid, payid)`. |

## Facesheets / documents

| Module | Responsibility |
|---|---|
| `facesheet_auth.py` | `<pdf>` — OCR a facesheet (`pdftoppm -r 220 -png` then `tesseract`), print payer / policy / auth candidates, flag tracking numbers as non-billable. |

## Reporting / audit

| Module | Responsibility |
|---|---|
| `build_money.py` | Rebuild the money ledger from `massrebillsearch` + the pass logs. |
| `audit_pr_transfer.py` | Sweep all patients' tx history for wrong-payer PR transfers; emit the audit workbook. |

## Browser bridge

| Module | Responsibility |
|---|---|
| `stedi_bridge.js` | Pasted into a Stedi portal tab. `window.elig`, `window.mbi`, `window.disc`, `window.medSumm`, `window.row`, `window.clean`. Needed because the container cannot reach `healthcare.us.stedi.com` (egress 403). **Not recovered** — see `scripts/browser/` for what was. |

## Dated one-off pass scripts

These were written per-pass and used as templates for the next one. All lost.
Names recorded because the reference notes cite them as the working examples:
`inspector_0907.py`, `unbilled_0907.py`, `excl_act_0907.py`,
`aet12_rebill_0907.py`.

---

## Data files (git-ignored by design — never committed)

| Path | Contents |
|---|---|
| `.amd_cred.json` | AMD credentials |
| `.session.json` | Cached session token |
| `secrets/stedi_live.key`, `secrets/stedi_test.key` | Stedi API keys |
| `patient_db/<patientid>/` | Per-patient eligibility raw + summaries — PHI |
| `chat_history/` | Session digests — PHI |
| `needs_facesheet_list.md` | Blocked claims + the insurance refresh list — PHI |
| `laterality_flag_log.md` | Laterality corrections log |
| `carriers.json`, `facilities.json` | Reference maps built by probing |
| `Writeoff_register_<date>.xlsx` | Per-pass write-off registers |

`carriers.json` and `facilities.json` hold no PHI and could reasonably be
committed; the carrier ids they contain are reproduced in the appendix of
`docs/captured_calls.md`. `facilities.json` is rebuildable from
`selectfacilities`.
