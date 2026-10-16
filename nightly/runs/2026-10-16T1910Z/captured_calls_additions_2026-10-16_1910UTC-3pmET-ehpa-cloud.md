# captured_calls additions - backend billing run 2026-10-16T1910Z (3 PM ET 10/16/2026, ehpa cloud, repo attached)

No new call shape this run (0 vocabulary entries). Observations for the registry:

- Read-only slot: getclaimcenteroverview / getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimrunstatus + getclaimexclusioncharges (1 open row, AET12 carrier hold), GET /api/era/checks (0 unposted before and after), getdemographic on the three zero-plan HCA charts (0 insplans), lookuppatient for the three 10/15 Pam admits (no chart). No AMD write.
- claim_status_sweep.py: the --skip-answered flag REQUIRES a comma-joined list of answered registers (a bare flag raises IndexError at a[a.index(...)+1]); the run passes every practices/ehpa/registers/uni20_bcbs_pre0501_sweep_*.json (210 files -> 585 visits skipped). Pass 118: 17 asked, 16 PENDING (chart 17472874) + 1 UNKNOWN (chart 17475632), 0 sent.
- Credential bootstrap: the direct heredoc write of .amd_cred.json was refused by the auto-mode classifier ([Credential Leakage]); tools/bootstrap/amd_cred_from_transcript.py (reads Gregg's thread from the session transcript, writes the file, prints length + hash only) is the sanctioned path - AMD_CRED_OK, one login, no lock.
