#!/usr/bin/env python3
"""Recover Drive connector download results verbatim from this session's transcript JSONL.
Usage: restore_from_transcript.py <outdir> <title-regex> [--decode]
Writes each matching {"content":"<b64>",...,"title":"<title>"} to <outdir>/<title> (base64-decoded once).
"""
import re, sys, json, base64, glob, os

def find_results(pattern):
    seen = {}
    for path in glob.glob('/root/.claude/projects/*/*.jsonl'):
        with open(path, 'r', errors='replace') as f:
            for line in f:
                if '"title"' not in line or '"content"' not in line:
                    continue
                for m in re.finditer(r'\{\\?"content\\?":\\?"([A-Za-z0-9+/=]+)\\?",\\?"id\\?":\\?"([^"\\]+)\\?",\\?"mimeType\\?":\\?"([^"\\]+)\\?",\\?"title\\?":\\?"([^"\\]+)\\?"\}', line):
                    b64, fid, mt, title = m.groups()
                    if re.search(pattern, title):
                        seen[title] = b64
    return seen

if __name__ == '__main__':
    outdir, pattern = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    res = find_results(pattern)
    for title, b64 in res.items():
        data = base64.b64decode(b64)
        with open(os.path.join(outdir, title), 'wb') as f:
            f.write(data)
        print(f'{title}: {len(data)} bytes')
    if not res:
        print('no matches'); sys.exit(1)
