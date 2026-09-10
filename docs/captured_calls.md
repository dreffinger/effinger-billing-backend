> NOTE (9/9/2026): This is the current registry. GitHub `main` is now the toolkit-of-record; see the final two sections for the auto-bootstrap procedure (github_sync.py pull at run start, push at run end). Drive remains the mirror.

# Captured AMD / Stedi calls — the registry (read this before guessing at any endpoint)

Rule (William, 9/7/2026): every call learned from a DevTools paste or by probing is written here the same night, with the shape that worked, the helper that wraps it, and the date. If it isn't in this file it hasn't been captured — ask William for the paste rather than guessing. Never store a bearer token or a password here.

Hosts: XML gateway `https://providerapi.advancedmd.com/processrequest/api-103/TEMP/xmlrpc/processrequest.aspx` (amd.post) · same gateway via `https://pm-wfe-103.advancedmd.com/practicemanager/xmlrpc/processrequest.aspx?long=1` (JSON ppmdmsg, era_post) · REST `https://pm-api-103.advancedmd.com/api/...` (Bearer = same token, `Accept: application/vnd.advancedmd.api.v2+json` for demographics) · locator `https://api-100.advancedmd.com/api/locator/urls` (Bearer; answers the service map — a 401 here in the browser = stale session, sign out/in).

## Demographics
| Call | Shape | Helper | Captured |
|---|---|---|---|
| Read patient | `GET /api/demographic/patients/{id}` (v2 accept) → currentaddress, contact, responsibleparty, names | `patient_patch.get(pid)` | 9/2 |
| Edit address (the pop-up's "Edit address") | `PATCH /api/demographic/patients/{id}` body `{updatedpatient, originalpatient, updateaccounttype:false, familyupdate:{capturepreviousaddress:false, responsiblepartyid, patientids:[0], homephone, newaddress:{address1,address2,zipcode,city,state,countrycode:"USA"}}, deleteappointments:false}` — the familyupdate block is what makes it save; without it → "Address is required" | `patient_patch.family_address(pid, address1, address2, zip, city, state)` | 9/7 (William's paste, MacAllister) |
| DOB / flat fields | same PATCH, familyupdate null | `patient_patch.patch(pid, {dob:...})` | 9/2 |
| Plans | `getdemographic` class=demographics patientid="patN" → insplanlist | `denial_act3.plans(pid)` | 8/29 |
| Add plan | `addinsurance` class=demographics (no grpnum) → new ins id + sequence | `add_ins.add(pid, car, num, begin, finclass)` | 9/3 |
| Update plan (end-date, member id) | `updateinsurance` class=demographics with o_<field> originals | `ins_update.update(pid, insid, **fields)` | 9/3 |
| Charge history with payments/write-offs | `gettxhistory` class=demographics (attrs insbal/patbal/paid/carrier/facname/payerinfo; children paymentlist/writeofflist) | `txh.fetch(pid)` | 8/30 |
| Charge detail (full visit echo source) | `getchargedetaildataicd10` class=demographics chargeid= — by CHARGE id only; visitid= returns nothing for new visits | `resave.detail(cid)`, `resave.visit_charges(cid)` | 9/2 |

