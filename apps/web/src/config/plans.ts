import type { Plan } from "@/lib/api";

/**
 * Fallback copy of plan configuration for the public pricing page.
 * The API (/v1/plans) is the source of truth; this is used if it is unreachable.
 */
export const FALLBACK_PLANS: Plan[] = [
  {
    id: "free",
    name: "Free",
    price_usd_cents_monthly: 0,
    price_usd_cents_yearly: 0,
    limits: {
      active_projects: 3,
      documents: 15,
      storage_mb: 100,
      assistant_messages: 20,
      academic_searches: 30,
      document_summaries: 10,
      matrix_sources: 5,
    },
    features: { citation_styles: ["apa7", "harvard", "ieee"], exports: ["docx", "bibtex", "csv"] },
  },
  {
    id: "pro",
    name: "Pro",
    price_usd_cents_monthly: 1000,
    price_usd_cents_yearly: 9600,
    limits: {
      active_projects: null,
      documents: 300,
      storage_mb: 5120,
      assistant_messages: 300,
      academic_searches: null,
      document_summaries: 200,
      matrix_sources: 15,
    },
    features: {
      citation_styles: ["apa7", "harvard", "ieee", "mla", "chicago"],
      exports: ["docx", "bibtex", "csv", "pdf", "ris"],
    },
  },
];

export const PLAN_TAGLINES: Record<string, string> = {
  free: "For exploring Móyee and smaller assignments.",
  pro: "For active students, postgraduate researchers and professionals.",
};
