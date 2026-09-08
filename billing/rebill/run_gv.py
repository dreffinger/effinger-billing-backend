# PLAIN ENGLISH (GV run list)
# Decides: Which patients gv_rebill runs for on a given night.
# Rules it uses: Names from the CO24/COB9 scan.
# Never touches: Anyone else.
# ---
import gv_rebill
for pid in ('22603','48458','17471365','17474272','17472573'):
    print('==',pid, flush=True)
    for l in gv_rebill.run(pid,'1,2'): print(l, flush=True)
print('=== done', flush=True)
