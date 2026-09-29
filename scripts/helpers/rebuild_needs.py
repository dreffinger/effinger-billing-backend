import glob,os
parts=[]
for d in sorted(glob.glob('/home/claude/effinger-billing-backend/nightly/runs/*/needs_section_*.md')):
    parts.append(open(d).read())
open('/home/claude/unbilled/needs_facesheet_list.md','w').write('\n\n'.join(parts))
print(len(parts),'sections')
