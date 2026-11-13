// PLAIN ENGLISH: the links the signed-in pages show - the header buttons to the practice's claude.ai pages, the Practice
// Database page's "Billing project pages", "Links" and "Routines that write here" lists, and the two pages a section points to
// (the Mandatory Approvals page, the CCM Documentation Hub). They are served only from /api routes (index.ts: a verified Neon
// Auth session for an allowed, confirmed email), so the public shell ("/") and the browser script (/app.js) carry no page
// addresses. The lists follow tools/db/practice_db_page.html (PAGES, LINKS, ROUTINES) with the in-page anchors pointed at this
// site's own views. One header button is a page of this site: the Insurance Refresh Board opens #db/insurance_refresh (the
// board's cards, read-only), which links on to the board on claude.ai for posting (BOARD_URL in board.ts).
export type Link = { key: string; label: string; url: string; note: string };

const REPO = "https://github.com/dreffinger/effinger-billing-backend";
const art = (id: string) => "https://claude.ai/artifact/" + id;

export const PRACTICE_DB_PAGE = art("QrLJpUcpFv3cFRB9xHfLyk");
export const INSURANCE_REFRESH_BOARD = art("NXKjnsha2dTyGHsiB4k6zg");
export const INSURANCE_REFRESH_PAGE = "#db/insurance_refresh";   // the board's cards on this site (views.ts insurance_refresh)
export const CCM_HUB = art("GSd9jcvXoBmxc9NkX2mWmR");
export const CCM_HUB_BUILD = art("Fsc6yZZLxuumAiJG9FAp8K");
export const APPROVALS_PAGE = art("HuYd2bSm2NxkFgYRqra7wR");

// the header buttons (William 11/12/2026: "add a button that goes to the insurance refresh board"; the CCM pages and the
// Practice Database page beside it). The board's button opens the board's page on this site; that page links to the board itself.
export const HEADER_LINKS: Link[] = [
  { key: "pdb", label: "Practice Database", url: PRACTICE_DB_PAGE, note: "The Practice Database page on claude.ai: its own database, the census inputs, every billing run" },
  { key: "irb", label: "Insurance Refresh Board", url: INSURANCE_REFRESH_PAGE, note: "Patients whose coverage is being resolved, as of the nightly copy; the page links to the board for posting" },
  { key: "ccm", label: "CCM Documentation Hub", url: CCM_HUB, note: "Read and sign the CCM late-entry notes (signing happens there)" },
  { key: "ccmbuild", label: "CCM Hub Build", url: CCM_HUB_BUILD, note: "How the CCM Documentation Hub was built" },
];

// [title, address, kind, what it is] - "Billing project pages" on the Overview
export const PAGES: [string, string, string, string][] = [
  ["ehpa Practice Database", PRACTICE_DB_PAGE, "page", "The Practice Database page on claude.ai and its own database"],
  ["Census inputs", "#db/feed", "view", "The feed and what AdvancedMD got (on this site)"],
  ["ehpa Billing Button", art("5Eyw5K3ydS13uDHkR8JJyZ"), "run", "Start a billing run; step feed pulls the Claimocity files"],
  ["Outstanding Claims", art("VNssV7RYwYrMrzvNwQtWwQ"), "report", "Every open insurance balance by payer, age and month"],
  ["Mandatory Approvals", APPROVALS_PAGE, "approve", "Writes the Claude routines could not make; Approve / Decline cards"],
  ["Insurance Refresh Board", INSURANCE_REFRESH_BOARD, "board", "Patients whose coverage is being resolved"],
  ["Working Denials", art("HDcGSG4QQHFSwt33g8E5qo"), "board", "Denial triage, live AMD status"],
  ["Effinger Money Ledger", art("6aYHyrozpmiCCf6GbM95EN"), "report", "Billed, outstanding, posted and written off"],
  ["Treasury Payments", art("WqPdTgjbFDKwGh4NH1nuSa"), "report", "Regions deposits matched to ERAs by payer"],
  ["Old Claims Disposition", art("X7a5aehSHPUyPppSdV1yAp"), "report", "The aged-claim review, batch by batch"],
  ["Credentialing Board", art("CmAo5e3hAouWyFEqwbdo4M"), "board", "Payer enrollments, licenses and renewals"],
  ["CCM Documentation Hub", CCM_HUB, "notes", "One late-entry note per patient and month of CCM; he signs there"],
  ["CCM Hub Build", CCM_HUB_BUILD, "learn", "How the CCM hub was built: languages, database, examples"],
  ["ehpa Home", art("R6zTSimdzdGv9ZShvkG5GH"), "home", "Visit, Claims, Treasury, Plan: the home screen"],
  ["Shared Workspaces", art("9r5xD5BvFW7CkYfWA35TaB"), "launcher", "Every session, routine, board and folder"],
  ["effinger-billing-backend on GitHub", REPO, "code", "The repository: scripts, runbooks, registers, reports"],
];

