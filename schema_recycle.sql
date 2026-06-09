alter table public.lead_assignments drop constraint if exists lead_assignments_lead_id_key;

alter table public.lead_assignments add constraint lead_assignments_lead_id_week_key
  unique (lead_id, week_start);
