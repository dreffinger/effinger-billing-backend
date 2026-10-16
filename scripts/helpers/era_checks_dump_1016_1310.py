# PLAIN ENGLISH (ERA checks dump, 9 AM ET 10/16/2026 run 2026-10-16T1310Z) - READ ONLY.
# Decides: nothing. Writes the full GET /api/era/checks answer to the file named on the command line so
#   era_fallback_0913b.py --checks <file> can read the check ids, payment numbers and deposit dates. No AMD write.
import era_post, json, sys
cs = era_post.checks(); json.dump(cs, open(sys.argv[1], "w"), indent=1); print(len(cs), "checks written to", sys.argv[1])