// "Links" on Mirror & sources: where each copy lives
export const MIRROR_LINKS: [string, string, string, string][] = [
  ["GitHub main (the record)", REPO + "/tree/main", "code", "scripts/helpers, nightly runbooks, practices/ehpa/registers, reports"],
  ["Synced branch (the Project reads it)", REPO + "/tree/claude/effinger-billing-backend-mirror-w74pqv", "code", "claude/effinger-billing-backend-mirror-w74pqv"],
  ["Drive · billing agent project files", "https://drive.google.com/drive/folders/1-AsLUHMaeqvHq-fqWKUVKKUU4Xkw6XTt", "drive", "runbooks, prompts, pastes"],
  ["Drive · chat history", "https://drive.google.com/drive/folders/1VCZfjSmok1fNNnYwf2yBTXlZ-zMUnAWU", "drive", "every run digest and START marker"],
  ["Drive · workspace mirror", "https://drive.google.com/drive/folders/135OCbRNCnFLyVm2GBXk1XsE3lt0vnsrn", "drive", "the PHI state bundle, deceased cache, helpers"],
  ["Drive · github mirror", "https://drive.google.com/drive/folders/1yr8X30h01-tPa0swclvtBFdAisiHzgJ8", "drive", "git bundles when a push is blocked"],
  ["Drive · Claimocity drop", "https://drive.google.com/drive/folders/1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI", "drive", "September feed copies and facesheets (history)"],
  ["Google Cloud bucket", "https://console.cloud.google.com/storage/browser/ehpa-claimocity-feed-50717", "cloud", "gs://ehpa-claimocity-feed-50717 - the Claimocity feed files, copied every 30 min"],
  ["Neon · ehpa-database (permanent store)", "https://console.neon.tech/app/projects/steep-rain-79347575", "database", "Postgres, HIPAA on: every board's documents, the registers and reports on main (raw.*, ops.*, ehpa.*, ccm.*) - this site reads it"],
  ["Practice Database page", PRACTICE_DB_PAGE, "page", "the claude.ai page with its own copy of the practice database"],
  ["Postman workspace", "https://www.postman.com/", "api", "AdvancedMD API vocabulary and collections (mirror of docs/api_vocabulary.json)"],
];

// "Routines that write here": [name, scheduled-task id or file on main, what it writes]
export const ROUTINES: [string, string, string][] = [
  ["ehpa Billing Button - full billing run", "trig_01S771Si8VJ8DvcwgHMHGYB5", "on demand from the Button page; writes billing_runs, feed_batches, feed_checks, era_runs, snapshots, then copies them to Neon (load-writes, run-log)"],
  ["Claimocity feed - daily", "trig_011wLUbRetVyUZdEBojuCwrs", "8:34 PM ET daily; writes feed_checks and, when files are new, feed_batches, then copies them to Neon"],
  ["Backend billing run - every 6 hours", "trig_01QRqT8KB4Q1H9EyYRG4NBKX", "the scheduled columns/ERA pass; writes billing_runs when it reports, sweeps main for the engine's reports and copies everything it sent to Neon"],
  ["Nightly insurance cascade - 05:35 UTC", "trig_01XVrVN9dpSdvAbB1ZrsAzFU", "writes its night to cascade_runs (tools/db/cascade_record.py, STEP 5b), sweeps the engine's reports into billing_runs and copies both to Neon"],
  ["Billing engine - GitHub Actions, every 2 hours + 05:35 UTC", ".github/workflows/billing-button.yml", "writes reports/button/<stamp>.json on main and no database document; the next Claude run sweeps them into billing_runs"],
  ["Billing approvals sync - hourly", "trig_01Bqg5n4YZZG55SULBq79JKJ", "copies waiting packages onto the Mandatory Approvals page"],
  ["Mandatory approval writes - 8:51 AM/PM", "trig_01YUgjTTz71pE9Nh65mMUeGY", "reminder of what is waiting"],
  ["Practice database sync - daily", "nightly/practice_db_sync_prompt_v1.txt", "copies the other billing pages' databases and datasets into artifact_copies and into Neon (load-docs, load-page)"],
];
export const routineUrl = (ref: string) => (ref.startsWith("trig_") ? "https://claude.ai/code/routines/" + ref : REPO + "/blob/main/" + ref);
export const githubFile = (path: string) => (/^[\w./-]+$/.test(path) && !path.includes("..") ? REPO + "/blob/main/" + path : "");
