-- Móyee schema v5: literature_matrices, literature_entries (Literature Review & Synthesis Studio).

create table if not exists public.literature_matrices (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  name varchar(255) not null,
  synthesis_notes jsonb not null default '{}'::jsonb, -- themes, contradictions, gaps
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists literature_matrices_project_idx on public.literature_matrices (project_id);
create index if not exists literature_matrices_owner_idx on public.literature_matrices (owner_id);

create table if not exists public.literature_entries (
  id uuid primary key default gen_random_uuid(),
  matrix_id uuid not null references public.literature_matrices (id) on delete cascade,
  project_source_id uuid not null references public.project_sources (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  -- Each key ('aim','methodology','sample','data_collection','analysis','findings','limitations','relevance')
  -- stores {"value": str, "page_number": int | null, "quote": str | null, "user_edited": bool}
  cells jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (matrix_id, project_source_id)
);
create index if not exists literature_entries_matrix_idx on public.literature_entries (matrix_id);

alter table public.literature_matrices enable row level security;
alter table public.literature_entries enable row level security;

create policy "own literature matrices" on public.literature_matrices for select using (auth.uid() = owner_id);
create policy "own literature entries" on public.literature_entries for select using (auth.uid() = owner_id);
