-- Móyee schema v1: profiles, plans, subscriptions, usage, projects.
-- Applied to Supabase Postgres (SQL editor or `supabase db push`).
-- The API connects with a privileged role and enforces ownership itself;
-- RLS is a second layer protecting against direct access with anon/authenticated keys.

create extension if not exists vector;
create extension if not exists pgcrypto;

-- ---------------------------------------------------------------- profiles
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email varchar(320),
  full_name varchar(200),
  research_level varchar(32) check (research_level in ('undergraduate','postgraduate','professional')),
  discipline varchar(200),
  default_citation_style varchar(16) not null default 'apa7'
    check (default_citation_style in ('apa7','harvard','ieee')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- plans
create table if not exists public.plans (
  id varchar(32) primary key,
  name varchar(64) not null,
  price_usd_cents_monthly integer not null default 0,
  price_usd_cents_yearly integer not null default 0,
  limits jsonb not null default '{}'::jsonb,
  features jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- subscriptions
create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.profiles (id) on delete cascade,
  plan_id varchar(32) not null default 'free' references public.plans (id),
  status varchar(32) not null default 'active',
  provider varchar(32),
  provider_customer_id varchar(128),
  provider_subscription_id varchar(128),
  current_period_end timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ---------------------------------------------------------------- usage
create table if not exists public.usage_counters (
  id bigserial primary key,
  user_id uuid not null references public.profiles (id) on delete cascade,
  metric varchar(64) not null,
  period_start date not null,
  count integer not null default 0,
  unique (user_id, metric, period_start)
);
create index if not exists usage_counters_user_idx on public.usage_counters (user_id);

-- ---------------------------------------------------------------- projects
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references public.profiles (id) on delete cascade,
  name varchar(200) not null,
  topic varchar(500) not null,
  description text,
  discipline varchar(200),
  research_level varchar(32) check (research_level in ('undergraduate','postgraduate','professional')),
  template varchar(32) not null default 'blank'
    check (template in ('thesis','journal_article','report','blank')),
  citation_style varchar(16) not null default 'apa7'
    check (citation_style in ('apa7','harvard','ieee')),
  objectives jsonb not null default '[]'::jsonb,
  research_questions jsonb not null default '[]'::jsonb,
  keywords jsonb not null default '[]'::jsonb,
  status varchar(32) not null default 'active' check (status in ('active','completed','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists projects_owner_idx on public.projects (owner_id);
create index if not exists projects_status_idx on public.projects (status);

-- ---------------------------------------------------------------- RLS
alter table public.profiles enable row level security;
alter table public.plans enable row level security;
alter table public.subscriptions enable row level security;
alter table public.usage_counters enable row level security;
alter table public.projects enable row level security;

create policy "plans are public" on public.plans for select using (true);

create policy "own profile" on public.profiles
  for select using (auth.uid() = id);

create policy "own subscription" on public.subscriptions
  for select using (auth.uid() = user_id);

create policy "own usage" on public.usage_counters
  for select using (auth.uid() = user_id);

create policy "own projects" on public.projects
  for select using (auth.uid() = owner_id);

-- Writes happen only through the API (service role), so no insert/update/delete
-- policies are granted to anon/authenticated roles.
