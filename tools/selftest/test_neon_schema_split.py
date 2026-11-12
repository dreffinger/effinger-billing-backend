#!/usr/bin/env python3
# PLAIN ENGLISH (self-test, 11/10/2026) - proves offline that `neon_db.py init` sends EVERY statement of tools/db/neon_schema.sql,
#   each one exactly as it is written.
# Why it exists: until 11/10/2026 the HTTPS SQL route (what a cloud run uses when neither psycopg nor pg8000 is installed) threw a
#   statement away whenever a `--` comment line stood above it. 12 of the file's 32 statements never ran that way (the ehpa schema,
#   billing_runs, approvals, board_documents, carriers, outstanding_claims, denial_visits, insurance_refresh_items, ar_aging_rows,
#   ops.app_access_log, routine_runs, era_line_outcomes) and the command still printed "neon_schema.sql applied".
# What it checks:
#   1. the splitting function (sql_statements in tools/db/neon_db.py) on a small made-up SQL text: a comment above a statement, a
#      comment inside one, a tail of comments only, and a semicolon inside a quoted string, a comment, a "quoted name", a $$ body $$
#      or parentheses - every create statement comes back, whole, exactly once; and a /* comment that is never closed is NOT
#      dropped with everything after it (it comes back as the last piece, so the server refuses it out loud);
#   2. the real schema file: every line that opens a statement comes back as its own statement, and every line of SQL in the file
#      is in exactly one statement - nothing lost, nothing added;
#   3. `init --dry`: prints that count with no connection string anywhere, so nothing can have been sent - and connects to nothing
#      when a connection string is there;
#   4. `init` itself over both routes, each route swapped for a recorder: over HTTPS every statement goes out as the function
#      returned it, one per request, and the count printed is the number sent; over the wire protocol the file still goes out
#      whole in one piece (that path is unchanged) and the count printed is the same number;
#   5. the %s places (11/12/2026): over HTTPS a %s becomes $1..$n only when values are sent with the statement. A statement sent
#      without values - every statement of the schema file, a `sql` question - goes out exactly as written; until 11/12 a %s inside
#      its text (like '%sent%' in a view) left as $1 and Postgres stored that without an error.
# No database, no network, no patient data: the SQL samples are made up, and see SAFETY FIRST below for why a container that holds
#   the real connection string cannot reach the database from here. Writes only to a temp directory, removed when the test ends.
# Run: python3 tools/selftest/test_neon_schema_split.py   (exit 1 on any failure)
import os, sys, re, ast, io, json, time, runpy, shutil, atexit, tempfile, subprocess, types, contextlib, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NEON_DB = os.path.join(ROOT, "tools", "db", "neon_db.py"); SCHEMA = os.path.join(ROOT, "tools", "db", "neon_schema.sql")
FAILS = []
def check(name, cond, extra=""):
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond: FAILS.append(name)

# SAFETY FIRST. A routine's container holds the real connection string, and `init` writes. Nothing below can reach the database:
#   the address this process hands the script is made up and sits on .invalid (a domain that cannot exist); the script is pointed
#   at a throwaway folder that holds only a schema file - on EVERY run below, whatever the command - so it finds no secrets/ file
#   either; and both ways out of the process - the HTTPS call and the psycopg driver - are swapped for recorders before it runs.
os.environ["NEON_DATABASE_URL"] = "postgres://selftest:selftest@db.invalid/neondb"; os.environ.pop("DATABASE_URL", None)
T = tempfile.mkdtemp(prefix="selftest_neon_"); atexit.register(shutil.rmtree, T, ignore_errors=True); os.makedirs(os.path.join(T, "tools", "db"))
shutil.copy(SCHEMA, os.path.join(T, "tools", "db", "neon_schema.sql"))

def lift(name):
    """neon_db.py is a command - it connects as it runs - so it cannot be imported: take this one function out of its source text."""
    found = [n for n in ast.parse(open(NEON_DB, encoding="utf-8").read()).body if isinstance(n, ast.FunctionDef) and n.name == name]
    if not found: return None
    ns = {"re": re}; exec(compile(ast.Module(body=found, type_ignores=[]), NEON_DB, "exec"), ns); return ns[name]
split = lift("sql_statements")
check("tools/db/neon_db.py has the splitting function sql_statements()", split is not None)
if split is None: print("\n1 failure(s): nothing else can be checked without the function"); sys.exit(1)

