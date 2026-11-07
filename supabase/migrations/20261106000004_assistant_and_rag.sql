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
