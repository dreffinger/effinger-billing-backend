# captured_calls additions - 2026-10-23T0040Z (9 PM ET 10/22/2026 slot, fired 00:39Z 10/23, backend billing run, ehpa cloud)

No new call shapes this run. Calls used (all already in the registry): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches,
getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges (columns_scan.py before/after inside the engine pass 00:46-00:49Z);
GET /api/era/checks (era_list.py before/after, 0 checks); posterapayments path (era_post.py --all-unposted, 0 lines); era_clear.py (0);
Stedi 276/277 (claim_status_sweep.py pass 158, 17 asked); lookuppatient (admit_lookup_1023_0040.py, seven name patterns incl. tonight's
Pam card photos). No AdvancedMD write by this container. Vocabulary entries added: 0.
Lesson (not a call): a Pam admit sent as iPhone HEIC photos - ImageMagick's heic delegate refuses the HEVC codec in this container;
`python3 -m venv /tmp/heifenv && /tmp/heifenv/bin/pip install pillow pillow-heif` and a 6-line convert (register_heif_opener, exif_transpose,
save JPEG) reads them; never `pip install pillow-heif` into the main interpreter (it replaced the workspace Pillow and broke `from PIL import Image`
until `pip install --ignore-installed pillow==10.2.0`).