# ------------------------------------------------------------------ 1. the splitting function on a small made-up SQL text
SAMPLE = """-- a made-up schema file; this header line ends in a semicolon;
-- and it has a second header line
create schema if not exists demo;

-- a comment line above the statement (the shape that used to be thrown away)
create or replace view demo.first as
select 1 as one;
create or replace view demo.second as
-- a comment inside the statement; it stays, and its semicolon ends nothing
select 'a;b' as one_line, 'first line;
second line' as two_lines, 'it''s; fine' as doubled_quote   -- words after the SQL; still part of it
from demo.first;

create table if not exists demo.t (id int);  -- a note after the closing semicolon
create index if not exists t_idx on demo.t (id);
-- a tail of comments only; nothing here to run;
-- (the one stretch the old rule was right to skip)
"""
got = split(SAMPLE); first = [s.split("\n")[0] for s in got]
check("every create statement of the sample comes back, in order", first == ["create schema if not exists demo", "create or replace view demo.first as", "create or replace view demo.second as",
      "create table if not exists demo.t (id int)", "create index if not exists t_idx on demo.t (id)"], first)
check("comment lines and blank lines above a statement are left out of it", bool(got) and all(s.startswith("create ") for s in got), first)
check("a comment inside a statement stays", len(got) > 2 and "-- a comment inside the statement; it stays" in got[2] and "-- words after the SQL; still part of it" in got[2], got[2:3])
check("a semicolon inside a quoted string or a comment ends nothing", len(got) > 2 and got[2].endswith("from demo.first") and "'first line;\nsecond line'" in got[2] and "'it''s; fine'" in got[2], got[2:3])
check("a tail of comments only is not a statement", len(got) == 5 and not any("tail of comments" in s for s in got), len(got))
check("no statement keeps its closing semicolon or a blank around it", bool(got) and all(s == s.strip() and not s.endswith(";") for s in got), got)
A, B = "create table demo.a (x int)", "create table demo.b (x int)"                         # two plain statements to stand before / after the shape under test
FUNC = "create function demo.f() returns int as $$\nbegin\n  return 1;\nend;\n$$ language plpgsql"
check("a $$ body $$ with semicolons inside is one statement", split(FUNC + ";\n" + A + ";") == [FUNC, A])
FUNC = "create function demo.g() returns text as $body$ select '$$;' ;\n$body$ language sql"
check("a $tag$ body $tag$ closes only on its own tag", split(FUNC + ";\n" + A + ";") == [FUNC, A])
check("a name with a $ in it, or a $1 parameter, opens no dollar quote", split("create table demo.a$b$c (x int);\nselect $1;\ncreate table demo.c$ (x int);") == ["create table demo.a$b$c (x int)", "select $1", "create table demo.c$ (x int)"])
BLOCK = "create table demo.c (x int /* the key; */)"
check("a /* block comment */ above a statement is left out, one inside stays, a nested one is still a comment", split("/* a block; with a semicolon\n   /* and one inside it; */ still the comment; */\n" + BLOCK + ";") == [BLOCK])
BLOCK = "create view demo.c2 as select 1 /* a; b */ as one"
check("a /* block comment */ inside a statement, outside any brackets, stays and its semicolon ends nothing", split(BLOCK + ";\n" + A + ";") == [BLOCK, A])
OPEN = "/* the paths /api/* and /app/* are read here */\ncreate view demo.v as select 1 as x"   # each /* inside opens one more level, so this comment never closes
check("a /* comment that is never closed is not dropped with the rest of the file: it comes back as the last piece", split(A + ";\n" + OPEN + ";\n") == [A, OPEN + ";"], split(A + ";\n" + OPEN + ";\n"))
OPEN = "create table demo.b (x int /* never closed;\n);\ncreate table demo.c (x int)"
check("...and one that opens inside a statement keeps everything after it in that statement", split(A + ";\n" + OPEN + ";\n") == [A, OPEN + ";"], split(A + ";\n" + OPEN + ";\n"))
check('a semicolon inside a "quoted name" ends nothing', split('create table demo."odd;na""me" (x int);\n' + A + ";") == ['create table demo."odd;na""me" (x int)', A])
RULE = "create rule r as on insert to demo.a do also (insert into demo.b values (1); insert into demo.c values (2))"
check("a semicolon inside parentheses ends nothing (a rule that runs two commands)", split(RULE + ";\n" + A + ";") == [RULE, A])
ESC = "create view demo.v as select E'it\\'s; fine' as x, E'a''b\\'c; d' as y"
check("an E'...' string with a backslash-quote stays whole, after a doubled quote too", split(ESC + ";\n" + A + ";") == [ESC, A])
ESC = "create view demo.v as select E'a' -- a note; between the pieces\n  'b\\'; c'\n'd\\'; e' as x"
check("an E'...' string that goes on after a line end keeps its backslash rule on every piece", split(ESC + ";\n" + A + ";") == [ESC, A], split(ESC + ";\n" + A + ";"))
t0 = time.perf_counter(); got_far = [split("select E'a'\n" + " " * 28 + "as x;\n" + A + ";"), split("select E'a' --" + "-" * 38 + "\nas x;\n" + A + ";")]; took = time.perf_counter() - t0
check("an E'...' string at a line end, then deep indentation or a ruler comment, is read at once (looking ahead for the next piece must not run away)",
      took < 2 and got_far == [["select E'a'\n" + " " * 28 + "as x", A], ["select E'a' --" + "-" * 38 + "\nas x", A]], "took %.1f s" % took)
