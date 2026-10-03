# captured_calls additions - run 2026-10-03T0110Z (9 PM ET 10/2, ehpa cloud)

No new AMD call shapes this run (read-only verification pass: columns_scan.py, GET /api/era/checks, GET /api/era/checkdetails?checkid=1052906, getdemographic on the 11 Unbilled 'insurance order' charts + pat17477953, gettxhistory typefilter=0 on pat17477953, lookuppatient x4 for the 9/30 admits). Lessons recorded:

- Pam's admit emails can repeat: the 10/2 23:11Z 'PATIENT969 BUTTERMERE / NA BW' photo is the same PCC Clinical Resident Profile the 10/1 15:11Z email carried (NA = new admit, BW = Brynwood). Before any cascade, re-read the chart (getdemographic) - if the plan from the earlier run is there and eligibility-verified, the re-sent sheet changes nothing.
- A 640x480 phone photo of a PCC screen can misread one digit of a 9-digit UHC member id after upscaling; an id that AMD/Stedi eligibility already answered ACTIVE on outranks the photo read - never rewrite a verified member id from a low-resolution photo.
- Four 9/30 Pam admits: WILBOURNE,PATIENT339% now resolves to one chart (pat17477966, created by the feed 10/2); THORNEY,[first]% / TRENT,[first]% / HARLOW,[first]% still return no chart.
