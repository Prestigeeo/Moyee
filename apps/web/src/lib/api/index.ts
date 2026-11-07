import { API_URL } from "@/lib/env";

/* Shared types mirroring the FastAPI schemas. */

export type ResearchLevel = "undergraduate" | "postgraduate" | "professional";
export type CitationStyle = "apa7" | "harvard" | "ieee";
export type ProjectTemplate = "thesis" | "journal_article" | "report" | "blank";
export type ProjectStatus = "active" | "completed" | "archived";

export interface Project {
  id: string;
  name: string;
  topic: string;
  description: string | null;
  discipline: string | null;
  research_level: ResearchLevel | null;
  template: ProjectTemplate;
  citation_style: CitationStyle;
  objectives: string[];
  research_questions: string[];
  keywords: string[];
  status: ProjectStatus;
  source_count: number;
  created_at: string;
  updated_at: string;
}

export type ProjectInput = Partial<Omit<Project, "id" | "source_count" | "created_at" | "updated_at">>;

export interface ProjectSuggestion {
  refined_description: string;
  research_questions: string[];
  objectives: string[];
  keywords: string[];
  methodology_recommendation: string;
  provider: string;
  model: string;
}

export interface Profile {
  id: string;
  email: string | null;
  full_name: string | null;
  research_level: ResearchLevel | null;
  discipline: string | null;
  default_citation_style: CitationStyle;
  created_at: string;
}

export interface Plan {
  id: string;
  name: string;
  price_usd_cents_monthly: number;
  price_usd_cents_yearly: number;
  limits: Record<string, number | null>;
  features: Record<string, string[]>;
}

export interface UsageItem {
  metric: string;
  used: number;
  limit: number | null;
  period: "day" | "month" | null;
  resets_at: string | null;
}

export interface Usage {
  plan: Plan;
  subscription_status: string;
  usage: UsageItem[];
}

export interface AuthorItem {
  name: string;
  given?: string | null;
  family?: string | null;
}

export interface DiscoveredWork {
  provider: string;
  external_id: string;
  doi: string | null;
  title: string;
  authors: AuthorItem[];
  abstract: string | null;
  publication_year: number | null;
  venue: string | null;
  publisher: string | null;
  publication_type: string | null;
  volume: string | null;
  issue: string | null;
  pages: string | null;
  source_url: string | null;
  oa_pdf_url: string | null;
  is_open_access: boolean;
  citation_count: number | null;
  keywords: string[];
}

export interface DiscoverySearchResponse {
  query: string;
  total: number;
  page: number;
  per_page: number;
  results: DiscoveredWork[];
}

export interface DocumentMeta {
  id: string;
  filename: string;
  mime_type: string;
  file_size_bytes: number;
  page_count: number;
  status: "queued" | "processing" | "ready" | "failed";
  error_message: string | null;
  created_at: string;
}

export interface ProjectSource {
  id: string;
  project_id: string;
  academic_source_id: string | null;
  source_kind: string;
  provider: string;
  title: string;
  authors: AuthorItem[];
  abstract: string | null;
  publication_year: number | null;
  venue: string | null;
  publisher: string | null;
  publication_type: string;
  volume: string | null;
  issue: string | null;
  pages: string | null;
  doi: string | null;
  source_url: string | null;
  oa_pdf_url: string | null;
  is_open_access: boolean;
  citation_count: number | null;
  citation_key: string;
  notes: string | null;
  inline_citation: string;
  formatted_reference: string;
  missing_fields: string[];
  document: DocumentMeta | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentPage {
  page_number: number;
  text_content: string;
  char_count: number;
}

export interface SummarySection {
  text: string;
  quote: string | null;
  page_number: number | null;
  chunk_id: string | null;
}

export interface SourceSummary {
  project_source_id: string;
  sections: Record<string, SummarySection>;
  updated_at: string;
}

export interface ReaderView {
  source: ProjectSource;
  pages: DocumentPage[];
  summary: SourceSummary | null;
}

export type AssistantMode = "qa" | "topic" | "methodology" | "explain";

export interface MessageCitation {
  citation_number: number;
  project_source_id: string;
  chunk_id: string | null;
  source_title: string;
  inline_label: string;
  page_number: number | null;
  quote: string;
}

export interface AssistantMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  interpretation: string | null;
  limitations: string | null;
  suggested_actions: string[];
  insufficient_evidence: boolean;
  feedback: number | null;
  provider: string | null;
  model: string | null;
  citations: MessageCitation[];
  created_at: string;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  mode: AssistantMode;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: AssistantMessage[];
}

