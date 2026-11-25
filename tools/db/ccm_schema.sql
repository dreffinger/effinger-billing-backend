-- PLAIN ENGLISH (CCM documentation hub on Neon - William 11/11/2026: "this will be the primary database for collecting ccm work and then
--   we will add into this database for each patient each month any data we can scrape from the practice that adds extra support";
--   "do patient level data on the neon database but also have an artifact pull from that and have patient data on it which is ok").
-- Where the data is: raw.documents, source 'ccm', written ONLY through the database's one door (python3 tools/db/neon_db.py load-docs
--   --src <folder> --source ccm) from the folders scripts/helpers/ccm_build.py writes:
--   collection 'patients' - one document per chart: name, birth date and sex as AdvancedMD shows them (scripts/helpers/ccm_patients.py);
--   collection 'months'   - one document per patient per calendar month with a CCM charge (doc_id <chart>_<YYYY-MM>): the charge lines
--                           (from amd.charges, the AdvancedMD history pulled 11/10/2026), codes, minutes, statement, flag, insurance, and
--                           the note's fields (scripts/helpers/ccm_notes.py note_fields) with their hash;
--   collection 'signed'   - one document per SIGNED note (same doc_id): who signed, when, the day it was written, the hash he signed and
--                           the note's final fields. Written once, from a signing on the hub page that ccm_build.py verified against the
--                           stored draft (scripts/helpers/ccm_notes.py verify_signature);
--   collection 'evidence' - supporting items for a patient-month (faxes, calls, transcripts, referrals ...), and 'faxes' - every fax
--                           received on the practice's number (RingCentral), matched to a patient or not yet;
--   collection 'addenda'  - one dated ADDENDUM per signed note (doc_id <chart>_<YYYY-MM>_dx): the ICD-10 diagnoses on that note's CCM
--                           charge lines (scripts/helpers/ccm_notes.py addendum_fields), with its hash and its flag - a signed note is
--                           never edited (William 11/12/2026: "add this as an addendum to the note, if needed i can sign the addendums
--                           later after they are added");
--   collection 'addenda_signed' - one document per SIGNED addendum (same doc_id), written once from a signing on the hub page that
--                           ccm_build.py verified against the stored draft, exactly like a signed note.
-- And, outside source 'ccm': the AdvancedMD history (source 'amd_history', collection 'chargedetail' - every charge line of every chart
--   with its ICD-10 codes) and ONE reference document of ICD-10-CM descriptions (source 'ref', collection 'icd10cm', doc_id 'descriptions':
--   the codes on any charge, with the CMS words and the fiscal year they come from - scripts/helpers/ccm_build.py icd10).
-- This file builds the ccm.* VIEWS over those documents (the way tools/db/neon_schema.sql builds ehpa.*) and ONE rule that keeps a signed
--   note final: a trigger on raw.documents skips any later change to, or removal of, a 'signed' document, and any change to the 'months'
--   record of a month whose note is signed. A correction to a signed note is a new late entry, never an edit. A signed addendum and its
--   draft are final the same way (11/12/2026). Views only - no new tables.
-- Patient data: the views carry names and birth dates - this database is the practice's HIPAA store (ops.settings hipaa_enabled = true,
--   which neon_db.py load-docs requires). Nothing of a patient is in this file. Every statement is idempotent (create or replace / if not
--   exists). Applied to the practice database on 11/11/2026 after a rehearsal on a temporary branch (William's go-ahead of 11/11/2026).
create schema if not exists ccm;

-- the patient: as AdvancedMD shows the chart
create or replace view ccm.patients as
select d.doc_id as chart_id, d.body->>'name' as name, nullif(d.body->>'dob', '')::date as birth_date, d.body->>'sex' as sex,
       nullif(d.body->>'read_at', '')::timestamptz as read_at, d.loaded_at
from raw.documents d where d.source = 'ccm' and d.collection = 'patients';

-- one row per patient per calendar month that carries a CCM charge (the unit CCM is billed in)
create or replace view ccm.months as
select d.doc_id as note_id, d.body->>'chart' as chart_id, to_date(d.body->>'month', 'YYYY-MM') as month,
       array(select jsonb_array_elements_text(d.body->'codes')) as codes, d.body->'counts' as counts, nullif(d.body->>'minutes', '')::int as minutes,
       d.body->>'statement' as statement, coalesce(d.body->>'flag', '') as flag, d.body->>'insurance' as insurance, d.body->'charges' as charges,
       d.body->'fields' as fields, d.body->>'fields_sha' as fields_sha, nullif(d.body->>'built_at', '')::timestamptz as built_at, d.loaded_at
from raw.documents d where d.source = 'ccm' and d.collection = 'months';

-- the signed late-entry notes: final once recorded
create or replace view ccm.signed_notes as
select d.doc_id as note_id, d.body->>'chart' as chart_id, to_date(d.body->>'month', 'YYYY-MM') as month, to_date(d.body->>'written', 'MM/DD/YYYY') as written_on,
       d.body->>'by' as signed_by, nullif(d.body->>'at', '')::timestamptz as signed_at, d.body->>'sha' as sha, d.body->'fields' as fields,
       d.body->>'via' as signed_via, d.first_loaded_at as recorded_at
from raw.documents d where d.source = 'ccm' and d.collection = 'signed';

-- every note in one list: ready to sign, flagged for his own eyes, waiting for the patient's name, or signed
create or replace view ccm.notes as
select m.note_id, m.chart_id, m.month, p.name as patient_name, p.birth_date, m.codes, m.minutes, m.flag, m.insurance,
       case when s.note_id is not null then 'signed' when m.flag <> '' then 'flagged' when coalesce(p.name, '') = '' then 'no name yet' else 'ready to sign' end as status,
       s.written_on, s.signed_by, s.signed_at, s.sha
from ccm.months m left join ccm.patients p on p.chart_id = m.chart_id left join ccm.signed_notes s on s.note_id = m.note_id;

-- supporting items for a patient-month, any number of them (scripts/helpers/ccm_notes.py KINDS)
create or replace view ccm.evidence as
select d.doc_id as evidence_id, d.body->>'chart' as chart_id, to_date(d.body->>'month', 'YYYY-MM') as month, d.body->>'kind' as kind,
       nullif(d.body->>'date', '')::date as item_date, d.body->>'summary' as summary, d.body->>'source' as source, d.body->>'file' as file, d.loaded_at
from raw.documents d where d.source = 'ccm' and d.collection = 'evidence';

-- every fax received on the practice's number (RingCentral keeps only the newest 200 / 30 days, so this is the archive)
create or replace view ccm.faxes as
select d.doc_id as message_id, nullif(d.body->>'received_at', '')::timestamptz as received_at, d.body->>'from' as from_number,
       nullif(d.body->>'pages', '')::int as pages, d.body->>'sha256' as sha256, d.body->>'file' as file, d.body->>'chart' as chart_id,
       d.body->>'kind' as kind, d.loaded_at
from raw.documents d where d.source = 'ccm' and d.collection = 'faxes';

-- the ICD-10-CM descriptions of every code on a charge (CMS code files, the newest fiscal year's words; a code retired since keeps its last)
create or replace view ccm.icd10 as
select x.key as code, x.value->>0 as description, case when x.value->>1 ~ '^[0-9]{4}$' then (x.value->>1)::int end as fiscal_year
from raw.documents d cross join lateral jsonb_each(case when jsonb_typeof(d.body->'codes') = 'object' then d.body->'codes' else '{}'::jsonb end) x
where d.source = 'ref' and d.collection = 'icd10cm' and d.doc_id = 'descriptions';

-- every chart's ICD-10 diagnosis list (William 11/12/2026: "icd 10 diagnoses lists definitely need to be downloaded for each patient chart
-- from advanced md and kept in each chart folder in the database"): each code on the chart's charge lines that are not void, from the
-- AdvancedMD history (every chart, not only CCM), the first and last charge date it was billed with, on how many charge lines, and its CMS
-- description. (The typed amd.charge_details.diagnoses is empty - it is not used.)
create or replace view ccm.chart_diagnoses as
select d.doc_id as chart_id, x.code, i.description,
       min(case when e->>'begindate' ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' then to_date(e->>'begindate', 'MM/DD/YYYY') end) as first_dos,
       max(case when e->>'begindate' ~ '^[0-9]{2}/[0-9]{2}/[0-9]{4}$' then to_date(e->>'begindate', 'MM/DD/YYYY') end) as last_dos,
       count(*) as charge_lines
from raw.documents d
cross join lateral jsonb_array_elements(case when jsonb_typeof(d.body->'charges') = 'array' then d.body->'charges' else '[]'::jsonb end) e
cross join lateral (select distinct v as code from jsonb_array_elements_text(case when jsonb_typeof(e->'dx') = 'array' then e->'dx' else '[]'::jsonb end) v) x
left join ccm.icd10 i on i.code = x.code
where d.source = 'amd_history' and d.collection = 'chargedetail' and lower(coalesce(e->>'void', '0')) not in ('1', 't', 'true', 'y', 'yes')
group by d.doc_id, x.code, i.description;

-- the dated addenda to signed notes (the diagnoses on each note's CCM charge lines), with the flag of one that needs his own eyes
create or replace view ccm.addenda as
select d.doc_id as addendum_id, d.body->>'note' as note_id, d.body->>'chart' as chart_id, to_date(d.body->>'month', 'YYYY-MM') as month,
       d.body->>'kind' as kind, coalesce(d.body->>'flag', '') as flag, d.body->'fields'->'diagnoses' as diagnoses, d.body->'fields' as fields,
       d.body->>'fields_sha' as fields_sha, d.body->>'note_sha' as note_sha, nullif(d.body->>'_written', '')::timestamptz as built_at, d.loaded_at
from raw.documents d where d.source = 'ccm' and d.collection = 'addenda';

-- the signed addenda: final once recorded, like a signed note
create or replace view ccm.signed_addenda as
select d.doc_id as addendum_id, d.body->>'note' as note_id, d.body->>'chart' as chart_id, to_date(d.body->>'month', 'YYYY-MM') as month,
       d.body->>'kind' as kind, to_date(d.body->>'written', 'MM/DD/YYYY') as written_on, d.body->>'by' as signed_by,
       nullif(d.body->>'at', '')::timestamptz as signed_at, d.body->>'sha' as sha, d.body->'fields' as fields, d.body->>'via' as signed_via,
       d.first_loaded_at as recorded_at
from raw.documents d where d.source = 'ccm' and d.collection = 'addenda_signed';

-- a signed note is final: a later change to it, or its removal, is skipped (and so is a change to the record of a signed month).
-- 11/12/2026: a signed addendum ('addenda_signed') and its draft ('addenda', same doc_id) are final exactly the same way.
-- "A change" is any new body, fingerprint (body_sha256) or key (source, collection, doc_id) - not only a new fingerprint: a hand-typed
-- UPDATE that edits the body and leaves body_sha256 alone is skipped too (tightened 11/11/2026 after an independent check found that gap;
-- rehearsed on the temporary branch - edit without a new fingerprint, rename and move of a signed note skipped, a reload that only
-- touches loaded_by and a change to an unsigned month applied - then applied to the practice database).
create or replace function ccm.keep_signed_final() returns trigger language plpgsql as $$
begin
  if tg_op = 'DELETE' then
    if old.collection in ('signed', 'addenda_signed')
       or (old.collection = 'months' and exists (select 1 from raw.documents s where s.source = 'ccm' and s.collection = 'signed' and s.doc_id = old.doc_id))
       or (old.collection = 'addenda' and exists (select 1 from raw.documents s where s.source = 'ccm' and s.collection = 'addenda_signed' and s.doc_id = old.doc_id)) then
      raise notice 'ccm: % belongs to a signed note or addendum - it is final, the removal was skipped', old.doc_id;
      return null;
    end if;
    return old;
  end if;
  -- a CCM record never changes its keys: moving an unsigned draft into 'signed' / 'addenda_signed' by hand would make a signing nobody
  -- made (and, being final, it could never be removed), and moving a signed record out would unsign it. The one door (neon_db.py
  -- load-docs) only ever inserts or upserts by key, so a key change can only come from a hand-typed UPDATE (11/12/2026 check).
  if new.source is distinct from old.source or new.collection is distinct from old.collection or new.doc_id is distinct from old.doc_id then
    raise notice 'ccm: % keeps its source, collection and id - the change was skipped', old.doc_id;
    return null;
  end if;
  -- an update that leaves what the record holds as it was (the same body and fingerprint) goes through
  if new.body is not distinct from old.body and new.body_sha256 is not distinct from old.body_sha256 then
    return new;
  end if;
  if old.collection in ('signed', 'addenda_signed')
     or (old.collection = 'months' and exists (select 1 from raw.documents s where s.source = 'ccm' and s.collection = 'signed' and s.doc_id = old.doc_id))
     or (old.collection = 'addenda' and exists (select 1 from raw.documents s where s.source = 'ccm' and s.collection = 'addenda_signed' and s.doc_id = old.doc_id)) then
    raise notice 'ccm: % belongs to a signed note or addendum - it is final, the change was skipped (a correction is a new late entry or addendum)', old.doc_id;
    return null;
  end if;
  return new;
end $$;
drop trigger if exists ccm_signed_is_final on raw.documents;
create trigger ccm_signed_is_final before update or delete on raw.documents for each row when (old.source = 'ccm') execute function ccm.keep_signed_final();

-- the routines' own role reads the section (it already writes raw.documents through neon_db.py; it never deletes)
grant usage on schema ccm to ehpa_routine;
grant select on all tables in schema ccm to ehpa_routine;
