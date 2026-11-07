"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Alert, Button, Card, Input, Label, Select, Textarea } from "@/components/ui";
import { CITATION_STYLES, RESEARCH_LEVELS, TEMPLATES } from "@/config/templates";
import type { CitationStyle, Project, ProjectTemplate, ResearchLevel } from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

export default function ProjectSettingsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    browserApi<Project>(`/projects/${projectId}`)
      .then(setProject)
      .catch(() => setError("Could not load project settings."));
  }, [projectId]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSaving(true);
    setSaved(false);
    setError(null);
    const form = new FormData(e.currentTarget);
    try {
      const updated = await browserApi<Project>(`/projects/${projectId}`, {
        method: "PATCH",
        body: JSON.stringify({
          name: String(form.get("name")),
          topic: String(form.get("topic")),
          description: String(form.get("description") || "") || null,
          discipline: String(form.get("discipline") || "") || null,
          research_level: (form.get("research_level") as ResearchLevel) || null,
          template: form.get("template") as ProjectTemplate,
          citation_style: form.get("citation_style") as CitationStyle,
          objectives: String(form.get("objectives") || "")
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
          research_questions: String(form.get("research_questions") || "")
            .split("\n")
            .map((s) => s.trim())
            .filter(Boolean),
          keywords: String(form.get("keywords") || "")
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        }),
      });
      setProject(updated);
      setSaved(true);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  }

  if (!project) {
    return <p className="text-sm text-stone-500">{error ?? "Loading project settings…"}</p>;
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Project Settings</h1>
        <p className="mt-1 text-sm text-stone-600">
          Update the context that guides discovery, assistant retrieval and document structure.
        </p>
      </div>

      <form onSubmit={onSubmit} className="space-y-6">
        {error && <Alert tone="error">{error}</Alert>}
        {saved && <Alert tone="success">Project settings saved.</Alert>}

        <Card className="space-y-4 p-6">
          <div>
            <Label htmlFor="name">Project title *</Label>
            <Input id="name" name="name" defaultValue={project.name} required />
          </div>
          <div>
            <Label htmlFor="topic">Research topic *</Label>
            <Textarea id="topic" name="topic" rows={2} defaultValue={project.topic} required />
          </div>
          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              name="description"
              rows={2}
              defaultValue={project.description ?? ""}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="discipline">Discipline</Label>
              <Input id="discipline" name="discipline" defaultValue={project.discipline ?? ""} />
            </div>
            <div>
              <Label htmlFor="research_level">Research level</Label>
              <Select
                id="research_level"
                name="research_level"
                defaultValue={project.research_level ?? "undergraduate"}
              >
                {RESEARCH_LEVELS.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label htmlFor="template">Document template</Label>
              <Select id="template" name="template" defaultValue={project.template}>
                {TEMPLATES.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="citation_style">Citation style</Label>
              <Select id="citation_style" name="citation_style" defaultValue={project.citation_style}>
                {CITATION_STYLES.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <div>
            <Label htmlFor="objectives">Research objectives (one per line)</Label>
            <Textarea
              id="objectives"
              name="objectives"
              rows={3}
              defaultValue={project.objectives.join("\n")}
            />
          </div>
          <div>
            <Label htmlFor="research_questions">Research questions (one per line)</Label>
            <Textarea
              id="research_questions"
              name="research_questions"
              rows={3}
              defaultValue={project.research_questions.join("\n")}
            />
          </div>
          <div>
            <Label htmlFor="keywords">Keywords (comma-separated)</Label>
            <Input id="keywords" name="keywords" defaultValue={project.keywords.join(", ")} />
          </div>
        </Card>

        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </form>
    </div>
  );
}
