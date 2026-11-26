#!/usr/bin/env python3
# PLAIN ENGLISH (the WORK QUEUE actor - William 11/26/2026: the runs do the next step on every denied and every unpaid claim WITHOUT
#   his click, by his standing rules; appeals, records and anything no rule covers come to him as ONE card per visit)
# Decides: nothing new - it carries out the next step the planner (work_queue.py -> registers/work_queue.json) wrote for each DUE visit.
#   DRY BY DEFAULT: without --live it reads AdvancedMD and prints what it would do, and writes nothing there. For each due row it first
#   re-reads the visit LIVE (gettxhistory) and SKIPS it when: nothing is left on it, a payment came since the row was planned, it was
#   acted on (or re-sent by any helper - registers/rebill_log.jsonl) in the last 30 days, it is on a watch list (FLO99 balances, the
#   timely-filing watch, a chart the board holds on William's turn). Then ONE action per visit per run, through the proven helpers only:
#     WRITE_OFF  - manual_post.post with the code the rule names (WOLATE, WONCS, WOINS, WOCLTREQ, WOCAID2ND only), the live insurance
#                  balance of each charge (manual_post never over-applies); a cost-share balance on the patient side goes back first
#                  (move_to_ins.move, no rebill)
#     WOINSBANK  - paid but never posted: ONLY when the claim-status check number matches a deposit on the Treasury ledger (--treasury,
#                  deposits_ledger.csv from Drive "treasury payments"; William 11/26/2026 decision 2) - otherwise a LIST line, nothing written
#     FIX_DX     - dx_primary_fix.fix_visit with the payer's claim number (frequency 7 - the claim was adjudicated); no number = his card
#     HOSPICE_GV - working_denials_act.act (fix kind hospice: GV + its own ONE frequency-1 rebill)
#     REDATE     - CO-151 on CCM: the visit re-entered on the last day of its month (addvisit + updvisitwithnewcharges, the pattern of
#                  redate_recode_1119.py, all its lines in ONE new visit), then the old lines' postings and charges voided
#     SECONDARY  - move_to_ins.move(--no-rebill) only when a balance must move or the visit order lacks the secondary, then ONE
#                  freq1_visit.run to the secondary's sequence
#     RESEND     - ONE freq1_visit.run to the billed plan; a silent claim first passes the free checks (the ERA cache, AdvancedMD's free
#                  eligibility answer on the billed plan: inactive = the RULE C cascade instead)
#     CASCADE    - listed for the run's RULE C cascade; `--reroute <visit>=<order>` then does ONE re-route (freq1_visit.reroute, or
#                  move_to_ins --no-rebill + freq1_visit.run when a balance sits on the patient side); `--no-plan <visit>` = his card
#     OWNER / FOLLOW_UP - one card per visit (outbox/work_queue_cards_<stamp>.json; with --live and --board-file the ops go into this
#                  run's board file through board_ops / facesheets_needed.handback_op) and, where an appeal fits, an APPEAL line with the
#                  facts the run needs to draft the letter (a Google Doc in Drive 'appeals' + a Gmail draft to William - never in git)
#   Every rebill goes through amd.rebill_charge inside those helpers (the deceased guard, one per visit per run, rebill_log.jsonl).
# Rules it uses: no action without a rule id; no write-off outside the named codes; never two rebills of one visit inside 30 days;
#   at most --max actions a run (default 25: a live pass stays inside the Bash limit); safe to start twice the same day - its own register
#   registers/work_queue_act_<stamp>.jsonl (visit and chart ids, action, rule id, dollars at the action, result - ids and amounts only)
#   is read back first and a visit acted on in the last 30 days (or carded under the same rule) is skipped.
# Never touches: a visit the queue did not plan, a visit with a payment since the plan, FLO99 balances, watch visits, patient names in
#   any register (a new board card carries the chart's name and birth date only in the board file, which goes to Drive, never to git).
# 11/26/2026, the independent review's eleven fixes: WOINSBANK only on a MATCHED Treasury row and never when the check is already posted on the
#   visit; 'a payment since the plan' goes by when it was POSTED (createtime) and counts the basis day; no resend / re-route to a payer that
#   already paid on the visit; a secondary is billed only after the claim detail shows it does NOT hold the claim already (no X-marked
#   insurance bill, none to it, none on/after the primary's payment - rules.md 9/21/2026); FLO99 on ANY line holds the visit; every write-off
#   line is guarded before the first post and whatever was posted is recorded; the re-date records its new visit at once, never makes a
#   second one, voids what it wrote when a step does not finish and cards William; frequency 7 only with a well-formed claim number of THAT
#   payer; the action is the step its RULE names; each write-off code is the one its rule names; AdvancedMD's answers go only into
#   logs/work_queue_act_<stamp>.log (workspace), never into a register; a dry start buys no look-up and asks no eligibility; the deceased
#   guard is asked before any helper edits a visit it will send - not cleared = no edit, a HOLD-DEATH line, outbox/work_queue_death_<stamp>.json.
#   python3 work_queue_act.py [--stamp <run stamp>] [--queue registers/work_queue.json] [--max 25] [--max-cards 50] [--max-cascade 10]
#       [--treasury work/deposits_ledger.csv[,availity_remit_recon_<stamp>.csv]] [--board-file outbox/board_updates_<stamp>.json
#        --items-dir <the board read>] [--reroute <visit>=<order> ...] [--no-plan <visit>[,...]] [--only <visit>[,...]] [--live]
import argparse, collections, datetime, glob, json, os, re, sys, time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import work_queue as wq

ALLOWED_WO = wq.ALLOWED_WO
REBILL_STEPS = ("FIX_DX", "HOSPICE_GV", "REDATE", "SECONDARY", "RESEND", "REROUTE")
CCM = wq.CCM_CODES
COSTSHARE_CODES = ("WOCAID2ND", "WOCLTREQ")          # nothing stays on the patient (rules.md 9/11, 10/13) - a patient-side balance goes back first


class Refused(Exception):
    """A guard refused the action - nothing was sent."""


def _f(x):
    try: return float(x or 0)
    except (TypeError, ValueError): return 0.0
def _d(x): return wq._digits(x)
def _now(): return datetime.datetime.now(datetime.timezone.utc)
def _mdy(d): return d.strftime("%m/%d/%Y")
def _answer(fn, *a):
    """A void helper's answer (ok, message) -> ok; an exception is a 'no'."""
    try:
        r = fn(*a)
        return bool(r[0]) if isinstance(r, (tuple, list)) else bool(r)
    except Exception:
        return False
def cut(text):
    """A helper's answer as a register or report line may carry it: everything from VERIFY-FAILED / FAULT / FAILED on is AdvancedMD's own text
    (a fault can name the patient) and is dropped - the whole answer is in the workspace-only log (the independent review of 11/26/2026, finding 9)."""
    return re.sub(r"(VERIFY-FAILED|FAULT|FAILED).*", r"\1", str(text), flags=re.I | re.S)


# the ONE code each standing write-off rule names (the independent review of 11/26/2026, finding 8); WO-OLD-1102 takes the code of the aging rule
# that decided the row (work_queue.code_for of its 'aging_rule' text, which the planner writes beside it)
RULE_CODE = {"WO-CCM-HOSPICE-1015": "WONCS", "WO-CCM-MEDICAID-0911": "WONCS", "WO-CROSSOVER-0911": "WOCAID2ND", "WO-PAID-NOT-POSTED-1102": "WOINSBANK"}


def guard_writeoff(code, rule, carrier, treasury_ok=False, aging_rule=None):
    """The write-off code guard (William 11/26/2026): a rule id, a code the rulebook names AND the one code that rule names, WOINSBANK only
    on a Treasury match, never FLO99."""
    if not rule or rule not in wq.RULES: raise Refused("no rule id - no write-off")
    if rule not in wq.WRITE_OFF_RULES: raise Refused("rule %s is not a write-off rule" % rule)
    if code not in ALLOWED_WO: raise Refused("code %s is not one the rulebook names (%s)" % (code, "/".join(ALLOWED_WO)))
    want = wq.code_for(aging_rule) if rule == "WO-OLD-1102" else RULE_CODE.get(rule)
    if code != want: raise Refused("code %s is not the code rule %s names (%s)" % (code, rule, want or "the row's aging rule names none"))
    if code == "WOINSBANK" and not treasury_ok: raise Refused("WOINSBANK only when the check number matches a Treasury ledger deposit")
    if code != "WOINSBANK" and rule == "WO-PAID-NOT-POSTED-1102": raise Refused("a paid-not-posted claim is written off WOINSBANK only")
    if str(carrier or "").strip() == "FLO99": raise Refused("FLO99 balances wait for the paper-check reconciliation (rules.md 9/22/2026)")


