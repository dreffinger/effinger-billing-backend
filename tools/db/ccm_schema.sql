-- CCM documentation hub: the section of the practice's Neon database for chronic care management (William 11/11/2026).
-- Neon is the PRIMARY store for this section: it holds patient-level data (names, notes, faxes), so it lives only here and in what is
-- filled from here - never in the repository. NOT APPLIED YET: this file is the proposal; applying it to the practice's database is its
-- own step, through tools/db/neon_db.py, on William's word. One record per patient per calendar month (the unit CCM is billed in).
create schema if not exists ccm;

-- one row per patient per calendar month that carries a CCM charge
create table if not exists ccm.patient_month (
  chart_id     text not null,                 -- AdvancedMD chart (patNNN)
  month        date not null,                 -- the first day of the calendar month
  patient_name text,
  birth_date   date,
  codes        text[] not null,               -- e.g. {99487} or {99487,99489}
  minutes      integer,                       -- 60 / 90 by the codes; null = no ready-made statement
  charges      jsonb not null default '[]',   -- the month's charge lines: date, code, visit, charge, facility, provider
  flag         text not null default '',      -- why William must look at this month himself ('' = nothing)
  loaded_at    timestamptz not null default now(),
  primary key (chart_id, month)
);

-- the physician's late-entry note for that month: written and signed by him, never by a routine
create table if not exists ccm.note (
  note_id      bigserial primary key,
  chart_id     text not null,
  month        date not null,
  statement    text not null,                 -- the sentence he attests to
  written_on   date not null,                 -- the day the late entry was written (never an earlier day)
  html         text not null,                 -- the note as laid out (scripts/helpers/ccm_notes.py)
  signed_by    text,
  signed_at    timestamptz,                   -- null = a draft; set only by his own signing
  foreign key (chart_id, month) references ccm.patient_month (chart_id, month),
  check (signed_at is null or signed_at::date >= written_on),
  check ((signed_by is null) = (signed_at is null))
);

-- a signed note is final: it is never changed or deleted, a correction is a new late entry
create or replace function ccm.note_signed_is_final() returns trigger language plpgsql as $$
begin
  if old.signed_at is not null then raise exception 'a signed CCM note is final - write a new late entry instead'; end if;
  if tg_op = 'DELETE' then return old; end if;
  return new;
end $$;
drop trigger if exists note_signed_is_final on ccm.note;
create trigger note_signed_is_final before update or delete on ccm.note for each row execute function ccm.note_signed_is_final();

-- every received fax, whether or not it has been matched to a patient yet (RingCentral keeps only the newest 200)
create table if not exists ccm.fax (
  message_id   text primary key,              -- RingCentral message id
  received_at  timestamptz not null,
  from_number  text,
  pages        integer,
  sha256       text not null,
  drive_file   text,                          -- where the PDF is kept
  chart_id     text,                          -- null until it is matched to a patient
  kind         text,                          -- lab, order, home health plan of care, other
  read_at      timestamptz
);

-- any number of supporting items for a patient-month
create table if not exists ccm.evidence (
  evidence_id  bigserial primary key,
  chart_id     text not null,
  month        date not null,
  kind         text not null check (kind in ('fax_lab','fax_order','fax_hhc_plan_of_care','fax_other','phone_call','call_transcript','referral','prescription','email','pcc_record','other')),
  item_date    date not null,
  source       text not null,                 -- e.g. ringcentral:<message id>
  summary      text not null default '',
  check (date_trunc('month', item_date)::date = month),
  foreign key (chart_id, month) references ccm.patient_month (chart_id, month),
  unique (chart_id, month, source)
);