export type MatrixFieldKey =
  | "aim"
  | "methodology"
  | "sample"
  | "data_collection"
  | "analysis"
  | "findings"
  | "limitations"
  | "relevance";

export interface MatrixCell {
  value: string;
  page_number: number | null;
  quote: string | null;
  user_edited: boolean;
}

export interface MatrixEntry {
  id: string;
  project_source_id: string;
  author_year: string;
  title: string;
  cells: Record<MatrixFieldKey, MatrixCell>;
  updated_at: string;
}

export interface SynthesisTheme {
  theme: string;
  sources: string[];
  summary: string;
}

export interface SynthesisNotes {
  themes: SynthesisTheme[];
  methodological_comparison: string;
  potential_gaps: string[];
}

export interface MatrixSummary {
  id: string;
  project_id: string;
  name: string;
  entry_count: number;
  created_at: string;
  updated_at: string;
}

export interface MatrixDetail {
  id: string;
  project_id: string;
  name: string;
  entries: MatrixEntry[];
  synthesis_notes: SynthesisNotes;
  created_at: string;
  updated_at: string;
}

export type WritingActionType = "clarity" | "grammar" | "academic_tone" | "shorten";

export interface DocumentSectionItem {
  id: string;
  title: string;
  content: string;
}

export interface ResearchDocument {
  id: string;
  project_id: string;
  title: string;
  sections: DocumentSectionItem[];
  cited_source_ids: string[];
  bibliography: string[];
  word_count: number;
  created_at: string;
  updated_at: string;
}

export interface WritingAssistResult {
  action: WritingActionType;
  original: string;
  suggestion: string;
  note: string;
}

export interface ChapterSubsectionGuide {
  heading: string;
  guidance: string;
  starter_sentence: string;
}

export interface ChapterGuide {
  section_title: string;
  chapter_goal: string;
  subsections: ChapterSubsectionGuide[];
  common_mistakes: string[];
  tailored_draft: string;
  cited_source_ids: string[];
  provider: string;
  model: string;
}

export interface CheckoutInit {
  provider: string;
  reference: string;
  authorization_url: string;
  mode: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body: Record<string, unknown> = {},
  ) {
    super(message);
  }
  get isQuota() {
    return this.status === 402 && this.body.code === "quota_exceeded";
  }
}

export async function apiFetch<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init.body instanceof FormData;
  let res: Response;
  try {
    res = await fetch(`${API_URL}/v1${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(0, "Can't reach the Móyee server. Check your connection and try again.");
  }
  if (res.status === 204) return undefined as T;
  const contentType = res.headers.get("content-type") ?? "";
  if (
    contentType.includes("x-bibtex") ||
    contentType.includes("x-research-info-systems") ||
    contentType.startsWith("text/plain") ||
    contentType.startsWith("text/csv")
  ) {
    return (await res.text()) as unknown as T;
  }
  if (contentType.includes("officedocument.wordprocessingml.document")) {
    return (await res.blob()) as unknown as T;
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Something went wrong.";
    throw new ApiError(res.status, detail, body);
  }
  return body as T;
}

export const METRIC_LABELS: Record<string, string> = {
  active_projects: "Active projects",
  assistant_messages: "Assistant messages today",
  academic_searches: "Academic searches today",
  writing_ai_actions: "Writing AI actions today",
  document_summaries: "Document summaries this month",
  documents: "Documents",
  storage_mb: "Storage (MB)",
};

export function quotaMessage(err: ApiError): string {
  const metric = METRIC_LABELS[String(err.body.metric)] ?? String(err.body.metric);
  return `You've reached your plan limit for ${metric.toLowerCase()} (${err.body.limit}). Upgrade to Pro or archive something to continue.`;
}
