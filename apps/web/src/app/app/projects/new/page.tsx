"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Sparkles } from "lucide-react";
import { Alert, Badge, Button, Card, Input, Label, Select, Textarea } from "@/components/ui";
import { CITATION_STYLES, RESEARCH_LEVELS, TEMPLATES } from "@/config/templates";
import {
  ApiError,
  quotaMessage,
  type CitationStyle,
  type Project,
  type ProjectSuggestion,
  type ProjectTemplate,
  type ResearchLevel,
} from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

function NewProjectForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [name, setName] = useState(params.get("name") ?? "");
  const [topic, setTopic] = useState(params.get("topic") ?? "");
  const [description, setDescription] = useState("");
  const [discipline, setDiscipline] = useState(params.get("discipline") ?? "");
  const [researchLevel, setResearchLevel] = useState<ResearchLevel>("undergraduate");
  const [template, setTemplate] = useState<ProjectTemplate>("thesis");
  const [citationStyle, setCitationStyle] = useState<CitationStyle>("apa7");
  const [researchQuestions, setResearchQuestions] = useState("");
  const [objectives, setObjectives] = useState("");
  const [keywords, setKeywords] = useState("");
  const [methodologyAdvice, setMethodologyAdvice] = useState<string | null>(null);
  const [suggesting, setSuggesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function generateRecommendations() {
    if (!topic.trim() && !name.trim()) {
      setError("Enter a project title or research topic first so Móyee AI can tailor recommendations.");
      return;
    }
    setError(null);
    setSuggesting(true);
    try {
      const rec = await browserApi<ProjectSuggestion>("/projects/suggest", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim() || topic.trim().slice(0, 120),
          topic: topic.trim() || name.trim(),
          description: description.trim() || null,
          discipline: discipline.trim() || null,
          research_level: researchLevel,
        }),
      });
      setDescription(rec.refined_description);
      setResearchQuestions(rec.research_questions.join("\n"));
      setObjectives(rec.objectives.join("\n"));
      setKeywords(rec.keywords.join(", "));
      setMethodologyAdvice(rec.methodology_recommendation || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate AI recommendations.");
    } finally {
      setSuggesting(false);
    }
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const created = await browserApi<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          topic: topic.trim(),
          description: description.trim() || null,
          discipline: discipline.trim() || null,
          research_level: researchLevel,
          template,
          citation_style: citationStyle,
          research_questions: researchQuestions.split("\n").map((s) => s.trim()).filter(Boolean),
          objectives: objectives.split("\n").map((s) => s.trim()).filter(Boolean),
          keywords: keywords.split(",").map((s) => s.trim()).filter(Boolean),
        }),
      });
      router.push(`/app/p/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not create project.");
      }
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/app" className="inline-flex items-center gap-1.5 text-sm text-stone-600 hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Back to projects
      </Link>
      <h1 className="mt-4 font-display text-3xl font-semibold">New Research Project</h1>
      <p className="mt-1 text-sm text-stone-600">
        Your topic, questions and settings guide Móyee’s retrieval and writing structure.
      </p>

      <form onSubmit={onSubmit} className="mt-8 space-y-6">
        {error && <Alert tone="error">{error}</Alert>}

        <Card className="space-y-4 p-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="font-semibold">1. Research basics</h2>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              disabled={suggesting}
              onClick={generateRecommendations}
            >
              <Sparkles className="size-3.5 text-brand-600" aria-hidden />
              {suggesting ? "Generating recommendations…" : "Generate Description & Questions with AI"}
            </Button>
          </div>
          <div>
            <Label htmlFor="name">Project title *</Label>
            <Input
              id="name"
              name="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Climate Variability & Maize Yields"
              required
            />
          </div>
          <div>
            <Label htmlFor="topic">Research topic or problem statement *</Label>
            <Textarea
              id="topic"
              name="topic"
              rows={2}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="What question or phenomenon are you investigating?"
              required
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="discipline">Academic discipline</Label>
              <Input
                id="discipline"
                name="discipline"
                value={discipline}
                onChange={(e) => setDiscipline(e.target.value)}
                placeholder="e.g., Computer Science, Economics"
              />
            </div>
            <div>
              <Label htmlFor="research_level">Research level</Label>
              <Select
                id="research_level"
                name="research_level"
                value={researchLevel}
                onChange={(e) => setResearchLevel(e.target.value as ResearchLevel)}
              >
                {RESEARCH_LEVELS.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div>
            <Label htmlFor="description">Project description &amp; background (AI-assisted or manual)</Label>
            <Textarea
              id="description"
              name="description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Scope, problem background, target population, or click 'Generate Description & Questions with AI' above"
            />
          </div>
          {methodologyAdvice && (
            <div className="rounded-lg border border-brand-200 bg-brand-50/50 p-3.5 text-xs text-stone-700">
              <div className="flex items-center gap-1.5 font-semibold text-brand-800">
                <Sparkles className="size-3.5" aria-hidden /> AI Recommended Methodology &amp; Design
              </div>
              <p className="mt-1 leading-relaxed">{methodologyAdvice}</p>
            </div>
          )}
        </Card>

        <Card className="space-y-4 p-6">
          <h2 className="font-semibold">2. Structure, questions &amp; citations</h2>
          <div>
            <Label>Document template</Label>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTemplate(t.id)}
                  className={`rounded-lg border p-3 text-left transition ${
                    template === t.id
                      ? "border-brand-600 bg-brand-50/60 ring-1 ring-brand-600"
                      : "border-stone-200 hover:border-stone-300"
                  }`}
                >
                  <p className="text-sm font-semibold">{t.name}</p>
                  <p className="mt-1 text-xs text-stone-600">{t.description}</p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <Label htmlFor="citation_style">Citation style</Label>
            <Select
              id="citation_style"
              name="citation_style"
              value={citationStyle}
              onChange={(e) => setCitationStyle(e.target.value as CitationStyle)}
            >
              {CITATION_STYLES.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </Select>
          </div>

          <div>
            <div className="flex items-center justify-between">
              <Label htmlFor="research_questions">Research questions (one per line)</Label>
              <Badge className="bg-stone-100 text-stone-600">Guides RAG &amp; Matrix</Badge>
            </div>
            <Textarea
              id="research_questions"
              name="research_questions"
              rows={4}
              value={researchQuestions}
              onChange={(e) => setResearchQuestions(e.target.value)}
              placeholder={"How does seasonal rainfall variability affect maize yield?\nWhat adaptation strategies do farmers use?"}
            />
          </div>

          <div>
            <Label htmlFor="objectives">Research objectives (one per line, optional)</Label>
            <Textarea
              id="objectives"
              name="objectives"
              rows={3}
              value={objectives}
              onChange={(e) => setObjectives(e.target.value)}
              placeholder={"To examine the baseline patterns of...\nTo evaluate the relationship between..."}
            />
          </div>

          <div>
            <Label htmlFor="keywords">Discovery search keywords (comma-separated)</Label>
            <Input
              id="keywords"
              name="keywords"
              value={keywords}
              onChange={(e) => setKeywords(e.target.value)}
              placeholder="rainfall variability, maize, adaptation"
            />
          </div>
        </Card>

        <div className="flex justify-end gap-3">
          <Link href="/app" className="inline-flex h-10 items-center px-4 text-sm text-stone-600 hover:text-ink">
            Cancel
          </Link>
          <Button type="submit" disabled={loading}>
            {loading ? "Creating…" : "Create project"}
          </Button>
        </div>
      </form>
    </div>
  );
}

export default function NewProjectPage() {
  return (
    <Suspense>
      <NewProjectForm />
    </Suspense>
  );
}
