-- Móyee schema v2: academic_sources, project_sources (discovery, library & references).

create table if not exists public.academic_sources (
  id uuid primary key default gen_random_uuid(),
  provider varchar(32) not null,              -- 'openalex' | 'crossref' | 'manual'
  external_id varchar(255) not null,          -- e.g. OpenAlex work ID or normalised DOI
  doi varchar(255),
  title text not null,
  authors jsonb not null default '[]'::jsonb, -- [{"given": "...", "family": "...", "name": "..."}]
  abstract text,
  publication_year integer,
  venue varchar(500),
  publisher varchar(300),
  publication_type varchar(64),               -- 'article' | 'book' | 'proceedings-article' | etc.
  volume varchar(64),
  issue varchar(64),
  pages varchar(64),
  source_url varchar(1000),
  oa_pdf_url varchar(1000),
  is_open_access boolean not null default false,
  citation_count integer,
  keywords jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider, external_id)
);
create index if not exists academic_sources_doi_idx on public.academic_sources (doi);

create table if not exists public.project_sources (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  academic_source_id uuid references public.academic_sources (id) on delete set null,
  source_kind varchar(32) not null default 'metadata'
    check (source_kind in ('metadata','document','manual')),
  -- Project-scoped editable reference fields (initialised from academic_sources when saved):
  title text not null,
  authors jsonb not null default '[]'::jsonb,
  abstract text,
  publication_year integer,
  venue varchar(500),
  publisher varchar(300),
  publication_type varchar(64) not null default 'article',
  volume varchar(64),
  issue varchar(64),
  pages varchar(64),
  doi varchar(255),
  source_url varchar(1000),
  oa_pdf_url varchar(1000),
  is_open_access boolean not null default false,
  citation_count integer,
  provider varchar(32) not null default 'manual',
  citation_key varchar(120) not null,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, academic_source_id)
);
create index if not exists project_sources_project_idx on public.project_sources (project_id);
create index if not exists project_sources_owner_idx on public.project_sources (owner_id);

alter table public.academic_sources enable row level security;
alter table public.project_sources enable row level security;

create policy "academic sources are readable by authenticated users"
  on public.academic_sources for select using (auth.role() = 'authenticated');

create policy "own project sources"
  on public.project_sources for select using (auth.uid() = owner_id);
