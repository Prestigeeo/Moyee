"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, Search, Sparkles } from "lucide-react";
import { Alert, Badge, Button, Card } from "@/components/ui";
import type { Project, ProjectSuggestion } from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

export function ProjectAdvisorCard({ project }: { project: Project }) {
  const router = useRouter();
  const [suggestion, setSuggestion] = useState<ProjectSuggestion | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generate() {
    setLoading(true);
    setError(null);
    setApplied(false);
    try {
      const data = await browserApi<ProjectSuggestion>(`/projects/${project.id}/suggest`, {
        method: "POST",
      });
      setSuggestion(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate project recommendations.");
    } finally {
      setLoading(false);
    }
  }

  async function applyAll() {
    if (!suggestion) return;
    setApplying(true);
    setError(null);
    try {
      await browserApi<Project>(`/projects/${project.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          description: suggestion.refined_description,
          research_questions: suggestion.research_questions,
          objectives: suggestion.objectives,
          keywords: suggestion.keywords,
        }),
      });
      setApplied(true);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply recommendations.");
    } finally {
      setApplying(false);
    }
  }

  return (
    <Card className="border-brand-200/80 bg-gradient-to-br from-white via-white to-brand-50/30 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-brand-600" aria-hidden />
            <h2 className="font-semibold text-ink">AI Research Advisor &amp; Topic Recommendations</h2>
            {suggestion && (
              <Badge className="bg-brand-50 text-brand-700">
                {suggestion.provider === "extractive" ? "Template Advisor" : `Powered by ${suggestion.provider}`}
              </Badge>
            )}
          </div>
          <p className="mt-1 text-xs text-stone-600">
            Generate tailored recommendations for your project description, research questions, objectives,
            methodology, and OpenAlex search keywords based on your research topic.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {suggestion && (
            <Button
              type="button"
              size="sm"
              variant={applied ? "secondary" : "primary"}
              disabled={applying || applied}
              onClick={applyAll}
            >
              {applied ? (
                <>
                  <Check className="size-3.5 text-emerald-600" aria-hidden /> Applied to project
                </>
              ) : applying ? (
                "Applying…"
              ) : (
                "Apply all to project"
              )}
            </Button>
          )}
          <Button type="button" size="sm" variant="secondary" disabled={loading} onClick={generate}>
            <Sparkles className="size-3.5 text-brand-600" aria-hidden />
            {loading
              ? "Generating…"
              : suggestion
                ? "Regenerate"
                : "Generate AI recommendations"}
          </Button>
        </div>
      </div>

      {error && <Alert tone="error" className="mt-4">{error}</Alert>}

      {suggestion && (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              Recommended Project Description &amp; Scope
            </p>
            <p className="text-sm leading-relaxed text-stone-800">{suggestion.refined_description}</p>
            {suggestion.methodology_recommendation && (
              <div className="border-t border-stone-100 pt-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Recommended Methodology &amp; Design
                </p>
                <p className="mt-1 text-xs leading-relaxed text-stone-700">
                  {suggestion.methodology_recommendation}
                </p>
              </div>
            )}
          </div>

          <div className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              Recommended Research Questions
            </p>
            <ol className="list-inside list-decimal space-y-1.5 text-xs leading-relaxed text-stone-800">
              {suggestion.research_questions.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ol>

            {suggestion.objectives.length > 0 && (
              <div className="border-t border-stone-100 pt-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                  Recommended Research Objectives
                </p>
                <ul className="mt-1 list-inside list-disc space-y-1 text-xs text-stone-700">
                  {suggestion.objectives.map((o) => (
                    <li key={o}>{o}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {suggestion.keywords.length > 0 && (
            <div className="rounded-lg border border-stone-200 bg-white p-4 md:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                Suggested Discovery Search Queries (Click to search OpenAlex)
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {suggestion.keywords.map((kw) => (
                  <Link
                    key={kw}
                    href={`/app/p/${project.id}/discover?q=${encodeURIComponent(kw)}`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-brand-200 bg-brand-50/60 px-3 py-1 text-xs font-medium text-brand-800 hover:bg-brand-100"
                  >
                    <Search className="size-3" aria-hidden />
                    {kw}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
