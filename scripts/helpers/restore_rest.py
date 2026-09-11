# PLAIN ENGLISH (Restore batch (9/3))
# Decides: Runs restore_charge over the list of charges the 9/3 bug voided.
# Rules it uses: List is from void_scan.
# Never touches: Anything else.
# ---
import json, restore_charge, time
v=json.load(open("void_scan.json")); live_by_visit={x["visit"]:x["live_charges_on_visit"] for x in v}
done={l.split()[1] for l in open("restore_charge.log") if " : OK" in l}
todo=[("COMSTOCK,HAZEL G","22461677","19390367"),("COMSTOCK,HAZEL G","22484861","19409385"),("KINGSLEY,BEATRIX","20976357","13987734"),("KINGSLEY,BEATRIX","21330026","14003083"),("KINGSLEY,BEATRIX","22423408","19358808"),("STOCKTON,SABINA","22484184","19408939"),("STOCKTON,SABINA","23316713","19413634"),("LYNDON,LOMAX","23350600","19442472"),("LYNDON,LOMAX","23355342","19446290"),("ALDERTON,HORACE L","23361359","19451315"),("BARRINGTON,ELSPETH","23361623","19451570")]
log=open("restore_charge.log","a")
for name,cid,visit in todo:
    if cid in done: continue
    live=(live_by_visit.get(visit) or [[None]])[0][0]
    try: msg="%s %s <- via %s : %s" % (name,cid,live,restore_charge.restore(cid,live))
    except Exception as e: msg="%s %s EXC %s" % (name,cid,str(e)[:120])
    print(msg, flush=True); log.write(msg+"\n"); log.flush(); time.sleep(0.8)
print("restore done")
