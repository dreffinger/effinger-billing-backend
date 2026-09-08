# Captured calls registry — AdvancedMD + Stedi

Every AMD/Stedi call learned from a DevTools paste, a Postman collection, or by
probing gets written here. **Not in this registry = not captured.** Ask for the
paste rather than guessing a call shape.

**Never store a bearer token, password, or license key in this file.**
Credentials live in `.amd_cred.json` / `secrets/` — both git-ignored.

Placeholders used below: `<LICENSEKEY>`, `<USERNAME>`, `<TOKEN>`.

---

## 0. Transport

| Style | Endpoint | Auth |
|---|---|---|
| XML / ppmdmsg | `https://PM-WFE-103.advancedmd.com/practicemanager/xmlrpc/processrequest.aspx` | usercontext token, `nocookie:1` |
| REST | `https://pm-api-103.advancedmd.com/api/...` | `Authorization: Bearer <TOKEN>` |
| Report engine | `https://reportingservices-103.advancedmd.com/rs/reportrequest.aspx` | same session token |

Both styles share one session token. ONE login attempt per run — a second
failed attempt locks the account. Auto-relogin reads `.amd_cred.json`.

Rate limit: Tier 2 = 12 requests/min peak (6am–6pm MT, Mon–Fri). Bulk sweeps
run off-peak (evenings/weekends).

A browser 401 on `api-100.advancedmd.com/api/locator/urls` means a stale
session — sign out and back in.

---

## 1. Eligibility — the free 271

**`POST https://pm-api-103.advancedmd.com/api/eligibility/EligibilityDetailsLegacy/checkEligibility`**

```
Content-Type: application/json
Authorization: Bearer <TOKEN>

{
  "licensekey": "<LICENSEKEY>",
  "username": "<USERNAME>",
  "patientinsurancecoverageid": "<numeric insplan id, no 'ins' prefix>",
  "servicetypecode": "30"
}
```

Synchronous (~0.2 s). Returns `<PPMDResults><Results eligibilityid
eligibilitystatusid patientname address subscriberid
insuranceeffectivestartdate><Edi271>...` — the FULL 271 — and stamps the
eligibility date on the AMD plan. Proven on Medicare, Medicaid, Sunshine, FCC.

Answers for **today only**.

Not this: the XML gateway's `checkeligibility` (fails "cannot create
PPMD_eligibility") and the REST `/api/eligibility` root (RBAC).

Lookup order: `patient_db` record → this call → Stedi → facesheet → human.
If AMD is down (401s in the UI), skip straight to Stedi.

---

## 2. Claims Center

### Board counts
`getclaimcenteroverview` class=claimsreports → `chargereviewcount`,
`claiminspectorcount`, `unbillablecount`, `exclusioncount` (+ amounts).

