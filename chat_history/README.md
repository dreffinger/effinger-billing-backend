# Run digests are not kept here

A run digest names patients. Its only home is Google Drive, folder "chat history" - every run uploads its digest there.

From 11/13/2026 to 11/25/2026 the six-hourly billing run wrote its digest into this folder of the repository clone and committed
it as "run <stamp> digest" - past the privacy gate, which only sees the mirror's own commit. Thirty digests reached GitHub that
way, nine of them with a patient name or a board card id. They were removed from the repository on 11/25/2026 (each has its copy
in Drive "chat history"); they are still in the repository's HISTORY until that is rewritten or the repository is private.

Everything in this folder except this file is git-ignored, so a digest cannot be added again by mistake.
