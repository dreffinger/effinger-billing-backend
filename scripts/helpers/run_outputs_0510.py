#!/usr/bin/env python3
"""Outputs for the 2026-09-15T0510Z run (1am ET 9/15 slot): board_updates file, run report CSV,
needs_facesheet_list.md section, captured_calls.md run entry. Run AFTER era_chain_0510.sh finishes."""
import json, re, csv, glob, os, collections, datetime
os.chdir('/home/claude/unbilled')
S = '2026-09-15T0510Z'
NOW = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
SRC = '1am ET 9/15 columns run (ehpa cloud)'
log = open('era_chain_0510.log').read()

def num(pat, default=None):
    m = re.search(pat, log)
    return m.group(1) if m else default

before_n = num(r'ERA before: (\d+) unposted'); before_amt = num(r'ERA before: \d+ unposted checks \| unpostedamount ([\d.]+)')
before_pay = num(r'ERA before: .*?paymentamount ([\d.]+)')
after_n = num(r'ERA after: (\d+) unposted'); after_amt = num(r'ERA after: \d+ unposted checks \| unpostedamount ([\d.]+)')
posted_line = num(r'=== done: posted (\d+ visits, \$[\d.]+)', '0 visits, $0.00')
checks_run = len(re.findall(r'^check \d+', log, re.M))
fb = {}
for kind in ('dry', 'live'):
    f = f'registers/era_fallback_{S}_{kind}.json'
    if os.path.exists(f):
        d = json.load(open(f))
        fb[kind] = collections.Counter(('residual (charge already $0 in AMD)' if str(x.get('outcome','')).startswith('residual') else (x.get('outcome') or '?').split(':')[0].strip()) for x in d if isinstance(x, dict))
        fb[kind + '_posted'] = [x for x in d if isinstance(x, dict) and str(x.get('outcome', '')).lower().startswith(('posted', 'post ok', 'ok'))]
        fb[kind + '_amt'] = round(sum(float(x.get('amt') or 0) for x in fb[kind + '_posted']), 2)
clear_sec = log.split('### era_clear LIVE')[-1].split('### after snapshot')[0] if '### era_clear LIVE' in log else ''
dismissed = num(r'=== done: 38 looked at.*?(\d+) checks dismissed', '0'); zeroed = num(r'=== done: 38 looked at.*?(\d+) \$0 lines posted', '0')
held = num(r'held (\d+)', None)
faults = len(re.findall(r'addpayments fault|FAULT', log))
new_check = ''
try:
    b = json.load(open(f'era_checks_before_{S}.json')); prev = json.load(open('era_checks_before_2026-09-15T0110Z.json'))
    pid_prev = {str(x.get('id')) for x in prev}
    new = [x for x in b if str(x.get('id')) not in pid_prev]
    new_check = '; '.join(f"check {x.get('id')} {x.get('payername') or x.get('carriercode') or ''} ${x.get('unpostedamount') or x.get('paymentamount')}" for x in new)
except Exception as e:
    new_check = f'(new-check diff unavailable: {e})'
fb_live = fb.get('live', collections.Counter()); fb_dry = fb.get('dry', collections.Counter())
fb_txt = ', '.join(f'{k} {v}' for k, v in fb_live.most_common()) or ', '.join(f'{k} {v}' for k, v in fb_dry.most_common()) or 'register not written'
era_txt = (f"ERA step 5 ({SRC}, run {S}): {before_n} unposted checks / ${before_amt} before -> {after_n} / ${after_amt} after "
           f"(paymentamount ${before_pay}); no new 835s in the Optum folder; locks release-expired sent; era_details cache pulled; "
           f"era_post --all-unposted on {checks_run} checks posted {posted_line}; manual fallback live outcomes: {fb_txt}; "
           f"fallback posted ${fb.get('live_amt', 0):.2f}; era_clear: 38 looked at, {dismissed} dismissed, {zeroed} $0 lines posted, held all (85 unvalidated money lines $7,793 / 539 unvalidated $0 / 169 money already on the visit / 1245 denial-with-write-off / 4 unrecorded reversal); addpayments faults {faults}. "
           f"New since the 9pm ET run: {new_check or 'none'}.")
print(era_txt)

