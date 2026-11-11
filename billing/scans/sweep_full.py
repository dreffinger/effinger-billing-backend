# PLAIN ENGLISH (Full claim-status sweep - every open insurance balance that is DUE; rewritten 11/10/2026, look-ups part A step 2)
# Decides: the same as claim_status_sweep.py, over every payer with a claim-status route: which unpaid claims are DUE for a paid Stedi
#   276/277 check by the rules in cs_rules.py (tonight's ageing file + the shared claim-status ledger), and what the payer says about them.
#   Until 11/10/2026 this helper asked EVERY unpaid visit older than 30 days, largest balance first (William approved the ~$1,500 one-time
#   cost on 9/6; run again 10/13 over claims older than 120 days: 250 checks, the military plan's 26 all empty). It now asks only what is
#   due, once, within the caps (150 checks or $25 a run, 400 checks or $100 a month), and payers whose claim status does not work are
#   never sent (cs_rules.CS_OFF - the codes it used to blank, Medicare and VA community care, are in cs_rules.CS_NO_ROUTE).
# Rules it uses: cs_rules.py through claim_status_sweep.run(). A live run needs the word --go; without it the helper prints what it WOULD
#   ask and makes no call. --help prints and exits; an unknown word is an error and nothing is asked.
# Never touches: AMD writes, balances, claims. Writes claimstatus_full_<date>.json (chart and visit ids, no names) and the ledger.
# ---
"""Usage: python3 sweep_full.py [--go] [--aging aging_latest.json] [--ledger PATH] [--new-ledger] [--carriers A,B] [--max N]
The same check as claim_status_sweep.py over every payer with a claim-status route. Without --go nothing is asked."""
import sys
import claim_status_sweep
if __name__ == "__main__": sys.exit(claim_status_sweep.main(sys.argv[1:], prog="sweep_full.py", out_name="claimstatus_full_%s.json", doc=__doc__))
