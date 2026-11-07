"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Archive, ArchiveRestore, Trash2 } from "lucide-react";
import { ApiError, quotaMessage, type Project } from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

export function ProjectCardActions({ project }: { project: Project }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);

  async function toggleArchive() {
    setBusy(true);
    try {
      const nextStatus = project.status === "archived" ? "active" : "archived";
      await browserApi(`/projects/${project.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      router.refresh();
    } catch (err) {
      alert(err instanceof ApiError && err.isQuota ? quotaMessage(err) : "Could not update project.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!confirm(`Permanently delete "${project.name}"? This cannot be undone.`)) return;
    setBusy(true);
    try {
      await browserApi(`/projects/${project.id}`, { method: "DELETE" });
      router.refresh();
    } catch {
      alert("Could not delete project.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-1">
      <button
        type="button"
        onClick={toggleArchive}
        disabled={busy}
        title={project.status === "archived" ? "Restore project" : "Archive project"}
        className="rounded p-1 text-stone-500 hover:bg-stone-100 hover:text-ink"
      >
        {project.status === "archived" ? (
          <ArchiveRestore className="size-3.5" aria-hidden />
        ) : (
          <Archive className="size-3.5" aria-hidden />
        )}
      </button>
      <button
        type="button"
        onClick={remove}
        disabled={busy}
        title="Delete project"
        className="rounded p-1 text-stone-500 hover:bg-red-50 hover:text-red-600"
      >
        <Trash2 className="size-3.5" aria-hidden />
      </button>
    </div>
  );
}
