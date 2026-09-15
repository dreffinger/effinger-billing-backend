# PLAIN ENGLISH (vocabulary entry for the frequency-7 corrected claim learned 9/15/2026): appends one call to
# docs/api_vocabulary.json (skips if the id already exists). Never touches: AMD.
import json
P="/home/user/effinger-billing-backend/docs/api_vocabulary.json"
v=json.load(open(P))
ent={"folder":"Charges & visits","name":"updextrainsinfo - frequency 7 corrected claim (payer ICN from the posted ERA payment)","method":"POST","url":"{{xmlgw}}",
 "headers":{"Content-Type":"text/xml","Cookie":"token={{token}}"},
 "body":"<ppmdmsg action=\"updextrainsinfo\" class=\"chargeentry\" msgtime=\"{{msgtime}}\" visitid=\"{{visitid}}\"><usercontext>{{token}}</usercontext><extins txtChargeCode=\"{{pcode}}\" resubmissioncode=\"7\" origrefnum=\"{{payer_icn}}\" patsignature=\"1\" emergency=\"0\" epsdt=\"0\" payprov=\"1\" employment=\"0\" autoaccident=\"0\" otheraccident=\"0\" pregnant=\"0\" outsidelab=\"0\"/></ppmdmsg>",
 "description":"Corrected claim to a payer that already adjudicated the visit (William 9/14: frequency 7 with the payer's claim number once it is in hand). The payer ICN is read from the charge itself: getchargedetaildataicd10 by charge id -> the ERA-posted <payment origrefnum=\"...\" checknumber=\"...\"> element (era checkdetails JSON never exposes it). Then POST /api/claim/chargerebill sequencenumber=<plan seq> -> 204; readback shows resubmissioncode=7 origrefnum=<ICN> insbilled=0. Proven 9/15/2026 on pat17473476 (Florida Blue CO-22 $0 denial, WOINS voided first, member id corrected).",
 "helper":"clack_fix_0710.py (pattern); void_tx.void_writeoff; ins_update.update; amd.rebill_charge","captured":"9/15/2026","body_language":"xml","status":"proven","tags":["frequency 7","ICN","corrected claim"],
 "id":"charges-visits/updextrainsinfo-frequency-7-corrected-claim-payer-icn"}
if not any(c.get("id")==ent["id"] for c in v["calls"]):
    v["calls"].append(ent); json.dump(v,open(P,"w"),indent=1); print("added; calls now",len(v["calls"]))
else: print("already present")
