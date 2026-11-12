import json, re, sys, glob, os
tr = sorted(glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")), key=os.path.getmtime)[-1]
uses = {}; rows = None
for line in open(tr, encoding="utf-8", errors="replace"):
    try: o = json.loads(line)
    except Exception: continue
    content = (o.get("message") or {}).get("content")
    if not isinstance(content, list): continue
    for c in content:
        if not isinstance(c, dict): continue
        if c.get("type") == "tool_use": uses[c.get("id")] = (c.get("name",""), c.get("input") or {})
        elif c.get("type") == "tool_result" and c.get("tool_use_id") in uses:
            name, inp = uses[c["tool_use_id"]]
            if name == "ArtifactData" and inp.get("collection") == "cred":
                cc = c.get("content"); txt = "".join(x.get("text","") for x in cc if isinstance(x, dict)) if isinstance(cc, list) else (cc or "")
                rows = []
                for m in re.finditer(r'^\{"id":.*\}$', txt, re.M):
                    d = json.loads(m.group(0)); data = d.get("data", {})
                    rows.append({"id": d["id"], "name": data.get("name",""), "due": data.get("due",""), "cycle": data.get("cycle",""), "turn": data.get("turn","")})
json.dump(rows, open("/home/claude/unbilled/cred_board_rows.json","w"), indent=1)
print("cred rows", len(rows))
