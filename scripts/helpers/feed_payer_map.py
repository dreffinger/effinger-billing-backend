# PLAIN ENGLISH (One table: the payer name a facility writes on its facesheet -> the practice's AdvancedMD carrier)
# Decides: which AdvancedMD carrier a payer NAME from a feed insurance block (or an admission notice) means, and what kind of plan
#   it is. Built 11/19/2026 (William: "fix it for the insurance intake for sure") after the comparison of every feed file with the
#   charts: 29 usable blocks carried a name no table knew ('First Coast Medicare', 'Medicare FL', 'VA CCN Optum', 'Staywell HMO',
#   'United American Ins Co'), 'AARP UHC Medicare Supplement' was read as the UnitedHealthcare Advantage plan (it is the AARP
#   Medigap plan), 'Medicaid Florida Community' as Medicaid fee-for-service (it is Florida Community Care), and the two feed helpers
#   kept two different tables. Order matters: the first pattern that matches wins, so the narrow names stand before the wide ones.
# Rules it uses: a name that says patient / resident liability, private pay, a coinsurance row of another plan, pending, therapy,
#   vaccine, lab, a stand-alone drug plan, hospice, dental, vision or life is NOT a plan to bill (skip() says which word) - TRICARE
#   FOR LIFE and a '... Health and Life Insurance Company' are medical. A long-term-care-only Medicaid plan (the name says LTC or
#   Long Term Care) is the nursing home's payer, not the physician's: kind() answers 'ltc' and the intake never bills it.
# Never touches: anything - a pure table. Used by claimocity_newcharts.py, claimocity_fixholds.py, feed_in1_intake.py, adt_ingest.py.
import re
TABLE = [
    (r"TRICARE FOR LIFE|\bTFL\b", "TRI05"), (r"TRICARE", "TRI00"), (r"CHAMPVA", "CHA03"),
    (r"VA CCN|VA COMMUNITY|VACCN|VETERAN", "VACCN"),
    (r"FLORIDA COMMUNITY|\bFCC\b", "FLO99"),                                     # before MEDICAID: 'Medicaid MMA Florida Community' is FCC
    (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"STAYWELL", "STA03"), (r"MOLINA", "MOL10"), (r"AMBETTER", "AMB03"),
    (r"AARP.*(SUPP|MEDIGAP|HEALTHCARE OPTIONS)|MEDICARE SUPP.*(AARP|UHC|UNITED)|^AARP$", "AAR01"),   # before UHC: the AARP Medigap plan
    (r"UNITED AMERICAN", "UNI01"),                                               # before UNITED HEALTH: a Medigap company
    (r"UNITED ?HEALTH|\bUHC\b|AARP MEDICARE ADV|AARP", "UNI20"),
    (r"HUMANA", "HUM01"), (r"WELLCARE", "WEL04"), (r"CAPITAL HEALTH", "CAP07"), (r"AETNA", "AET07"), (r"CIGNA", "CIG09"),
    (r"FLORIDA BLUE|BCBS|BLUE CROSS|BC/BS", "BCBS"),
    (r"RAILROAD", "RET01"),
    (r"MEDICARE A\b|MEDICARE B\b|MEDICARE PART [AB]|FCSO|FIRST COAST|TRADITIONAL MEDICARE|^MEDICARE( FL| FLORIDA)?$|^MCA-|^MCB|^CMS$", "FLO02"),
    (r"MEDICAID(?! MANAGED)|AHCA|^MCD|-MCD\b|^MCD-", "MCAD"),
]
SKIP = r"LIABILITY|RESLIAB|SELF.?PAY|PRIVATE PAY|PENDING|COINS|CO-INS|THERAPY|VACCIN|\bLAB\b|PART D|\bPDP\b|PRESCRIPTION|HOSPICE|DENTAL|VISION|\bLIFE\b|PATIENT RESOURCES|X-OVER"
MEDICAID_FAMILY = {"MCAD", "FLO99", "SUN01", "SIM01", "STA03", "MOL10"}
SECONDARY_ONLY = {"AAR01", "UNI01", "TRI05", "CHA03"}
def skip(name):
    """The word that makes a feed insurance row NOT a plan to bill, '' when it may be one."""
    t = (name or "").upper().replace("TRICARE FOR LIFE", "TRICARE")
    m = re.search(SKIP, t)
    if m and m.group(0) == "LIFE" and "HEALTH" in t: m = re.search(SKIP.replace(r"|\bLIFE\b", ""), t)
    return m.group(0).lower() if m else ""
def code(name):
    """The AdvancedMD carrier code for a payer name, None when no pattern knows it."""
    t = (name or "").upper()
    return next((c for pat, c in TABLE if re.search(pat, t)), None)
def kind(name, c=None):
    """'ltc' (a long-term-care-only Medicaid plan - never the physician's payer), 'medicaid' (fee-for-service or a managed medical plan),
    'secondary' (Medigap, TRICARE For Life, CHAMPVA), 'primary' (anything else that maps), '' (unknown name)."""
    c = c or code(name); t = (name or "").upper()
    if not c: return ""
    if re.search(r"\bLTC\b|LONG.?TERM", t) and c != "FLO99": return "ltc"      # Florida Community Care is its members' comprehensive plan (271, 9/7/2026)
    if c in MEDICAID_FAMILY or (c == "HUM01" and re.search(r"MCD|MEDICAID|MEDICAL PLAN", t)): return "medicaid"
    if c in SECONDARY_ONLY: return "secondary"
    return "primary"
if __name__ == "__main__":
    T = {"First Coast Medicare": "FLO02", "Medicare First Coast Service Options Inc": "FLO02", "Medicare FL": "FLO02", "Medicare B": "FLO02", "MCA-Medicare A": "FLO02",
         "AARP UHC Medicare Supplement": "AAR01", "AARP Healthcare Options": "AAR01", "United Healthcare": "UNI20", "AARP Medicare Advantage": "UNI20",
         "United American Ins Co": "UNI01", "Medicaid MMA Florida Community": "FLO99", "FLORIDA COMMUNITY CARE MCO": "FLO99", "Medicaid-FL": "MCAD", "MCD-Medicaid Florida": "MCAD",
         "VA CCN Optum - 100% PDPM": "VACCN", "Staywell HMO": "STA03", "Tricare for Life": "TRI05", "BC/BS of FL": "BCBS", "Humana LTC MCD FL": "HUM01",
         "Medicaid Sunshine State Health Plan": "SUN01", "Capital Health Plan": "CAP07", "American Elder Care": None}
    bad = [(n, code(n), w) for n, w in T.items() if code(n) != w]
    assert not bad, bad
    assert skip("Patient Liability") == "liability" and skip("Tricare for Life") == "" and skip("COINS-Medicaid HMO B") == "coins" and skip("Sierra Health and Life Insurance Company") == "" and skip("Constitution Life") == "life"
    assert kind("Humana LTC MCD FL") == "ltc" and kind("Florida Community Care") == "medicaid" and kind("Humana Medical Plan, Inc.") == "medicaid" and kind("Humana") == "primary" and kind("AARP UHC Medicare Supplement") == "secondary"
    print("selftest ok: %d names" % len(T))
