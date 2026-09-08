# Captured AMD / Stedi calls — the registry (read this before guessing at any endpoint)

Rule (William, 9/7/2026): **every call learned from a DevTools paste or by probing is written here the same night**, with the shape that worked, the helper that wraps it, and the date. If it isn't in this file it hasn't been captured — ask William for the paste rather than guessing. Never store a bearer token or a password here.

Hosts: XML gateway `https://providerapi.advancedmd.com/processrequest/api-103/TEMP/xmlrpc/processrequest.aspx` (amd.post) · same gateway via `https://pm-wfe-103.advancedmd.com/practicemanager/xmlrpc/processrequest.aspx?long=1` (JSON ppmdmsg, era_post) · REST `https://pm-api-103.advancedmd.com/api/...` (Bearer = same token, `Accept: application/vnd.advancedmd.api.v2+json` for demographics) · locator `https://api-100.advancedmd.com/api/locator/urls` (Bearer; answers the service map — a 401 here in the browser = stale session, sign out/in).

## Demographics
| Call | Shape | Helper | Captured |
|---|---|---|---|
| Read patient | `GET /api/demographic/patients/{id}` (v2 accept) → currentaddress, contact, responsibleparty, names | `patient_patch.get(pid)` | 9/2 |
| **Edit address (the pop-up's "Edit address")** | `PATCH /api/demographic/patients/{id}` body `{updatedpatient, originalpatient, updateaccounttype:false, familyupdate:{capturepreviousaddress:false, responsiblepartyid, patientids:[0], homephone, newaddress:{address1,address2,zipcode,city,state,countrycode:"USA"}}, deleteappointments:false}` — the familyupdate block is what makes it save; without it → "Address is required" | `patient_patch.family_address(pid, address1, address2, zip, city, state)` | **9/7 (William's paste, MacDonald)** |
| DOB / flat fields | same PATCH, familyupdate null | `patient_patch.patch(pid, {dob:...})` | 9/2 |
| Plans | `getdemographic` class=demographics patientid="patN" → insplanlist | `denial_act3.plans(pid)` | 8/29 |
| Add plan | `addinsurance` class=demographics (no grpnum) → new ins id + sequence | `add_ins.add(pid, car, num, begin, finclass)` | 9/3 |
| Update plan (end-date, member id) | `updateinsurance` class=demographics with o_<field> originals | `ins_update.update(pid, insid, **fields)` | 9/3 |
| Charge history with payments/write-offs | `gettxhistory` class=demographics (attrs insbal/patbal/paid/carrier/facname/payerinfo; children paymentlist/writeofflist) | `txh.fetch(pid)` | 8/30 |
| Charge detail (full visit echo source) | `getchargedetaildataicd10` class=demographics chargeid= — **by CHARGE id only**; visitid= returns nothing for new visits | `resave.detail(cid)`, `resave.visit_charges(cid)` | 9/2 |

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
| **Open balances by carrier (Mass Write-off screen search)** | `POST /api/masswriteoff/masswriteoffsearch` `{carrierids:[<car number>], isinsbalance:true, billstartdate, billenddate, all other keys null}` → chargedetails[] with patientid/visitid/chargedetailid/insbalance/lastpaymentdate; `isinsbalance:false` = patient-balance charges | inline (see aet12_rebill_0907.py) | **9/7 (William's paste)** |
| **Unpaid list / visits by last-billed carrier (Mass Rebill screen search)** | `POST /api/claim/massrebillsearch` `{carrierids:[id], begindateofservicestartdate, begindateofserviceenddate, rest null}`; `{}` = whole unpaid list | `build_money.py`, `claim_status_sweep.py` | 8/30, filters 9/7 |
| Mass Rebill button | **NOT captured** — ask William for the POST when he clicks Rebill | — | — |

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
| **AMD eligibility — WORKS (William re-pasted it 9/7/2026 from a prior chat; proven same night on Deas/Medicare and Tillman/Medicaid)** | `POST https://pm-api-103.advancedmd.com/api/eligibility/EligibilityDetailsLegacy/checkEligibility` headers `Content-Type: application/json`, `Authorization: Bearer <token>`; body `{"licensekey":"152563","username":"POI0712","patientinsurancecoverageid":"<numeric insplan id, no 'ins' prefix>","servicetypecode":"30"}`. Synchronous, ~200 ms: returns `<PPMDResults><Results eligibilityid eligibilitystatusid="1" patientname address subscriberid insuranceeffectivestartdate ...><Edi271>...` — the FULL 271 (EB segments, plan dates, other payers, address) and it stamps the eligibility date on the AMD insplan. No AAA = active. Helper: `amd.check_eligibility(insplan_id)`; parser: `elig_amd.py`. The XML gateway's `checkeligibility` and REST `/api/eligibility` root are NOT it. |
| Stedi eligibility | `POST https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3` (payer ids: 77027 Medicaid, 68069 Sunshine, 87726 UHC, 60054 Aetna, 61101 Humana, 95112 CHP, MBILUNOSSN Medicare by name/DOB, CMS = AAA 41 until HEET propagates) | `stedi.elig`, `stedi.mbi` | 9/5 |
| Stedi claim status | `.../change/medicalnetwork/claimstatus/v2` | `claim_status_sweep.status` | 9/5 |
| Stedi discovery | `.../insurance-discovery/check/v1` (enrollment still STEDI_ACTION_REQUIRED) | `stedi.disc`, `disc_run.py --check` | 9/6 |

## Master files (none work from the API)
No carrier read/write call exists (`getcarrierlist`, `getcarrier`, `lookupcarrier` → invalid action); no patient list/search call; carrier payer ids only visible as `payerinfo` on gettxhistory charges. Carrier setup = William in Master Files.
