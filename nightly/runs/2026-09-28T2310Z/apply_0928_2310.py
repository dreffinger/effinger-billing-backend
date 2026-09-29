# PLAIN ENGLISH (Unbilled 'Insurance order is missing' - eight new HCA charts + pat21489 exclusions, 7pm ET 9/28/2026 run 2026-09-28T2310Z)
# Decides, per William's lookup order (patient_db -> AMD 271 -> Stedi -> facesheet -> William) run this slot (inv_2310.json + cascade2_2310.json;
#   the plan/member config lives in secrets/newcharts_0928_2310_cfg.json - member ids never leave the workspace):
#   straight Medicare (MBI, no MA entity) -> FLO02; Medicare's 271 names an MA plan -> that plan alone (Humana PPO x2 via Stedi 61101 with
#   the MBI, AARP MA from UHC via discovery + 87726); CMS 'OT' UHC entity with no MA type = AARP Medigap -> FLO02 first + AAR01 second.
#   Per chart: add_ins.add (NO group number) -> AMD free 271 on the new plan -> address line 1 moved up from line 2 (Claimocity feed
#   leaves it blank) -> admission date = the stay's own 99223 DOS via updextrainsinfo hospitalizationfrom ONLY -> PRIMARY-DX GATE
#   (dx_primary_fix.plan on the first code; the cascade helper resaves + freq-1 rebills) -> full-visit resave insorder + onhcfa=1 (every
#   live charge echoed) -> patient default order (ins_update sequence=) -> release from Unbilled (hideunbillablevisits).
#   pat21489: SUN01 INACTIVE on AMD's 271, Medicaid 271 names SMMC MMA Capitated FLORIDA COMMUNITY CARE (FCC seq 4 on the chart) ->
#   SUN01 end-dated 04/13/2026, the two 99309 visits set to insorder 4, freq-1 rebilled to FCC, exclusions on run 1700243 completed.
#   HOLDS: pat17477892 (MBI 72 + discovery 0 -> William, facesheet), pat17477898 + pat17477850 (CHP MA - CHP wants its own member id -> William).
