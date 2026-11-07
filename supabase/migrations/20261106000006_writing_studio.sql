-- Móyee schema v6: research_documents (Writing Studio & DOCX export).

create table if not exists public.research_documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  title varchar(300) not null,
  -- Ordered array of {"id": str, "title": str, "content": str}
  sections jsonb not null default '[]'::jsonb,
  cited_source_ids jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists research_documents_project_idx on public.research_documents (project_id);
create index if not exists research_documents_owner_idx on public.research_documents (owner_id);

alter table public.research_documents enable row level security;

create policy "own research documents"
  on public.research_documents for select using (auth.uid() = owner_id);
