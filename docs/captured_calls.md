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
Columns 0/2/0/11 by list calls — every open row deliberately held (Lowry Fenwick VACCN 13-byte auth VA90108366827, confirmed printed ON the hospital's own 8/18 facesheet by visual read, so the fix is HSRM/Optum not a re-drop; Orme Cotterell ×7 SIM01 "rendering NPI must be registered with the state" = Pam Garland-G FL Medicaid enrollment ATN 1127554).
MIRROR AUDIT RESULT: GitHub main was docs+browser only; this session synced the FULL current helper set into scripts/helpers/ (amd, amdw, stedi, elig271, precheck, excl_fix_0909, github_sync, github_restore.sh, carriers.json — no secrets), refreshed docs/captured_calls.md to the current Drive registry, and regenerated docs/postman_effinger_amd.json to include the XML-gateway calls (login, four columns, demographics writes, extrainsinfo, resave skeleton, referral plan, lookups, payments) — the old export had only REST+Stedi. github_sync.py FIXED: _remote() now uses the x-access-token URL form (dreffinger:<pat>@ is rejected by GitHub). Tarball upload to Drive "github mirror" FAILED again (the Drive connector rejects multi-part base64 payloads that size from scheduled runs — same as the 1 PM run); nothing lost, every file is mirrored individually (helpers in "workspace mirror", docs in "billing agent project files"). GitHub push from runs stays proxy-blocked until William adds dreffinger/effinger-billing-backend to this scheduled task's authorized sources — that is THE fix: the next authorized run regenerates and pushes scripts/helpers/ + docs/ to main automatically.
## 2026-09-10 — learnings (chat + 7pm nightly, save-every-run rule)
STANDING RULE (William 9/10/2026): at the END of every nightly run or chat session, append everything learned that day (new calls, codes, carriers, fixes) here and push to the GitHub main mirror + Drive so the AMD-API vocabulary grows continuously.

### New captured calls
- PATIENT NAME SEARCH (finally captured): `lookuppatient class="api" name="LASTNAME, FIRSTNAME%"` → <patient id="patNNN" name dob chart> hits. `code=` matches the CHART code not the name; `lastname=`/`firstname=`/`searchtext=` are ignored (return the first 50 alphabetically). Use the `name="LAST, FIRST%"` wildcard. (Found Norcott Calder dup charts pat22546 / pat22776.)
- ERA reversal pipeline (WOINSBANK) — `wo_reversal_post.py`: voids the 5/31/2026 WOINSBANK bulk write-offs (`void_tx.void_writeoff`) so the balance returns to INSURANCE (not patient — verified), then posts the ERA. BUG FOUND + FIXED 9/10: its `post_check` posted $0 because the ERA remit stores each visit's `insurancebalance` as of remit-load time (=0, the write-off had zeroed it) and `postable()` gates on balance>0. FIX: add the just-voided visit ids to `era_post.FORCE_VISITS` before `post_check`, then clear them (patch committed). `era_post.py --visits` takes a COMMA-separated list (space-separated silently forces only the first). Each ERA charge line: `paymentamount + adjustmentamount = fee`, so a correct post nets the charge to $0, or leaves the coinsurance on the secondary; a Medicare patient with NO supplement legitimately keeps the ~20% as a patient balance.
- ERA bulk-dismiss — `era_clear.py`: dismisses a check only when no postable money remains (money already posted / denials the cascade handles / $0 dup lines), HOLDS anything money-bearing (postable / unrecorded-reversal / unvalidated-with-money). Reversible via `/api/era/checks/reversedismiss`. 9/10: 1,352 dismissed, ERA Center 1,982→629; the 629 held are 568 reversal-pipeline + 49 unvalidated-with-money + 12 orphan.
- ERA poster from a SCHEDULED run without a 2nd login: write `/home/claude/unbilled/.session.json` = {web, token, ts} from the mirror's `.amdtoken.json` (repo `core/amd.py.login_cached` reads `.session.json` and returns (web, token); the mirror `amd.py` reads `.amdtoken.json` and returns bool — two different interfaces). Run repo ERA scripts from the repo dir with `env.sh` so `import amd` resolves to `core/amd.py`.

### Carriers / codes
- car302853 = UNITEDHEALTHCARE DUAL COMPLETE (UHCMA, D-SNP) — used for FL UnitedHealthcare Dual Complete HMOPOS.
- car41991 = (unlabeled, appeared on Calder chart, num 9551029429) — identity TBD, treat as stale until confirmed.
- Claim Inspector 117065068 "Hospitalization From Date in the Extra Info": set `hospitalizationfrom` = most-recent 99223 admission (≤45 days) via `updextrainsinfo`, then full-echo resave `onhcfa=1`; the referral-plan `preauth` survives the resave if echoed. Re-inspect → clears.

### Coding / payer
- D-SNP fix (Calder): UHC Dual Complete member id (on the chart; not repeated here) stays the SAME across plan years (2025-02-01→ and 2026); Stedi MBI lookup shows the MA plan history (other/U entity + coordinationOfBenefits date). Bill the D-SNP primary + Medicaid secondary (insorder "primaryseq,medicaidseq"); end-date straight-Medicare + stale plans the day before the D-SNP begin. Straight Medicare on a D-SNP member denies CO24.
- VA auth NPV087: must be VA/UC + exactly 12 bytes; a facesheet value like VA90108366827 (13 bytes) is invalid even though the hospital printed it — needs Optum VA CCN 877-881-7618, never invent.


## 9/10/2026 — 11 PM ET columns run (03:00 UTC, workspace loss #6): GitHub restore PROVEN FULL
`git clone` + `git fetch main` via the x-access-token URL form returned the FULL Cloud Practice backend this run — 106 py scripts (commits c2fe5d7 "Add the real Cloud Practice backend: 104 scripts" + b9ecde8 "Pseudonymize patient names", 9/8) — so the 9/9 1 PM "docs+browser only" finding is obsolete: main now IS the toolkit restore source. Caveat: the repo's DEFAULT branch is the mirror-w74pqv branch (docs+browser only) — always fetch/checkout `main` explicitly (github_restore.sh does this correctly). Drive `workspace mirror` copies of amd.py / amdw.py / stedi.py / elig271.py / carriers.json / excl_fix_0909.py (9/8–9/9) are NEWER than the repo commits — overlay them after the clone.
Restore recipe proven this run: clone/fetch main → symlink repo *.py/*.json flat into /home/claude/unbilled → overwrite with Drive-mirror versions → Gmail creds (AMD psw thread 1866ce7e2233e4c0, Stedi key thread 1a083035f566f9fb, GitHub PAT thread "github claude token") → ONE login_cached, success.
Run result: columns 0/1/0/11 → 0/0/0/11. Calder Norcott (UHCMA, visit 19421055, CCM 99487+99489 10/25/2025): Pattern 35790 advisory, 99489 already carried mod 25 → bypassclaimedits edit 394011, batch list empty after. Exclusions unchanged standing holds: Orme Cotterell ×7 SIM01 (Pam Garland-G FL Medicaid ATN 1127554) + Lowry Fenwick ×4 VACCN (needs 12-byte VA auth from HSRM/Optum; VA90108366827 is 13 bytes). No new board drops; no new Pam attachments. Full registry body unchanged — this file is append-only additions per the 9/9 0500-run precedent (Drive connector cannot edit a file in place; full re-upload skipped to keep the authoritative copy pristine).

## 9/10/2026 — 1:30 AM nightly (05:30 UTC, workspace loss #7): full restore recipe re-proven
GitHub `git clone --branch main` (x-access-token form) returned the full 115-script toolkit; flattened into /home/claude/unbilled, overlaid with the Drive `workspace mirror` copies (precheck/elig271/amdw/stedi/carriers/wo_reversal_post/github_sync — all newer than the 9/8 repo commits), creds from Gmail (AMD psw thread 1866ce7e2233e4c0, Stedi key 1a083035f566f9fb, PAT "github claude token"). ONE login_cached, success.

### API/toolkit learnings
- TWO amd.py generations exist: repo `core/amd.py` (login_cached()->(web,token), .session.json, amd.post/amd.msg — what all repo scripts use) vs the mirror amd.py (login_cached()->bool, .amdtoken.json, amd.call/rest_post — what amdw/precheck use). MERGED tonight: repo amd.py + appended compat shims (esc, call, wfe_call, rest_get, rest_post, check_eligibility_xml). One interface, both script generations run. Merged amd.py uploaded to workspace mirror.
- precheck.py patched: CARIDS now built from the RICH carriers.json (carN -> [code,name] — the format every repo script expects); its eligibility call now amd.check_eligibility_xml (raw 271 text). Patched precheck.py uploaded to workspace mirror.
- carriers.json format conflict resolved: workspace keeps the rich practices/ehpa format; the code->carN map is derived in-script.
- void_rules.json rebuilt (was lost): ELLERY, HOLLIS F = pat17477530 (found via lookuppatient name="ELLERY%"), dos 09/05/2026 rule re-armed; charge has NOT landed yet (9/2-9/4+9/6 charges previously voided; no 9/5 line in txh).
- wo_reversal cycle at scale: era_clear (writes era_clear_reversal_<date>.json) -> copy to wo_reversal_<date>.json -> wo_reversal_post (FORCE_VISITS fix works) -> strip the posted checks' HOLD lines from era_clear.log -> rerun era_clear to dismiss. Ran x3 tonight: voided $81,826 WOINSBANK write-offs, posted $36,969.87, dismissed 221 checks; ERA Center 629 -> 110 open.
- Ledger continuity after workspace loss: payments_by_carrier.json reconstructed from the 9/7 per-payer paid_* numbers embedded in the live Money Ledger artifact D-json (totals reconcile to the penny: 762,992.67 / 948,220.72 / 532,986.28). Real pay_scan re-run Sunday needs patient_universe rebuilt too (also lost).
- tools/mirror/ is NOT on repo main and Drive `github mirror` folder is EMPTY — mirror.py sync unavailable to scheduled runs; Drive-only mirror legs tonight, GitHub push leg skipped (also still proxy-gated for this task).

### Cascade results (details in tonight's board rows + needs_facesheet_list)
- Draycott Marisa Ione: Medicare's enrolled first name is IONE (CMS 271 ACTIVE for IONE DRAYCOTT + UHC supplement entity); chart first name MARISA IONE -> AAA 73 forever. Chart rename left for William (board row, status william).
- Selby Annie: 3rd straight visit Claimocity-billed to FLO02 despite CHP MA since 2007 — repointed + freq-1 re-sent. Consider a standing auto-repoint rule for her.
## 9/10/2026 — 3 AM ET columns run (07:00 UTC, workspace loss #8): registry MERGED
This file now carries the 9/10 additions (learnings, 11 PM ET run, 1:30 AM nightly) merged into the registry body — the three additions files on Drive are superseded by this copy. Restore this run: clone main (x-access-token), flatten, overlay Drive workspace-mirror copies + amd_shims_2026-09-10.py appended to core amd.py, Gmail creds, ONE login_cached, success. No NEW calls captured this run (all calls used were already registered). Columns 0/4/1/61 -> 0/0/1/61: Selby 99233 9/8 hospitalizationfrom=09/06 (99223 anchor) + resave; three Pattern-35790 CCM advisories bypassed (mod 25 already on each 99489); Unbilled = Fairholm Elowen (NO insurance on chart, cascade exhausted: discovery 0 coverages, FL Medicaid needs member id, no facesheet anywhere — board row fairholm-elowen, william's turn); Exclusions 61 = standing holds (Orme x7 SIM01 enrollment, Lowry x4 VACCN auth, AET12 x50 carrier CPID — 5th consecutive TIN run on 1700166). tools/mirror/ still absent from main + `github mirror` folder still empty + push still proxy-gated -> Drive-only mirror legs again.

## 2026-09-10 overnight — full unpaid audit + rebill (William: "get everything sent in the past year to the correct place")
### New tools (repo root; run from the repo with env.sh)
- `claims_audit.py <CARRIER> --days 365 --max N` (lives in /home/claude/unbilled, mirror helpers): massrebillsearch scoped to the carrier → one FREE AMD 271 per patient on the billed plan → classifies WRONG-PAYER / AAA / DATE-OF-DEATH / INACTIVE / ACTIVE-OK / NO-PLAN → incremental, resumable CSV.
- `claims_fix.py <CARRIER> <audit.csv> [--backlog-only] [--dry]` (repo): acts per flag — ACTIVE-OK → freq-1 rebill (skips `settling()` visits that already carry a payment); DATE-OF-DEATH → WOINS post-death DOS, rebill pre-death; WRONG-PAYER → map MA plan name → carrier, member id from the 271 entity id or a Stedi elig with the MBI, add plan / end-date old / insorder / rebill; AAA (FLO02 ONLY) → Stedi MBI lookup, fix subscribernum if it differs, rebill; everything unresolved → `claims_fix_escalate_*.csv` for William. Resumable via `DONE <pid>` log lines.
### Calls / gotchas learned
- massrebillsearch `chargedetailids` is a COMMA-SEPARATED STRING ("23363033,23363034"), not a list — split it (the first run posted nothing because `cids[0]` was the character "2").
- A COMMERCIAL plan's 271 (BCBS, UNI20…) lists the subscriber's own name, benefit riders ("BLUE VIEW VISION") and "NO OTHER INSURANCE" as other/U-R entities — those are NOT alternate payers; the billed plan is simply ACTIVE. Only a name that maps to a real health payer (another Blue, Medicare, Humana, UHC…) is a genuine wrong-payer. Medicare 271s are the ones where other/U = the MA plan.
- The Medicare MBI lookup must NEVER be used to "correct" a commercial plan's member id — it briefly wrote an MBI onto two BCBS plans (Marlow, Gresham; reverted within minutes, nothing billed). AAA on a non-Medicare plan = that payer rejected the id → card/facesheet.
- Carriers: SIM01 = car42019 (Simply; was missing from carriers.json — an unmapped carrier makes massrebillsearch fall back to ALL carriers). CMS Health Plan / "Children's Medical Services" (Medicaid specialty plan, ages ≤21) is administered by Sunshine → bill SUN01 car6194 (payer 68069), NOT FL Medicaid FFS (Fairholm 9/10: FL Medicaid 271 full-active + Sunshine 271 "CMS Title XIX" active on the same member id).
- Long jobs: run scripts with `nohup … &` and poll the log — a foreground command dies at the 10-minute cap and (if it only writes at the end) loses its work. Two AMD write processes + one audit ran concurrently all night with zero 429s.
- CONCURRENT SESSIONS on the ERA Center: the 1:30 AM nightly ran its own era_clear → wo_reversal_post cycle (posted $36,969.87, dismissed 221) while this session's full-scale reversal was running. No double work happened only because `recorded()` (visit already has a non-void payment / a reversal-register line) skips visits the other session finished (235 skipped here) — so keep that gate, and before starting any ERA reversal run check `pgrep -f "wo_reversal_post|era_clear"` and the newest `Writeoff_reversal_register_*.csv`.
### Standing rules (William 9/10)
- UNI20/BCBS pre-5/1/26 ERA-backlog visits are NO LONGER skipped in the audit — verify insurance and rebill them too (the WOINSBANK reversal posted those ERAs, so `settling()` now protects the ones that were paid). `--backlog-only` re-runs just those.
- CHARGE REVIEW INSURANCE GATE (every 2-hour run, first column): before approving, run AMD eligibility on the listed plan; ACTIVE + insurance order set → approve; INACTIVE/AAA/other payer → Stedi correction (MBI → payer elig → discovery), fix plan + order, then approve; NO plan → MBI lookup + discovery, add if found, then approve; nothing found → visit STAYS in Charge Review with a board row until the correct insurance is attached (only William bypasses). Build as `charge_review_gate.py` reusing claims_audit/claims_fix.
### Results 9/10 overnight
- WOINSBANK reversal (5/31/26 bulk write-off undone, wo_reversal_post force-post fix): 5,166 write-offs reversed, $393,894 ERA posted, 0 errors.
- Unpaid audit, 12 cohorts, 1,001 patients / $528K: 1,895 visits rebilled = $286,166; 18 wrong-payer patients moved to their real plan; 9 wrong MBIs corrected; $0 written off; 163 patients / $145K parked (62 AAA, 60 inactive → discovery pass next, 28 DOD confirm, 13 wrong-payer no-id).

# captured_calls additions — 2026-09-10 1 PM ET columns run

No new API calls captured (all four columns were steady standing holds).

Observation (rule refinement, not a new call):
- AET12 (Aetna Senior Supplemental Medigap secondaries), exclusion run 1700166: the rejection signature CHANGED between the 9am/11am reads (PREF0288 "invalid payer id/CPID = TIN") and the 1pm read (**PREF0264 MISS/INVD PAYER DOC CONTRL NUM**). Reading each run's getclaimexclusioncharges error text is the only window into whether a carrier-master CPID fix landed. PREF0264 on a Medigap secondary = missing Medicare crossover document-control number; freq-1 does not fix it, freq-7 only with William's payer ICN. So: after a carrier-master CPID fix, re-read the exclusion error before assuming the claim is now billable — the block can move from carrier-setup to missing-crossover-DCN.

# captured_calls additions — 2026-09-10 3 PM ET columns run

No new API calls captured (registry unchanged; all four columns worked with registered calls only).

API-behavior lessons (rule refinements, not new endpoints):
- **Stedi payer eligibility refuses old dates of service**: Centene 68069 and UHC 87726 both answer AAA 62 "Date of Service Not Within Allowable Inquiry Period" for a DOS ~22 months back (pat17472230, DOS 11/2024). The **MBI lookup (MBILUNOSSN) still answers for those same DOS** — including the U/PR Medicare-Advantage COB window and QMB — so for aged claims the MBI lookup is the only backend window into who covered the patient then; the 271 may name no MA entity (U-code row with empty entity list).
- **UHC 87726 for a terminated/unknown supplement policy** returns only bare U/X benefit codes (no planStatus, no membership echo) rather than an explicit Inactive — treat "no membership data" as policy-not-recognized (pat17473020, pat17473232).
- Confirmed the 9am lesson end-to-end: the 52 BCBS Medigap secondaries re-sent freq-1 at 9am ET re-rejected on the next run (1700181) with PREF0283 MISSING PAYER DOC CONTROL NUM — freq-1 does not supply the Medicare DCN; 27 of them also carried PDTP0303 (admission dates stripped by the earlier freq-1 resets), repaired this run via updextrainsinfo full-echo with hospitalizationfrom.
- Unbilled "payment from prior payor" release rule re-proven at scale: 92 rows, every sampled charge primary FLO02 billdate 09/05/2026 paid 0 -> hideunbillablevisits hide=-1 in batches of 40, column 104 -> 12.

Mirror note (3pm run, fresh container): GitHub push still proxy-blocked (403, repo not in this task's sources) — this run's commit is in Drive github mirror as 2026-09-10_1945UTC.bundle.b64 (BASE64 TEXT this time). The two earlier binary .bundle files in that folder download 121 bytes short via the Drive connector (pack corrupt on fetch: "bad object at offset 10723"), so the pending 0500/1104 commits could not be restored into this run's clone; both files were left in place (NOT pruned to two) because their commits exist nowhere else. Store future bundles as .b64 text.

# captured_calls additions — 2026-09-10 5 PM ET columns run

No new API calls captured (all four columns handled with registered calls; registry/vocabulary unchanged).

State confirmations (no rule changes):
- Unbilled #INT interest-line pattern re-confirmed unchanged (pat17472733, pat12180125, pat17472968) — standing 9am rule (move ins bal to patient, held for William).
- AET12 PREF0288 TIN-as-CPID persists to a 5th consecutive run (1700166); BCBS PREF0283 DCN cluster persists (1700181/1700166). Both remain William/carrier-blocked; no rebill.
- Recovered the 05:00/11:04/19:45 UTC mirror bundles from Drive github mirror and merged all three into main (the 19:45 file was double-base64; decode twice).

Mirror note (5pm): GitHub push proxy-gated (403, repo not in this task's sources). The .b64 bundle upload via the Drive connector truncated on the large inline blob this run, so commit 15906ec is preserved as this readable additions doc + the chat-history digest rather than a binary bundle; prior 1945 bundle still holds through the 3pm commit.

# captured_calls additions — 2026-09-10 7 PM ET columns run (23:00 UTC)

RUN BLOCKED — NO EGRESS TO ADVANCEDMD / STEDI / GITHUB from this run's environment.
- The session's egress proxy answered CONNECT 403 (policy denial) for EVERY AdvancedMD host (partnerlogin, pm-api-103, providerapi, pm-wfe-103, api-100) AND healthcare.us.stedi.com AND enrollments.us.stedi.com; git to github.com refused with "request blocked: no rule allows host github.com".
- Prior same-day runs (5 PM ET and earlier) had AMD + GitHub-read egress, so this looks like a per-run/task network-permission regression, not an AMD outage. WILLIAM: check the scheduled task's authorized sources / org egress allowlist (Claude admin -> Capabilities) — AdvancedMD + Stedi hosts (and the GitHub repo) need to be allowed for the task's runs.
- SAFETY: no login attempt reached AdvancedMD (connections were rejected at OUR proxy before any credential was transmitted) — POI0712 lockout counter untouched. The one-attempt lock protocol was honored; local lock cleared after confirming the failure was network-layer.
- Workspace restore (fresh container, loss #9): Drive workspace-mirror helpers + registry restored fine (Gmail/Drive/board connectors all work); GitHub read now ALSO blocked for this run, so repo-only scripts (resave/recode/era_post/era_clear/freq1_visit/add_ins/ins_update/move_to_ins/manual_post/txh/patient_patch) were unavailable — moot, since AMD itself was unreachable.
- Work done with the reachable connectors: board drops 0 new; Pam attachment sweep 0 new; standing 7 PM "current face sheets needed" email SENT to dreffinger@gmail.com (carried-forward list, caveated); run-report CSV delivered in-chat + copied to Drive bht hca facesheets; needs_facesheet_list.md rebuilt locally with this run's section.
- Columns before -> after: NOT READ -> unchanged (no list calls possible). No calls captured (none reachable). Vocabulary/Postman unchanged.
- Mirror legs this run: GitHub BLOCKED (no clone, so no bundle possible); Postman SKIPPED (collection unchanged); Drive DONE (this file + run report + digest).

# captured_calls additions — 2026-09-10 nightly insurance cascade (fired 7:52 PM ET / 23:52 UTC, finished ~9 PM ET)

RUN BLOCKED AT THE NETWORK LAYER — no egress to AdvancedMD / Stedi / CMS / OIG / GitHub from this run's container.
- Egress proxy answered CONNECT 403 (organization policy, "no rule allows host") for partnerlogin / pm-api-103 / pm-wfe-103 .advancedmd.com, healthcare.us.stedi.com, enrollments.us.stedi.com, npiregistry.cms.hhs.gov, data.cms.gov, oig.hhs.gov and github.com. Same wall as the 7 PM ET run and the two parallel firings at 8:25 / 8:45 PM ET. Policy 403s are report-only (proxy runbook) — not retried.
- SAFETY: no login attempt reached AdvancedMD (curl probes, no credentials); POI0712 lockout counter untouched. AMD password and Stedi key fetched from their Gmail threads into the workspace only (`.amd_cred.json`, `secrets/stedi_live.key`) — never copied anywhere durable.
- Steps 1 / 2b / 3 / 3b / 5 skipped (each needs AMD and/or Stedi); Step 2 N/A (Thursday). 0 visits checked, 0 Stedi lookups ($0.00), $0 re-sent, $0 ERA posted, no write-offs (no Writeoff register written).

No new API calls captured. Vocabulary unchanged.

RESTORE LESSON (new, proven this run): with GitHub blocked, the full toolkit still restores WITHOUT GitHub:
1. Claude-project doc `mirror/outbox/effinger-billing-backend_<date>.bundle.b64` (project_read → base64-decode → `git clone --branch main <bundle>`) gives `main` with tools/mirror, docs/api_vocabulary.json and all 116 scripts (copied flat into /home/claude/unbilled).
2. Drive `workspace mirror` (id 135OCbRNCnFLyVm2GBXk1XsE3lt0vnsrn) overlays the newer helpers: amd.py (= repo core/amd.py + the 9/10 compat shims: esc/call/wfe_call/rest_get/rest_post/check_eligibility_xml), void_rules.json, payments_by_carrier.json, pseudonyms.json → secrets/.
3. Drive `billing agent project files`: captured_calls.md (real names) + every captured_calls_additions_*.md newer than it (mirror.py sync merges them).
4. Drive `github mirror` 2026-09-10_1945UTC.bundle.b64 (double-base64) holds the 3 PM ET registry commit 1253044 on a b9ecde8 base — merged into main this run (commit 33745ae) so the two lineages are one again. The two binary .bundle files there (0500 / 1104 UTC) are still corrupt on fetch; store bundles as .b64 text only.
5. This run re-exports main as a fresh bundle to Drive `github mirror` AND to the project doc `mirror/outbox/` so the next fresh container restores the newest main.

Credentialing (Step 4b) partial via connectors: NPPES for 1629515325 / 1225327380 / 1235128869 read through the NPI Registry connector — all three unchanged vs the 9/6 snapshots (group: Ginger Dr second location + Medicaid id still on record, last updated 2021-09-07; WE current 2026-07-21; PG stale 2019-02-26, taxonomy still 207R00000X). No board writes on the NPI cards. cred_nppes_snapshot.json now seeded in the workspace for cred_check.py's diff. CMS revalidation list and OIG LEIE unreachable (403; WebFetch would need an interactive approval). Reminder windows: pay-cigna and pay-uhc (due 9/10/2026) passed — one note + one check each, both stay on William's turn (Cigna's three 9/9 PSU secure-email notices are still unread; UHC directory attestation still unconfirmed in the mailbox).

Board: Insurance Refresh Board `drops` — `dice-rename-approved-2026-09-10` (pat17477350: William-approved first-name fix via patient_patch + free 271 verify + 3 FLO02 freq-1 rebills) is still `new`; an attempt entry logged; it needs the first run that has AMD egress. Two older drops already `done`.

FIX FOR WILLIAM (unchanged from the 7 PM run): allow *.advancedmd.com, healthcare.us.stedi.com, enrollments.us.stedi.com — and ideally github.com, data.cms.gov, oig.hhs.gov, npiregistry.cms.hhs.gov — for the scheduled task's runs (Claude admin → Capabilities / the task's authorized sources). Until then every firing restores the workspace and stops at the same wall; the ~110 unposted ERA checks from the 9/10 1:30 AM run and the DRAYCOTT drop are waiting.

Mirror legs this run: GitHub push BLOCKED (bundle written); Postman SKIPPED (vocabulary unchanged); Drive DONE (this file, registry re-upload, bundle .b64, digest); project doc bundle refreshed.
