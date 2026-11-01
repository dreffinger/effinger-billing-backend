# captured_calls additions - backend billing run 2026-11-01T0641Z (1:41 AM ET 11/1, ehpa cloud, columns task v7)

No new AMD or Stedi call shapes this run. Calls used (all already in the registry / docs/api_vocabulary.json): login (one, inside tools/button/run_all.py), getclaimcenteroverview, getclaiminspectorbatches/getclaiminspectorcharges, getclaimunbillablecharges, getclaimrunstatus/getclaimexclusioncharges, GET /api/era/checks, posterapayments (Post button, nothing to post), GCS bucket listing (claimocity_gcs.py), lookupdiagcode codeset=10 (claimocity_retry_dx.py). Vocabulary entries added: 0.

Lesson re-confirmed (fresh container): the GCS key install needs cffi for THIS interpreter - `python3 -m pip install cffi` (a bare `pip install` lands in Python 3.13 and the cryptography import panics 'Python API call failed').
