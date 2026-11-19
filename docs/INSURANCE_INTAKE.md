# Insurance intake - where each plan comes from and what is checked before a claim goes out (11/19/2026)

William 11/19/2026: "optimize getting the correct insurances for billing on the back end using apis first".

## What the comparison of the whole feed showed (31 files, 1,425 charge messages)

- 717 messages carry an insurance block; 662 carry a usable medical plan with a member number (the rest are patient liability,
  coinsurance rows, pending, vaccine / therapy rows, dental).
- By kind of visit: nursing facility 88% with insurance, hospital 21%, care management 12%, home / assisted living 0%.
- Of 376 usable blocks on 172 charts: 230 were on the chart, 43 on the chart with a different number, 74 never reached the chart,
  29 had a payer name no table knew.
- Cause of the 74: the import entered feed insurance only when it CREATED a chart. Nearly all were the Medicaid side of a
  nursing-home resident and a few Medigap plans.

## What changed 11/19/2026

| Piece | Change |
|---|---|
| `feed_payer_map.py` | ONE payer-name table for every feed helper. Unknown names 29 -> 13 (what is left: blank names and long-term-care plans AdvancedMD has no carrier for). Fixed: 'AARP UHC Medicare Supplement' is the AARP Medigap plan, 'Medicaid ... Florida Community' is Florida Community Care. |
| `feed_in1_intake.py` | New feed step (c3): existing charts get the Medicaid side and the Medigap / TRICARE For Life plans the feed carries. First run: 17 Medicaid plans and 3 Medigap plans added on 19 charts, each put last in the chart's order. |
| `stedi.disc_summ` | A dental / vision / life look-up hit is marked not medical everywhere it is read. |
| `adt_ingest.py` | Reads every insurance block of a feed message or an admission notice. |
| `stedi_cob.py` | Stedi's coordination-of-benefits check, stand-alone. |
| `availity.py` | Availity client, waiting for the credential (docs/TODO_DATA_SOURCES.md). |

## The order of sources (cheapest and most certain first)

1. **The chart** (free): a plan already there with a payment on file is trusted.
2. **The feed's insurance block** (free): primary plans inform, they are not entered on an existing chart; Medicaid and secondary
   plans go through step 4 or 5.
3. **AdvancedMD's own eligibility check** (free): today's status of every plan on the chart; Medicare's answer names the Advantage
   plan, the Medigap company and the drug plan; Medicaid's answer names the managed plan.
4. **Florida Medicaid through Stedi** (ordinary eligibility price): the state's answer decides whether Medicaid is active and WHICH
   managed plan to bill - it wins over the feed's wording.
5. **The payer through Stedi, dated to the visit** (ordinary eligibility price): required before a never-billed visit is sent on a
   plan that came from a look-up; not needed when the plan already paid a visit of the same stay.
6. **Medicare look-up through Stedi** (look-up price): when the chart has no Medicare number; with the SSN when the feed carries
   one (289 feed patients do) - it is the cheaper, surer form.
7. **Insurance discovery** (the dearest call): only when nothing above names a payer; dental / vision / life hits are ignored.
8. **Availity** (once the credential exists): Florida Blue and Humana by name and birth date, and claim status.
9. **A person**: a facesheet or card, asked for on the board with the trail.

## What a claim needs before it goes out

| Situation | Check |
|---|---|
| Plan already paid a visit of this stay | none |
| Plan from the feed's block or a facesheet, verified active by AdvancedMD's free check | none more |
| Plan found only by a look-up | a Stedi eligibility check dated to the visit |
| Medicare names another primary plan on that date | that plan's member number first; never sent to Medicare |
| Medicaid as secondary | the state's answer for the managed plan (step 4) |

## Secondaries

- Medicare's own answer lists the Medigap company and the Medicaid status - that is where most secondaries are found, at no extra cost.
- Stedi's coordination-of-benefits check was tried 11/19/2026 on a Florida Blue member who also has Medicare: it answered 'no other
  coverage'. It does not know Medicare, so it finds a second COMMERCIAL plan only. It costs about a dollar a call; worth asking only
  for a working-age hospital patient with a commercial plan.
- A commercial payer's eligibility answer often lists the other payer (the Federal plan's answer named the member's Medicare plan as
  secondary on 11/19).

## Capital Health Plan member numbers

Tested 11/19/2026 on two charts whose CHP number is known: CHP's eligibility answers error 72 to name + birth date + SSN and to name +
birth date alone. It answers only to its own member number. Medicare names CHP as the plan but never gives the number. Discovery
does not return CHP. The feed carried no CHP block for the three charts that needed one, and no other chart of ours held one.

What can supply the number, in order:
1. The hospital facesheet through Claimocity (hospital messages carry insurance only 21% of the time - docs/TODO_DATA_SOURCES.md, 1).
2. The state exchange's admission notices, if they carry insurance (docs/TODO_DATA_SOURCES.md, 3).
3. A CHP number printed without its letters verifies with the CIO prefix (Medicare plans) - tried before asking.
4. The CHP provider portal, by a person, for what is left.