PLAIN = "create view demo.w as select 'a\\' as x, name'C:\\dir\\' as y"                        # name'...' is a typed value, not an E'...' string, though the name ends in e
check("an ordinary string that ends in a backslash still closes, right after a name too", split(PLAIN + ";\n" + A + ";") == [PLAIN, A])
PLAIN = "create view demo.w as select x from demo.t where x like '%\\_%' escape\n'\\'"         # the line above the string ends in e: still not an E'...' string
check("...and when it opens a line whose line above ends in e", split(PLAIN + ";\n" + A + ";") == [PLAIN, A], split(PLAIN + ";\n" + A + ";"))
check("two statements on one line are two; an empty statement is none; a blank before the semicolon is not kept", split(A + " ; " + B + "\n;;\n;\n") == [A, B])
check("a last statement without its semicolon still comes back", split(A + ";\n" + B + "\n") == [A, B])
check("a text with nothing to run gives nothing", split("") == [] and split("\n  \n-- only words;\n/* and a block */\n") == [])
check("a -- comment ends at a bare carriage return too", split("-- words;\r" + A + ";\r-- more\r" + B + ";\r") == [A, B], split("-- words;\r" + A + ";\r-- more\r" + B + ";\r"))
check("form feed and vertical tab are blanks", split("\x0c\x0b" + A + "\x0b;\x0c" + B + ";") == [A, B])
NBSP = "\xa0"                                                                                # a no-break space: to Postgres it is part of a name, never a blank
LETTER = "\xe9"                                                                              # a letter outside ASCII: part of a name too
check("a letter outside ASCII is part of a name: no E'...' string and no dollar quote opens right after one, and a dollar tag may hold one",
      split("select " + LETTER + "E'a\\' as y;\nselect 1 as " + LETTER + "$a$;\nselect 2 as b$a$;\nselect $" + LETTER + "t$ a;b $" + LETTER + "t$ as z;") ==
      ["select " + LETTER + "E'a\\' as y", "select 1 as " + LETTER + "$a$", "select 2 as b$a$", "select $" + LETTER + "t$ a;b $" + LETTER + "t$ as z"])
check("a no-break space is kept as written (to Postgres it belongs to a name), never trimmed as a blank", split(NBSP + "select 1;\nselect 1 as x" + NBSP + ";") == [NBSP + "select 1", "select 1 as x" + NBSP], split(NBSP + "select 1;\nselect 1 as x" + NBSP + ";"))

# ------------------------------------------------------------------ 2. the real schema file
text = open(SCHEMA, encoding="utf-8").read(); stmts = split(text)
# two second, simpler rules to compare against, good for the way THIS file is written (a statement opens at the start of a line with
# one of the words below; no comment after a closing semicolon). A statement written another way fails here on purpose: look at it,
# then widen the rule.
openers = [l.rstrip().rstrip(";") for l in text.split("\n") if re.match(r"(create|grant|revoke|alter|drop|comment)\b", l)]
came = [s.split("\n")[0].rstrip().rstrip(";") for s in stmts]
check("neon_schema.sql: all %d statements come back, each as its own statement and nothing else (%d returned)" % (len(openers), len(stmts)),
      came == openers, "missing: %s | extra: %s" % (sorted(set(openers) - set(came)), sorted(set(came) - set(openers))))
def sql_lines(lines): return [l for l in lines if l.strip() and not l.lstrip().startswith("--")]
check("neon_schema.sql: every line of SQL in the file is in exactly one statement, in order - nothing lost, nothing added",
      sql_lines(l for s in stmts for l in (s + ";").split("\n")) == sql_lines(text.split("\n")))