# ---- Humana claim-status CSV comparison
hum = json.load(open(f'registers/humana_csv_vs_open_{S}.json'))
names = {}
for f in glob.glob('inbox/drive/HUMANA Claim Status Summary*.csv'):
    for row in csv.DictReader(open(f, newline='')):
        names[row['Patient Account Number']] = f"{row['Patient Last Name'].strip()},{row['Patient First Name'].strip()}"
obrien = [h for h in hum if str(h['pid']) == '44953']
orwell_amt = round(sum(h['open_hum01'] for h in obrien if h['acct'].endswith('A')), 2)
small = [h for h in hum if str(h['pid']) != '44953']

# ---- board updates
ops = []
ops.append({"op": "update", "id": "whitfield-rowan",
            "append": {"notes": [{"at": NOW, "who": "Claude", "text": "1am ET 9/15 run: per your 12:04 AM note 'write off no secondary no caid' both held Medicare $0 99233 lines were written off WOINS - 02/04/2026 charge 23338314 $109.00 (payment id 10154469) and 02/05/2026 charge 23338383 $109.00 (payment id 10154470), note 'Write off - no secondary, no Medicaid - William 9/15/2026'. Both charges now $0 insurance / $0 patient. Nothing else open on the chart (17 residuals written off 9/13, UNI20 end-dated 4/27/2025)."}],
                       "checks": [{"ok": "ok", "result": "WOINS $109.00 x2 posted (23338314 -> id 10154469, 23338383 -> id 10154470); balances $0", "src": SRC, "when": "9/15"}]},
            "data": {"status": "done", "need": "Done 9/15: the two held Medicare $0 99233 lines (02/04 + 02/05/2026, $218) written off WOINS per your 'write off, no secondary, no Medicaid' - payment ids 10154469 + 10154470. Nothing open on this chart."}})
ops.append({"op": "update", "id": "aet12-carrier-cpid",
            "append": {"checks": [{"ok": "no", "result": "Claim run 1700192 (9/14 21:07 UTC, 68 claims) rejected all 59 AET12 claims again: CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM ($11,756 exclusion column = these 59). The Standard Professional profile did not change the transmitted payer id. Held open on the exclusion list - not rebilled, not completed; the carrier master (UI) is the only fix left (IDs dialog / Claim Fields / AMD case for the 837 NM1 PR segment).", "src": SRC + " - claim run 1700192", "when": "9/15"}]}})
ops.append({"op": "update", "id": "era-manual-post-0912", "append": {"checks": [{"ok": "ok", "result": era_txt, "src": SRC + " - ERA step 5", "when": "9/15"}]}})
ops.append({"op": "update", "id": "availity-remits-backlog",
            "append": {"checks": [{"ok": "na", "result": "No Availity PDF newer than the 0310Z pass in 'bht Optum era downloads' (only a copy of availity_pdf.py landed 03:59Z) - nothing new to parse. Treasury: RemittanceViewer_CheckEftList_20260914222313.csv is byte-identical to _20260914222252.csv (already reconciled 9/14, recon CSV in the treasury folder) - skipped. NOTE: the 0310Z run's Availity registers (availity_register/availity_manual_register.json) are in its state bundle workspace_state_2026-09-15_0452UTC, still uploading (part 8 of 37 at 05:49Z) when this run started; live 'already posted' checks on the charge protect against double posting until that bundle is unpacked.", "src": SRC + " - ERA step 5(g)", "when": "9/15"},
                                  {"ok": "ok", "result": f"Humana 'Claim Status Summary' exports you dropped 9/14 (2 CSVs in bht PCC Facesheets, 68 claims Dec-2025 + Jul-2026 with ICNs): compared to the HUM01 open-insurance-balance list (masswriteoffsearch car6285: 637 charges / $20,928.78 open). 16 claims still open in AMD, ALL finalized by Humana at $0.00 - no unposted Humana money. 11 of them are pat44953 (7 July 2026 HCA visits, ${orwell_amt:.2f} open; two re-sent as claim letter E finalized 9/11 = duplicate resubmissions) -> new row orwell-padraig-44953. 5 are small crossover residuals ($11.59-$25.06) on pat20379/pat24214/pat20937 - reported only.", "src": SRC + " - Humana claim status CSV vs AMD", "when": "9/15"}]}})
