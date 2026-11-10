# Universal Practice Optimization (`optimization/`)

PLAIN ENGLISH: a framework for running any medical practice as a business, and its application to Effinger Health PA.
William, 11/10/2026: "do a universal practice optimization outline in the neon database and in the universal optimisation
app ... apply it to my practice with recommendations and work lists and projects."

Two layers, kept apart on purpose:

| Layer | What it holds | Where it lives |
|---|---|---|
| **Universal** | Domains -> areas (categories) -> metrics, each with what good looks like, where it breaks, what to do, benchmarks and sources. Works for any practice. No practice data. | `universal/` seed files -> `upo.domains`, `upo.categories`, `upo.metrics`, `upo.sources` |
| **Practice** | One practice's standing on every area, its metric values, risk findings, recommendations, projects, the work list and the valuation. Aggregates only: dollars, counts, rates. | `practices/<code>/` seed files -> `upo.practice_*`, `upo.risk_findings`, `upo.recommendations`, `upo.projects`, `upo.worklist_items`, `upo.valuations` |

Around them: `vendor/` (the purchased CleanClaimRx library: a digest of every document and the fact-check of its claims; the
PDFs themselves stay in Drive and are never committed), `research/` (primary-source research notes), `learning/` (the learning
modules the app shows under Learn), `db/upo_schema.sql` (the `upo` schema) and `tools/upo_load.py` (the one door between the
seed files and the database).

## The loop

```bash
python3 optimization/tools/upo_load.py validate                   # every seed file: required fields, references, no identifiers
python3 optimization/tools/upo_load.py schema --target preview    # build / update the upo schema (idempotent)
python3 optimization/tools/upo_load.py load --target preview      # make the database match the seeds
python3 optimization/tools/upo_load.py status --target prod       # rows per table
```

`--target preview` is a Neon branch used to test before production (`optimization/.preview_host` and `.preview_branch`,
git-ignored, name it); `--target prod` is the live database. The seed files are the source of truth with one exception: the
owner changes a work-list row's status and note in the app, so a reload never overwrites those two fields and never deletes a
work-list row.

## The app

`apps/ehpadb` serves it: after sign-in a hub links to Universal Practice Optimization (`#upo`), Practice Optimization for this
practice (`#practice`), the ehpa Practice Database dashboard (`#db`) and Learn (`#learn`). Server routes are in
`apps/ehpadb/src/upo.ts`; pages in `apps/ehpadb/src/client/`. Deploy with `apps/ehpadb/scripts/deploy-api.sh preview|prod`
(Neon API; no CLI session needed) or `npm run deploy` (neon CLI).

## Rules

- No patient data here, ever: no names, dates of birth, member ids or chart-level rows. `upo_load.py validate` refuses a seed
  that looks like it carries one, and `tools/mirror/phi_gate.py` still runs before a commit.
- The purchased library is copyrighted. Digests summarize it in our own words; the framework text is original and cites
  primary sources. Do not paste the vendor's text or spreadsheets into the seeds, the database or the app.
- A risk finding is a pattern in the practice's own aggregates set beside the rule it touches. It is a reason to look at
  charts, not a conclusion. Where a review suggests an overpayment, involve a healthcare attorney: federal law puts a deadline
  on reporting and returning it.
