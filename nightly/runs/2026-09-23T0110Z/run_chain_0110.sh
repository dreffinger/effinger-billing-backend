#!/bin/bash
# 2026-09-23T0110Z run (9pm ET 9/22 slot): columns before -> ERA chain -> columns after -> run outputs -> mirror
cd /home/claude/unbilled
S=2026-09-23T0110Z
timeout 900 python3 columns_scan_0912.py before > scan_before_0110.log 2>&1
bash era_chain_0923_0110.sh > logs/era_chain_0923_0110.log 2>&1
timeout 900 python3 columns_scan_0912.py after > logs/columns_after_0110.log 2>&1
python3 run_outputs_0923_0110.py
