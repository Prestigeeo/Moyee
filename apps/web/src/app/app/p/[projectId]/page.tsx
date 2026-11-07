import Link from "next/link";
import { CheckCircle2, Circle, FileSearch, Layers, PenLine, Sparkles } from "lucide-react";
import { ProjectAdvisorCard } from "@/components/ProjectAdvisorCard";
import { Badge, buttonClass, Card } from "@/components/ui";
import { CITATION_STYLES, RESEARCH_LEVELS, TEMPLATES } from "@/config/templates";
import type { Project } from "@/lib/api";
import { serverApi } from "@/lib/api/server";

export default async function ProjectOverviewPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const project = await serverApi<Project>(`/projects/${projectId}`);
  const tmpl = TEMPLATES.find((t) => t.id === project.template) ?? TEMPLATES[0];
  const levelLabel = RESEARCH_LEVELS.find((r) => r.id === project.research_level)?.label;
  const styleLabel = CITATION_STYLES.find((c) => c.id === project.citation_style)?.label;

  const base = `/app/p/${project.id}`;
  const checklist = [
    {
      done: project.source_count > 0,
      label: "Discover or upload your first research sources",
      href: `${base}/discover`,
      cta: "Find sources",
      icon: FileSearch,
    },
    {
      done: false,
      label: "Ask the research assistant a grounded question",
      href: `${base}/assistant`,
      cta: "Open assistant",
      icon: Sparkles,
    },
    {
      done: false,
      label: "Compare studies in a literature matrix",
      href: `${base}/literature`,
      cta: "Build matrix",
      icon: Layers,
    },
    {
      done: false,
      label: "Draft your chapters with inline citations",
      href: `${base}/write`,
      cta: "Open writing studio",
      icon: PenLine,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-display text-2xl font-semibold md:text-3xl">{project.name}</h1>
            {levelLabel && <Badge>{levelLabel}</Badge>}
            {styleLabel && <Badge>{styleLabel}</Badge>}
          </div>
          <p className="mt-2 max-w-3xl text-stone-700">{project.topic}</p>
          {project.description && (
            <p className="mt-1 max-w-3xl text-sm text-stone-500">{project.description}</p>
          )}
        </div>
        <Link href={`${base}/settings`} className={buttonClass("secondary", "sm")}>
          Edit project
        </Link>
      </div>

      {/* AI Research Advisor & Project Setup Recommendations */}
      <ProjectAdvisorCard project={project} />

      {/* Onboarding / next steps checklist */}
      <Card className="p-6">
        <h2 className="font-semibold">Next steps in this project</h2>
        <p className="mt-1 text-xs text-stone-500">
          Follow the research loop from sources to cited chapters.
        </p>
        <ul className="mt-4 divide-y divide-stone-100">
          {checklist.map((item) => (
            <li key={item.label} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="flex items-center gap-3 text-sm">
                {item.done ? (
                  <CheckCircle2 className="size-4 text-emerald-600" aria-hidden />
                ) : (
                  <Circle className="size-4 text-stone-300" aria-hidden />
                )}
                <span>{item.label}</span>
              </div>
              <Link href={item.href} className={buttonClass("ghost", "sm")}>
                {item.cta} →
              </Link>
            </li>
          ))}
        </ul>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Research questions</h2>
            <Link href={`${base}/settings`} className="text-xs text-brand-600 hover:underline">
              Edit
            </Link>
          </div>
          {project.research_questions.length === 0 ? (
            <p className="mt-3 text-sm text-stone-500">
              No research questions added yet. Add them in settings so Móyee can tailor retrieval.
            </p>
          ) : (
            <ol className="mt-3 list-inside list-decimal space-y-2 text-sm text-stone-700">
              {project.research_questions.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ol>
          )}

          {project.keywords.length > 0 && (
            <div className="mt-5 border-t border-stone-100 pt-4">
              <p className="text-xs font-medium text-stone-500">Keywords</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {project.keywords.map((kw) => (
                  <Badge key={kw}>{kw}</Badge>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card className="p-6">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">Document structure ({tmpl.name})</h2>
            <Link href={`${base}/write`} className="text-xs text-brand-600 hover:underline">
              Open studio
            </Link>
          </div>
          <ol className="mt-3 space-y-1.5 text-sm text-stone-700">
            {tmpl.sections.map((s) => (
              <li key={s} className="rounded bg-stone-50 px-3 py-1.5">
                {s}
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}
