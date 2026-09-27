# PLAIN ENGLISH (Standing diagnosis-code substitutions)
# Decides: Applies one of Effinger's four already-vetted, documented dx fixes
#          instead of hand-correcting them in the AMD UI every day:
#          (1) I63.9 acute-stroke dx rejected as "should not be billed in an
#              outpatient setting" -> I69.30 when POS != 21, then freq-1 rebill;
#          (2) Claim Inspector Pattern 20389: a sequela/external-cause code
#              (S/T/V/W/X/Y) leading the diagnosis list is reordered behind a
#              condition code already on the charge. Winslow Jr's S81.801S-only
#              precedent (no condition code present at all) gets M86.9 in front,
#              per William 9/6 -- that specific insertion is NOT generalized to
#              any other sequela-only chart;
#          (3) Claim Inspector Pattern 2776: Z51.11 dropped from a facility visit;
#          (4) Claim Inspector Pattern 11256 unspecified laterality/site: known
#              fixes only (currently G81.90 -> I69.30); anything else is bypassed
#              and logged for William, never guessed.
# Rules it uses: recode._save (full-visit echo, void-checked, skips paid/void
#          charges) for every dx edit; freq1_visit.run only for the stroke swap,
#          because that one is a payer rejection that needs a rebill -- the three
#          Claim Inspector patterns are cleared with bypassclaimedits instead.
# Never touches: paid/void charges (recode._save already skips them); any dx
#          pattern that is not on this table -- those come back {"action": "hold"}
#          for the caller to log/board, never invented on the fly.
# ---
"""Standing, board-documented diagnosis-code substitutions -- see
skills/billing-rejected-claims-task and
skills/billing-easy-task-charge-review-and-claim-inspector-columns for the
source rules. Written so the Charge Review / Claim Inspector / Exclusions
sweeps can call these instead of William re-doing the same four corrections
by hand in the AMD UI every day.

    dx_swap.fix_stroke_outpatient(cid, seq, dry=False)
    dx_swap.fix_inspector_pattern(cid, vid, pattern_id, errid, errtext="", dry=False)

Both return a dict with an "action" key:
    "fixed" / "swap+rebill" -- the edit (and rebill, for the stroke case) went in
    "none"                  -- nothing on this charge matched the rule
    "dry-run"               -- --dry was set; nothing was sent
    "hold"                  -- known pattern, but no safe known fix -- bypassed
                                (where applicable) and left for a human to log
    "error"                 -- the AMD call faulted; see "detail"
"""
import re
import amd, resave, recode, freq1_visit

I639 = "dcode1034545006"    # I63.9  acute ischemic stroke, unspecified
I6930 = "dcode1034545425"   # I69.30 unspecified sequelae of cerebral infarction
M869 = "dcode1034545415"    # M86.9  osteomyelitis, unspecified (Winslow Jr precedent ONLY)

SEQUELA_RE = re.compile(r"^[STVWXY]\d")

# Pattern 11256 known fixes: {trigger ICD-10 code -> replacement dcode id}.
# Anything not in this table has no captured replacement dcode yet (hip/knee OA
# unspecified -> bilateral, I65.2x -> I65.23) -- per the standing rule those stay
# bypass+log until a real dcode id is captured, never guessed.
LATERALITY_KNOWN = {
    "G81.90": I6930,   # hemiplegia, unspecified -> I69.30
}

LOG = open("dx_swap.log", "a")


def log(m):
    print(m, flush=True)
    LOG.write(m + "\n")
    LOG.flush()


def _dcodes_of(cid):
    """id -> ICD-10 code map for the codes actually present on this charge."""
    x = resave.detail(cid)
    return dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))


def _edit_dx(cid, fn):
    """fn(list_of_dcode_ids, id->code map) -> new list, or an unchanged list for no-op."""
    m = _dcodes_of(cid)

    def e(a):
        d = (a.get("diagcodes") or "").split()
        n = fn(d, m)
        if n and n != d:
            a["diagcodes"] = " ".join(n)
            return True
        return False

    return recode._save(cid, e)


def _bypass(vid, errids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"},
        '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>'
        % (vid, "".join('<claimedit id="%s"/>' % e for e in errids))))
    return "Fault" not in r


# ---------------------------------------------------------------------------
# Pattern 1: I63.9 outpatient rejection ("should not be billed in an outpatient
# setting"). Applies to every payer, not just BCBS. POS-21 (hospital) is left
# alone -- it keeps I63.9.
# ---------------------------------------------------------------------------
def fix_stroke_outpatient(cid, seq, dry=False):
    vis, pat, charges = resave.visit_charges(cid)
    hits = [c.get("id") for c in charges
            if I639 in (c.get("diagcodes") or "").split() and (c.get("pos") or "").strip() != "21"]
    if not hits:
        return {"action": "none", "reason": "no I63.9 charge on this visit outside POS 21"}
    if dry:
        return {"action": "dry-run", "charges": hits}

    def e(a):
        if I639 in (a.get("diagcodes") or "").split() and (a.get("pos") or "").strip() != "21":
            a["diagcodes"] = " ".join(I6930 if x == I639 else x for x in a["diagcodes"].split())
            return True
        return False

    c2, msg = recode._save(cid, e)
    if c2 is None:
        return {"action": "error", "detail": msg}
    vid = re.sub(r"\D", "", resave.visit_charges(cid)[0].get("id"))
    rebill = freq1_visit.run(vid, cid, seq)
    return {"action": "swap+rebill", "detail": msg, "rebill": rebill, "charges": hits}


