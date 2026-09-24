#!/bin/bash
cd /home/claude/unbilled
export DECEASED_CACHE=/home/claude/unbilled/registers/deceased_cache.json
echo "### hum LIVE $(date -u +%H:%M:%S)"; timeout 900 python3 hum_1052825_0110.py
echo "### uhc LIVE $(date -u +%H:%M:%S)"; timeout 1200 python3 uhc_1052824_0110.py
echo "### DENIALS CHAIN DONE $(date -u +%H:%M:%S)"