**The counts lag** (cached, refreshes on AMD's schedule). Truth is the list
calls: empty `getclaiminspectorbatches`, `totalcount` on
`getclaimunbillablecharges`, `totalcount` on `getclaimexclusionclaimruns`.

### Charge Review
- List: `getreviewcharges` class=chargeentry → visits with chargelist.
- Approve: `approvecharges` class=chargeentry `visits="id,id,..."`.

### Claim Inspector
- Batches: `getclaiminspectorbatches` class=chargeentry.
- Claims + errors: `getclaiminspectorcharges` class=chargeentry `batchid=<ID>`
  → visits (claimstatus ERROR/PENDING/CLEAN), errorlist (id, number, text).
  **Error ids change on every reinspection — always re-list first.**
- Bypass: `bypassclaimedits` class=chargeentry, child
  `<visitlist><visit id="<visitid>"><claimeditlist><claimedit id="<errid>"/>
  </claimeditlist></visit></visitlist>`.
  **Never bypass a missing-DATA error.**
- Hospitalization From Date (error 117065068): `updextrainsinfo`
  class=chargeentry `visitid="vst<ID>"` child
  `<extins txtChargeCode="<CPT>" hospitalizationfrom="MM/DD/YYYY"
  patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0"
  autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>`.
  Only clears when the claim is CMS-1500 (`onhcfa=1`); if `onhcfa=0`, also
  resave with `onhcfa=1`.

### Resave ("Complete")
`updvisitwithnewcharges` class=chargeentry — FULL charge echo from
`getchargedetaildataicd10`; skip void/payment-posted charges; echo all visit
attrs; `approval="1" inspectorenabled="1" getfinancials="-1"
customclaimfieldsavailable="1"`.

**Always fetch detail by CHARGE id.** `getchargedetaildataicd10 visitid=`
returns no charges for the newest visits.

### Unbilled
- List: `getclaimunbillablecharges` class=claimsreports
  `lowdate="" highdate="" carrier="" provider=""`.
  **Cached snapshot** — fixing the data does not remove a row; only the
  release does.
- Release: `hideunbillablevisits` class=claimsreports `hide="-1"` child
  `<visitlist><visit id="<visitid>"/>...</visitlist>` (many visits per call).
  **Never release a visit whose data is still broken — it just hides it.**

### Exclusions
- Runs: `getclaimexclusionclaimruns` class=claimsreports.
- List: `getclaimexclusioncharges` class=claimsreports `claimrunid=<ID>
  clearinghouse="1" payer="1"` — **both flags required** or it returns empty.
- Complete: `hideexclusions` class=claimsreports `claimrunid=<ID> hide="-1"`
  child `<visitlist><visit id="<visitid>" claimid="<claimid>"/></visitlist>`.

### Run alerts
`getclaimrunstatus` class=claimsreports `nocookie="1"` → alert-type
definitions + every flagged run (id, date, submitter, totalamount, totalsent,
totalexclusions, totaldroppedtopaper, exclusionreportid, alert flags).

Alert taxonomy: 1 = no clearinghouse report 4+ days · 2/3/6 = no insurance
payment 45+ days (run / carrier-in-run / carrier) · 4 = ≥5% claims excluded ·
5 = ≥7% dropped to paper.

### Archive / reporting
`getclaimrunhistory`, `getclaimruncarriers` (claimrunuid),
`geteclaimsreporttypes`, `geteclaimsreportlist` (`begindate enddate reporttext
titlefirst="1" getarchivedreports="0" reporttypeid="-1"`) — all
class=claimsreports.

### NOT captured
- **EDI Reports column** — no action name found by probing. `exclusionreportid`
  and `droppedtopaperreportid` resolve nowhere. Unlock by clicking the column
  in Chrome while capturing network requests.
- **Mass Rebill button POST** — rebill list-wise instead (see §4).

---

## 3. Demographics

- `getdemographic` class=demographics `patientid` → insplanlist / refplanlist /
  `<address>` / `<contactinfo>`.
- `gettxhistory` class=demographics `patientid filterhistory="0"
  pagenumber="1" typefilter="1" sortbypayment="false" groupbyvisit="0"
  sortdescending="1" visitid="0" getmemo="false"` → full charge history.
  Attributes are `insbal` / `patbal` / `paid` / `carrier` / `facname` /
  `payerinfo` — note `insbal`, **not** `insbalance`.
- REST read: `GET /api/demographic/patients/{id}` with
  `Accept: application/vnd.advancedmd.api.v2+json`.

### Insurance writes
`addinsurance` class=demographics:

```xml
<patient id="patNNN" changed="1">
  <insplanlist>
    <insplan id="" carrier="carNNN" subscriber="respNNN"
             subscribernum="<policy>" relationship="1" hipaarelationship="18"
             sequence="N" begindate="<1yr back>" enddate="" coverage="1"
             copay="0.00" copaytype="$" grpname="" grpnum=""/>
  </insplanlist>
</patient>
```

`updateinsurance` class=demographics needs the `o_<field>` originals:
`<insplan id="insNNN" <attrs> o_<attr>="original">` → `success="1"`.

**Standing rule: never send a group number.** `grpnum` and `grpname` stay
empty on every carrier, even when the card or facesheet shows one.

### Address write (PATCH)
`PATCH /api/demographic/patients/{id}` with
`Accept: application/vnd.advancedmd.api.v2+json`, body =
`updatedpatient` + `originalpatient` (flat shape) **plus**:

```json
"familyupdate": {
  "capturepreviousaddress": false,
  "responsiblepartyid": "<respparty>",
  "patientids": [0],
  "homephone": "<phone>",
  "newaddress": {
    "address1": "...", "address2": "", "zipcode": "...",
    "city": "...", "state": "...", "countrycode": "USA"
  }
}
```

The `familyupdate` block is what the UI's *Edit address* button adds. Without
it AMD answers "Address is required" (that was the bug in the earlier
`familyupdate: null` attempts). Verify with the GET afterwards.

Placeholder rule when a chart has no street address: line 1 = `HCA`
(hospital), `SNF` (nursing home), or `ALF` (ALF/home visit); city/state/zip =
the practice's.

---

## 4. Carrier-wide searches

- `POST /api/masswriteoff/masswriteoffsearch`
  `{"carrierids":[<numeric car id>], "isinsbalance":true,
  "billstartdate":"YYYY-MM-DD", "billenddate":"YYYY-MM-DD", <every other key
  null>}` → `{chargedetails:[{patientid, visitid, chargedetailid,
  dateofservice, insbalance, carriercode, carriername, lastpaymentdate}],
  totalchargecount}` = every open insurance balance on that carrier,
  secondaries included. `isinsbalance:false` = patient balances.
  **The fastest way to scope any payer.**
- `POST /api/claim/massrebillsearch`
  `{"carrierids":[id], "begindateofservicestartdate":...,
  "begindateofserviceenddate":..., <rest null>}` → visits by the carrier they
  were LAST BILLED to (empty for secondaries billed to Medicare).
  `{}` = the whole unpaid list.

---

## 5. Rebilling — always an original claim

1. Reset the corrected-claim flag per charge: `updextrainsinfo`
   `resubmissioncode="1" origrefnum=""`.
2. `POST /api/claim/chargerebill`
   `{chargedetailfid, sequencenumber: <first insorder digit>,
   rebillentireclaim: true}` → expect **204**.
3. Verify `insbilled=0` + a rebill record.

**Never frequency 7** unless handed the payer ICN.

---

## 6. ERA Center

| Call | Shape |
|---|---|
| `GET /api/era/checks` | unposted only |
| `GET /api/era/checkdetails` | check detail |
| Post button | `posterapayments` class=autoremitreports, JSON ppmdmsg to the wfe gateway |
| Process Accepted ($0.00) | same with all amounts 0 |
| `POST /api/era/checks/dismiss` | body = JSON string of the check id |
| `GET /api/era/checks/dismiss?DismissedDateBegin=YYYY-MM-DD` | list dismissed |
| `POST /api/era/checks/reversedismiss` | body `[{"id":<checkid>,"dismissedat":"<value>"}]` |
| `POST /api/era/locks/release-expired` | release stuck locks |

**On an unvalidated ERA line, post the PAYMENT line — never the $0 denial
line.**

---

## 7. Payments / voids

- `addpayments` class=paymententry — manual post
  (`cid, carrier, pay, wo, wocode, checknumber, depositdate, note`).
- Void write-off / void payment by `(pid, cid, woid|payid)`.
- A voided write-off can land on the patient balance → move it back to
  insurance before re-posting.

---

## 8. Master files / facilities

- **No carrier read/write call exists.** `getcarrierlist`, `getcarrier`,
  `lookupcarrier` all return "invalid action". Carrier setup is manual in the
  AMD UI. The `payerinfo` attribute on `gettxhistory` charges
  (e.g. "Payor ID: NNNN") is the only window onto a carrier's payer id.
- No patient list/search call. Lookups use `%wildcard%`.
- `selectfacilities` class=masterfiles → uid/facilityname map.
  The visit attr `facility="facNN"` says where the patient was seen — use it
  to route facesheet lookups.

---

## 9. Report Center

- SPA URL pattern:
  `https://static-100.advancedmd.com/practicemanager/reportcenter/#/main/FinancialTotals/<reportid>`
  (573 = Transaction Detail).
- The SPA posts ppmdmsg JSON (`@class:"reports"`, e.g. action
  `updaterecentreports`, `reportid`) to the wfe gateway with `nocookie:1`.
- Results render inside an iframe (`reportselectionform.htm`) — the page shell
  alone does not contain them.
- **Always narrow carriers.** An all-carrier Transaction Detail ran >10 min
  and never finished.
- Run payload not yet captured: install an XHR interceptor on both the parent
  window and the iframe *before* clicking Run Report, then replay from the
  backend. Sanitize usercontext tokens before echoing anything.

---

## 10. Stedi (eligibility / discovery)

Base: `https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/`
Header: `Authorization: <key>` (key lives in `secrets/`, never in this repo).

| Call | Path |
|---|---|
| Eligibility | `POST .../eligibility/v3` |
| Insurance discovery | `POST .../insurance-discovery/check/v1` (billable per check) |
| Payer search | `GET .../payers/search?query=` |
| Enrollments | `https://enrollments.us.stedi.com/2024-09-01/{providers,enrollments,tasks/{id}}` |

Eligibility body: `tradingPartnerServiceId`, `provider {organizationName, npi}`,
`subscriber {firstName, lastName, dateOfBirth (yyyymmdd), memberId | ssn |
address.state}`, `encounter {dateOfService, serviceTypeCodes: ["30"]}`.

Working payer ids: Medicare MBI lookup `MBILU` (with SSN) / `MBILUNOSSN`
(state) · direct Medicare `CMS` · UHC 87726 · Humana 61101 · Aetna 60054 ·
Cigna 62308 · Cigna/HealthSpring MA 63092 · Centene (Sunshine/WellCare/
Ambetter) 68069 · Simply `SMPLY` · CHP 95112 · Florida Blue `BCBSF` ·
FL Medicaid 77027 · TRICARE East 99727 · VA CCN `VACCN`.

Not available: Florida Community Care (portal only), Railroad Medicare
(enrollment pending).

**Network note:** the cloud container cannot reach `healthcare.us.stedi.com`
(egress 403). Until the host is allowlisted, these run from the browser via
the bridge helper.

The MBI lookup returns the whole Medicare picture for a date of service:
Part A/B dates, Medicare Advantage plan (codes U/R with entity name and
coordination-of-benefits dates), Part D (R/OT = drug plan only → original
Medicare), QMB/Medicaid, SNF stays (X), hospice (service type 45), and
`planDateInformation.dateOfDeath`. Error 72 = not a Medicare beneficiary.

---

## Appendix — reference ids

Carrier ids (AMD internal):

| Code | Carrier | id |
|---|---|---|
| FLO02 | Florida Medicare | car6085 |
| MCAD | Florida Medicaid | car6113 |
| BCBS | Florida Blue (incl. HIX, out-of-state Blues) | car6062 |
| UHCMA | UnitedHealthcare Dual Complete | car302853 |
| UNI20 | United Healthcare | car6404 |
| HUM01 | Humana | car6285 |
| TRI00 | TRICARE East | car6872 |
| SUN01 | Sunshine | car6194 |
| CAP07 | — | car41826 |
| FLO99 | Florida Community Care (LTC, custodial) | car42008 |
| AET12 | Aetna Senior Supplemental (Medigap) | car42009 |

**AET12 ≠ AET07.** AET12 is Aetna Senior Supplemental (Medigap, payer 62118).
AET07 is Aetna commercial/MA (CPID 6400). Different companies — never merge.

Diagnosis code ids seen in charge detail:

| Code | Meaning | dcode |
|---|---|---|
| I63.9 | Acute ischemic stroke | dcode1034545006 |
| I69.30 | Unspecified sequelae of cerebral infarction | dcode1034545425 |
| M86.9 | Osteomyelitis, unspecified | dcode1034545415 |

Procedure code ids: 99349 = `pcode65142`.

**Modifier ids are not modifier codes.** Modifier 25 = `mcode7`. Writing
`modcodes="25"` is read as `mcode25` = modifier 78. Verify with the
`<modcode ... code="25">` element in `getchargedetaildataicd10`.
