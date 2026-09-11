#!/bin/bash
cd /home/claude/unbilled
for i in $(seq 1 40); do
  [ -f scan_DONE ] && { echo "ALL DONE at batch $i"; break; }
  echo "=== batch $i $(date +%T) ==="
  timeout -s KILL 140 python3 scan_txh.py --max 8
  echo "batch $i rc=$? lines=$(wc -l < scan_charges.jsonl)"
  sleep 1
done
