Effinger feed import example (10/28/2026) - what is in this folder
(11/25/2026: this folder is the 10/28 example and is not kept up to date. The live helpers are in scripts/helpers/; since 11/25/2026 they choose a feed
 patient's chart by the identity rule of scripts/helpers/feed_identity.py - a patient the feed sends with a wrong birth date goes to the chart that patient
 already has - and the new-chart step makes a chart only where that rule says so.)

claimocity_in1_to_amd_carrier.csv  THE TABLE: every distinct IN1-4 payer name in the 10/16-10/27 files (100 names, 1,076 rows) -> the
                               AdvancedMD carrier code / carrier id / carrier name we map it to, and the action (addinsurance, SKIP for
                               liability / private pay / pending / coinsurance / therapy / vaccine-lab / Part D / hospice rows, or NO MAP ->
                               held for a facesheet). Member id = IN1-49 (Insured's ID number) - IN1-36 is empty in every row.
                               The mapping itself is the PAYER_MAP regex list at the top of claimocity_newcharts.py.
claimocity_dft_parser.py       step 1: folder of Claimocity DFT^P03 .hl7 files -> one JSON record per message (normalizes CR / LF / CRLF
                               segment terminators and splits messages on "MSH|", so both the pre-10/15 and the current format parse)
claimocity_newcharts.py        step 3 (only for feed patients with no AdvancedMD chart): addpatient from the PID segment (Claimocity patient id
                               kept as additionalmrn), updaterespparty to name the responsible party, then addinsurance for each IN1 payer that
                               maps to one of our carriers (payer name IN1-4 -> carrier code via the PAYER_MAP regexes, member id IN1-49; liability /
                               self-pay / Part D / vaccine / lab / hospice IN1 rows skipped; no group numbers - our rule)
add_ins.py                     the addinsurance helper the step above calls (begin date defaults to one year back so earlier visits can bill)
claimocity_import.py           step 4: per message, addvisit (empty visit) then updvisitwithnewcharges (one charge per FT1 line: CPT -> pcode id,
                               ICD codes -> dcode ids via lookupdiagcode codeset=10, facility/POS from MSH-4, provider profile from PV1-7 NPI,
                               modifier 25 on 99489/99497 add-ons, fee from our schedule), then updextrainsinfo for the admission date (PV1-44)
                               on hospital CPTs. Dedupe: a line whose chart already has a live charge with the same CPT + DOS is skipped.
amd_call_shapes_feed_import.txt the exact XML bodies of every AdvancedMD gateway call the scripts send, with the gotchas we hit
                               (diagcodes attr AND finclasscode required on new charges; insorder not allowed on a brand-new visit; addpatient
                               needs a unique chart number; address line 2 must repeat line 1; codeset="10" required for ICD-10 lookups).

Chart matching (feed_match / feed_resolve, not included - they are tied to our helper stack): lookuppatient "LAST, FIR%" and match on DOB;
several same-DOB charts -> the one with the most recent non-void charge; no chart -> step 3.
The amd / resave / txh helpers imported by these scripts are our thin wrappers around the gateway (login, post, read charge history);
they are not included - the call shapes file has everything they send.