check("neon_schema.sql: nothing returned is empty or starts with a comment", bool(stmts) and all(s and not s.startswith(("--", "/*")) for s in stmts))

# ------------------------------------------------------------------ 3. `init --dry`: the count, with no connection string anywhere
env = {k: v for k, v in os.environ.items() if k not in ("NEON_DATABASE_URL", "DATABASE_URL", "NEON_DB_MODE", "EHPA_REPO", "EHPA_WS")}; env["HOME"] = T
r = subprocess.run([sys.executable, NEON_DB, "init", "--dry", "--repo", T, "--ws", T], capture_output=True, text=True, env=env, timeout=60)
m = re.search(r"neon_schema\.sql\D*(\d+) statement", r.stdout)
check("`init --dry` prints the full count (%d) and needs no connection string, so nothing was sent" % len(stmts),
      r.returncode == 0 and bool(m) and int(m.group(1)) == len(stmts) and "dry" in r.stdout and len(r.stdout.strip().splitlines()) == 1, (r.returncode, r.stdout.strip()[:240], r.stderr.strip()[:240]))
dry_line = r.stdout; E = tempfile.mkdtemp(prefix="selftest_neon_empty_"); atexit.register(shutil.rmtree, E, ignore_errors=True)   # a folder with no schema file in it
r = subprocess.run([sys.executable, NEON_DB, "init", "--dry", "--repo", E, "--ws", E], capture_output=True, text=True, env=env, timeout=60)
check("`init --dry` says so when there is no schema file where it looked", r.returncode == 0 and "no neon_schema.sql" in r.stdout and E in r.stdout, (r.returncode, r.stdout.strip()[:240], r.stderr.strip()[:240]))
r = subprocess.run([sys.executable, NEON_DB, "init", "--dry", "--repo", T, "--ws", T], capture_output=True, text=True, env=dict(env, NEON_DATABASE_URL=os.environ["NEON_DATABASE_URL"], NEON_DB_MODE="http"), timeout=60)
check("`init --dry` connects to nothing when a connection string IS there (the made-up one: a connection attempt would fail the run)", r.returncode == 0 and r.stdout == dry_line, (r.returncode, r.stdout.strip()[:240], r.stderr.strip()[:240]))

# ------------------------------------------------------------------ 4. `init` over both routes, each swapped for a recorder
SENT = []; VALUES = []                                    # every statement sent, and beside it the values sent with it
class Reply:                                              # what the HTTPS route answers: no rows
    def __enter__(self): return self
    def __exit__(self, *x): return False
    def read(self): return b'{"rows": [], "rowCount": 0}'
def fake_urlopen(req, timeout=None): body = json.loads(req.data.decode("utf-8")); SENT.append(body["query"]); VALUES.append(body["params"]); return Reply()
class Cursor:                                             # what the wire-protocol driver answers: no rows
    description = None; rowcount = 0
    def execute(self, sql, params=None): SENT.append(sql); VALUES.append(params)
    def fetchall(self): return []
    def close(self): pass
class Conn:
    def cursor(self): return Cursor()
    def close(self): pass
fake_psycopg = types.ModuleType("psycopg"); fake_psycopg.connect = lambda url, **kw: Conn()
def run(mode, *command, repo=None):
    """`python3 tools/db/neon_db.py <command>` inside this process over one route (pg | http): what it printed, what it sent, the values sent beside.
    The script is always pointed at a throwaway folder (repo, or the copy of the real schema file) - never at a real checkout with its secrets/."""
    del SENT[:], VALUES[:]; os.environ["NEON_DB_MODE"] = mode; out = io.StringIO()
    keep = (sys.argv, urllib.request.urlopen, sys.modules.get("psycopg"))
    sys.argv = [NEON_DB] + list(command) + ["--repo", repo or T, "--ws", T]; urllib.request.urlopen = fake_urlopen; sys.modules["psycopg"] = fake_psycopg
    try:
        with contextlib.redirect_stdout(out): runpy.run_path(NEON_DB, run_name="__main__")
    except SystemExit as e: out.write(" EXIT %s" % (e.code,))
    finally:
        sys.argv, urllib.request.urlopen = keep[0], keep[1]
        if keep[2] is None: sys.modules.pop("psycopg", None)
        else: sys.modules["psycopg"] = keep[2]
    return out.getvalue().strip(), list(SENT), list(VALUES)
def run_init(mode):
    """...and for `init` on the copy of the real schema file: the line it printed, the count in it, what it sent"""
    line, sent, _ = run(mode, "init"); m = re.search(r"neon_schema\.sql applied \((\d+) statement", line)
    return line, (int(m.group(1)) if m else None), sent

