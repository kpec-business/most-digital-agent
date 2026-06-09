-- ============================================================
-- Most Digital — Lead System Migration
-- Uruchom w Supabase > SQL Editor
-- ============================================================

-- 1. Tabela wszystkich pobranych leadów (master list)
create table if not exists public.leads (
  id           uuid default gen_random_uuid() primary key,
  name         text not null,
  category     text,
  address      text,
  phone        text,
  email        text,
  website      text,
  rating       text,
  reviews      integer,
  priorytet    text check (priorytet in ('GORACY','CIEPLY')),
  powod        text,
  city         text,
  source_query text,
  scraped_at   timestamptz default now(),
  unique (name, address)
);

alter table public.leads enable row level security;

-- Zalogowani użytkownicy mogą czytać leady
create policy "leads_read" on public.leads
  for select using (auth.role() = 'authenticated');

-- Tylko service role (agent Python) może wstawiać
-- (service role automatycznie omija RLS)


-- 2. Tabela przydziałów leadów (kto dostał który lead w danym tygodniu)
create table if not exists public.lead_assignments (
  id          uuid default gen_random_uuid() primary key,
  lead_id     uuid not null references public.leads(id) on delete cascade,
  employee_id uuid not null references public.profiles(id) on delete cascade,
  status      text not null default 'nowy'
                check (status in ('nowy','nie','zainteresowany','sprzedane')),
  week_start  date not null,          -- poniedziałek tygodnia przydziału
  assigned_at timestamptz default now(),
  updated_at  timestamptz default now(),
  unique (lead_id)                    -- każdy lead przydzielony tylko raz (nigdy ponownie)
);

alter table public.lead_assignments enable row level security;

-- Sprzedawca widzi tylko swoje przydziały
create policy "assign_seller_read" on public.lead_assignments
  for select using (employee_id = auth.uid());

-- Sprzedawca może zmieniać status tylko swoich leadów
create policy "assign_seller_update" on public.lead_assignments
  for update using (employee_id = auth.uid())
  with check (
    employee_id = auth.uid()
    and status in ('nowy','nie','zainteresowany','sprzedane')
  );

-- Admin widzi wszystko
create policy "assign_admin_all" on public.lead_assignments
  for all using (public.is_admin());


-- 3. Widok dla admina: leady z przydziałami tego tygodnia
create or replace view public.leads_this_week as
  select
    la.id            as assignment_id,
    la.status,
    la.week_start,
    la.employee_id,
    p.full_name      as employee_name,
    l.id             as lead_id,
    l.name,
    l.category,
    l.phone,
    l.email,
    l.website,
    l.address,
    l.city,
    l.priorytet,
    l.reviews
  from public.lead_assignments la
  join public.leads l on l.id = la.lead_id
  join public.profiles p on p.id = la.employee_id
  where la.week_start = date_trunc('week', current_date)::date;

grant select on public.leads_this_week to authenticated;
