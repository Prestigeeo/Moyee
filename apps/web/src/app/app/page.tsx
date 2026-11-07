import type { Metadata } from "next";
import Link from "next/link";
import { Archive, FolderOpen, Plus, Sparkles } from "lucide-react";
import { Alert, Badge, buttonClass, Card } from "@/components/ui";
import { TEMPLATES } from "@/config/templates";
import { serverApi } from "@/lib/api/server";
import type { Project } from "@/lib/api";
import { formatRelative } from "@/lib/utils";
import { ProjectCardActions } from "./project-card-actions";

export const metadata: Metadata = { title: "Dashboard" };

const EXAMPLE_TOPICS = [
  {
    name: "Climate & Smallholder Yields",
    topic: "Effects of seasonal rainfall variability on smallholder maize yields",
    discipline: "Agricultural Science",
  },
  {
    name: "AI Tutoring in Higher Education",
    topic: "Impact of evidence-grounded AI feedback on undergraduate academic writing",
    discipline: "Education & Computing",
  },
  {
    name: "Urban FinTech Adoption",
    topic: "Determinants of mobile payment adoption among micro-enterprises",
    discipline: "Economics & Business",
  },
];

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>;
}) {
  const { tab } = await searchParams;
  const showArchived = tab === "archived";

  let projects: Project[] = [];
  let apiError: string | null = null;
  try {
    projects = await serverApi<Project[]>(`/projects?archived=${showArchived}`);
  } catch (err) {
    apiError = err instanceof Error ? err.message : "Could not load your projects.";
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-semibold">Research Projects</h1>
          <p className="mt-1 text-sm text-stone-600">
            Every project keeps its sources, assistant conversations, matrices and chapters together.
          </p>
        </div>
        <Link href="/app/projects/new" className={buttonClass("primary", "md")}>
          <Plus className="size-4" aria-hidden /> New project
        </Link>
      </div>

      {/* Active / Archived tabs */}
      <div className="mt-6 flex gap-2 border-b border-stone-200">
        <Link
          href="/app"
          className={`border-b-2 px-3 py-2 text-sm font-medium ${
            !showArchived
              ? "border-brand-600 text-brand-700"
              : "border-transparent text-stone-500 hover:text-ink"
          }`}
        >
          Active
        </Link>
        <Link
          href="/app?tab=archived"
          className={`inline-flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium ${
            showArchived
              ? "border-brand-600 text-brand-700"
              : "border-transparent text-stone-500 hover:text-ink"
          }`}
        >
          <Archive className="size-3.5" aria-hidden /> Archived
        </Link>
      </div>

      {apiError && (
        <Alert tone="error" className="mt-6">
          {apiError}
        </Alert>
      )}

      {projects.length === 0 ? (
        <Card className="mt-8 p-10 text-center">
          <FolderOpen className="mx-auto size-10 text-brand-600" aria-hidden />
          <h2 className="mt-4 font-display text-xl font-semibold">
            {showArchived ? "No archived projects" : "Start your first research project"}
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-stone-600">
            {showArchived
              ? "Archived projects appear here and don’t count toward your active project limit."
              : "Define a topic and research questions, or pick an example below to see how Móyee works."}
          </p>
          {!showArchived && (
            <>
              <div className="mt-6">
                <Link href="/app/projects/new" className={buttonClass("primary", "md")}>
                  <Plus className="size-4" aria-hidden /> Create project
                </Link>
              </div>
              <div className="mx-auto mt-8 max-w-2xl border-t border-stone-100 pt-6 text-left">
                <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-stone-500">
                  <Sparkles className="size-3.5 text-accent-600" aria-hidden /> Or try a starter topic
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  {EXAMPLE_TOPICS.map((ex) => (
                    <Link
                      key={ex.name}
                      href={`/app/projects/new?name=${encodeURIComponent(ex.name)}&topic=${encodeURIComponent(ex.topic)}&discipline=${encodeURIComponent(ex.discipline)}`}
                      className="rounded-lg border border-stone-200 p-3 text-sm hover:border-brand-400 hover:bg-brand-50/40"
                    >
                      <p className="font-medium text-ink">{ex.name}</p>
                      <p className="mt-1 line-clamp-2 text-xs text-stone-600">{ex.topic}</p>
                    </Link>
                  ))}
                </div>
              </div>
            </>
          )}
        </Card>
      ) : (
        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => {
            const tmpl = TEMPLATES.find((t) => t.id === p.template);
            return (
              <Card key={p.id} className="flex flex-col justify-between p-5">
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <Link
                      href={`/app/p/${p.id}`}
                      className="font-display text-lg font-semibold text-ink hover:text-brand-700"
                    >
                      {p.name}
                    </Link>
                    <Badge>{tmpl?.name ?? p.template}</Badge>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-stone-600">{p.topic}</p>
                  {p.discipline && (
                    <p className="mt-2 text-xs text-stone-500">Discipline: {p.discipline}</p>
                  )}
                </div>
                <div className="mt-5 flex items-center justify-between border-t border-stone-100 pt-3 text-xs text-stone-500">
                  <span>
                    {p.source_count} sources · Updated {formatRelative(p.updated_at)}
                  </span>
                  <ProjectCardActions project={p} />
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