## Charges / visits / claims
| Call | Shape | Helper | Captured |
|---|---|---|---|
| Resave visit (insorder, onhcfa, facility, preauth, dx, modifiers) | `updvisitwithcharges` class=chargeentry, FULL charge echo, `force="1" approval="1" inspectorenabled="1"`; `modcodes` = mcode ids (25 = `mcode7`); `diagcodes` = dcode ids | `recode._save(cid, fn)`, `move_to_ins.move(cid, seq)` | 9/2, mcode 9/7 |
| Hospitalization date | `updextrainsinfo` class=chargeentry visitid="vstN" `<extins txtChargeCode hospitalizationfrom .../>` | `inspector_0907.set_date` | 9/2 |
| Frequency reset + rebill | `updextrainsinfo` resubmissioncode="1" origrefnum="" then `POST /api/claim/chargerebill` (rebillentireclaim) → 204 | `freq1_visit.run(vid, cid, seq)`, `amd.rebill_charge(cid, seq)` | 9/3 |
| Claim center counts | `getclaimcenteroverview` class=claimsreports (cached, lags) | — | 9/2 |
| Charge review / approve | `getreviewcharges`, `approvecharges` class=chargeentry | — | 9/2 |
| Inspector | `getclaiminspectorbatches`, `getclaiminspectorcharges batchid=`, `bypassclaimedits` | `inspector_0907.bypass` | 9/2 |
| Unbilled | `getclaimunbillablecharges` class=claimsreports; release `hideunbillablevisits hide="-1"` | `unbilled_0907.release` | 9/2 |
| Exclusions | `getclaimexclusionclaimruns`; `getclaimexclusioncharges claimrunid= clearinghouse="1" payer="1"`; complete `hideexclusions claimrunid= hide="-1"` | `excl_act_0907.py` | 9/2 |
| Claim runs | `getclaimrunstatus` class=claimsreports | `build_money.py` | 8/31 |
| Open balances by carrier (Mass Write-off screen search) | `POST /api/masswriteoff/masswriteoffsearch` `{carrierids:[<car number>], isinsbalance:true, billstartdate, billenddate, all other keys null}` → chargedetails[] with patientid/visitid/chargedetailid/insbalance/lastpaymentdate; `isinsbalance:false` = patient-balance charges | inline (see aet12_rebill_0907.py) | 9/7 (William's paste) |
| Unpaid list / visits by last-billed carrier (Mass Rebill screen search) | `POST /api/claim/massrebillsearch` `{carrierids:[id], begindateofservicestartdate, begindateofserviceenddate, rest null}`; `{}` = whole unpaid list | `build_money.py`, `claim_status_sweep.py` | 8/30, filters 9/7 |
| Mass Rebill button | NOT captured — ask William for the POST when he clicks Rebill | — | — |

## Payments / ERA
| Call | Shape | Helper | Captured |
|---|---|---|---|
| ERA unposted checks | `GET /api/era/checks` (unposted only); `GET /api/era/checkdetails?...` | `era_post.checks/details` | 9/4 |
| Post an ERA check (the Post button) | `posterapayments` class=autoremitreports JSON ppmdmsg via the wfe gateway | `era_post.post_check` | 9/4 |
| Process Accepted ($0.00) | same posterapayments with all amounts "0" | `era_clear.zero_post` | 9/7 |
| Dismiss a check | `POST /api/era/checks/dismiss` body = JSON string of the check id | `era_clear.dismiss` | 9/7 (William) |
| Dismissed list | `GET /api/era/checks/dismiss?DismissedDateBegin=YYYY-MM-DD` | — | 9/7 (William) |
| Restore a dismissed check | `POST /api/era/checks/reversedismiss` body `[{"id":<checkid>,"dismissedat":"<value from the list>"}]` | — | 9/7 (William) |
| Release stale locks | `POST /api/era/locks/release-expired` | `era_post.locks` | 9/4 |
| Manual payment (Payment Entry) | `addpayments` class=paymententry (pay + write-off per charge, check #, deposit date) | `manual_post.post(cid, carrier, pay, wo, code, checknumber, depositdate, note)`; `era_manual_post.py` for an unvalidated ERA line | 9/3 |
| Void a write-off / payment | `void_tx.void_writeoff(pid, cid, woid)`, `void_tx.void_payment(pid, cid, payid)` | void_tx.py | 9/6 |

## Eligibility
| Call | Status |
|---|---|
| AMD eligibility — WORKS (William re-pasted it 9/7/2026 from a prior chat; proven same night on Dunmore/Medicare and Thackeray/Medicaid) | `POST https://pm-api-103.advancedmd.com/api/eligibility/EligibilityDetailsLegacy/checkEligibility` headers `Content-Type: application/json`, `Authorization: Bearer <token>`; body `{"licensekey":"152563","username":"POI0712","patientinsurancecoverageid":"<numeric insplan id, no 'ins' prefix>","servicetypecode":"30"}`. Synchronous, ~200 ms: returns `<PPMDResults><Results eligibilityid eligibilitystatusid="1" patientname address subscriberid insuranceeffectivestartdate ...><Edi271>...` — the FULL 271. No AAA = active. Helper: `amd.check_eligibility(insplan_id)`; parser: `elig271.py` (XML-ized 271; see 9/9 section). |
| Stedi eligibility | `POST https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3` (payer ids: 77027 Medicaid, 68069 Sunshine, 87726 UHC, 60054 Aetna, 61101 Humana, 95112 CHP, MBILUNOSSN Medicare by name/DOB, CMS = AAA 41 until HEET propagates) | `stedi.elig`, `stedi.mbi` | 9/5 |
| Stedi claim status | `.../change/medicalnetwork/claimstatus/v2` | `claim_status_sweep.status` | 9/5 |
| Stedi discovery | `.../insurance-discovery/check/v1` (LIVE 9/8 — see the 9/8 evening section for the proven headless shape) | `stedi.disc`, `disc_run.py --check` | 9/6, live 9/8 |

## Master files (none work from the API)
No carrier read/write call exists (`getcarrierlist`, `getcarrier`, `lookupcarrier` → invalid action — but `lookupcarrier` class="lookup" code="%XXX%" DOES work, 9/8); no patient list/search call except `lookuppatient` class=api; carrier payer ids only visible as `payerinfo` on gettxhistory charges. Carrier setup = William in Master Files. Carrier ids confirmed 9/8: AAR01 car6600 AARP, CIG09 car6687 Cigna, CIG13 car42014 Cigna HealthSpring, CIGFS car42090, SUN01 car6194, MCAD car6113, AET07 car6047, AET12 car42009, WEL04 car6174, UNI20 car6404, UHCMA car302853, FLO02 car6085, BCBS car6062, FLO99/FCC car42008.

## 9/8/2026 — chat-session additions
| Call | Shape | Helper | Captured |
|---|---|---|---|
| Create referral plan (per-stay VA auth) | `addreferralplan` class=chargeentry, child `<refplan id="" patient="patN" ismain="0" status="stat1" preauthreq="0" sequence="2" refprov="rprovN" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility=""/>` → BLANK plan + new rplan id. Without ismain/status it get-or-returns the existing main plan. | inline | 9/8 (Lowry Fenwick) |
| Link visit to referral plan + write auth | resave with visit attrs `refplan="rplanX" preauth="VAxxxx"` → repoints AND writes preauth onto THAT plan AND the visit's PREVIOUS plan. Process the stay that keeps the original plan LAST; verify each plan's preauth + each visit's refplan. `refplan=""` snaps back to main; nested `<refplan>` child ignored. | inline | 9/8 (Lowry: 4 stays → 4 plans) |
| Why: VA auths live on REFERRAL PLANS, not the encounter | "Charge Auth #" box greys out — UI manages auths at referral-plan level; multiple VA stays MUST have one referral plan each or every claim prints the last-written auth. | — | 9/8 |
| updateinsurance wrapped shape | Bare `<insplan id field o_field/>` can fault "Value can not be null" — wrap: `<patient id="patN" changed="1"><insplanlist><insplan id="insN" field="new" o_field="old"/></insplanlist></patient>`. | ins_update wrapped | 9/8 (Denholm) |
| Unbilled "payment from prior payor required", primary just billed | Every charge shows PRIMARY, paid=0, billdate days old → primary out/unanswered; release all `hideunbillablevisits hide="-1"`. 82 released 9/8. | unbilled release | 9/8 |

## Shared-memory protocol (William, 9/8/2026)
Chat sessions and the nightly task share ONE growing rule set. The Drive folder `billing agent project files` (id 1-AsLUHMaeqvHq-fqWKUVKKUU4Xkw6XTt) is the Drive source of truth for this file (GitHub `main` is now the toolkit source of truth — see final sections):
1. START: download `captured_calls.md` from that Drive folder into the workspace before relying on the local copy; run `github_sync.py pull` to restore the full toolkit.
2. END: append what was learned (dated), upload it back to the Drive file, drop a dated digest in `aa claude folders → chat history` (id 1VCZfjSmok1fNNnYwf2yBTXlZ-zMUnAWU), and `github_sync.py push`.
3. Nightly mirrors helpers (`*.py`, `carriers.json`, `facilities.json`) to Drive `workspace mirror` AND to GitHub whenever they change.
4. Standing RULES also go into the synced skills via a proposed skill update for William to save.

## 9/8/2026 — columns-run additions (4:57 PM ET)
| Call | Shape | Helper | Captured |
|---|---|---|---|
| Diagnosis edit on a charge (THE working shape) | `diagcodes` attr on resave is SILENTLY IGNORED for edits. Dx saves only via nested child: `<charge ...><diagcodelist><diagcode id="<NUMERIC dcode id, no 'dcode'>"/>...</diagcodelist></charge>` in order. dcode-prefixed id faults int-conversion. Full echo + `approval="1" inspectorenabled="1" batchid=` still required. | inline | 9/8 (Winslow Jr; M86.9 primary ahead of S81.801S) |
| Diagnosis code lookup (dcode ids) | `lookupdiagcode` class="lookup" exactmatch="0" code="M86.9%" orderby="code" page="1" → `<diagcode id="dcode1034545415" code="M86.9" .../>`. Anchor the code at the start; `%`-prefix returns nothing. | inline | 9/8 |

WORKSPACE LOSS NOTE (9/8 ~4:57 PM ET): fresh container; nightly workspace gone, Drive "workspace mirror" was EMPTY. Rebuilt amd.py + mirrored. Mirror helpers EVERY time they change.

## 9/8/2026 evening — Stedi headless + cascade (William live-authorized)
| Call | Shape | Helper | Captured |
|---|---|---|---|
| Stedi KEY HOMES | Live key: Gmail subject "stedi claude key" (thread 1a083035f566f9fb) + workspace `secrets/stedi_live.key`. Cloud egress to healthcare.us.stedi.com OPEN for scheduled runs. Never write the key into a synced file. | stedi.py reads secrets/ | 9/8 |
| Stedi eligibility v3 headless | `POST /2024-04-01/change/medicalnetwork/eligibility/v3`, header `Authorization: <key>`; dates YYYYMMDD. MBILUNOSSN = MBI lookup. ERR 72 not Medicare; 62 (Centene) DOS too old; 79 (CHP) needs member id; 43 (Aetna) provider-not-on-file but echoes memberId (Medigap id finder); 50 provider-ineligible (out-of-network). UHC 87726 says Inactive-30 for Medigap — CMS 271 authoritative. | `stedi.elig/mbi`, `stedi.summarize_elig` | 9/8 |
| Stedi insurance discovery headless | `POST /2024-04-01/insurance-discovery/check/v1` (NO /change prefix), body {provider{organizationName,npi}, subscriber{firstName,lastName,dateOfBirth,address{state}}, encounter{dateOfService YYYYMMDD}} → {coveragesFound, items[{payer, subscriber.memberId, planDateInformation incl dateOfDeath, benefitsInformation}]}. $1.50/check. | `stedi.disc` | 9/8 |
| Payer-switch rebill worker | addinsurance → updateinsurance wrapped enddate → per visit full-echo resave with new insorder → updextrainsinfo resubmissioncode 1 → REST chargerebill(seq) 204. | `amdw.py` + inline | 9/8 (41 visits/69 charges, zero voids) |
| Stedi payer search / CPID xref | `GET /2024-04-01/payers/search?query=<name>` → items[].payer{displayName, stediId, aliases[]}; aliases = Change CPID list. | inline | 9/8 (Highmark HOXDH) |

WORKSPACE LOSS #2 (9 PM ET, same day): restore recipe proven end-to-end (mirror helpers + Gmail creds + ONE login_cached). Columns 0/0/0/5 — Lowry Fenwick (VACCN, needs 9/4 VA auth) + Abernathy Corvin (HIG04 wrong-Highmark; board row abernathy-corvin).

## 9/9/2026 — nightly insurance cascade (1:30 AM run)
| Call | Shape | Helper | Captured |
|---|---|---|---|
| Unpaid list with DOS filter | `POST /api/claim/massrebillsearch` `{carrierids:null, begindateofservicestartdate:"YYYY-MM-DD", begindateofserviceenddate:"YYYY-MM-DD"}` → rows carry patientid/patientname/visitid/dateofservice/carriercode/cpid/npid/insbalance/chargedetailids | `precheck.py` | 9/9 (31 rows) |
| getdemographic insplan has NO carriercode attr | Only `carrier="carN"` — match billed carrier by car number via carriers.json | `precheck.py` CARIDS | 9/9 |
| AMD checkEligibility 271 format | `<Edi271>` = XML-ized EDI: `<EligibilityOrBenefitInformation EB01_ EB03_ EB04_>` blocks. EB01 1=active 6/7/8=inactive; EB01 U + EB04 HN + NM103 entity = Medicare Advantage plan; EB R + EB04 OT/stc 88 = stand-alone Part D (= original Medicare); AAA03 rejection (72 bad id, 73 bad name); DTP 442 = date of death; `subscriberid` attr = matched id | `elig271.py` parse/summarize | 9/9 (17 patients) |
| Visit insorder semantics | visit attr `insorder` = comma list of plan SEQUENCE numbers ("1,2"); repoint by full-echo resave with insorder="2" then freq-1 chargerebill sequencenumber=2 | `amdw.resave_visit` + `amdw.freq1` | 9/9 (Hollis, Selby ×2, zero voids) |
| AMD-first cascade order | AMD free 271 answers 13/17 (no Stedi cost); only AAA/INACTIVE/MA-conflict escalate to Stedi | `precheck.py` | 9/9 (5 Stedi lookups ≈ $3.60/31 visits) |

WORKSPACE LOSS #3 (9/9 1:30 AM): fresh container again; restored (mirror + Gmail creds). Rebuilt+mirrored 9/9: precheck.py, elig271.py, carriers.json, github_sync.py. STILL MISSING (never mirrored — pull from GitHub main once configured, else rebuild supervised): era_post.py, era_clear.py, void_rules.py+json (Ellery Hollis F 9/5 rule), cred_check.py, build_money.py + payments_by_carrier.json, wo_reversal_post.py, claim_status_sweep.py, patient_db, registers. ERA read-only: 817 checks / $579,572.40 unposted; new since 9/6 = HUM01 199107297260905 (9/4) $114.76.

## 9/9/2026 — GitHub as toolkit-of-record + auto-bootstrap (William, standing procedure)
Make GitHub `main` the source of truth; bootstrap from it EVERY run. Mirror to BOTH GitHub and Drive.

STANDING RUN PROCEDURE (fold into the nightly steps):
- RUN START (before Step 1), after restoring amd/amdw/stedi from Drive: `python3 github_sync.py pull`
  → fetches origin/main into /home/claude/unbilled, restoring the FULL toolkit (era_post, era_clear,
  void_rules+json, build_money, cred_check, claim_status_sweep, wo_reversal_post, precheck, elig271,
  carriers.json, facilities.json). Ends the workspace-loss cycle — no more per-file rebuilding.
- RUN END (after Step 5): `python3 github_sync.py push "nightly <date>: <what changed>""` → commits
  tracked helpers and pushes to main. Keep Drive `workspace mirror` copies too (belt and suspenders).

CONFIG (both in secrets/, gitignored, NEVER committed):
- secrets/github_pat.key = fine-grained PAT "claude billing backend" (Gmail subject "github claude
  token" / "claude github read write", thread 1a084f16f2f10b2b, 9/9/2026 — fetch at runtime like the
  AMD password / Stedi key).
- secrets/github_repo.txt = repo slug "dreffinger/<REPONAME>" (William to confirm the exact name; the
  9/8 "Cloud Practice" repo, layout core/billing/era/rebill/eligibility/credentialing/claimocity/
  boards/nightly/practices/ehpa/docs, PHI-stripped, likely already holds the lost era/rebill scripts).

TWO ACCESS GATES (both required for push from a scheduled run):
1. Harness binding: GitHub access is bound at SESSION-CREATION time. A run started BEFORE the repo was
   added to the task's authorized sources gets 403 "access not enabled for this session". FIX: William
   adds the repo to the scheduled task's authorized sources (the task's GitHub / "option 2" setup) —
   effective on runs created AFTER that. The 1:30 AM 9/9 run predated it, so it logged the skip.
2. PAT scope: the PAT must have Contents:read+write on that exact repo. git-over-https with the PAT
   embedded authenticates fine (proven 9/9); a wrong slug returns "Repository not found".
   api.github.com/user/repos is blocked by the harness even with the PAT, so the slug can't be
   enumerated from a scheduled run — William supplies it once into secrets/github_repo.txt.

github_sync.py is safe: no slug / no access → one-line skip, no error, cascade never blocks on GitHub.
Added to workspace + Drive `workspace mirror` 9/9.

## 9/9/2026 — GitHub mirror wired for READ/RESTORE (columns-run session, ~3 AM ET)
William created a fine-grained GitHub PAT (repo dreffinger/effinger-billing-backend, Contents read+write) and emailed it to himself.
- Token home: Gmail thread subject "github claude token" (dreffinger@gmail.com, 9/9/2026). Fetch at runtime like the AMD password / Stedi key; write ONLY to secrets/github_pat.key (chmod 600, gitignored, ephemeral). NEVER store the token in Drive, the repo, memory, or any synced file.
- READ / restore: WORKS from scheduled runs. Clone/fetch via https://x-access-token:<TOK>@github.com/dreffinger/effinger-billing-backend . The repo's main branch holds the FULL backend — ~106 Python scripts (inspector/ERA/freq1/resave/precheck/etc.), pseudonymized but logic intact — a richer restore source than the Drive workspace mirror. Bootstrap script: github_restore.sh (in Drive "workspace mirror" folder id 135OCbRNCnFLyVm2GBXk1XsE3lt0vnsrn) clones main to /home/claude/effinger-billing-backend then scrubs the token from the remote URL.
- PUSH: BLOCKED by the agent git proxy for scheduled runs ("not in this session's authorized repository set") — an org-egress 403, do NOT retry/route around. Push unblocks only when the repo is added to this task's authorized sources (a task-setup step). Until then commit locally + tarball to Drive "github mirror"; William pushes manually. Try granting the Claude GitHub App on the repo at github.com/settings/installations to open it.
- API note: api.github.com/repos is proxy-gated the same way ("use add_repo"); /user works. Git-over-HTTPS token-in-URL is the working read path, not the REST API.

## 9/9/2026 — 9 AM ET columns run (13:00 UTC, workspace loss #4)
Board already clear 0/0/0/0 by list calls (7 AM run left it clean); no new board drops, no new Pam attachments. Restored the 8 mirror helpers + Gmail creds; ONE login_cached, success.
GITHUB READ CAVEAT: this run's git-over-https restore FAILED — proxy/GitHub answered "Invalid username or token. Password authentication is not supported for Git operations" on the `dreffinger:<pat>@` form, and the session's permission layer then blocked further credentialed-git commands (x-access-token form untested in this run). So READ from scheduled runs is NOT reliable yet — treat the Drive `workspace mirror` as the working restore path until the repo is added to this scheduled task's authorized sources (which fixes pull AND push properly). github_sync.py unchanged; it still no-ops safely.

## 9/9/2026 — 1 PM ET columns run (17:00 UTC, workspace loss #5)
Columns 0/0/0/0 by all four list calls (getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges totalcount=0, getclaimexclusionclaimruns totalcount=0); overview agrees. No new board drops, no new Pam attachments. ONE login_cached, success.
GITHUB READ NOW PROVEN: `git clone https://x-access-token:<PAT>@github.com/dreffinger/effinger-billing-backend` WORKS from a scheduled run (the 9 AM failure was the `dreffinger:<pat>@` URL form — always use x-access-token). BUT repo main does NOT hold the ~106 Python scripts — it is docs + browser scripts only (see its docs/script_inventory.md: "the Python helper source is gone"); the Drive `workspace mirror` remains the only helper restore source. This run committed the current mirror helpers (amd.py, amdw.py, stedi.py, elig271.py, carriers.json — no secrets) into the local repo mirror under scripts/helpers/ (commit d72b71f). A tarball could NOT be uploaded to Drive — the Drive connector rejects payloads that size from scheduled runs — but nothing is lost: every helper is already in Drive `workspace mirror` and the docs are on GitHub main. NEXT STEP for William: add the repo to this scheduled task authorized sources so runs can push scripts/helpers/ to main directly; a `github mirror` Drive folder (id 1yr8X30h01-tPa0swclvtBFdAisiHzgJ8) now exists for future tarballs if push stays blocked.
## 9/9/2026 — 5 PM ET run + live mirror audit (William asked "is GitHub serving as a mirror?")
Columns 0/2/0/11 by list calls — every open row deliberately held (Lowry Fenwick VACCN 13-byte auth VA90108366827, confirmed printed ON the hospital's own 8/18 facesheet by visual read, so the fix is HSRM/Optum not a re-drop; Orme Cotterell ×7 SIM01 "rendering NPI must be registered with the state" = Pam Garcia FL Medicaid enrollment ATN 1127554).
MIRROR AUDIT RESULT: GitHub main was docs+browser only; this session synced the FULL current helper set into scripts/helpers/ (amd, amdw, stedi, elig271, precheck, excl_fix_0909, github_sync, github_restore.sh, carriers.json — no secrets), refreshed docs/captured_calls.md to the current Drive registry, and regenerated docs/postman_effinger_amd.json to include the XML-gateway calls (login, four columns, demographics writes, extrainsinfo, resave skeleton, referral plan, lookups, payments) — the old export had only REST+Stedi. github_sync.py FIXED: _remote() now uses the x-access-token URL form (dreffinger:<pat>@ is rejected by GitHub). Tarball upload to Drive "github mirror" FAILED again (the Drive connector rejects multi-part base64 payloads that size from scheduled runs — same as the 1 PM run); nothing lost, every file is mirrored individually (helpers in "workspace mirror", docs in "billing agent project files"). GitHub push from runs stays proxy-blocked until William adds dreffinger/effinger-billing-backend to this scheduled task's authorized sources — that is THE fix: the next authorized run regenerates and pushes scripts/helpers/ + docs/ to main automatically.