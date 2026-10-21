#!/usr/bin/env bash
# PLAIN ENGLISH: the ERA settlement chain of the 7 PM ET 10/21/2026 run on UHC check 1053251, run under nohup (Bash cap 600 s):
# (1) era_co45_relink.py --live = void each Post-button payment and re-post it ERA-linked with WOINS for the CO-45/CO-253 contractual
# (PR amounts stay); (2) era_b9_1021_2310.py --live = WONCS the one $0 CO-B9 hospice CCM line; (3) era_clear.py = dismiss the check once
# no postable money remains; (4) era_list.py after = confirm the Center; (5) era_audit_1021_2310.py = read every charge live again.
cd /home/claude/unbilled
echo "== relink live $(date -u +%H:%M:%SZ)"; python3 era_co45_relink.py 1053251 --meta registers/era_checks_meta_1053251.json --live
echo "== b9 live $(date -u +%H:%M:%SZ)"; python3 era_b9_1021_2310.py --only 19455651 --live
echo "== era_clear $(date -u +%H:%M:%SZ)"; python3 era_clear.py
echo "== era_list after $(date -u +%H:%M:%SZ)"; python3 era_list.py after 2026-10-21T2355Z
echo "== audit $(date -u +%H:%M:%SZ)"; python3 era_audit_1021_2310.py | tail -3
echo "== CHAIN_DONE $(date -u +%H:%M:%SZ)"
