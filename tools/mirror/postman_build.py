#!/usr/bin/env python3
# PLAIN ENGLISH (Build the Postman collection from the API vocabulary)
# Decides: Nothing about billing. Turns docs/api_vocabulary.json (one entry per captured call)
#   into docs/postman_effinger_amd.json, a Postman v2.1 collection William can import or that the
#   Postman connector pushes straight into his workspace. Folders = vocabulary folders, one
#   request per call, every secret left as a {{variable}}.
# Rules it uses: the vocabulary is the source, the collection is generated - never hand-edit the
#   collection. Refuses to write if any body/url/header looks like it carries a real token or key.
# Never touches: AMD, Stedi, Drive, GitHub. Pure file in, file out.
# ---
import json, os, re, sys, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VOCAB = os.path.join(ROOT, "docs", "api_vocabulary.json")
OUT = os.path.join(ROOT, "docs", "postman_effinger_amd.json")

SECRET_RE = re.compile(r"(github_pat_[A-Za-z0-9_]{20,}|Bearer\s+[A-Za-z0-9\-_\.]{40,}|usercontext>[A-Za-z0-9\-_\.=]{40,}<|psw=\"(?!\{\{)[^\"]{4,}\")")

def build(vocab):
    folders = {}
    for c in vocab["calls"]:
        req = {
            "method": c["method"],
            "header": [{"key": k, "value": v} for k, v in c.get("headers", {}).items()],
            "url": {"raw": c["url"]},
            "description": (c.get("description", "") +
                            ("\n\nHelper: " + c["helper"] if c.get("helper") else "") +
                            ("\nCaptured: " + c["captured"] if c.get("captured") else "") +
                            ("\nStatus: " + c["status"] if c.get("status") else "")).strip(),
        }
        if c.get("body"):
            lang = c.get("body_language", "text")
            req["body"] = {"mode": "raw", "raw": c["body"], "options": {"raw": {"language": lang}}}
        folders.setdefault(c["folder"], []).append({"name": c["name"], "request": req})
    order = vocab.get("folders", []) + [f for f in folders if f not in vocab.get("folders", [])]
    items = [{"name": f, "item": folders[f]} for f in order if f in folders]
    return {
        "info": {
            "name": "Effinger AMD — captured calls (generated %s, %d calls)" % (datetime.date.today().isoformat(), len(vocab["calls"])),
            "description": "GENERATED from docs/api_vocabulary.json by tools/mirror/postman_build.py — edit the vocabulary, not this file. Fill the collection variables (token, amd_password, stedi_key) locally; they are never stored.",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
        },
        "item": items,
        "variable": [{"key": k, "value": ("" if "never stored" in v else v)} for k, v in vocab.get("variables", {}).items()],
    }

def main():
    vocab = json.load(open(VOCAB))
    ids = [c["id"] for c in vocab["calls"]]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        sys.exit("duplicate call ids in vocabulary: %s" % sorted(dup))
    coll = build(vocab)
    text = json.dumps(coll, indent=1, ensure_ascii=False)
    m = SECRET_RE.search(text)
    if m:
        sys.exit("REFUSING to write collection: looks like a real secret at %r" % m.group(0)[:30])
    if "--check" in sys.argv:
        old = open(OUT).read() if os.path.exists(OUT) else ""
        changed = re.sub(r"generated [0-9-]+, ", "", old).strip() != re.sub(r"generated [0-9-]+, ", "", text).strip()
        print("collection %s (%d calls)" % ("OUT OF DATE" if changed else "up to date", len(vocab["calls"])))
        sys.exit(1 if changed else 0)
    open(OUT, "w").write(text + "\n")
    print("wrote %s: %d folders, %d calls" % (os.path.relpath(OUT, ROOT), len(coll["item"]), len(vocab["calls"])))

if __name__ == "__main__":
    main()
