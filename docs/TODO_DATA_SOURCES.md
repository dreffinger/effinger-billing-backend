# To do - insurance data sources (written 11/19/2026 for William)

Why: on 11/19/2026 about 20 charts were insured by hand from pasted facesheets. Every member number was already on a
facesheet or at a payer. These steps get that data to the back end without typing.

Status key: **YOU** = only William can do it (accounts, signatures). **BUILT** = code is on main. **NEXT** = Claude does it
once the step above it is done.

## 1. Claimocity feed - insurance is there, but not for hospital patients

Checked 11/19/2026 on six feed files (298 charge messages):

| Kind of visit | Messages | With an insurance block |
|---|---|---|
| Nursing facility (9930x / 9931x) | 85 | 75 (88%) |
| Hospital (9922x / 9923x) | 175 | 38 (21%) |
| Care management (99487) | 33 | 4 (12%) |
| Home / assisted living (9934x) | 5 | 0 |

So the insurance segment is still in the feed for the nursing homes. The gap is the hospital census: four of five hospital
messages arrive with no insurance.

- [ ] **YOU** Ask Claimocity support: "Our DFT charge messages for HCA Florida Capital Hospital and TMH patients arrive
      without IN1 segments (about 80% of them). Nursing-facility patients carry IN1. Please send IN1 (company name, member
      number in IN1-36, plan dates) for every patient whose facesheet is in Claimocity, and confirm where the hospital
      insurance comes from (facesheet upload, census import, or typed)."
- [ ] **YOU** If Claimocity only has what is typed or uploaded: upload the HCA / TMH facesheet when the patient is added to
      the census - the member number then rides the feed.
- [x] **BUILT** `scripts/helpers/adt_ingest.py` reads every insurance block of a feed or admission message and marks the ones
      that are not a medical payer (patient liability, coinsurance rows, pending, dental, vision, life).

## 2. Availity API - Florida Blue and Humana eligibility and claim status

- [ ] **YOU** 1. Go to https://developer.availity.com/partner and choose Create account (email, name, password, emailed
      code, authenticator app). This is separate from the Availity Essentials login.
- [ ] **YOU** 2. Dashboard > My Org/Users > create the organization (Effinger Health PA, tax id, the Availity Essentials
      administrator's details).
- [ ] **YOU** 3. My Apps > create an application. Availity shows a **client id** and a **client secret**. The secret is
      shown once - copy both.
- [ ] **YOU** 4. API Products > the HIPAA transactions product (Coverages / Claim Statuses) > Access this Product > plan
      **Demo** > pick the application > submit. Demo is approved automatically, costs nothing and returns canned answers.
- [ ] **YOU** 5. Put the client id and secret where the runs can read them: claude.ai > the ehpa cloud environment >
      environment variables `AVAILITY_CLIENT_ID` and `AVAILITY_CLIENT_SECRET` (plus `AVAILITY_SCOPE` if the product page
      lists scopes). Never in a chat, an email to anyone else, or the repository.
- [ ] **NEXT** 6. Claude runs `python3 availity.py token` and one Demo eligibility call, corrects the parameter table in
      `availity.py` against the product specification, and records the call.
- [ ] **YOU** 7. Request the **Standard** plan (live data) on the same product page, then https://www.availity.com/contact-sales/
      - Availity's Trading Partner Management sets up a contract before it approves. Ask for the price per transaction
      for a provider organization; it is not published.
- [ ] **NEXT** 8. Once Standard is approved: Availity becomes the first source for Florida Blue and Humana in the insurance
      cascade (eligibility by name and birth date, claim status with the payer's claim number for corrected claims).
- [x] **BUILT** `scripts/helpers/availity.py` (token, eligibility, claim status, polling, usage log, Demo switch). The API
      host is already reachable from the cloud environment.

Limits from Availity's guide: Demo 5 calls a second / 500 a day; Standard 100 a second / 100,000 a day; a token lasts 5
minutes.

## 3. Florida's health information exchange - admission notices (Encounter Notification Service)

What it is: hospitals send their admission / discharge / transfer messages to the state service; it matches them to a
subscriber's patient list and sends a notice (HL7 message or CSV; by SFTP, Direct message or a web screen).

- [ ] **YOU** 1. Email flhie_info@ainq.com (the service's operator) and FLHII@ahca.myflorida.com: "Effinger Health PA
      (NPI 1629515325), a physician group rounding in Tallahassee hospitals and nursing facilities, wants to subscribe to
      the Encounter Notification Service. Please send the subscriber onboarding packet, the subscription agreement and the
      fee schedule." Ask three things: (a) is delivery by SFTP as raw HL7 ADT available, (b) do the notices carry the
      insurance segments (IN1) or only the encounter, (c) are HCA Florida Capital and Tallahassee Memorial data sources.
- [ ] **YOU** 2. Sign the subscription agreement. Older program material says the subscriber must be authorized for every
      patient on its list - confirm the current wording.
- [ ] **YOU** 3. Choose SFTP + HL7 delivery and send Claude the SFTP host name (the cloud environment needs it on its
      network list; the key goes in as an environment credential).
- [ ] **NEXT** 4. Claude builds the nightly patient list (every chart with a visit in the last 90 days: name, birth date,
      sex, address - the fields the service matches on) and the upload.
- [ ] **NEXT** 5. Claude wires the pull: new notices -> `adt_ingest.py` -> the practice database (Neon) -> the insurance
      cascade: a notice with a usable plan and member number is checked for eligibility and offered for the chart; a new
      admission with no chart is listed for the feed.
- [x] **BUILT** the reader (`adt_ingest.py`, self-tested).

Unknown until they answer: whether the notices include insurance. If they carry only the encounter, the service still tells
the run WHERE the patient was admitted and when, and the member number still has to come from Claimocity, Availity or the
facility.

## 4. Federal Medicare sources

- Medicare's eligibility system (HETS) is the federal source for coverage, and the runs already use it through Stedi: it
  names the Medicare Advantage plan but never gives that plan's member number.
- CMS's claims-data interfaces (Blue Button for patients, the Beneficiary Claims Data API for ACOs, Data at the Point of
  Care for fee-for-service providers) return CLAIMS history, not member numbers, and each has its own enrollment. Not a fix
  for the CHP problem.
- The national exchange networks (TEFCA, Carequality, CommonWell) can return facesheet-type documents, but a practice joins
  them through its EHR vendor or a network on-ramp company.
- [ ] **YOU** Ask AdvancedMD support whether the practice's AdvancedMD is connected to Carequality / CommonWell, and
      whether patient documents retrieved that way are reachable through the API.

## 5. Capital Health Plan

No public API found. Options, in order: member numbers from the feed (section 1), admission notices (section 3), and for
the remainder a lookup on William's own computer through the CHP provider portal, started by him per patient.
