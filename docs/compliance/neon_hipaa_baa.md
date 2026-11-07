# Neon (Databricks) HIPAA Business Associate Agreement - accepted 2026-11-06

- **Accepted by:** William Effinger (dreffinger@gmail.com) for Effinger Health PA, through the ehpa organization's settings in the Neon Console (Organization settings -> HIPAA support -> Enable -> "I have read and agree to the terms of Neon's Business Associate Agreement (BAA)"), 2026-11-07 04:43 UTC (11:43 PM ET 2026-11-06). The click-through was performed by Claude at William's instruction in his own Chrome session.
- **Parties:** Databricks, Inc. (parent of Neon, LLC) as Business Associate; Effinger Health PA as Customer / Covered Entity. The BAA supplements the Neon Product Specific Schedule (https://neon.com/platform-terms).
- **Organization:** ehpa (`org-sparkling-silence-16346164`), Scale plan. **Project flagged HIPAA:** ehpa-database (`steep-rain-79347575`, AWS us-east-1). Enabling HIPAA on a project is irreversible; disabling it for the organization needs a Neon support request after every HIPAA project is deleted.
- **Copy of the agreement:** `neon_databricks_baa_accepted_2026-11-06.pdf` beside this note (downloaded from https://neon.com/baa -> https://www.databricks.com/legal/neon-baa at acceptance). A countersigned copy can be requested at https://neon.com/baa/signed.
- **Cost:** HIPAA support is free today; Neon has announced a 15% surcharge on the monthly invoice once it starts charging, with advance notice.

## What Databricks promises (BAA sections)
- 3: uses and discloses PHI only as the BAA permits, the Agreement requires, or law requires; no de-identification or aggregate reports from the practice's PHI unless the practice asks.
- 5: commercially reasonable administrative, physical and technical safeguards per 45 CFR Part 164 Subpart C.
- 6.1-6.3: reports a Security Breach **within five business days** of becoming aware; supplements with the 45 CFR 164.410 details **no later than 60 calendar days** after discovery; mitigates harmful effects.
- 7: subcontractors bound to the same material level of protection.
- 8-10: makes PHI available for individuals' access/amendment rights, keeps what is needed for an accounting of disclosures, opens books to HHS when the law requires.
- 11-12: either party may terminate on an uncured material breach (30-day cure when a cure is possible); on termination Databricks returns or destroys PHI, or keeps protecting it where return is infeasible.

## What the practice promises (section 4 and the Neon HIPAA guide)
- Configure and use Neon in a HIPAA-compliant way; obtain any consents needed before storing PHI; never make PHI available to Databricks personnel outside the service (no PHI in support tickets, project names, metadata, table or column names, or SQL that ends up in audit logs such as `CREATE ROLE ... PASSWORD`).
- Keep PHI on the covered paths only: the Postgres wire protocol (port 5432) and the HTTPS SQL endpoint, never the PostgREST Data API (excluded from Neon's HIPAA coverage).
- Configure a session timeout for console users; audit-log access is by support request.
