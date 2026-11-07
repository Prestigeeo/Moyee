-- Móyee schema v3: documents, document_pages, document_chunks, document_summaries.

create table if not exists public.documents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  project_source_id uuid not null unique references public.project_sources (id) on delete cascade,
  filename varchar(300) not null,
  mime_type varchar(120) not null default 'application/pdf',
  file_size_bytes integer not null,
  sha256 varchar(64) not null,
  storage_path varchar(500) not null,
  page_count integer not null default 0,
  status varchar(32) not null default 'queued'
    check (status in ('queued','processing','ready','failed')),
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (project_id, sha256)
);
create index if not exists documents_project_idx on public.documents (project_id);
create index if not exists documents_owner_idx on public.documents (owner_id);

create table if not exists public.document_pages (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references public.documents (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  page_number integer not null,
  text_content text not null,
  char_count integer not null default 0,
  unique (document_id, page_number)
);
create index if not exists document_pages_doc_idx on public.document_pages (document_id);

create table if not exists public.document_chunks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  project_source_id uuid not null references public.project_sources (id) on delete cascade,
  document_id uuid references public.documents (id) on delete cascade,
  chunk_index integer not null,
  page_number integer,                 -- null when chunk comes from a metadata-only abstract
  char_start integer not null default 0,
  char_end integer not null default 0,
  text_content text not null,
  embedding jsonb,                    -- portable vector representation; pgvector index optional
  created_at timestamptz not null default now()
);
create index if not exists document_chunks_project_idx on public.document_chunks (project_id);
create index if not exists document_chunks_source_idx on public.document_chunks (project_source_id);

create table if not exists public.document_summaries (
  id uuid primary key default gen_random_uuid(),
  project_source_id uuid not null unique references public.project_sources (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  -- Each field stores {"text": str, "page_number": int | null, "quote": str | null, "chunk_id": str | null}
  sections jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.documents enable row level security;
alter table public.document_pages enable row level security;
alter table public.document_chunks enable row level security;
alter table public.document_summaries enable row level security;

create policy "own documents" on public.documents for select using (auth.uid() = owner_id);
create policy "own document pages" on public.document_pages for select using (auth.uid() = owner_id);
create policy "own document chunks" on public.document_chunks for select using (auth.uid() = owner_id);
create policy "own document summaries" on public.document_summaries for select using (auth.uid() = owner_id);
