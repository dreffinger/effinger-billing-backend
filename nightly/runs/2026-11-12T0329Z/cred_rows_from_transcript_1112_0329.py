import json, glob, os, re, sys
# read the newest ArtifactData 'cred' list result out of this session's transcript and write cred_board_rows.json
tr = sorted(glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")), key=os.path.getmtime)[-1]
uses = {}; best = None
for line in open(tr, encoding="utf-8", errors="replace"):
    try: o = json.loads(line)
    except Exception: continue
    c = (o.get("message") or {}).get("content")
    if not isinstance(c, list): continue
    for x in c:
        if not isinstance(x, dict): continue
        if x.get("type") == "tool_use": uses[x.get("id")] = x
        elif x.get("type") == "tool_result":
            u = uses.get(x.get("tool_use_id"))
            if not u or u.get("name") != "ArtifactData": continue
            if (u.get("input") or {}).get("collection") != "cred": continue
            cc = x.get("content"); txt = "".join(y.get("text", "") for y in cc if isinstance(y, dict)) if isinstance(cc, list) else (cc or "")
            best = txt
rows = []
for line in best.splitlines():
    line = line.strip()
    if not line.startswith('{"id"'): continue
    d = json.loads(line); data = d.get("data", {})
    rows.append({"id": d["id"], "name": data.get("name", ""), "due": data.get("due", ""), "cycle": data.get("cycle", ""), "turn": data.get("turn", ""), "version": d.get("version")})
out = "/home/claude/unbilled/cred_board_rows.json"
json.dump(rows, open(out, "w"), indent=1)
print("wrote", out, len(rows), "rows")