line, n_wire, sent = run_init("pg")
check("over the wire protocol the schema file still goes out whole, once, unchanged", "via psycopg" in line and sent.count(text) == 1 and sent[-2:-1] == [text], line[:240])
base = sent.index(text) if text in sent else 0            # how many statements `init` sends before the schema file (its own base schemas and tables)
m = re.search(r"(\d+) base statement", dry_line)
check("`init --dry` counts the base statements too, as many as `init` sends before the schema file (%s said, %d sent)" % (m.group(1) if m else None, base), bool(m) and int(m.group(1)) == base)
line, n_http, sent = run_init("http")
reqs = sent[1 + base:-1]                                  # after the connection probe and the base tables, before the closing read of the HIPAA marker: the schema file
went = [q.split("\n")[0].rstrip().rstrip(";") for q in reqs]
check("over HTTPS every create / grant of the schema file goes out, one statement per request", "via http" in line and [w for w in went if re.match(r"(create|grant)\b", w)] == openers,
      "%s | missing: %s" % (line[:120], sorted(set(openers) - set(went))))
check("over HTTPS no request is empty or starts with a comment", bool(reqs) and all(q and not q.startswith(("--", "/*")) for q in reqs))
check("over HTTPS each request is one statement exactly as the function returned it, in order", reqs == stmts)
check("the count printed over HTTPS is the number of statements sent (%s printed, %d sent)" % (n_http, len(reqs)), n_http == len(reqs))
check("the count printed over the wire protocol is that same number of statements (%s printed)" % n_wire, n_wire == len(stmts) == len(reqs))

# ------------------------------------------------------------------ 5. the %s places: turned into $1..$n only when values are sent
P = tempfile.mkdtemp(prefix="selftest_neon_places_"); atexit.register(shutil.rmtree, P, ignore_errors=True); os.makedirs(os.path.join(P, "tools", "db"))
AS_WRITTEN = ["create or replace view demo.sent as select 1 as one where 'x' ilike '%sent%' or 'y' like '%s'",
              "create or replace view demo.pair as select format('%s / %s', 'a', 'b') as both"]          # a made-up schema file whose statements hold %s as plain text
open(os.path.join(P, "tools", "db", "neon_schema.sql"), "w", encoding="utf-8").write("-- made up: each statement holds %s as plain text\n" + ";\n".join(AS_WRITTEN) + ";\n")
line, sent, _ = run("http", "init", repo=P)
check("over HTTPS a %s inside a statement of the schema file goes out as written, not as $1", "applied (2 statements)" in line and sent[1 + base:-1] == AS_WRITTEN, sent[1 + base:-1])
line, sent, _ = run("http", "sql", "select 'a%sb' as v")
check("over HTTPS a %s inside the quotes of a `sql` question goes out as written", sent[1:] == ["select 'a%sb' as v"], sent[1:])
line, sent, values = run("http", "set", "--key", "selftest_key", "--value", "100%sure")
check("over HTTPS a statement sent WITH values still gets $1, $2, $3 in place of its %s, and the values travel beside it untouched",
      len(sent) == 2 and "values ($1, $2, $3)" in sent[1] and "%s" not in sent[1] and values[1][:2] == ["selftest_key", "100%sure"] and len(values[1]) == 3, (sent[1:], values[1:]))
line, sent, values = run("http", "run-log", "--routine", "selftest", "--stamp", "2026-11-12T0000Z", "--status", "ok", "--headline", "100%sure")
check("...numbered in order, one for each value (the nine of a run-log line)",
      len(sent) == 2 and re.findall(r"\$\d+", sent[1]) == ["$%d" % k for k in range(1, 10)] and "%s" not in sent[1] and len(values[1]) == 9 and "100%sure" in values[1], (sent[1:], values[1:]))
line, sent, values = run("pg", "set", "--key", "selftest_key", "--value", "100%sure")
check("over the wire protocol the driver still gets the %s places and the values as they are (that path is unchanged)",
      len(sent) == 1 and "values (%s, %s, %s)" in sent[0] and "$" not in sent[0] and list(values[0])[:2] == ["selftest_key", "100%sure"], (sent, values))

os.environ.pop("NEON_DB_MODE", None)
print("\n%d failure(s)%s" % (len(FAILS), " - every statement of the schema file is sent as written, and the count says so" if not FAILS else ": " + "; ".join(FAILS)))
sys.exit(1 if FAILS else 0)