# ------------------------------------------------------------------------------------------------------------------ the AdvancedMD door
class Port:
    """Every AdvancedMD read and write the actor makes, through the proven helpers (the self-test puts its stand-in AdvancedMD behind them)."""
    def login(self):
        import amd; amd.login_cached()
    def history(self, pid, vid):
        import txh; return txh.fetch_visit(pid, vid)
    def chart_history(self, pid):
        import txh; return txh.fetch(pid)
    def detail(self, cid):
        import resave; return resave.detail(cid)
    def visit_charges(self, cid):
        import resave; return resave.visit_charges(cid)
    def plans(self, pid):
        import elig_amd; return elig_amd.plans(pid)
    def eligibility(self, pid, insid):
        import elig_amd; return elig_amd.run_plan(pid, insid)
    def post_writeoff(self, cid, carrier, amount, code, check, depositdate, note, dry):
        import manual_post; return manual_post.post(cid, carrier, 0.0, amount, code, check, depositdate, note, dry=dry)
    def carriers(self):
        import manual_post; return manual_post.CAR
    def move(self, cid, order, dry):
        import move_to_ins; return move_to_ins.move(cid, order, dry, rebill=False)
    def freq1(self, vid, cid, seq):
        import freq1_visit; return freq1_visit.run(str(vid), str(cid), seq)
    def reroute(self, vid, cid, order, dry):
        import freq1_visit; return freq1_visit.reroute(str(vid), str(cid), order, dry=dry)
    def dx_fix(self, pid, vid, cid, seq, dry, icn):
        import dx_primary_fix; return dx_primary_fix.fix_visit(pid, vid, str(cid), seq, dry=dry, icn=icn)
    def hospice(self, item, dry):
        import working_denials_act; return working_denials_act.act(item, dry)
    def death_check(self, pid, dos, carrier, code, allow_lookup=True):
        import deceased_guard; return deceased_guard.check(pid, dos, carrier, code, allow_lookup=allow_lookup)
    def death_covered(self, pid, dos):
        import deceased_guard; return deceased_guard.covered(pid, dos)
    def carrier_names(self):
        """carrier code -> its name (carriers.json, the rich form carN -> [code, name]); {} for the simple form."""
        try: j = json.load(open("carriers.json"))
        except (OSError, ValueError): return {}
        return {v[0]: str(v[1] if len(v) > 1 else "") for v in j.values() if isinstance(v, (list, tuple)) and v}
    def post(self, body):
        import amd; return amd.post(body)
    def msg(self, *a, **k):
        import amd; return amd.msg(*a, **k)
    def void_state(self, cid):
        import void_tx; return void_tx.charge_state(cid)
    def void_writeoff(self, pid, cid, woid):
        import void_tx; return void_tx.void_writeoff(pid, cid, woid)
    def void_payment(self, pid, cid, payid):
        import void_tx; return void_tx.void_payment(pid, cid, payid)
    def void_charge(self, pid, cid):
        import void_tx; return void_tx.void_charge(pid, cid)


class Visit:
    """One visit as its live history shows it: the non-void charges of THIS visit, their balances, payments and bill dates."""
    def __init__(self, pid, vid, root):
        self.pid, self.vid, self.charges = str(pid), str(vid), []
        for c in root.iter("charge"):
            if c.get("void") == "1" or str(c.get("visit") or c.get("visitid") or vid) != str(vid): continue
            if str(c.get("fee") or "").startswith("-"): continue
            pays = []; zero = []
            for p in c.iter("payment"):
                if p.get("void") == "1": continue
                amt = abs(_f(p.get("amount")))
                # date = the check / deposit date; posted = when it was POSTED (createtime, else date) - 'a payment since the plan' goes by posted
                # (the independent review of 11/26/2026, finding 2: a remit posted today with a check dated before the plan was invisible)
                (pays if amt > 0.005 else zero).append({"date": wq._date(p.get("date")), "posted": wq._date(p.get("createtime")) or wq._date(p.get("date")),
                                                        "amount": amt, "carrier": (p.get("carrier") or "").strip(), "check": wq.norm_check(p.get("checknumber"))})
            self.charges.append({"cid": _d(c.get("id")), "cpt": (c.get("proccode") or "").strip(), "carrier": (c.get("carrier") or "").strip(),
                                 "dos": wq._date(c.get("dos") or c.get("dateofservice")), "fee": _f(c.get("fee") or c.get("amount")),
                                 "insbal": round(_f(c.get("insbal") or c.get("insbalance")), 2), "patbal": round(_f(c.get("patbal") or c.get("patbalance")), 2),
                                 "billdate": wq._date(c.get("billdate")), "mods": (c.get("modcodes") or c.get("modifiers") or ""), "pays": pays, "zero": zero})
    @property
    def insbal(self): return round(sum(c["insbal"] for c in self.charges), 2)
    @property
    def patbal(self): return round(sum(c["patbal"] for c in self.charges), 2)
    @property
    def carrier(self): return next((c["carrier"] for c in self.charges if c["carrier"]), "")
    @property
    def last_billed(self): return max([c["billdate"] for c in self.charges if c["billdate"]] or [None], key=lambda d: d or datetime.date.min)
    def payments_since(self, day):
        return [p for c in self.charges for p in c["pays"] if day and p["posted"] and p["posted"] >= day]      # POSTED on or after the day of the evidence
    def checks_posted(self):
        """Every check number posted on the visit - money or $0 lines alike (the remit is posted either way)."""
        return {p["check"] for c in self.charges for p in c["pays"] + c["zero"] if p["check"]}
    def paid_by(self, carrier):
        """The live insurance payments (money) of this carrier code on the visit."""
        return [p for c in self.charges for p in c["pays"] if carrier and p["carrier"] == carrier]
    @property
    def dos(self): return next((c["dos"] for c in self.charges if c["dos"]), None)
    @property
    def lead_cpt(self):
        """The procedure the deceased guard is asked about: a care-management code when the visit has one (it decides the guard's look-up), else the first."""
        cpts = [c["cpt"] for c in self.charges if c["cpt"]]
        return next((x for x in cpts if x in CCM), cpts[0] if cpts else "")
    def first_cid(self): return self.charges[0]["cid"] if self.charges else ""