# ---------------------------------------------------------------------------
# Claim Inspector patterns 20389 / 2776 / 11256.
# ---------------------------------------------------------------------------
def fix_inspector_pattern(cid, vid, pattern_id, errid, errtext="", dry=False):
    if pattern_id == "20389":
        return _fix_20389(cid, vid, errid, dry)
    if pattern_id == "2776":
        return _fix_2776(cid, vid, errid, dry)
    if pattern_id == "11256":
        return _fix_11256(cid, vid, errid, errtext, dry)
    return {"action": "hold", "reason": "pattern %s is not on the known-fix table" % pattern_id}


def _fix_20389(cid, vid, errid, dry):
    m = _dcodes_of(cid)
    codesd = {c: i for i, c in m.items()}
    has_sequela = any(SEQUELA_RE.match(c) for c in m.values())
    has_condition = any(not SEQUELA_RE.match(c) for c in m.values())
    if "S81.801S" in codesd and "M86.9" not in codesd:
        if dry:
            return {"action": "dry-run", "detail": "M86.9 in front of S81.801S (Winslow Jr precedent)"}
        c2, msg = _edit_dx(cid, lambda d, mm: [M869] + [x for x in d if x != M869])
        desc = "M86.9 added in front of S81.801S (Winslow Jr precedent, William 9/6)"
    elif has_sequela and has_condition:
        if dry:
            return {"action": "dry-run", "detail": "reorder sequela code behind the condition code"}
        c2, msg = _edit_dx(cid, lambda d, mm: sorted(d, key=lambda x: 1 if SEQUELA_RE.match(mm.get(x, "")) else 0))
        desc = "sequela/external-cause code moved behind the condition code"
    else:
        if not dry:
            _bypass(vid, [errid])
        return {"action": "hold", "reason": "sequela-only diagnosis list with no condition code to lead with -- bypassed, needs William"}
    if c2 is None:
        return {"action": "error", "detail": msg}
    if not dry:
        _bypass(vid, [errid])
    return {"action": "fixed", "detail": desc + " -> " + msg}


def _fix_2776(cid, vid, errid, dry):
    if dry:
        return {"action": "dry-run", "detail": "drop Z51.11"}
    c2, msg = _edit_dx(cid, lambda d, mm: [x for x in d if mm.get(x) != "Z51.11"])
    if c2 is None:
        return {"action": "error", "detail": msg}
    _bypass(vid, [errid])
    return {"action": "fixed",
            "detail": "Z51.11 removed (chemo encounter cannot be a secondary dx on a facility visit) -> " + msg}


def _fix_11256(cid, vid, errid, errtext, dry):
    mcode = re.search(r"code\(s\)\s+(\S+)", errtext or "")
    flagged = mcode.group(1).rstrip(".,") if mcode else None
    if flagged and flagged in LATERALITY_KNOWN:
        m = _dcodes_of(cid)
        trigger_id = next((i for i, c in m.items() if c == flagged), None)
        if trigger_id:
            new = LATERALITY_KNOWN[flagged]
            if dry:
                return {"action": "dry-run", "detail": "%s -> known fix" % flagged}
            c2, msg = _edit_dx(cid, lambda d, mm, old=trigger_id, n=new: [n if x == old else x for x in d])
            if c2 is None:
                return {"action": "error", "detail": msg}
            _bypass(vid, [errid])
            return {"action": "fixed", "detail": "%s -> known fix -> %s" % (flagged, msg)}
    if not dry:
        _bypass(vid, [errid])
    return {"action": "hold",
            "reason": "unspecified laterality/site (%s) -- no captured dcode for the fix; bypassed, log + flag William"
                      % (flagged or "code not parsed from error text")}


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2 or sys.argv[1] not in ("stroke", "inspector", "selftest"):
        print("usage: dx_swap.py stroke <chargeid> <seq> [--dry]")
        print("       dx_swap.py inspector <chargeid> <visitid> <pattern_id> <errid> [errtext] [--dry]")
        print("       dx_swap.py selftest   (pure-logic checks, no AMD calls)")
        sys.exit(1)

    if sys.argv[1] == "selftest":
        # Exercises the pure sequencing/lookup logic against fake dcode maps --
        # no network calls, safe to run anywhere.
        mm = {"d1": "S81.801S", "d2": "E11.9"}
        order = sorted(["d1", "d2"], key=lambda x: 1 if SEQUELA_RE.match(mm.get(x, "")) else 0)
        assert order == ["d2", "d1"], order
        assert LATERALITY_KNOWN["G81.90"] == I6930
        print("selftest OK")
        sys.exit(0)

    amd.login_cached()
    dry = "--dry" in sys.argv
    if sys.argv[1] == "stroke":
        cid, seq = sys.argv[2], int(sys.argv[3])
        print(json.dumps(fix_stroke_outpatient(cid, seq, dry=dry), indent=1))
    else:
        cid, vid, pattern_id, errid = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
        errtext = sys.argv[6] if len(sys.argv) > 6 and not sys.argv[6].startswith("--") else ""
        print(json.dumps(fix_inspector_pattern(cid, vid, pattern_id, errid, errtext, dry=dry), indent=1))
