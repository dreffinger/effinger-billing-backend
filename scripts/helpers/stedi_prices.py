# PLAIN ENGLISH (the vendor's price table - look-ups part A, 11/10/2026)
# Decides: nothing. ONE table of what each kind of paid Stedi call costs, read by the usage log in stedi.py, the usage reader
#   stedi_usage.py and the claim-status caps. Pay-as-you-go list prices (stedi.com/pricing, read 11/10/2026): every kind of call has its
#   own monthly ladder and each call is billed at the price of the tier it falls into. A plain Medicare check (payer id CMS) is an
#   ordinary eligibility check on the statement, so it shares the eligibility ladder. The two look-ups (with and without SSN) are two
#   lines on the statement, each on its own ladder. October 2026 as billed - claim status 6,770 = $889.50; look-ups 986 without SSN +
#   78 with SSN = $783.50; discovery 187 = $237.00; eligibility 505 = $113.25 - price() gives exactly these.
# Never touches: anything - no file, no network. Change the table here when the vendor's prices or a custom plan change.
LADDERS = {                                    # kind -> [(last call of the tier in the month, price per call)]; None = no upper end
    "eligibility":         [(250, 0.30), (3500, 0.15), (10000, 0.10), (None, 0.08)],
    "claim status":        [(250, 0.30), (3500, 0.15), (10000, 0.10), (None, 0.08)],
    "look-up without SSN": [(100, 1.00), (750, 0.75), (1250, 0.50), (None, 0.40)],
    "look-up with SSN":    [(100, 1.00), (750, 0.75), (1250, 0.50), (None, 0.40)],
    "discovery":           [(100, 1.50), (750, 1.00), (1250, 0.75), (None, 0.65)],
}
SAME_LADDER = {"plain Medicare": "eligibility"}  # a plain Medicare check is billed as an eligibility check
KINDS = ("eligibility", "plain Medicare", "look-up without SSN", "look-up with SSN", "discovery", "claim status")
def ladder_of(kind):
    """The name of the ladder a kind of call is billed on."""
    k = SAME_LADDER.get(kind, kind)
    if k not in LADDERS: raise KeyError("no price for %r - known: %s" % (kind, ", ".join(KINDS)))
    return k
def first_tier(kind):
    """The list price of one call of this kind at the first tier (what the usage log writes on every line)."""
    return LADDERS[ladder_of(kind)][0][1]
def _cents(kind, units, before=0):
    total = 0; n = int(units); done = int(before); low = 0
    for top, price in LADDERS[ladder_of(kind)]:
        room = (top - max(low, done)) if top is not None else n
        take = max(0, min(n, room))
        total += take * int(round(price * 100)); n -= take; done += take
        if top is not None: low = top
        if n <= 0: break
    return total
def price(kind, units, before=0):
    """Dollars for `units` calls of this kind in one month, after `before` calls on the same ladder were already made that month."""
    return _cents(kind, units, before) / 100.0
def breakdown(kind, units):
    """'100 x $1.00 + 650 x $0.75 + ...' for `units` calls of this kind in one month."""
    parts = []; n = int(units); low = 0
    for top, p in LADDERS[ladder_of(kind)]:
        take = min(n, (top - low) if top is not None else n)
        if take > 0: parts.append("%d x $%.2f" % (take, p))
        n -= take
        if top is not None: low = top
        if n <= 0: break
    return " + ".join(parts) or "0"
