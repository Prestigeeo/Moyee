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
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
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
-- Móyee schema v4: conversations, messages, message_citations (grounded RAG assistant).

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  title varchar(255) not null,
  mode varchar(32) not null default 'qa'
    check (mode in ('qa','topic','methodology','explain')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists conversations_project_idx on public.conversations (project_id);
create index if not exists conversations_owner_idx on public.conversations (owner_id);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations (id) on delete cascade,
  project_id uuid not null references public.projects (id) on delete cascade,
  owner_id uuid not null references public.profiles (id) on delete cascade,
  role varchar(16) not null check (role in ('user','assistant')),
  content text not null,
  interpretation text,
  limitations text,
  suggested_actions jsonb not null default '[]'::jsonb,
  insufficient_evidence boolean not null default false,
  feedback integer check (feedback in (-1, 1)),
  provider varchar(32),
  model varchar(64),
  created_at timestamptz not null default now()
);
create index if not exists messages_conversation_idx on public.messages (conversation_id);

create table if not exists public.message_citations (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references public.messages (id) on delete cascade,
  citation_number integer not null,
  project_source_id uuid not null references public.project_sources (id) on delete cascade,
  chunk_id uuid references public.document_chunks (id) on delete set null,
  source_title text not null,
  inline_label varchar(120) not null,
  page_number integer,
  quote text not null
);
create index if not exists message_citations_msg_idx on public.message_citations (message_id);

alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.message_citations enable row level security;

create policy "own conversations" on public.conversations for select using (auth.uid() = owner_id);
create policy "own messages" on public.messages for select using (auth.uid() = owner_id);
create policy "own message citations" on public.message_citations for select
  using (exists (select 1 from public.messages m where m.id = message_id and m.owner_id = auth.uid()));
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
