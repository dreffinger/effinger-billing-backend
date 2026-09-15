---
name: billing-run-alerts-task
description: "New billing step: process AMD run alerts into actions/triggers — getclaimrunstatus taxonomy, the $199K aged-run backlog watch, EDI-reports unlock plan, and the ERA-posting frontier."
---

# Processing Run Alerts (added 9/1/2026)

## The call
`action="getclaimrunstatus" class="claimsreports" nocookie="1"` → alert-type definitions + every flagged claim run (id, date, submitter MCKGRP, totalamount, totalsent, totalexclusions, totaldroppedtopaper, exclusionreportid, alert flags). Read it EVERY run.

## Alert taxonomy → standing actions
- **1 — No clearinghouse report in 4+ days**: EDI pipeline may be down. Same-day: check with AMD support/clearinghouse.
- **2/3/6 — No insurance payment in 45+ days (run / carrier-in-run / carrier)**: identify the silent carrier; if its ERA route is known-broken (United) it's backlog — watch; if the route works, chase the payer. **Baseline 9/1/2026: 21 runs 6/12–7/17, ~$199K / 1,084 claims, all flagged — this is the recovery scoreboard; report the weekly delta as United ERA fix + VA/Tricare portals land.**
- **4 — ≥5% claims excluded**: same-day pull of that run's exclusion rows; classify: duplicates → complete (William's rule), data errors → fix+rebill, systematic payer-id/enrollment → escalate. (8/29/2026 run's 91/160 exclusions = the hospitalization start/end date error wave — since fixed and the date fix is now automated.)
- **Reading a rebill's verdict — timing rule:** a freq-1 rebill does NOT transmit on the claim run created at rebill time; it goes out on the next NIGHTLY claim run (the ~21:07 ET run), so its clearinghouse verdict is read on the FIRST 21:07 run whose `date` is after the rebill, not before. Do not declare a rebill fixed because an empty/earlier run shows no exclusion — wait for that nightly run. Proven 9/15: the 59 AET12 claims rebilled 9/14 04:20 UTC showed a clean earlier run but bounced again (PREF0288 + PREF0264) on nightly run 1700192 (9/14 21:07 ET) — verdict: not fixed.
- **5 — ≥7% dropped to paper**: payer electronic-routing/enrollment gap → feeds the credentialing project.

## EDI Reports column — NOT YET UNLOCKED (high value)
The claims center's last column holds Change Healthcare reports (999/277/payer EOB reports). No API action name found by probing (classes: claimsreports, claimstatus exist; every get*report guess failed; exclusionreportid/droppedtopaperreportid resolve nowhere yet). **Unlock plan: when William opens AMD's claims center in Chrome, click the EDI Reports column while capturing read_network_requests — record the real xmlrpc action here.** Why it matters: payer reports carry PAYER CLAIM NUMBERS (ICNs) — which would unlock the WPS tricare4u admin registration and myVACCN Instant Access without waiting for paper EOBs/mailed codes, plus denial detail for the run-alert exclusions.

## Completing ERA posting — next frontier (William 9/1/2026)
Many ERAs fail AMD's auto-posting tool and sit stuck needing MANUAL number adjustments before they post; William hasn't had a method for them. Build plan: (1) parse the nightly "Automation Center notification for ERA" emails from noreply@advancedmd.com — they list per-payment-code rule results incl. failures; (2) have William walk through 2–3 manual adjustments to learn the pattern; (3) find the ERA-module API calls (probe off-peak, or capture from Chrome) and automate adjust+post. Track stuck-ERA count as a daily metric once readable.

## Where this lives
Step 8–10 of the Daily Run Playbook + "Run Alerts Processing" tab in Billing_Agent_Project_Master.xlsx (Drive: billing agent project files).