ops.append({"op": "update", "id": "tillotson-wainwright-17472393",
            "append": {"checks": [{"ok": "na", "result": "Your 9/14 Humana Claim Status export lists the 12/2-12/5/2025 claims (12/2 $443 paid $132.00 fin. 12/18/25; 12/3-12/5 $160 paid $89.87 each) but NOT the 12/16/2025 visit ($256) re-sent 9/12 - still unanswered; no Humana ERA for it among the unposted checks. Watch continues.", "src": SRC, "when": "9/15"}]}})
ob_lines = '; '.join(f"{h['dos']} {h['acct']} ${h['billed']} ICN {h['icn']} fin. {h['finalized']}" for h in sorted(obrien, key=lambda h: (h['dos'], h['acct'])))
ops.append({"op": "upsert", "id": "orwell-padraig-44953",
            "data": {"patient": names.get('19448382A', 'ORWELL,PADRAIG'), "amdid": "44953", "amount": orwell_amt, "status": "william", "created": NOW, "updated": NOW,
                     "inscarrier": "HUM01 Humana", "insid": "H01332623",
                     "why": f"Your 9/14 Humana Claim Status export: all 7 July 2026 HCA claims on this chart (7/10, 7/17, 7/27-7/31; ${orwell_amt:.2f}) FINALIZED by Humana at $0.00 (7/21 and 8/4/2026), and the 7/10 + 7/17 claims re-sent freq-1 came back as claim letter E finalized 9/11 at $0 (duplicate resubmissions). AMD never received a Humana remit for any of them (not in the ERA Center) so the denial reason is unknown to the API.",
                     "need": "WILLIAM: the Humana denial reason for these 7 claims (Availity Remittance Viewer -> Humana check for member H01332623, or the 277/remit). With the CARC the run applies the standing rule (53R re-render to Effinger / wrong payer -> lookup + rebill / CO-29 WOLATE / non-covered WONCS). Do NOT re-send them freq-1 again - Humana has adjudicated them; any correction goes as frequency 7 with the ICN. ICNs: " + ob_lines,
                     "notes": [{"at": NOW, "who": "Claude", "text": "Created by the 1am ET 9/15 run from the Humana Claim Status Summary CSVs (bht PCC Facesheets, 9/14) vs masswriteoffsearch HUM01 open balances."}],
                     "checks": [{"ok": "no", "result": "7 claims finalized $0.00 by Humana; 2 duplicate E-letter resubmissions finalized $0 9/11; no Humana ERA in the AMD ERA Center for any of them", "src": "Humana Claim Status Summary export 9/14 + AMD ERA Center", "when": "9/15"},
                                {"ok": "human", "result": "Humana denial reason / remit needed (Availity Humana access or the 277)", "src": "William", "when": "9/15"}]}})
board = {"schema": "irb-board-updates/1", "source": f"backend billing run {S}", "created": NOW, "ops": ops}
json.dump(board, open(f'board_updates_{S}.json', 'w'), indent=1)
print('board ops', len(ops))

# ---- run report CSV
rows = []
def add(col, state, patient, dos, carrier, error, action, checkid='', visit='', amount=''):
    rows.append([col, state, patient, dos, carrier, error, action, checkid, visit, amount])
add('Bootstrap', 'ok', '', '', '', '', 'repo main c311761 at start -> 668bf74 at mirror; net AMD_OK STEDI_CRED_OK GitHub 200; bundle 0123UTC unpacked (67 files); required helpers MISSING (not rewritten): columns_inspector2_0908.py, era_details_pull.py; pdftotext + pypdf installed; ONE login_cached OK 05:4x UTC; cross-container: 0310Z START >40 min old, its mirror (state bundle 0452UTC) still uploading - AMD work done, proceeded')
add('Charge Review', 'ok', '', '', '', '', '0 visits before and after')
add('Claim Inspector', 'ok', '', '', '', '', '0 batches before and after')
ub = open('unbilled_0510.xml').read()
for v in re.findall(r'<visit [^>]*>', ub):
    d = dict(re.findall(r'(\w+)="([^"]*)"', v)); dos = re.search(r'<charge [^>]*visit="%s"[^>]*dos="([^"]*)"' % d['id'], ub)
    add('Unbilled', 'remaining', d.get('patientname', ''), dos.group(1) if dos else '', d.get('carriercode', ''), 'Payment reason codes are missing or do not balance.', 'held - 2024 coinsurance manual post with empty reason list; fix = re-post the payment with the remit CARCs (chat 9/15 rule: never release); no captured call edits a posted payment', '', d['id'])
