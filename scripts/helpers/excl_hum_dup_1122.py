# PLAIN ENGLISH: complete the 3 Humana 'seems to be a duplicate of a claim submitted 11/0x/2026' exclusion rows on claim run 1700397
# (visits 19461785 / 19461794 / 19461795 - Garland-G -> Effinger re-renders of 11/19 whose originals 19459674 / 19460177 / 19460187
# Humana already holds). Standing rule step 4: duplicate-claim rejection -> hideexclusions, no rebill. Run 2026-11-22T1240Z.
import re, json, time, amd
amd.login_cached(); RUN = "1700397"
rows = [("19461785","19461785A"),("19461794","19461794A"),("19461795","19461795A")]
lst = "".join('<visit id="%s" claimid="%s"/>' % r for r in rows)
x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
print("hideexclusions ->", re.sub(r"\s+", " ", x[:250])); time.sleep(1)
y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
left = re.findall(r'<visit [^>]*\bid="(\d+)"', y); print("left on run", RUN, left)
json.dump({"run": RUN, "rows": rows, "left": left, "stamp": "2026-11-22T1240Z"}, open("registers/excl_hum_dup_2026-11-22T1240Z.json", "w"), indent=1)
