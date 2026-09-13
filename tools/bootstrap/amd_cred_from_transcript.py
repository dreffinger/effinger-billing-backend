#!/usr/bin/env python3
"""Write /home/claude/unbilled/.amd_cred.json from the Gmail thread result already in this session's
transcript JSONL (thread 1866ce7e2233e4c0, Gregg's "reset the password to <psw>" line) - WITHOUT the
password ever passing through a typed command.

Lesson 9/13/2026 15:10 UTC: a plain regex over the transcript also matched the regex's OWN source text
inside an earlier Bash command ("(\\S+?)"), so a 7-byte junk string was written and sent to AMD, costing
the run its one login attempt. This helper therefore (1) only accepts candidates that look like an AMD
password (8-32 chars, letters+digits only), (2) takes the MOST COMMON candidate across the transcript
(the thread quotes the line many times), (3) refuses to write anything ambiguous, and (4) prints only
length + a hash fragment, never the value. Exit 0 = written; exit 2 = not found/ambiguous (do NOT log in).
"""
import re, sys, json, glob, os, hashlib, collections

CRED = '/home/claude/unbilled/.amd_cred.json'
PAT = re.compile(r'reset the password to ([A-Za-z0-9]{8,32}) and let me know')

def main():
    counts = collections.Counter()
    for path in glob.glob('/root/.claude/projects/*/*.jsonl'):
        with open(path, errors='replace') as f:
            for line in f:
                if 'reset the password to' not in line:
                    continue
                for m in PAT.finditer(line):
                    counts[m.group(1)] += 1
    if not counts:
        print('AMD_CRED_NOT_FOUND: fetch Gmail thread 1866ce7e2233e4c0 with get_thread first'); return 2
    (best, n), = counts.most_common(1)
    if len(counts) > 1:
        second = counts.most_common(2)[1]
        if second[1] >= n:
            print('AMD_CRED_AMBIGUOUS: %d candidates - not writing' % len(counts)); return 2
    with open(CRED, 'w') as f:
        json.dump({'psw': best}, f)
    os.chmod(CRED, 0o600)
    print('AMD_CRED_OK: len=%d sha8=%s seen=%d' % (len(best), hashlib.sha256(best.encode()).hexdigest()[:8], n))
    return 0

if __name__ == '__main__':
    sys.exit(main())
