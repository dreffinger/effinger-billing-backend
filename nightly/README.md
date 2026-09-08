# Nightly back-end run

One scheduled task (Anthropic scheduled task, ~11 pm Eastern) starts a fresh Claude session with `nightly_task_prompt_v5.txt`. In English the run is: log in to AMD once; work the four Claims Center columns (Charge Review, Claim Inspector, Unbilled, Exclusions) with the scripts in `billing/claims_center`; post or dismiss everything in ERA Center (`billing/era`); for every denial ask what coverage really was in the lookup order patient database -> AMD eligibility -> Stedi -> facesheet -> William (`eligibility/`); rebill as an original claim or write off by the practice rules in `practices/<code>/rules.md`; refresh the boards (`boards/`); run the credentialing check (`credentialing/`); on Sundays rescan payments; then write the chat digest to Drive.

A second loop polls Stedi Insurance Discovery every 30 minutes (`eligibility/disc_run.py --check`) and runs discovery over the held board cards the moment the enrollment goes live.
