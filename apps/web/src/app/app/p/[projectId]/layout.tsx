import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight } from "lucide-react";
import { Badge } from "@/components/ui";
import { ApiError, type Project } from "@/lib/api";
import { serverApi } from "@/lib/api/server";
import { ProjectSidebar } from "./project-sidebar";

async function loadProject(projectId: string): Promise<Project> {
  try {
    return await serverApi<Project>(`/projects/${projectId}`);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }
}

export default async function ProjectLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  const project = await loadProject(projectId);

  return (
    <div className="flex min-h-[calc(100dvh-3.5rem)] flex-col">
      <div className="border-b border-stone-200 bg-white px-6 py-2.5">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 text-sm">
          <div className="flex items-center gap-2 truncate">
            <Link href="/app" className="text-stone-500 hover:text-ink">
              Projects
            </Link>
            <ChevronRight className="size-4 shrink-0 text-stone-400" aria-hidden />
            <span className="truncate font-medium text-ink">{project.name}</span>
            {project.status === "archived" && <Badge>Archived</Badge>}
          </div>
          <span className="hidden text-xs uppercase tracking-wider text-stone-500 sm:inline">
            {project.citation_style.toUpperCase()}
          </span>
        </div>
      </div>

      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col md:flex-row">
        <ProjectSidebar projectId={projectId} />
        <div className="flex-1 p-6 md:p-8">{children}</div>
      </div>
    </div>
  );
}
