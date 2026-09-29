# PLAIN ENGLISH (7pm ET 9/28/2026 run 2026-09-28T2310Z): Pam's Brynwood readmit record for pat20729 (Medicare A primary, Medicaid # on the sheet,
# secondary 'Medicare A coinsurance from Medicaid - SUNSHINE STATE') - the chart carries Medicare alone (QMB on AMD's 271). Adds the Sunshine
# SMMC plan (SUN01, the Medicaid number from the sheet, no group), reads AMD's 271 on it; if ACTIVE sets the patient order 1,2 and the two
# 9/23-9/24 HCA visits resaved this run to insorder 1,2 (full-visit echo). Never touches: payments, other charts.
import amd, add_ins, elig_amd, ins_update, resave, json, re, sys, time