add('Exclusions', 'remaining', '15 charts (AET12 Medigap secondaries)', '', 'AET12', 'CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM', 'claim run 1700192 (9/14 21:07 UTC): 59/59 rejected again after the Standard Professional profile change - held open, not rebilled, not completed; carrier master (UI) fix required', '', '1700192', '11756.00')
add('Board', 'done', 'WHITFIELD,ROWAN', '02/04/2026', 'FLO02', 'held Medicare $0 99233', 'WOINS $109.00 per William 9/15 "write off no secondary no caid" - payment id 10154469', '', '19431647', '109.00')
add('Board', 'done', 'WHITFIELD,ROWAN', '02/05/2026', 'FLO02', 'held Medicare $0 99233', 'WOINS $109.00 per William 9/15 - payment id 10154470', '', '19431726', '109.00')
add('Board', 'verified', 'BULL/COALSON/COLLINS/FORD/MORROW/MORLAND/PETERSON/PENHALE/ALCOTT/BROWN/GRAY/CLACK/TILLOTSON', '', '', '', 'all worked by the 0310Z run (board_updates_2026-09-15T0310Z.json in the inbox): write-offs at $0 balance, rebills show billdate 09/14/2026, Bull CAP07 on chart + released; board_act_0310 --dry re-run confirms nothing left to do')
add('ERA', 'ok', '', '', '', '', era_txt)
add('Availity', 'ok', '', '', '', '', 'no new Availity PDFs since the 0310Z pass; CheckEftList_20260914222313.csv duplicate of _222252 (already reconciled); 0310Z Availity registers travel in bundle workspace_state_2026-09-15_0452UTC (uploading during this run)')
for h in sorted(hum, key=lambda h: (h['pid'], h['dos'])):
    add('Humana claim status CSV', 'finalized $0 - open in AMD', names.get(h['acct'], f"pat{h['pid']}"), h['dos'], 'HUM01', f"Humana finalized {h['finalized']} paid $0.00 (ICN {h['icn']}, acct {h['acct']})", 'no remit in AMD; denial reason needed -> board row orwell-padraig-44953 (pat44953) / report only (small residuals)', '', h['visit'], f"{h['open_hum01']:.2f}")
