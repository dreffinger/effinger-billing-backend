# PLAIN ENGLISH: bypass the 'Source of Payment you have chosen is not typical for this carrier' advisory on v19462190 (chart 17478349,
# UMR - the same advisory the 11/11 run bypassed by error id on this chart). Error id from the engine's after-scan minutes ago.
import amd, re
amd.login_cached()
r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="19462190"><claimeditlist><claimedit id="398626"/></claimeditlist></visit></visitlist>'))
print("bypass v19462190 ->", "ok" if 'success="1"' in r and "Fault" not in r else re.sub(r"\s+", " ", r[:300]))
