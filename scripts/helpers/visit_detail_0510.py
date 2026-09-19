# PLAIN ENGLISH (1am ET 9/19 run): read-only visit detail (getchargedetaildataicd10 by charge id via resave.visit_charges) for the
# visits on tonight's new HCA charts - insorder / refplan / preauth / onhcfa / admission date / diagnosis list. Never touches: AMD writes.
import amd, resave, json, sys
amd.login_cached(); out={}
for cid in sys.argv[1:]:
    try:
        v,p,ch=resave.visit_charges(cid); ex=v.find("extins")
        d={"visit":v.get("id"),"pid":p.get("id"),"insorder":v.get("insorder"),"refplan":v.get("refplan"),"preauth":v.get("preauth"),"onhcfa":v.get("onhcfa"),"facility":v.get("facility"),
           "hospfrom":ex.get("hospitalizationfrom") if ex is not None else None,"resub":ex.get("resubmissioncode") if ex is not None else None,
           "charges":[(c.get("id"),c.get("proccode"),c.get("modcodes"),c.get("pos"),c.get("diagcodes"),c.get("void")) for c in ch]}
        dx=[(x.get("id"),x.get("code")) for x in v.iter("diagcode")]
        d["dxmap"]=dx
    except Exception as e: d={"error":str(e)[:200]}
    out[cid]=d; print(cid,json.dumps(d))
json.dump(out,open("registers/visit_detail_2026-09-19T0510Z.json","w"),indent=1)
