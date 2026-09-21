#!/bin/bash
cd /home/claude/unbilled
echo "### newest claim runs $(date -u +%T)"; python3 -c "
import amd,re; amd.login_cached(); t=amd.post(amd.msg('getclaimrunstatus','claimsreports',{'nocookie':'1'}),timeout=120)
rs=re.findall(r'<claimrun id=\"(\d+)\" date=\"([^\"]+)\"[^>]*totalsent=\"(\d+)\"[^>]*totalexclusions=\"(\d+)\"',t); print(len(rs),'runs; newest:',rs[-3:])"
echo "### aet12 verify $(date -u +%T)"; timeout 900 python3 aet12_verify_0921_0310.py
bash era_chain_0921_0310.sh 2>&1 | tee logs/era_chain_0310.log
echo "### columns AFTER $(date -u +%T)"; timeout 600 python3 columns_scan_0912.py after > logs/columns_after_0310.log 2>&1; head -3 logs/columns_after_0310.log; grep -n "UNBILLED totalcount\|EXCLUSIONS total\|INSPECTOR visits" logs/columns_after_0310.log
echo "### ALL DONE $(date -u +%T)"
