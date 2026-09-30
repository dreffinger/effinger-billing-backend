# captured_calls additions - 2026-09-30 0310 UTC (11 PM ET 9/29 slot, ehpa cloud copy)

No new AMD call shapes this run. Calls exercised: login (one attempt, AMD_PSW environment credential, token cache only), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches + getclaiminspectorcharges (12 batches), getclaimunbillablecharges, getclaimrunstatus + getclaimexclusioncharges (79 runs), lookuppatient name wildcard, getdemographic, gettxhistory class=demographics, GET /api/era/checks (0).

Lessons recorded:
- `gettxhistory` is class="demographics" (with filterhistory/pagenumber/typefilter/... attrs as in txh.fetch); class="api" answers fault -2147219453 'Action gettxhistory not found' - a probe fault, never a relogin trigger (amd._expired ignores it).
- Drive large-file transport (three 1.3-1.9 MB scanned PDFs): download_file_content spills to the harness tool-results file; `jq -r .content <file> | base64 -d` reproduced all three byte-for-byte (sizes 1,283,955 / 1,940,209 / 1,940,209); ocr_pdf.py (pdftoppm + tesseract) read them - two 10-page copies of a discharge summary and a 5-page H&P. Clinical records in the facesheet folder carry no payer data: the run books them to the board (William's turn) instead of guessing.
- The Claims Center overview lagged again (exclusioncount 11 / $2,194 while the per-run list calls returned one exclusion row) - trust the list calls, as the standing rule says.
