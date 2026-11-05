#!/usr/bin/env python3
# PLAIN ENGLISH (never retype a connector result - read it back out of the session transcript)
# Decides: nothing. The Drive / Gmail connectors answer with base64 or long text that the model would otherwise have to
#   retype into a Write call - and a retyped base64 string is how the 9/18 state bundle (part04 / part21) and two GitHub
#   packages got corrupted. This helper reads the connector's own answer back out of the session transcript JSONL
#   (~/.claude/projects/<cwd slug>/<session id>.jsonl - every tool_use / tool_result is in there verbatim) and writes the
#   decoded bytes to disk. Big answers (over the tool-result size cap) land as files under
#   ~/.claude/projects/<slug>/<session>/tool-results/*.txt - the same JSON, pass that path with --from-file.
# Rules it uses: the LATEST result for a given id wins; base64 is padded and whitespace-stripped before decoding; nothing
#   is printed but the byte count. Secrets decoded here (keys, passwords) stay in the workspace - never in a file that
#   leaves it; chmod 600 anything under secrets/.
# Never touches: AMD, Drive, Gmail, the repo. Pure local file work.
# Usage:
#   python3 -I tools/bootstrap/transcript_extract.py drive <fileId>=<outpath> [...]          # download_file_content results
#   python3 -I tools/bootstrap/transcript_extract.py gmail-body <threadId>=<outpath> [...]   # newest message plaintextBody (get_thread)
#   python3 -I tools/bootstrap/transcript_extract.py raw-attachments <messageId>=<outdir>    # get_message RAW -> every attachment
#   python3 -I tools/bootstrap/transcript_extract.py drive --from-file <tool-results .txt> <outpath>
#   [--transcript <path>]  defaults to the newest *.jsonl under ~/.claude/projects/
import sys, os, json, base64, re, glob, email

def newest_transcript():
    c = sorted(glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")), key=os.path.getmtime)
    if not c: sys.exit("no transcript JSONL under ~/.claude/projects/")
    return c[-1]

def iter_results(tr):
    """yield (tool name, input dict, result text) for every tool_use that got a tool_result."""
    uses = {}
    for line in open(tr, encoding="utf-8", errors="replace"):
        try: o = json.loads(line)
        except Exception: continue
        content = (o.get("message") or {}).get("content")
        if not isinstance(content, list): continue
        for c in content:
            if not isinstance(c, dict): continue
            if c.get("type") == "tool_use": uses[c.get("id")] = (c.get("name", ""), c.get("input") or {})
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in uses:
                cc = c.get("content"); txt = "".join(x.get("text", "") for x in cc if isinstance(x, dict)) if isinstance(cc, list) else (cc or "")
                name, inp = uses[c["tool_use_id"]]
                # a result over the size cap is a pointer to a file on disk - follow it
                m = re.search(r"Output has been saved to (\S+\.txt)", txt)
                if m and os.path.exists(m.group(1)): txt = open(m.group(1), encoding="utf-8", errors="replace").read()
                yield name, inp, txt

def b64decode(s):
    s = re.sub(r"\s+", "", s or "")
    s += "=" * (-len(s) % 4)
    if "-" in s or "_" in s: return base64.urlsafe_b64decode(s)   # Gmail RAW is url-safe base64
    return base64.b64decode(s)

def write(path, data):
    d = os.path.dirname(path)
    if d: os.makedirs(d, exist_ok=True)
    open(path, "wb").write(data)
    if "/secrets/" in path or path.startswith("secrets/"): os.chmod(path, 0o600)
    print("wrote", path, len(data), "bytes")

def main(a):
    if not a: sys.exit(__doc__ or "usage: see header")
    mode = a[0]; a = a[1:]
    tr = None
    if "--transcript" in a: i = a.index("--transcript"); tr = a[i + 1]; a = a[:i] + a[i + 2:]
    if "--from-file" in a:
        i = a.index("--from-file"); src, out = a[i + 1], a[i + 2]
        j = json.load(open(src))
        if mode == "drive": write(out, b64decode(j.get("content") or j.get("base64Content") or ""))
        elif mode == "gmail-body": write(out, (j["messages"][-1]["plaintextBody"] if "messages" in j else j["plaintextBody"]).encode())
        elif mode == "raw-attachments": raw_attachments(b64decode(j["raw"]), out)
        return
    tr = tr or newest_transcript()
    want = dict(x.split("=", 1) for x in a if "=" in x)
    found = {}
    for name, inp, txt in iter_results(tr):
        if mode == "drive" and "download_file_content" in name and inp.get("fileId") in want:
            try: found[inp["fileId"]] = b64decode(json.loads(txt).get("content") or "")
            except Exception: pass
        elif mode == "gmail-body" and "get_thread" in name and inp.get("threadId") in want:
            try: found[inp["threadId"]] = json.loads(txt)["messages"][-1]["plaintextBody"].encode()
            except Exception: pass
        elif mode == "raw-attachments" and "get_message" in name and inp.get("messageId") in want and inp.get("messageFormat") == "RAW":
            try: found[inp["messageId"]] = b64decode(json.loads(txt)["raw"])
            except Exception: pass
    for k, out in want.items():
        if k not in found: print("NOT FOUND in transcript:", k); continue
        if mode == "raw-attachments": raw_attachments(found[k], out)
        else: write(out, found[k])

def raw_attachments(raw, outdir):
    m = email.message_from_bytes(raw); n = 0
    for p in m.walk():
        fn = p.get_filename()
        if fn:
            write(os.path.join(outdir, os.path.basename(fn)), p.get_payload(decode=True)); n += 1
    if not n: print("no attachments in", outdir)

if __name__ == "__main__": main(sys.argv[1:])
