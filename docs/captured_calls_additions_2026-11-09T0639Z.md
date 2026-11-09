# captured_calls additions - run 2026-11-09T0639Z (1:39 AM ET Mon 11/9/2026, six-hourly columns slot, ehpa cloud)

No new AdvancedMD or Stedi call shapes this run (vocabulary +0). Lessons:

- A hospital-facesheet authorization written through the full-visit `updvisitwithnewcharges` echo (`preauth="..."` on the visit
  element) lands on the visit's REFERRAL PLAN (`<refplan ... preauth="...">` in getchargedetaildataicd10), not as a visit attribute -
  a readback that compares `visit@preauth` reports a false "verify failed"; read the refplan element instead (the 9/8 VA finding, now
  confirmed on an Aetna MA chart).
- `resave._extins_xml(vis, hospfrom)` on a feed-created visit whose detail shows an EMPTY `<extins />` did not persist
  `hospitalizationfrom` through `updvisitwithnewcharges` (readback still `<extins />`); the inspector pass's `updextrainsinfo` +
  full-visit resave is the path that writes the admission date on such visits.
- A chart the Claimocity feed creates can carry a wrong DOB (here 1929 for a 1949 patient); the HCA MedCity Visit Detail is the
  source - `patient_patch.patch(pid, {"dob": "YYYY-MM-DD"})` PATCH answered 200 and the demographic read back the new date.
- The quiet-slot shape stands: feed bucket 0 new -> one line; engine pass for the four columns + ERA; board file append-only.
