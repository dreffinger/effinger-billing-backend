# captured_calls additions - backend billing run 2026-11-05T1839Z (ehpa cloud, 1:39 PM ET 11/5, six-hourly slot)

No new AdvancedMD or Stedi call shapes this run (every call used is already in the registry). Lessons only:

1. Pam's Brynwood admit photos (iPhone 640x480 JPEGs) defeat tesseract entirely at any upscale; reading the 3x upscaled crops visually (Read tool on the image) recovers every field. Keep the OCR attempt short and go to the visual read.
2. A chart whose CMS 271 lists a FL QMB Plan is not necessarily a dual today: the QMB entry carries its own date window (eb type QM, dates 290 = 20260501-20260731 on pat17470804) and Stedi's Florida Medicaid 271 (77027, name/DOB/gender, no member id) answers planStatus 6 Inactive at the DOS while still returning the Medicaid member id. Read the QMB window before adding a MCAD plan; an inactive answer = Medicare alone, cost-share WOCLTREQ by the 10/13 rule.
3. PCC admission records print the Humana Medicaid plan as "Primary Payer: MCD Humana / Ins. Company: Humana Medical Plan, Inc." with the Medicaid number, while the AMD HUM01 plan carries Humana's own H-member id; AMD's 271 on that plan answering "MEDICAID GATE CAP" confirms it is the same SMMC coverage - no plan change needed (pat20379, order 1,4 Medicare first).
4. run_all.py --mode live --steps columns,era with --stedi-proxy and the AMD_PSW environment credential is the whole engine pass (3.5 min) when nothing new is on the columns; the scan files land in scan_<stamp>/summary_{before,after}.json (inspector keyed by batch, exclusions keyed by claim run).