# ------------------------------------------------------------------------------------------------------------------ the actor
class Actor:
    def __init__(self, a, port=None, out=print):
        self.a, self.port, self.say = a, port or Port(), out
        self.live = bool(a.live); self.stamp = a.stamp or _now().strftime("%Y-%m-%dT%H%MZ"); self.today = wq._date(a.today) or datetime.date.today()
        self.regs = a.registers
        q = wq._load(a.queue, {}) or {}
        self.queue = q; self.planned = wq._date(q.get("planned")) or self.today
        dirs = [d for d in (self.regs, os.path.join(a.repo, "practices", "ehpa", "registers") if a.repo else None) if d and os.path.isdir(d)]
        self.dirs = dirs
        self.acted = wq.last_actions(wq.act_lines(dirs))
        self.deaths = []      # this start's HOLD-DEATH visits: the date-of-death rule's list (outbox/work_queue_death_<stamp>.json, ids only)
        # AdvancedMD's own answers (fault texts can name a patient) go ONLY into this workspace log - never into a register (the independent review of
        # 11/26/2026, finding 9): logs/ is not copied to the repository by any step
        self.log_path = os.path.join(a.ws or ".", "logs", "work_queue_act_%s%s.log" % (self.stamp, "" if self.live else "_dry"))
        self.rebilled = wq.rebill_dates([os.path.join(d, "rebill_log.jsonl") for d in dirs])
        self.watch = set().union(*[wq.watch_visits(os.path.join(d, "tf_writeoff_watch.json")) for d in dirs]) if dirs else set()
        self.board = wq.board_charts(dirs)[0] if dirs else set()
        self.treasury = wq.treasury_checks([p for p in (a.treasury or "").split(",") if p.strip()])
        self.reg_path = os.path.join(self.regs, "work_queue_act_%s%s.jsonl" % (self.stamp, "" if self.live else "_dry"))
        self.cards = []; self.counts = collections.Counter(); self.skips = collections.Counter(); self.done = set(); self.n_actions = 0
        self.reroute = dict(x.split("=", 1) for x in (a.reroute or []) if "=" in x)      # each --reroute is ONE visit=order (an order holds commas)
        self.reroute = {_d(k): v.strip() for k, v in self.reroute.items() if _d(k) and re.fullmatch(r"\d+(,\d+)*", v.strip())}
        self.no_plan = {_d(x) for x in (a.no_plan or "").split(",") if _d(x)}
        self.only = {_d(x) for x in (a.only or "").split(",") if _d(x)}

    # ---- the register: ids, codes and amounts only
    def full_log(self, row, action, text):
        """The helper's whole answer, into the workspace-only log (logs/work_queue_act_<stamp>.log) - never a register, never the repository."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)
            with open(self.log_path, "a") as fh: fh.write("%s v%s %s %s: %s\n" % (_now().strftime("%Y-%m-%dT%H:%M:%SZ"), row.get("visitid"), action, row.get("rule"), text))
        except OSError: pass

    def record(self, row, action, dollars, result, ok, code=None, extra=None):
        self.full_log(row, action, result)
        e = {"at": _now().strftime("%Y-%m-%dT%H:%M:%SZ"), "stamp": self.stamp, "visit": str(row["visitid"]), "pid": str(row.get("pid") or ""),
             "action": action, "rule": row["rule"], "dollars": round(_f(dollars), 2), "result": re.sub(r"[^\w .:;,=$/()+#-]", "", cut(result))[:160],
             "ok": bool(ok), "live": self.live}
        if code: e["code"] = code
        if extra: e.update(extra)
        os.makedirs(os.path.dirname(os.path.abspath(self.reg_path)), exist_ok=True)
        with open(self.reg_path, "a") as fh: fh.write(json.dumps(e) + "\n")
        self.done.add(str(row["visitid"]))
        s = self.acted.setdefault(str(row["visitid"]), {"acted": None, "card": {}, "tries": 0})
        if action != "CARD" and ok and action in wq.COUNTING: s["acted"] = self.today
        if e.get("wrote"): s["acted"] = self.today
        if e.get("new_visit"): s["new_visit"] = str(e["new_visit"])
        if action == "HOLD-DEATH": s["death"] = self.today
        if action == "CARD": s["card"][row["rule"]] = self.today
        return e

    def skip(self, row, why):
        self.skips[why.split(" (")[0].split(" - ")[0]] += 1
        self.say("SKIP v%s %s: %s" % (row["visitid"], row["rule"], why))
        return None

    def refuse(self, row, why):
        self.say("REFUSED v%s %s: %s - nothing sent" % (row["visitid"], row["rule"], why)); self.skips["refused by a guard"] += 1
        return None

    # ---- the deceased guard BEFORE any helper edits a visit it will send (the independent review of 11/26/2026, finding 11)
    def death_hold(self, row, v, dos=None, carrier=None, cpt=None):
        """True when the visit must not be touched. deceased_guard.check once - a look-up only in a live start (a dry start buys none and says
        'DRY - date of death not checked' when the cache does not cover the date). A block or a death on record whose day is not known (DayLost):
        nothing is edited or sent, a HOLD-DEATH line is recorded (later starts and the planner hold the visit) and the visit goes on the
        date-of-death rule's list. Any other error: nothing is edited this start, no line (the next start asks again)."""
        dos = dos or v.dos; carrier = v.carrier if carrier is None else carrier; cpt = cpt or v.lead_cpt
        diso = dos.isoformat() if hasattr(dos, "isoformat") else str(dos or "")
        try:
            blocked, _ = self.port.death_check(v.pid, diso, carrier, cpt, allow_lookup=self.live)      # (its words carry the day of death: never in a line)
            kind = "blocked"
        except Exception as e:
            if type(e).__name__ != "DayLost":
                self.skip(row, "the date-of-death check gave no answer (%s) - nothing edited; the next start asks again" % type(e).__name__)
                return True
            blocked, kind = True, "day not known"      # a date of death on record whose day cannot be read here: not cleared
        if not blocked:
            if not self.live:
                try: covered = self.port.death_covered(v.pid, diso)
                except Exception: covered = False
                if not covered: self.say("  DRY - date of death not checked v%s DOS %s (a dry start buys no look-up)" % (v.vid, diso))
            return False
        self.counts["HOLD-DEATH"] += 1
        self.deaths.append({"visit": str(row["visitid"]), "pid": v.pid, "charges": [c["cid"] for c in v.charges], "dos": diso, "kind": kind, "rule": row["rule"]})
        self.say("HOLD-DEATH v%s pat%s %s DOS %s: the deceased guard did not clear it (%s) - nothing edited or sent; the date-of-death rule decides (void)" % (
            row["visitid"], v.pid, row["rule"], diso, kind))
        self.record(row, "HOLD-DEATH", v.insbal, "deceased guard: %s - DOS %s; nothing edited or sent" % (kind, diso), True, extra={"death": kind})
        return True

    # ---- the live read and the skips every row passes
    def resolve_pid(self, row):
        if row.get("pid"): return row["pid"]
        cid = row.get("charge")
        if not cid: return ""
        try:
            m = re.search(r'<patient\s(?:[^>]*?\s)?id="(?:pat)?(\d+)"', self.port.detail(cid))
            return m.group(1) if m else ""
        except Exception:
            return ""

    def precheck(self, row):
        """-> Visit, or None after a SKIP line. The live re-read and the skips of the specification (B3)."""
        vid = str(row["visitid"])
        if vid in self.done: return self.skip(row, "already acted on in this run - one action per visit")
        if vid in self.watch: return self.skip(row, "on the timely-filing watch")
        pid = self.resolve_pid(row)
        if not pid: return self.skip(row, "chart unknown - the visit's charge detail could not be read")
        row["pid"] = pid
        if pid in self.board: return self.skip(row, "the chart waits on William's turn on the board")
        last = self.acted.get(vid) or {}
        if last.get("death"): return self.skip(row, "held: the deceased guard did not clear it on %s - the date-of-death rule decides" % last["death"].isoformat())
        for d in (last.get("acted"), self.rebilled.get(vid)):
            if d and (self.today - d).days < wq.WAIT_DAYS:
                return self.skip(row, "acted on %s - the 30-day wait" % d.isoformat())
        try: v = Visit(pid, vid, self.port.history(pid, vid))
        except Exception as e: return self.skip(row, "visit history unreadable (%s) - next run" % type(e).__name__)
        if not v.charges: return self.skip(row, "no live charge on the visit")
        if any(c["carrier"] == "FLO99" for c in v.charges): return self.skip(row, "FLO99 balance on a line of the visit - the paper-check hold")
        if v.insbal + v.patbal <= 0.005: return self.skip(row, "nothing left on the visit - settled")
        paid = v.payments_since(wq._date(row.get("basis")) or self.planned)
        if paid and row["step"] != "FOLLOW_UP": return self.skip(row, "a payment came since the plan (posted %s, $%.2f)" % (paid[0]["posted"], paid[0]["amount"]))
        lb = v.last_billed
        if lb and (self.today - lb).days < wq.WAIT_DAYS and row["step"] not in ("FOLLOW_UP",):
            return self.skip(row, "re-sent %s - the 30-day wait" % lb.isoformat())
        return v

    def cap(self, row):
        if self.n_actions >= self.a.max:
            self.skips["the run's action cap"] += 1
            self.say("LATER v%s %s: the run's cap of %d actions is reached - the next run" % (row["visitid"], row["rule"], self.a.max))
            return True
        return False

    # ---- the actions
    def act(self, row):
        step = row["step"]
        if step != wq.RULES[row["rule"]][0]:      # the action comes from the step the RULE names, never from a damaged row (the review of 11/26/2026, finding 8)
            return self.refuse(row, "step %s does not match its rule (the rule's step is %s)" % (step, wq.RULES[row["rule"]][0]))
        if step == "CASCADE": return self.cascade(row)
        if step in ("OWNER", "FOLLOW_UP"): return self.owner(row)
        if step in ("WAIT", "HOLD", "LIST"): self.counts[step] += 1; return None
        if step == "WOINSBANK" and not [c for c in (row.get("checks") or []) if wq.norm_check(c) in self.treasury]:
            return self.woinsbank(row, None)                       # no Treasury match: a LIST line - nothing is read or written, no cap used
        if self.cap(row): return None
        v = self.precheck(row)
        if v is None: return None
        fn = {"WRITE_OFF": self.write_off, "WOINSBANK": self.woinsbank, "FIX_DX": self.fix_dx, "HOSPICE_GV": self.hospice,
              "REDATE": self.redate, "SECONDARY": self.secondary, "RESEND": self.resend}.get(step)
        if not fn: return self.skip(row, "no action for step %s" % step)
        try:
            return fn(row, v)
        except Refused as e:
            return self.refuse(row, str(e))
        except Exception as e:
            self.say("ERROR v%s %s: %s (the whole text: %s)" % (row["visitid"], row["rule"], type(e).__name__, self.log_path)); self.skips["error"] += 1
            self.full_log(row, "ERROR", "%s %s" % (type(e).__name__, e))
            return None

    def finish(self, row, action, dollars, result, ok, code=None, extra=None):
        self.n_actions += 1
        self.counts[action + ("" if self.live else " (dry)")] += 1
        short = cut(result)
        self.say("ACT v%s pat%s %s %s $%.2f -> %s%s%s" % (row["visitid"], row["pid"], action + (" " + code if code else ""), row["rule"], _f(dollars), short,
                                                       (" (AdvancedMD's whole answer: %s)" % self.log_path) if short != str(result) else "", "" if self.live else " [DRY]"))
        return self.record(row, action, dollars, result, ok, code, extra)

    def wo_lines(self, row, v, code, cars, treasury_ok, with_patient=False):
        """[(charge, carrier code)] of every line a write-off would touch, EVERY one through the code guard and the carrier-code check before
        anything is posted (the independent review of 11/26/2026, finding 4: the guard ran line by line, after the first post)."""
        out = []
        for c in v.charges:
            if c["insbal"] <= 0.004 and not (with_patient and c["patbal"] > 0.004): continue
            car = c["carrier"] if c["carrier"] in cars else (row.get("payer") if row.get("payer") in cars else c["carrier"])
            guard_writeoff(code, row["rule"], car, treasury_ok=treasury_ok, aging_rule=row.get("aging_rule"))
            if car not in cars: raise Refused("line c%s: no carrier code %s for the write-off" % (c["cid"], car))
            out.append((c, car))
        return out

    def write_off(self, row, v, code=None, check=None, depositdate=None, note=None, treasury_ok=False):
        code = code or row.get("code")
        guard_writeoff(code, row["rule"], v.carrier, treasury_ok=treasury_ok, aging_rule=row.get("aging_rule"))
        cars = self.port.carriers()
        move = code in COSTSHARE_CODES and v.patbal > 0.005
        if not self.wo_lines(row, v, code, cars, treasury_ok, with_patient=move): return self.skip(row, "no open insurance balance to write off")
        if move:                                                       # nothing stays on the patient: the cost-share goes back to insurance first
            r = self.port.move(v.first_cid(), None, not self.live)
            self.say("  move_to_ins (no rebill) v%s: %s" % (v.vid, cut(r)))
            if self.live:
                v = Visit(v.pid, v.vid, self.port.history(v.pid, v.vid))
        lines = self.wo_lines(row, v, code, cars, treasury_ok)          # the lines as they stand now - every one guarded again, before the first post
        if not lines: return self.skip(row, "no open insurance balance to write off")
        total, res, ok = 0.0, [], True
        rule_words = wq.RULES[row["rule"]][2]
        note = re.sub(r'[<>&"]', "", note or ("Work queue %s - rule %s: %s (William 11/26/2026)" % (self.stamp, row["rule"], rule_words)))[:250]
        try:
            for c, car in lines:
                good, msg = self.port.post_writeoff(c["cid"], car, c["insbal"], code, check or ("WQ" + self.stamp[:10].replace("-", "")), depositdate, note, not self.live)
                res.append("c%s %s $%.2f %s" % (c["cid"], code, c["insbal"], "ok" if good else "FAILED " + re.sub(r"\s+", " ", str(msg))[:400]))      # (the register keeps only 'FAILED')
                if good: total += c["insbal"]
                else: ok = False
        except Exception as e:                                         # whatever was posted before it is recorded all the same (ok=False)
            ok = False; res.append("stopped at line %d of %d: %s" % (len(res) + 1, len(lines), type(e).__name__))
            self.full_log(row, "WRITE_OFF", "%s %s" % (type(e).__name__, e))
        return self.finish(row, "WOINSBANK" if code == "WOINSBANK" else "WRITE_OFF", total, "; ".join(res), ok and total > 0, code)

    def woinsbank(self, row, v):
        checks = [c for c in (row.get("checks") or []) if c]
        hit = [c for c in checks if wq.norm_check(c) in self.treasury]
        if not hit:
            self.counts["LIST"] += 1
            self.say("LIST v%s pat%s %s paid not posted $%.2f - %s: stays on William's list (decision 2)" % (
                row["visitid"], row.get("pid") or "?", row.get("payer"), v.insbal if v else _f(row.get("amount")),
                ("check %s not on the Treasury ledger" % ",".join(checks)) if checks else "no check number on file"))
            return None
        posted = {wq.norm_check(c) for c in checks} & v.checks_posted()
        if posted:                                                     # the remit IS posted on the visit: not 'paid, never posted' (review of 11/26/2026, finding 2)
            return self.skip(row, "check %s is already posted on the visit - not paid-never-posted; what is left waits for its own rule" % ",".join(sorted(posted)))
        d = wq._date(row.get("paid_on")) or self.today
        note = ("Paid not posted - payer %s, check %s, paid %s, $%.2f; Treasury deposit matched (rules.md 11/2/2026; William 11/26/2026) - work queue %s" % (
            row.get("payer"), hit[0], d.isoformat(), _f(row.get("paid") or v.insbal), self.stamp))[:250]
        return self.write_off(row, v, code="WOINSBANK", check=hit[0], depositdate=_mdy(d), note=note, treasury_ok=True)

    def seq_of(self, v):
        vis, pat, allc = self.port.visit_charges(v.first_cid())
        order = [x for x in str((vis.get("insorder") if vis is not None else "") or "").replace(" ", "").split(",") if x]
        return order

    def seq_for(self, v, payer):
        """The chart sequence of the payer the row names (getdemographic plans, the carrier code -> carN of carriers.json); no payer named = the
        first plan of the visit's order. None when that payer has no plan in force on the date of service."""
        if not payer: return (self.seq_of(v) or [None])[0]
        car = self.port.carriers().get(payer)
        pa, plans = self.port.plans(v.pid)
        dos = v.charges[0]["dos"]
        live = [p for p in plans if car and p.get("carrier") == car and not (wq._date(p.get("enddate")) and dos and wq._date(p.get("enddate")) < dos)]
        return str(live[0].get("sequence")) if len(live) == 1 else None

    def icn_live(self, v, payer):
        """The payer's claim number on the posted ERA payments of THAT payer on the visit (getchargedetaildataicd10: the <payment> carries
        origrefnum and carrierfid - the carrier's number without 'car'). Only when exactly ONE distinct number remains; else '' (never a guess -
        the independent review of 11/26/2026, finding 7: another payer's $0 denial gave Medicare's corrected claim BCBS's number)."""
        car = str(self.port.carriers().get(payer) or "") if payer else ""
        if not car: return ""
        found = set()
        for c in v.charges:
            try: root = ET.fromstring(self.port.detail(c["cid"]))
            except Exception: continue
            for p in root.iter("payment"):
                if p.get("void") == "1": continue
                fid = (p.get("carrierfid") or "").strip()
                mine = fid and (fid == car or fid.upper() == payer.upper() or (_d(fid) and _d(fid) == _d(car)))
                n = (p.get("origrefnum") or "").strip()
                if mine and n: found.add(n)
        return found.pop() if len(found) == 1 else ""

    def fix_dx(self, row, v):
        if self.death_hold(row, v): return None
        row_icn = str(row.get("icn") or "").strip()
        live = self.icn_live(v, row.get("payer"))
        icn = row_icn or live
        why = None
        if row_icn and live and row_icn != live: why = "the claim number on file is not the one on %s's remit" % row.get("payer")
        elif not re.fullmatch(r"[A-Za-z0-9-]{6,30}", icn or ""): why = "correction needs the payer's claim number" + (" (the one on file is not well-formed)" if icn else "")
        if why:
            row = dict(row, rule="OWNER-NO-ICN", step="OWNER", turn="william", kind=why)
            return self.owner(row, v=v)
        seq = self.seq_for(v, row.get("payer"))
        if not seq: return self.skip(row, "no single plan of %s on the chart - next plan" % row.get("payer"))
        r = self.port.dx_fix(v.pid, v.vid, v.first_cid(), seq, not self.live, icn)
        if str(r).startswith(("OK ", "SKIP")):                   # the cascade finds nothing to change: no rule makes the correction - his card
            return self.owner(dict(row, rule="OWNER-CORRECT", step="OWNER", turn="william", kind="the payer refuses the primary diagnosis; the dx cascade finds nothing to change (%s)" % str(r)[:60]), v=v)
        ok = (" -> 204" in str(r)) if self.live else str(r).startswith("DRY")
        return self.finish(row, "FIX_DX", v.insbal, r, ok)

    def hospice(self, row, v):
        seq = self.seq_for(v, row.get("payer"))
        if not seq: return self.skip(row, "no single plan of %s on the chart - next plan" % row.get("payer"))
        if self.death_hold(row, v): return None
        item = {"who": "v%s" % v.vid, "pid": v.pid, "vid": v.vid, "cid": v.first_cid(), "seq": seq, "fix": "hospice", "note": row["rule"]}
        r = self.port.hospice(item, not self.live)
        ok = (" -> 204" in str(r)) if self.live else str(r).startswith("DRY")
        return self.finish(row, "HOSPICE_GV", v.insbal, r, ok)

    def holds_claim(self, v, sec):
        """Why the secondary `sec` already HOLDS the claim, read from the claim detail first (rules.md 9/21/2026; the independent review of
        11/26/2026, finding 3) - '' when nothing shows it: an insurance bill (<insbill>) marked paperedi="X" (the primary's remit forwarded it - the
        crossover), one that names the secondary's carrier, one billed on/after the primary's payment, the claim's own bill date on/after that
        payment, or a payment of the secondary itself. -> (True, why) when it holds the claim; (False, why) when the visit cannot be judged (no
        answer of the primary on it, a detail that cannot be read) - it waits as well; (False, '') when nothing stands in the way."""
        if v.paid_by(sec): return True, "%s already paid on the visit" % sec
        other = [p for c in v.charges for p in c["pays"] if p["carrier"] != sec] or [p for c in v.charges for p in c["zero"] if p["carrier"] != sec]
        days = [p["date"] for p in other if p["date"]]
        if not days: return False, "no answer of the primary on the visit - the secondary waits for it"
        paid_on = min(days)
        try: root = ET.fromstring(self.port.detail(v.first_cid()))
        except Exception as e: return False, "the claim detail could not be read (%s) - next run" % type(e).__name__
        car = str(self.port.carriers().get(sec) or ""); name = re.sub(r"[^A-Z0-9]", "", str(self.port.carrier_names().get(sec) or "").upper())
        for b in root.iter("insbill"):
            bd = wq._date(b.get("billeddate")); when = bd.isoformat() if bd else "no date"
            if (b.get("paperedi") or "").strip().upper() == "X": return True, "an insurance bill marked X - the crossover - %s" % when
            bname = re.sub(r"[^A-Z0-9]", "", str(b.get("carriername") or "").upper())
            ids = {str(b.get(k) or "").strip() for k in ("carrier", "carrierid", "carrierfid", "carriercode")} - {""}
            if (bname and bname in (name, re.sub(r"[^A-Z0-9]", "", sec.upper()))) or sec in ids or (car and (car in ids or (_d(car) and _d(car) in {_d(x) for x in ids}))):
                return True, "an insurance bill to %s %s" % (sec, when)
            if bd and bd >= paid_on: return True, "billed %s, on/after the primary's payment %s" % (when, paid_on.isoformat())
        if v.last_billed and v.last_billed >= paid_on: return True, "the claim was billed %s, on/after the primary's payment %s" % (v.last_billed.isoformat(), paid_on.isoformat())
        return False, ""

    def plan_at(self, v, seq):
        """The chart's plan at sequence `seq` -> (its carrier id carN, its carrier code by carriers.json); ('', '') when there is none."""
        try: pa, plans = self.port.plans(v.pid)
        except Exception: return "", ""
        rev = {car: code for code, car in self.port.carriers().items()}
        p = next((x for x in plans if str(x.get("sequence")) == str(seq)), None)
        return (p.get("carrier") or "", rev.get(p.get("carrier"), "")) if p else ("", "")

    def resend(self, row, v):
        seq = self.seq_for(v, row.get("payer"))
        if not seq: return self.skip(row, "no single plan of %s on the chart - next plan" % row.get("payer"))
        order = [seq]
        if row.get("payer") and v.carrier and row["payer"] != v.carrier:
            return self.skip(row, "billed to %s now, planned for %s - next plan" % (v.carrier, row["payer"]))
        target = row.get("payer") or v.carrier
        got = v.paid_by(target)
        if got: return self.skip(row, "%s already paid on this visit (posted %s, $%.2f) - a resend would be a second claim" % (target, got[0]["posted"], got[0]["amount"]))
        if [p for c in v.charges for p in c["pays"] if p["carrier"] != target]:      # the target is a secondary: never a second claim to one that holds the crossover
            holds, why = self.holds_claim(v, target)
            if holds and why.startswith("an insurance bill marked X"): return self.skip(row, "the secondary already holds the claim (%s) - claim status, never a second claim (rules.md 9/21/2026)" % why)
        if self.death_hold(row, v): return None
        if row["rule"] == "RESEND-SILENT-NOROUTE-1015":
            era = self.era_cache_hit(v.vid)
            if era: return self.skip(row, "the ERA cache holds a remit for the visit (%s) - the ERA step posts it" % era)
            if not self.live:                                          # a dry start makes no outside call that costs or records (review of 11/26/2026, finding 10)
                return self.finish(row, "RESEND", v.insbal, "DRY free checks (AdvancedMD eligibility on seq %s), then freq1 + rebill seq %s" % (order[0], order[0]), True)
            st = self.free_eligibility(v, order[0])
            if st == "INACTIVE":
                return self.cascade(dict(row, rule="COB-WRONG-PAYER", step="CASCADE", turn="run", why="AdvancedMD eligibility: the billed plan is not active"))
            if st != "ACTIVE": return self.skip(row, "AdvancedMD eligibility gave no answer (%s) - next run" % st)
        if not self.live:
            return self.finish(row, "RESEND", v.insbal, "DRY freq1 + rebill seq %s" % order[0], True)
        r = self.port.freq1(v.vid, v.first_cid(), order[0])
        return self.finish(row, "RESEND", v.insbal, r, " -> 204" in str(r))

    def era_cache_hit(self, vid):
        for p in glob.glob(os.path.join(self.a.ws, "era_details", "*.json")):
            try: j = json.load(open(p))
            except (OSError, ValueError): continue
            for x in (j.get("eracheckdetails") or []) if isinstance(j, dict) else []:
                if str(x.get("visitid")) == str(vid): return "check %s" % os.path.basename(p)[:-5]
        return ""

    def free_eligibility(self, v, seq):
        try:
            pa, plans = self.port.plans(v.pid)
            p = next((x for x in plans if str(x.get("sequence")) == str(seq)), None)
            if not p: return "no plan at sequence %s" % seq
            return str((self.port.eligibility(v.pid, str(p.get("id") or "").replace("ins", "")) or {}).get("status") or "UNKNOWN").split()[0]
        except Exception as e:
            return "error %s" % type(e).__name__

    def secondary(self, row, v):
        code = str(row.get("secondary") or "").strip()
        if not code or " " in code: return self.skip(row, "no single secondary on the plan")
        car = self.port.carriers().get(code)
        pa, plans = self.port.plans(v.pid)
        dos = v.charges[0]["dos"]
        live = [p for p in plans if (car and p.get("carrier") == car) and not (wq._date(p.get("enddate")) and dos and wq._date(p.get("enddate")) < dos)]
        if len(live) != 1: return self.skip(row, "secondary %s: %d live plan(s) of that carrier on the chart - next plan" % (code, len(live)))
        holds, why = self.holds_claim(v, code)                         # the claim detail FIRST - before any move or rebill
        if holds: return self.skip(row, "the secondary already holds the claim (%s) - claim status, never a second claim (rules.md 9/21/2026)" % why)
        if why: return self.skip(row, why)
        if self.death_hold(row, v): return None
        sseq = str(live[0].get("sequence"))
        order = self.seq_of(v)
        new_order = None if sseq in order else ",".join(order + [sseq])
        if v.patbal > 0.005 or new_order:
            r = self.port.move(v.first_cid(), new_order, not self.live)
            self.say("  move_to_ins --no-rebill v%s order %s: %s" % (v.vid, new_order or "unchanged", cut(r)))
            if self.live and str(r).startswith("FAULT"): return self.finish(row, "SECONDARY", v.insbal + v.patbal, "move did not go through: %s" % r, False)
        if not self.live:
            return self.finish(row, "SECONDARY", v.insbal + v.patbal, "DRY freq1 + rebill seq %s (%s)" % (sseq, code), True)
        r = self.port.freq1(v.vid, v.first_cid(), sseq)
        return self.finish(row, "SECONDARY", v.insbal + v.patbal, "%s (%s)" % (r, code), " -> 204" in str(r))

    def redate(self, row, v):
        """CO-151 on CCM: ONE new visit on the last day of the month with all the visit's lines (redate_recode_1119.py's two-step create),
        read back, then the old lines' write-offs, $0 postings and charges voided. Refused: real money on the visit, a lead code that is not
        CCM, another CCM claim of the chart in that month (the duplicate rule: void, never rebill - William), a date-of-death answer.
        11/26/2026 (the independent review, finding 5): the moment addvisit returns the new visit a register line says so (wrote, new_visit) -
        it counts as acted at once (the 30-day wait), and no second re-date of the claim is made while that new visit exists (it goes to William's
        card). When the charge step or the read-back fails, the new visit's lines are voided and William gets a card; every void's answer is
        read, and an old line that could not be voided is never reported ok (two CCM claims in the month - his card)."""
        prior = (self.acted.get(str(row["visitid"])) or {}).get("new_visit")
        if prior:
            return self.owner(dict(row, rule="OWNER-REDATE-1004", step="OWNER", turn="william",
                                   kind="re-date: new visit %s was already made for this claim - no second re-date while it exists" % prior), v=v)
        if any(c["pays"] for c in v.charges): raise Refused("real money is posted on the visit")
        if not set(c["cpt"] for c in v.charges) & CCM: raise Refused("not a CCM claim")
        dos = v.charges[0]["dos"]; new = wq.last_day_of_month(dos)
        if new == dos: raise Refused("already dated the last day of its month")
        month = [c for c in self.port.chart_history(v.pid).iter("charge") if c.get("void") != "1" and str(c.get("visit")) != v.vid
                 and (c.get("proccode") or "").strip() in CCM and wq._date(c.get("dos")) and wq._date(c.get("dos")).replace(day=1) == dos.replace(day=1)]
        if month: raise Refused("the chart holds another CCM claim in that month (visit %s) - the duplicate rule is William's" % month[0].get("visit"))
        if self.death_hold(row, v, dos=new): return None              # the NEW date, before anything is written
        vis, pat, allc = self.port.visit_charges(v.first_cid())
        lines = [c for c in allc if c.get("void") != "1"]
        if len(lines) != len(v.charges): raise Refused("the visit's charges could not all be read")
        if not self.live:
            return self.finish(row, "REDATE", v.insbal, "DRY would re-enter %d line(s) on %s and void the old lines" % (len(lines), _mdy(new)), True)
        d = self.port.post(self.port.msg("getdemographic", "demographics", {"patientid": v.pid, "nocookie": "1"}))
        m = re.search(r'<respparty id="(resp\d+)"', d)
        if not m: raise Refused("no responsible party on the chart")
        nd = _mdy(new); chg = ""
        for c in lines:
            dc = (c.get("diagcodes") or "").split(); fee = c.get("fee") or "0"
            chg += ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="%s" aging="%s" billins="1" proccode="%s" cobcode="" '
                    'pos="%s" tos="%s" units="%s" netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" '
                    'finclasscode="CC" lineitemnote=""><diagcodelist>%s</diagcodelist></charge>') % (
                m.group(1), nd, nd, c.get("diagcodes") or "", c.get("modcodes") or "", nd, c.get("proccode"), c.get("pos") or "", c.get("tos") or "01",
                c.get("units") or "1", fee, fee, fee, fee, "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dc))
        ctx = {k: vis.get(k) for k in ("episode", "profile", "facility", "refplan", "insorder", "onhcfa")}
        hdr = {"patientid": "pat" + v.pid, "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}
        appt = ('<appt id="" patient="pat%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" '
                'isappt="0" note="" billingnote="" referenceid=""/>') % (v.pid, ctx["episode"], nd, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"] or "0")
        r0 = self.port.post(self.port.msg("addvisit", "chargeentry", hdr, appt))
        mv = re.search(r'id="(vst\d+)"', r0 or "")
        if "Fault" in (r0 or ""): return self.finish(row, "REDATE", v.insbal, "addvisit refused - nothing written, nothing voided", False)
        if not mv:                                                     # no fault and no visit id: a visit may have been made - held as one, William's card
            self.record(row, "REDATE", v.insbal, "addvisit gave no visit id - a new visit may exist", False, extra={"wrote": True, "new_visit": "unknown"})
            self.finish(row, "REDATE", v.insbal, "addvisit gave no visit id - nothing else written; card for William", False)
            return self.owner(dict(row, rule="OWNER-REDATE-1004", step="OWNER", turn="william", kind="re-date: addvisit gave no visit id - look for a new empty visit on %s" % nd), v=v)
        newv = mv.group(1); nid = _d(newv)
        self.record(row, "REDATE", v.insbal, "new visit %s made on %s - its lines next" % (nid, nd), False, extra={"wrote": True, "new_visit": nid})      # at once: counts as acted
        visx = ('<visit id="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" force="1"><chargelist>%s</chargelist></visit>') % (
            newv, nd, ctx["profile"], ctx["facility"], ctx["refplan"], ctx["insorder"], ctx["onhcfa"] or "0", chg)
        try: r1 = self.port.post(self.port.msg("updvisitwithnewcharges", "chargeentry", hdr, visx))
        except Exception as e: r1 = "Fault %s" % type(e).__name__
        if "Fault" in (r1 or ""):
            undone = self.void_new(v, nid)
            self.finish(row, "REDATE", v.insbal, "new visit %s made, its lines not added; %s; old lines kept; card for William" % (nid, undone), False)
            return self.owner(dict(row, rule="OWNER-REDATE-1004", step="OWNER", turn="william", kind="re-date: new visit %s made, its lines not added (%s)" % (nid, undone)), v=v)
        newc = [c for c in self.port.chart_history(v.pid).iter("charge") if c.get("void") != "1" and str(c.get("visit")) == nid]
        if len(newc) != len(lines):
            undone = self.void_new(v, nid, newc)
            self.finish(row, "REDATE", v.insbal, "new visit %s read back %d of %d lines; %s; old lines kept; card for William" % (nid, len(newc), len(lines), undone), False)
            return self.owner(dict(row, rule="OWNER-REDATE-1004", step="OWNER", turn="william", kind="re-date: new visit %s read back %d of %d lines (%s)" % (nid, len(newc), len(lines), undone)), v=v)
        voids, fails = 0, []
        for c in v.charges:
            try: ch, wos, pays = self.port.void_state(c["cid"])
            except Exception as e: fails.append("c%s state unreadable" % c["cid"]); continue
            for kind, items, fn in (("write-off", wos, self.port.void_writeoff), ("posting", pays, self.port.void_payment)):
                for x in items:
                    if x.get("void") == "1": continue
                    ok_ = _answer(fn, v.pid, c["cid"], x.get("id"))
                    if ok_: voids += 1
                    else: fails.append("%s %s of c%s" % (kind, x.get("id"), c["cid"]))
            if _answer(self.port.void_charge, v.pid, c["cid"]): voids += 1
            else: fails.append("charge c%s" % c["cid"])
        if fails:
            self.finish(row, "REDATE", v.insbal, "new visit %s on %s with %d line(s); old line NOT voided (%s) - two CCM claims in the month; card for William" % (nid, nd, len(newc), "; ".join(fails)), False)
            return self.owner(dict(row, rule="OWNER-REDATE-1004", step="OWNER", turn="william",
                                   kind="re-date: old line not voided - two CCM claims in the month (new visit %s; %s)" % (nid, "; ".join(fails))), v=v)
        return self.finish(row, "REDATE", v.insbal, "new visit %s on %s with %d line(s); %d void(s) on the old visit" % (nid, nd, len(newc), voids), True)

    def void_new(self, v, nid, newc=None):
        """The new visit's lines voided after a re-date step that did not finish (an empty new visit has none) -> what was done, in words."""
        if newc is None:
            try: newc = [c for c in self.port.chart_history(v.pid).iter("charge") if c.get("void") != "1" and str(c.get("visit")) == nid]
            except Exception as e: return "the new visit could not be read (%s) - its lines not voided" % type(e).__name__
        if not newc: return "the new visit holds no line"
        done = sum(1 for c in newc if _answer(self.port.void_charge, v.pid, _d(c.get("id"))))
        return "the new visit's lines voided %d of %d" % (done, len(newc))

    # ---- wrong payer: the run's RULE C, then ONE re-route here
    def cascade(self, row):
        vid = str(row["visitid"])
        if vid in self.no_plan:
            return self.owner(dict(row, rule="OWNER-NO-RULE", step="OWNER", turn="william", kind="insurance: the RULE C cascade found no live plan - face sheet needed"))
        if vid in self.reroute:
            if self.cap(row): return None
            v = self.precheck(row)
            if v is None: return None
            order = self.reroute[vid]
            seq0 = order.split(",")[0]; car_id, target = self.plan_at(v, seq0)
            if not car_id: return self.skip(row, "no plan at sequence %s on the chart - next plan" % seq0)
            if not target: return self.skip(row, "the plan at sequence %s (%s) has no carrier code in carriers.json - next plan" % (seq0, car_id))
            got = v.paid_by(target)
            if got: return self.skip(row, "%s already paid on this visit (posted %s, $%.2f) - a re-route to it would be a second claim" % (target, got[0]["posted"], got[0]["amount"]))
            if self.death_hold(row, v): return None
            if v.patbal > 0.005:                                   # never the patient balance: it goes back with the order, then ONE rebill
                r = self.port.move(v.first_cid(), order, not self.live)
                if not self.live: return self.finish(dict(row), "REROUTE", v.insbal + v.patbal, "%s | DRY freq1 + rebill seq %s" % (r, order.split(",")[0]), True)
                if str(r).startswith("FAULT"): return self.finish(row, "REROUTE", v.insbal + v.patbal, "move failed: %s" % r, False)
                r2 = self.port.freq1(v.vid, v.first_cid(), order.split(",")[0])
                return self.finish(row, "REROUTE", v.insbal + v.patbal, "%s | %s" % (r, r2), " -> 204" in str(r2))
            r = self.port.reroute(v.vid, v.first_cid(), order, not self.live)
            ok = (" -> 204" in str(r)) if self.live else "DRY" in str(r)
            return self.finish(row, "REROUTE", v.insbal, r, ok)
        if len(self.cascade_charts) >= self.a.max_cascade and row.get("pid") not in self.cascade_charts:
            self.skips["the run's cascade cap"] += 1; return None
        self.cascade_charts.add(row.get("pid"))
        self.counts["CASCADE"] += 1
        self.say("CASCADE v%s pat%s charge %s %s %s $%.2f%s: RULE C decides the live plan, then `python3 work_queue_act.py --live --stamp %s --reroute %s=<order>` (nothing found: --no-plan %s)" % (
            vid, row.get("pid"), row.get("charge") or "-", row.get("payer"), ",".join(row.get("codes") or []) or "-", _f(row.get("amount")),
            (" (" + row["why"] + ")") if row.get("why") else "", self.stamp, vid, vid))
        return None

    # ---- William's turn: one card per visit, an appeal letter's facts where one fits
    def owner(self, row, v=None):
        vid = str(row["visitid"])
        if row["rule"] in ((self.acted.get(vid) or {}).get("card") or {}):
            return self.skip(row, "the card is already on William's turn")
        if len(self.cards) >= self.a.max_cards:
            self.skips["the run's card cap"] += 1; return None
        if row["step"] == "FOLLOW_UP":
            v = v or self.precheck_soft(row)
            if v is not None and v.payments_since(wq._date(row.get("appeal_sent"))):
                self.counts["FOLLOW_UP paid"] += 1; self.say("FOLLOW-UP v%s: paid since the appeal - nothing to do" % vid); return None
            if wq._date(row.get("due")) and wq._date(row["due"]) > self.today: self.counts["WAIT"] += 1; return None
        card = self.card(row)
        self.cards.append(card)
        self.counts["CARD"] += 1
        self.say("CARD v%s pat%s %s %s $%.2f: %s" % (vid, row.get("pid"), row["rule"], row.get("payer"), _f(row.get("amount")), card["need"][:150]))
        if card.get("appeal"):
            ap = card["appeal"]
            self.say("APPEAL v%s pat%s %s DOS %s %s codes %s $%.2f ICN %s - proof: %s" % (vid, row.get("pid"), ap["payer"], ap["dos"], ap["cpts"], ",".join(ap["codes"]) or "-", ap["amount"], ap["icn"] or "-", ap["proof"]))
        self.record(row, "CARD", row.get("amount"), card["kind"], bool(self.live and self.a.board_file))      # ok = it goes into this run's board file
        return card

    def precheck_soft(self, row):
        try: return Visit(row["pid"], row["visitid"], self.port.history(row["pid"], row["visitid"])) if row.get("pid") else None
        except Exception: return None

    def card(self, row):
        rule = row["rule"]; words = wq.RULES[rule][2]; amt = _f(row.get("amount"))
        head = "%s ($%s, v%s, DOS %s, %s, %s%s)" % (
            {"OWNER-APPEAL": "APPEAL", "OWNER-RECORDS": "RECORDS", "OWNER-AUTH": "AUTHORIZATION", "OWNER-CRED": "CREDENTIALING", "OWNER-POS-1110": "PLACE OF SERVICE",
             "OWNER-PAST-12M-1120": "PAST 12 MONTHS", "OWNER-HANDOFF-1110": "ASK THE PAYER", "OWNER-TWO-SECONDARIES": "WHICH SECONDARY",
             "OWNER-NO-ICN": "CORRECTED CLAIM", "FOLLOWUP-APPEAL-1126": "APPEAL FOLLOW-UP", "OWNER-CROSSOVER-SILENT-0921": "ASK THE SECONDARY",
             "OWNER-REDATE-1004": "RE-DATE NOT FINISHED"}.get(rule, "DENIAL"),
            ("%.2f" % amt).rstrip("0").rstrip("."), row["visitid"], row.get("dos") or "?", row.get("cpts") or "-", row.get("payer") or "-",
            (", " + ",".join(row.get("codes") or [])) if row.get("codes") else "")
        ask = {"OWNER-APPEAL": "the appeal letter is drafted (Drive 'appeals' and a Gmail draft to you): sign it and send it by portal or fax, then say 'sent' on this card - the 30-day follow-up starts",
               "OWNER-RECORDS": "the payer asks for records: send them, or say 'write off' with the code",
               "OWNER-AUTH": "paste the authorization / referral (face sheet or VA authorization), or say 'write off' with the code",
               "OWNER-CRED": "an enrollment gap - say what to do (fix the enrollment, re-render, or write off with the code)",
               "OWNER-POS-1110": "say whether this claim is corrected to 31 and sent again as a new claim (never again at 32)",
               "OWNER-PAST-12M-1120": "past the 12-month window: say 'send' (it goes once, on the timely-filing watch) or 'write off' with the code",
               "OWNER-HANDOFF-1110": "claim status gives no usable answer: ask the payer by portal or phone and say what they answered",
               "OWNER-TWO-SECONDARIES": "two live secondaries (%s): say which one is billed (the other is ended or billed after)" % (row.get("secondary") or "?"),
               "OWNER-NO-ICN": "the payer adjudicated this claim; the correction goes out as frequency 7 with the payer's claim number - paste the number from the remit or the portal",
               "FOLLOWUP-APPEAL-1126": "the appeal you sent on %s has no answer in 30 days: ask the payer by portal or phone (claim status is not bought for a claim with a denial on file)" % row.get("appeal_sent"),
               "OWNER-CROSSOVER-SILENT-0921": "the secondary %s has held this claim since it crossed over (%s days, no answer; the Sunday claim status asks only the primary that paid): ask it by portal or phone and say what it answered - never a second claim (rules.md 9/21/2026)" % (row.get("secondary") or row.get("payer") or "?", row.get("days_silent", "?")),
               "OWNER-REDATE-1004": "the CO-151 re-date did not finish (%s): look at the chart in AdvancedMD - one CCM claim in the month goes out, never two; say what to keep" % (row.get("kind") or "see the register")}.get(
                   rule, "say what to do (correct and send, appeal, or write off with the code)")
        need = "%s: %s" % (head, ask)
        appeal = None
        if rule == "OWNER-APPEAL":
            lead = next((c for c in row.get("codes") or []), "")
            from working_denials import DENIAL_RULES
            proof = row.get("ask") or {"29": "proof of timely submission (the clearinghouse acceptance report dated inside the filing window)", "50": "the visit note showing medical necessity",
                                       "39": "the authorization request and the facility's notice", "167": "a corrected diagnosis or the note that supports the one billed",
                                       "96": "the note and the benefit the remark names", "272": "the note against the payer's coverage guideline"}.get(wq.norm(lead), "the visit note and the remit")
            appeal = {"visit": str(row["visitid"]), "pid": str(row.get("pid") or ""), "payer": row.get("payer") or "", "dos": row.get("dos") or "", "cpts": row.get("cpts") or "",
                      "codes": row.get("codes") or [], "rarc": row.get("rarc") or [], "amount": amt, "icn": row.get("icn") or "",
                      "reason": (DENIAL_RULES.get(wq.norm(lead)) or ("", ""))[1][:200], "proof": proof}
        return {"card": "denial-%s-%s" % (row.get("pid") or "x", row["visitid"]), "visit": str(row["visitid"]), "pid": str(row.get("pid") or ""), "rule": rule,
                "kind": row.get("kind") or words[:60], "need": need, "why": "%s - %s (rule %s; %s)" % (words, wq.RULES[rule][3], rule, ",".join(row.get("source") or [])),
                "amount": amt, "appeal": appeal}

    # ---- the board file (live only): one card per visit through board_ops / facesheets_needed.handback_op
    def write_board_file(self):
        if not (self.live and self.a.board_file and self.cards): return 0
        import board_ops
        from facesheets_needed import handback_op
        items = load_items(self.a.items_dir, self.a.items)
        by_id = {r.get("id"): r for r in items}
        now = _now().strftime("%Y-%m-%dT%H:%M:%SZ")
        doc = wq._load(self.a.board_file) if os.path.exists(self.a.board_file) else None
        doc = doc or {"schema": "irb-board-updates/1", "source": "work queue %s" % self.stamp, "created": now, "ops": []}
        if self.a.asof and not doc.get("asof"): doc["asof"] = self.a.asof
        names = {}
        for c in self.cards:
            note = [{"who": "Claude", "text": "Work queue %s: %s" % (self.stamp, c["why"]), "at": now}]
            if c["card"] in by_id:
                doc["ops"].append(handback_op(c["card"], c["need"], note[0]["text"], why=c["why"], amount=c["amount"], ask="decision", at=now)); continue
            twin = next((r for r in items if c["pid"] and c["pid"] in board_ops.chart_numbers(r)), None)
            if twin: who = {k: twin.get(k, "") for k in ("patient", "dob", "facility", "mbi")}
            else:
                if c["pid"] not in names:
                    try:
                        pa, _ = self.port.plans(c["pid"]); names[c["pid"]] = {"patient": pa.get("name", ""), "dob": pa.get("dob", ""), "facility": "", "mbi": ""}
                    except Exception:
                        names[c["pid"]] = {"patient": "chart %s" % c["pid"], "dob": "", "facility": "", "mbi": ""}
                who = names[c["pid"]]
            row = dict(who, id=c["card"], amdid=c["pid"], need=c["need"], why=c["why"], amount=c["amount"], status="william", ask="decision", notes=note)
            doc["ops"] += board_ops.plan_new_row(items, row, same_item=False, now=now)
            items.append(row); by_id[row["id"]] = row
        board_ops.clean_file(doc)
        os.makedirs(os.path.dirname(os.path.abspath(self.a.board_file)), exist_ok=True)
        json.dump(doc, open(self.a.board_file, "w"), indent=1)
        return len(self.cards)

    def run(self):
        rows = [r for r in self.queue.get("rows") or [] if isinstance(r, dict) and r.get("rule") in wq.RULES]
        if self.only: rows = [r for r in rows if str(r.get("visitid")) in self.only]
        if self.reroute or self.no_plan: rows = [r for r in rows if str(r.get("visitid")) in set(self.reroute) | self.no_plan and r.get("step") == "CASCADE"]
        self.cascade_charts = set()
        due = [r for r in rows if (wq._date(r.get("due")) or self.today) <= self.today or r.get("step") == "FOLLOW_UP"]
        if any(r["step"] not in ("WAIT", "HOLD", "LIST") for r in due): self.port.login()
        order = {"FIX_DX": 0, "HOSPICE_GV": 0, "REDATE": 0, "SECONDARY": 1, "RESEND": 2, "WOINSBANK": 3, "WRITE_OFF": 4, "CASCADE": 5, "OWNER": 6, "FOLLOW_UP": 6}      # money first: corrections and bills, then write-offs
        for r in sorted(due, key=lambda r: (order.get(r["step"], 9), -_f(r.get("amount")))):
            self.act(r)
        if self.cards:
            os.makedirs(self.a.outbox, exist_ok=True)
            p = os.path.join(self.a.outbox, "work_queue_cards_%s%s.json" % (self.stamp, "" if self.live else "_dry"))
            json.dump({"stamp": self.stamp, "live": self.live, "cards": self.cards}, open(p, "w"), indent=1)
            self.say("cards -> %s" % p)
        n = self.write_board_file()
        if self.deaths:                                                # the date-of-death rule's list (ids only; the outbox stays in the workspace)
            os.makedirs(self.a.outbox, exist_ok=True)
            p = os.path.join(self.a.outbox, "work_queue_death_%s%s.json" % (self.stamp, "" if self.live else "_dry"))
            json.dump({"stamp": self.stamp, "live": self.live, "about": "visits the work queue's deceased guard did not clear - nothing was edited or sent; "
                       "the date-of-death rule decides (a charge dated after a known death is VOIDED)", "visits": self.deaths}, open(p, "w"), indent=1)
            self.say("date-of-death list -> %s" % p)
        acts = {k: v for k, v in self.counts.items() if k not in ("WAIT", "HOLD", "LIST", "CARD", "CASCADE", "HOLD-DEATH")}
        self.say("RESULT work_queue_act %s %s: %d due of %d rows; acted %d (%s); cards %d%s; cascade %d; listed %d; held for the date of death %d; skipped %d (%s) -> %s" % (
            self.stamp, "LIVE" if self.live else "DRY (nothing written in AdvancedMD)", len(due), len(rows), sum(acts.values()),
            ", ".join("%s %d" % kv for kv in sorted(acts.items())) or "none", self.counts.get("CARD", 0), (" (%d into %s)" % (n, self.a.board_file)) if n else "",
            self.counts.get("CASCADE", 0), self.counts.get("LIST", 0), self.counts.get("HOLD-DEATH", 0), sum(self.skips.values()),
            ", ".join("%s %d" % kv for kv in self.skips.most_common()) or "none",
            self.reg_path if (acts or self.cards or self.deaths) else "no register lines"))
        return 0


def load_items(items_dir=None, items=None):
    """The board as the run saved it: <folder>/items/<card id>.json (or the folder itself), or one file {card id: card}."""
    out = []
    if items_dir:
        d = os.path.join(items_dir, "items") if os.path.isdir(os.path.join(items_dir, "items")) else items_dir
        for p in glob.glob(os.path.join(d, "*.json")):
            o = wq._load(p, {}) or {}; x = dict(o.get("data", o)); x.setdefault("id", os.path.basename(p)[:-5]); out.append(x)
    if items:
        j = wq._load(items, {}) or {}
        out += [dict(v, id=v.get("id") or k) for k, v in j.items() if isinstance(v, dict)]
    return out


def parse(argv=None):
    ap = argparse.ArgumentParser(description="the work-queue actor - dry unless --live")
    ap.add_argument("--live", action="store_true", help="write in AdvancedMD (without it: read and print only)")
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--queue", default=os.path.join("registers", "work_queue.json"))
    ap.add_argument("--registers", default="registers")
    ap.add_argument("--repo", default="/home/claude/effinger-billing-backend")
    ap.add_argument("--ws", default=".")
    ap.add_argument("--outbox", default="outbox")
    ap.add_argument("--today", default=None)
    ap.add_argument("--max", type=int, default=25, help="at most N AdvancedMD actions this run (default 25)")
    ap.add_argument("--max-cards", type=int, default=50)
    ap.add_argument("--max-cascade", type=int, default=10, help="charts listed for the RULE C cascade this run (each costs look-ups)")
    ap.add_argument("--treasury", default="", help="the Treasury ledger (deposits_ledger.csv) and/or availity_remit_recon_*.csv, comma separated")
    ap.add_argument("--board-file", default=None, help="this run's board_updates_<stamp>.json (live only)")
    ap.add_argument("--items-dir", default=None); ap.add_argument("--items", default=None); ap.add_argument("--asof", default=None)
    ap.add_argument("--reroute", action="append", default=[], help="<visit>=<order> (repeat it per visit) - the RULE C cascade's answer for a CASCADE row")
    ap.add_argument("--no-plan", default="", help="<visit>[,...] - the RULE C cascade found no live plan: William's card")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    if a.repo and not os.path.isdir(a.repo): a.repo = None
    return a


if __name__ == "__main__":
    sys.exit(Actor(parse()).run())