add('Facesheets', 'ok', '', '', '', '', 'no new facesheet in hca/tmh/PCC/Claimocity folders or the parent since 9/14 20:00Z (only CSV/py/md drops); Pam Gmail sweep newer_than:2d = 0; board drops new = 0; denials command queue = 0')
with open(f'_run report 9-15 0510.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['column', 'state', 'patient', 'dos', 'carrier', 'error', 'action', 'checkid', 'visit', 'amount']); w.writerows(rows)
print('report rows', len(rows))

# ---- needs_facesheet_list.md section
sec = f"""

## 2026-09-15 1 AM ET columns run (05:10-{datetime.datetime.utcnow().strftime('%H:%M')} UTC 9/15, ehpa cloud Code Routine, prompt v7)
Bootstrap: repo ATTACHED (origin/main c311761 at start, 668bf74 by mirror time - a chat session pushed 6b6a3db/1c5b301/668bf74 during this run); net AMD_OK, STEDI_CRED_OK (proxy credential), GitHub 200; state bundle workspace_state_2026-09-15_0123UTC unpacked (67 files); bootstrap check: required helpers columns_inspector2_0908.py + era_details_pull.py MISSING (not rewritten; era_step_b_0913.py covers the cache); pdftotext (apt) + pypdf (cffi/cryptography fix) installed; ONE login_cached attempt SUCCEEDED, no .amd_login_lock. Cross-container guard: 0310Z START (03:12Z) had no RUN COMPLETE digest but was >40 min old and its AMD work was finished (board_updates_2026-09-15T0310Z.json in the inbox 04:50Z, main c311761) - its mirror leg (g) was still uploading workspace_state_2026-09-15_0452UTC (37 parts, part 8 at 05:49Z) while this run ran.
COLUMNS (list calls, before -> after): Charge Review 0 -> 0 | Claim Inspector 0 batches -> 0 | Unbilled 11 ($2,422.58) -> 11 | Exclusions 59 ($11,756.00, run 1700192) -> 59. Overview 0/0/11/59 before and after.
UNBILLED held (unchanged): 11 "Payment reason codes are missing or do not balance" rows (RYLANCE, KINROSS, COGSWELL, DELMAR, SIMCOE x4, ROWANTREE NATHAN x2, CARROW JODIE - 2024 coinsurance manual posts with an empty reason list; fix = re-post the payment with the remit CARCs, never release; no captured call edits a posted payment -> William/chat). BULL cleared by the 0310Z run (CAP07 CHP01052326 on chart, admit 9/10/2026, both visits released, billdate 09/14/2026).
EXCLUSIONS held: claim run 1700192 (9/14 21:07 UTC, 68 claims) rejected all 59 AET12 Medigap secondaries again - PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM ($11,756 column). The Standard Professional profile change did not alter the transmitted payer id. Not rebilled, not completed; carrier master (UI) fix required - board row aet12-carrier-cpid.
BOARD: whitfield-rowan -> WOINS $109 x2 (02/04 + 02/05/2026 99233, payment ids 10154469/10154470) per William's 9/15 note, status done. All other Claude-turn rows (Bull, Coalson x2, Collins, Ford, Morrow, Morland, Peterson, Penhale, Alcott, Brown, Gray, Clack, Tillotson) were worked by the 0310Z run - verified live (write-offs at $0, rebills billdate 09/14/2026); board_act_0310.py --dry confirms nothing left. New row orwell-padraig-44953 (pat44953) on William's turn: 7 July 2026 HCA claims ${orwell_amt:.2f} finalized $0 by Humana (from his 9/14 Claim Status export), no remit in AMD, denial reason needed; 2 freq-1 re-sends came back as E-letter duplicates 9/11 - do not re-send again.
{era_txt}
AVAILITY (5g): no PDF newer than the 0310Z pass in 'bht Optum era downloads'; RemittanceViewer_CheckEftList_20260914222313.csv is byte-identical to _222252 (already reconciled) - nothing to reconcile. Humana Claim Status Summary CSVs (2, dropped 9/14 in bht PCC Facesheets) compared to masswriteoffsearch HUM01 open balances (637 charges / $20,928.78): 16 open claims all finalized $0.00 by Humana, no unposted money; details in the run report.
Facesheets: no new files in hca/tmh/PCC/Claimocity or the parent since 9/14 20:00Z; Pam Gmail sweep 0; drops new 0; denials queue 0 (no denials_updates file).
Calls learned: none new (masswriteoffsearch + addpayments manual post already in the registry). Write-offs: WHITFIELD WOINS $218.00. Insurance entered: none. Dollars re-sent: $0.
Waiting on William: AET12 carrier master CPID (59 claims $2,052.25 ins balance / $11,756 billed); ORWELL Humana denial reason (${orwell_amt:.2f}); 11 unbalanced 2024 coinsurance postings (re-post with CARCs); CLACK EULA void-and-corrected-claim OK ($206); TILLOTSON 12/16/2025 Humana answer ($256, watch).
"""
open('needs_facesheet_list.md', 'a').write(sec)
cc = f"""

## 2026-09-15 1 AM ET columns run (ehpa cloud Code Routine, 05:10-{datetime.datetime.utcnow().strftime('%H:%M')} UTC) - run entry, NO new calls captured
Calls exercised (all in the registry): login (one attempt), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimexclusionclaimruns, getclaimexclusioncharges (run 1700192), gettxhistory (txh.fetch), addpayments via manual_post.post (WOINS x2, pat17473232), POST /api/masswriteoff/masswriteoffsearch (carrierids [6285] isinsbalance true -> 637 chargedetails), GET /api/era/checks + checkdetails, POST /api/era/locks/release-expired, posterapayments (era_post --all-unposted), era_fallback (manual_post dry+live), era_clear.
Columns before -> after: CR 0 -> 0 | CI 0 -> 0 | Unbilled 11 -> 11 (reason-code holds) | Exclusions 59 -> 59 (AET12 PREF0288+PREF0264 on run 1700192 - the Standard Professional profile did not fix the transmitted payer id; held).
{era_txt}
Lesson: Humana 'Claim Status Summary' CSV (Availity export) joined to masswriteoffsearch by visit id (Patient Account Number minus the claim letter) = a free 'finalized-at-$0 but still open in AMD' list; the E-letter rows with a later finalized date are the freq-1 duplicate re-sends. pat44953 x7 July 2026 -> William (denial reason not in AMD).
"""
open('captured_calls.md', 'a').write(cc)
print('done')
