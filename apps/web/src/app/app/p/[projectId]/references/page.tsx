"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, Copy, Download, Pencil, Plus, Trash2 } from "lucide-react";
import { Alert, Badge, Button, Card, Input, Label, Select } from "@/components/ui";
import { CITATION_STYLES } from "@/config/templates";
import type { CitationStyle, ProjectSource } from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

const MISSING_LABELS: Record<string, string> = {
  authors: "authors",
  publication_year: "year",
  venue_or_publisher: "journal/publisher",
  doi_or_url: "DOI or URL",
};

export default function ReferencesPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [sources, setSources] = useState<ProjectSource[]>([]);
  const [style, setStyle] = useState<CitationStyle>("apa7");
  const [showAdd, setShowAdd] = useState(false);
  const [editing, setEditing] = useState<ProjectSource | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSources = useCallback(
    async (selectedStyle: CitationStyle) => {
      setLoading(true);
      try {
        const list = await browserApi<ProjectSource[]>(
          `/projects/${projectId}/sources?style=${selectedStyle}`,
        );
        setSources(list);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load references.");
      } finally {
        setLoading(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    loadSources(style);
  }, [loadSources, style]);

  async function onCreateManual(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    const authorsRaw = String(form.get("authors") || "");
    const yearRaw = String(form.get("publication_year") || "");
    try {
      await browserApi(`/projects/${projectId}/sources`, {
        method: "POST",
        body: JSON.stringify({
          title: String(form.get("title")),
          authors: authorsRaw
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
            .map((name) => ({ name })),
          publication_year: yearRaw ? Number(yearRaw) : null,
          venue: String(form.get("venue") || "") || null,
          publisher: String(form.get("publisher") || "") || null,
          volume: String(form.get("volume") || "") || null,
          issue: String(form.get("issue") || "") || null,
          pages: String(form.get("pages") || "") || null,
          doi: String(form.get("doi") || "") || null,
          source_url: String(form.get("source_url") || "") || null,
        }),
      });
      setShowAdd(false);
      await loadSources(style);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add reference.");
    }
  }

  async function onSaveEdit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!editing) return;
    const form = new FormData(e.currentTarget);
    const authorsRaw = String(form.get("authors") || "");
    const yearRaw = String(form.get("publication_year") || "");
    try {
      await browserApi(`/projects/${projectId}/sources/${editing.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: String(form.get("title")),
          authors: authorsRaw
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
            .map((name) => ({ name })),
          publication_year: yearRaw ? Number(yearRaw) : null,
          venue: String(form.get("venue") || "") || null,
          publisher: String(form.get("publisher") || "") || null,
          volume: String(form.get("volume") || "") || null,
          issue: String(form.get("issue") || "") || null,
          pages: String(form.get("pages") || "") || null,
          doi: String(form.get("doi") || "") || null,
          source_url: String(form.get("source_url") || "") || null,
        }),
      });
      setEditing(null);
      await loadSources(style);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update reference.");
    }
  }

  async function removeSource(id: string, title: string) {
    if (!confirm(`Remove "${title}" from this project?`)) return;
    try {
      await browserApi(`/projects/${projectId}/sources/${id}`, { method: "DELETE" });
      setSources((prev) => prev.filter((s) => s.id !== id));
    } catch {
      setError("Could not delete reference.");
    }
  }

  async function downloadBibtex() {
    try {
      const bib = await browserApi<string>(`/projects/${projectId}/sources/bibtex`);
      const blob = new Blob([bib], { type: "application/x-bibtex;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `moyee-references-${projectId}.bib`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not export BibTeX.");
    }
  }

  function copyCitation(id: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold md:text-3xl">
            References &amp; Citations
          </h1>
          <p className="mt-1 text-sm text-stone-600">
            Format citations in APA 7, Harvard or IEEE, fix missing metadata, and export BibTeX.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Select
            value={style}
            onChange={(e) => setStyle(e.target.value as CitationStyle)}
            aria-label="Citation style"
            className="w-44"
          >
            {CITATION_STYLES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.label}
              </option>
            ))}
          </Select>
          <Button type="button" variant="secondary" size="md" onClick={() => setShowAdd(!showAdd)}>
            <Plus className="size-4" aria-hidden /> Add manually
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="md"
            disabled={sources.length === 0}
            onClick={downloadBibtex}
          >
            <Download className="size-4" aria-hidden /> Export BibTeX
          </Button>
        </div>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {showAdd && (
        <Card className="p-6">
          <h2 className="font-semibold">Add reference manually</h2>
          <form onSubmit={onCreateManual} className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Label htmlFor="title">Title *</Label>
              <Input id="title" name="title" required />
            </div>
            <div>
              <Label htmlFor="authors">Authors (comma-separated)</Label>
              <Input id="authors" name="authors" placeholder="Ada Okafor, Musa Bello" />
            </div>
            <div>
              <Label htmlFor="publication_year">Publication year</Label>
              <Input id="publication_year" name="publication_year" type="number" placeholder="2023" />
            </div>
            <div>
              <Label htmlFor="venue">Journal / conference / book</Label>
              <Input id="venue" name="venue" />
            </div>
            <div>
              <Label htmlFor="publisher">Publisher</Label>
              <Input id="publisher" name="publisher" />
            </div>
            <div>
              <Label htmlFor="volume">Volume</Label>
              <Input id="volume" name="volume" />
            </div>
            <div>
              <Label htmlFor="issue">Issue</Label>
              <Input id="issue" name="issue" />
            </div>
            <div>
              <Label htmlFor="pages">Pages</Label>
              <Input id="pages" name="pages" placeholder="10-22" />
            </div>
            <div>
              <Label htmlFor="doi">DOI</Label>
              <Input id="doi" name="doi" placeholder="10.1016/..." />
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="source_url">URL</Label>
              <Input id="source_url" name="source_url" type="url" />
            </div>
            <div className="flex justify-end gap-2 sm:col-span-2">
              <Button type="button" variant="ghost" onClick={() => setShowAdd(false)}>
                Cancel
              </Button>
              <Button type="submit">Save reference</Button>
            </div>
          </form>
        </Card>
      )}

      {editing && (
        <Card className="border-brand-300 p-6">
          <h2 className="font-semibold">Edit reference</h2>
          <form onSubmit={onSaveEdit} className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Label htmlFor="edit_title">Title *</Label>
              <Input id="edit_title" name="title" defaultValue={editing.title} required />
            </div>
            <div>
              <Label htmlFor="edit_authors">Authors (comma-separated)</Label>
              <Input
                id="edit_authors"
                name="authors"
                defaultValue={editing.authors.map((a) => a.name).join(", ")}
              />
            </div>
            <div>
              <Label htmlFor="edit_year">Publication year</Label>
              <Input
                id="edit_year"
                name="publication_year"
                type="number"
                defaultValue={editing.publication_year ?? ""}
              />
            </div>
            <div>
              <Label htmlFor="edit_venue">Journal / venue</Label>
              <Input id="edit_venue" name="venue" defaultValue={editing.venue ?? ""} />
            </div>
            <div>
              <Label htmlFor="edit_publisher">Publisher</Label>
              <Input id="edit_publisher" name="publisher" defaultValue={editing.publisher ?? ""} />
            </div>
            <div>
              <Label htmlFor="edit_volume">Volume</Label>
              <Input id="edit_volume" name="volume" defaultValue={editing.volume ?? ""} />
            </div>
            <div>
              <Label htmlFor="edit_issue">Issue</Label>
              <Input id="edit_issue" name="issue" defaultValue={editing.issue ?? ""} />
            </div>
            <div>
              <Label htmlFor="edit_pages">Pages</Label>
              <Input id="edit_pages" name="pages" defaultValue={editing.pages ?? ""} />
            </div>
            <div>
              <Label htmlFor="edit_doi">DOI</Label>
              <Input id="edit_doi" name="doi" defaultValue={editing.doi ?? ""} />
            </div>
            <div className="sm:col-span-2">
              <Label htmlFor="edit_url">URL</Label>
              <Input id="edit_url" name="source_url" defaultValue={editing.source_url ?? ""} />
            </div>
            <div className="flex justify-end gap-2 sm:col-span-2">
              <Button type="button" variant="ghost" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button type="submit">Update reference</Button>
            </div>
          </form>
        </Card>
      )}

      {loading ? (
        <p className="text-sm text-stone-500">Loading references…</p>
      ) : sources.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="font-medium text-ink">No references in this project yet</p>
          <p className="mt-1 text-sm text-stone-600">
            Save papers from Discover or click “Add manually” above.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {sources.map((src) => (
            <Card key={src.id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-3xl space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge className="bg-brand-50 text-brand-800">{src.inline_citation}</Badge>
                    <Badge>{src.provider}</Badge>
                    {src.missing_fields.length > 0 && (
                      <span className="inline-flex items-center gap-1 rounded-full bg-accent-100 px-2.5 py-0.5 text-xs font-medium text-accent-600">
                        <AlertTriangle className="size-3" aria-hidden />
                        Missing: {src.missing_fields.map((m) => MISSING_LABELS[m] ?? m).join(", ")}
                      </span>
                    )}
                  </div>
                  <p className="font-reading text-sm leading-relaxed text-ink">
                    {src.formatted_reference}
                  </p>
                </div>

                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => copyCitation(src.id, src.formatted_reference)}
                  >
                    <Copy className="size-3.5" aria-hidden />
                    {copiedId === src.id ? "Copied" : "Copy"}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setEditing(src)}
                    aria-label="Edit reference"
                  >
                    <Pencil className="size-3.5" aria-hidden />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeSource(src.id, src.title)}
                    aria-label="Delete reference"
                  >
                    <Trash2 className="size-3.5 text-red-600" aria-hidden />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
