-- Add country column to leads table
-- Run once in Supabase SQL Editor

alter table public.leads
  add column if not exists country text not null default 'pl';

-- Mark all existing leads as Polish (they already are)
update public.leads set country = 'pl' where country is null or country = '';

-- Index for fast filtering by country in distribution
create index if not exists leads_country_idx on public.leads(country);
