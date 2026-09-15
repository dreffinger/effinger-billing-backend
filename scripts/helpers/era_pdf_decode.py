# PLAIN ENGLISH: rebuild the Availity CheckDetails PDFs William dropped in Drive from this session's persisted
# connector results (tool-results/mcp-Google_Drive-download_file_content-*.txt) into era_pdfs/<title>. Decides nothing.
import json, base64, glob, os
os.makedirs("era_pdfs", exist_ok=True); n = 0
for p in glob.glob("/root/.claude/projects/*/*/tool-results/mcp-Google_Drive-download_file_content-*.txt"):
    try:
        d = json.load(open(p))
    except Exception:
        continue
    t = d.get("title", "")
    if not t.lower().endswith(".pdf"): continue
    out = "era_pdfs/" + t
    if os.path.exists(out): continue
    open(out, "wb").write(base64.b64decode(d["content"])); n += 1
print("decoded", n, "total", len(glob.glob("era_pdfs/*.pdf")))
