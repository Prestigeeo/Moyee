"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Download, Layers, Pencil, Plus, Trash2 } from "lucide-react";
import { Alert, Badge, Button, Card, Input, Label, Textarea } from "@/components/ui";
import {
  ApiError,
  quotaMessage,
  type MatrixDetail,
  type MatrixFieldKey,
  type MatrixSummary,
  type ProjectSource,
} from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

const MATRIX_COLUMNS: { key: MatrixFieldKey; label: string }[] = [
  { key: "aim", label: "Research Aim" },
  { key: "methodology", label: "Methodology" },
  { key: "sample", label: "Population / Sample" },
  { key: "data_collection", label: "Data Collection" },
  { key: "analysis", label: "Analysis Method" },
  { key: "findings", label: "Key Findings" },
  { key: "limitations", label: "Limitations" },
  { key: "relevance", label: "Relevance" },
];

export default function LiteraturePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [matrices, setMatrices] = useState<MatrixSummary[]>([]);
  const [activeMatrix, setActiveMatrix] = useState<MatrixDetail | null>(null);
  const [sources, setSources] = useState<ProjectSource[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<Set<string>>(new Set());
  const [matrixName, setMatrixName] = useState("Comparative Literature Matrix");
  const [showBuilder, setShowBuilder] = useState(false);
  const [editingCell, setEditingCell] = useState<{
    entryId: string;
    field: MatrixFieldKey;
    value: string;
  } | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openMatrix = useCallback(
    async (matrixId: string) => {
      try {
        const detail = await browserApi<MatrixDetail>(
          `/projects/${projectId}/matrices/${matrixId}`,
        );
        setActiveMatrix(detail);
      } catch {
        setError("Could not load literature matrix.");
      }
    },
    [projectId],
  );

  useEffect(() => {
    Promise.all([
      browserApi<MatrixSummary[]>(`/projects/${projectId}/matrices`),
      browserApi<ProjectSource[]>(`/projects/${projectId}/sources`),
    ])
      .then(([list, srcs]) => {
        setMatrices(list);
        setSources(srcs);
        setSelectedSourceIds(new Set(srcs.slice(0, 5).map((s) => s.id)));
        if (list.length > 0) openMatrix(list[0].id);
        else setShowBuilder(true);
      })
      .catch(() => setError("Could not load literature studio."));
  }, [projectId, openMatrix]);

  function toggleSource(id: string) {
    setSelectedSourceIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function onCreateMatrix(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (selectedSourceIds.size === 0) return;
    setCreating(true);
    setError(null);
    try {
      const created = await browserApi<MatrixDetail>(`/projects/${projectId}/matrices`, {
        method: "POST",
        body: JSON.stringify({
          name: matrixName,
          source_ids: Array.from(selectedSourceIds),
        }),
      });
      setActiveMatrix(created);
      setShowBuilder(false);
      const list = await browserApi<MatrixSummary[]>(`/projects/${projectId}/matrices`);
      setMatrices(list);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not build literature matrix.");
      }
    } finally {
      setCreating(false);
    }
  }

  async function saveCellEdit() {
    if (!editingCell || !activeMatrix) return;
    try {
      const updated = await browserApi<MatrixDetail>(
        `/projects/${projectId}/matrices/${activeMatrix.id}/entries/${editingCell.entryId}`,
        {
          method: "PATCH",
          body: JSON.stringify({ field: editingCell.field, value: editingCell.value }),
        },
      );
      setActiveMatrix(updated);
      setEditingCell(null);
    } catch {
      setError("Could not update cell.");
    }
  }

  async function downloadCsv() {
    if (!activeMatrix) return;
    try {
      const csvText = await browserApi<string>(
        `/projects/${projectId}/matrices/${activeMatrix.id}/csv`,
      );
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${activeMatrix.name.toLowerCase().replace(/\s+/g, "-")}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not export CSV.");
    }
  }

  async function removeMatrix(matrixId: string) {
    if (!confirm("Delete this literature matrix?")) return;
    try {
      await browserApi(`/projects/${projectId}/matrices/${matrixId}`, { method: "DELETE" });
      const remaining = matrices.filter((m) => m.id !== matrixId);
      setMatrices(remaining);
      if (activeMatrix?.id === matrixId) {
        if (remaining.length > 0) openMatrix(remaining[0].id);
        else setActiveMatrix(null);
      }
    } catch {
      setError("Could not delete matrix.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold md:text-3xl">
            Literature Review &amp; Synthesis Studio
          </h1>
          <p className="mt-1 text-sm text-stone-600">
            Compare studies across aims, methods, samples, findings and limitations. Click any cell
            to edit or jump to its source page.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setShowBuilder(!showBuilder)}
          >
            <Plus className="size-4" aria-hidden /> New matrix
          </Button>
          {activeMatrix && (
            <>
              <Button type="button" variant="secondary" size="sm" onClick={downloadCsv}>
                <Download className="size-4" aria-hidden /> Export CSV
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeMatrix(activeMatrix.id)}
                aria-label="Delete matrix"
              >
                <Trash2 className="size-4 text-red-600" aria-hidden />
              </Button>
            </>
          )}
        </div>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {/* Matrix builder */}
      {showBuilder && (
        <Card className="p-6">
          <h2 className="font-semibold">Build Comparative Literature Matrix</h2>
          {sources.length === 0 ? (
            <p className="mt-2 text-sm text-stone-600">
              Add sources in{" "}
              <Link href={`/app/p/${projectId}/discover`} className="text-brand-600 underline">
                Discover
              </Link>{" "}
              or{" "}
              <Link href={`/app/p/${projectId}/library`} className="text-brand-600 underline">
                Library
              </Link>{" "}
              first.
            </p>
          ) : (
            <form onSubmit={onCreateMatrix} className="mt-4 space-y-4">
              <div>
                <Label htmlFor="matrixName">Matrix title</Label>
                <Input
                  id="matrixName"
                  value={matrixName}
                  onChange={(e) => setMatrixName(e.target.value)}
                  required
                />
              </div>
              <div>
                <Label>Select project sources to compare ({selectedSourceIds.size} selected)</Label>
                <div className="mt-2 max-h-52 space-y-2 overflow-y-auto rounded-lg border border-stone-200 p-3">
                  {sources.map((s) => (
                    <label
                      key={s.id}
                      className="flex cursor-pointer items-center gap-2.5 text-sm text-stone-700"
                    >
                      <input
                        type="checkbox"
                        checked={selectedSourceIds.has(s.id)}
                        onChange={() => toggleSource(s.id)}
                        className="size-4 rounded border-stone-300 text-brand-600"
                      />
                      <span className="font-medium text-ink">{s.inline_citation}</span>
                      <span className="truncate text-stone-600">— {s.title}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="ghost" onClick={() => setShowBuilder(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={creating || selectedSourceIds.size === 0}>
                  <Layers className="size-4" aria-hidden />
                  {creating ? "Extracting matrix…" : "Extract & compare"}
                </Button>
              </div>
            </form>
          )}
        </Card>
      )}

      {/* Active matrix table */}
      {activeMatrix && (
        <>
          <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white shadow-sm">
            <table className="w-full min-w-[1100px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-stone-200 bg-stone-50 text-stone-600">
                  <th className="sticky left-0 bg-stone-50 p-3 font-semibold">Study</th>
                  {MATRIX_COLUMNS.map((col) => (
                    <th key={col.key} className="p-3 font-semibold">
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-100 align-top">
                {activeMatrix.entries.map((entry) => (
                  <tr key={entry.id} className="hover:bg-stone-50/60">
                    <td className="sticky left-0 w-48 bg-white p-3 font-medium text-ink">
                      <p className="text-brand-700">{entry.author_year}</p>
                      <p className="mt-1 line-clamp-3 text-stone-600">{entry.title}</p>
                    </td>
                    {MATRIX_COLUMNS.map((col) => {
                      const cell = entry.cells[col.key] ?? {
                        value: "Not reported",
                        page_number: null,
                        quote: null,
                        user_edited: false,
                      };
                      const isEditing =
                        editingCell?.entryId === entry.id && editingCell.field === col.key;

                      return (
                        <td key={col.key} className="w-56 p-3">
                          {isEditing ? (
                            <div className="space-y-2">
                              <Textarea
                                rows={3}
                                value={editingCell.value}
                                onChange={(e) =>
                                  setEditingCell({ ...editingCell, value: e.target.value })
                                }
                                className="text-xs"
                              />
                              <div className="flex gap-1">
                                <Button type="button" size="sm" onClick={saveCellEdit}>
                                  Save
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => setEditingCell(null)}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <div className="group space-y-1.5">
                              <p
                                className={
                                  cell.value === "Not reported"
                                    ? "italic text-stone-400"
                                    : "leading-relaxed text-ink"
                                }
                              >
                                {cell.value}
                              </p>
                              <div className="flex items-center gap-1.5">
                                {cell.page_number != null && (
                                  <Link
                                    href={`/app/p/${projectId}/library/${entry.project_source_id}?page=${cell.page_number}&q=${encodeURIComponent((cell.quote ?? "").slice(0, 50))}`}
                                    className="rounded bg-accent-100 px-1.5 py-0.5 text-[11px] font-semibold text-accent-600 hover:bg-accent-300/60"
                                  >
                                    [p. {cell.page_number}]
                                  </Link>
                                )}
                                {cell.user_edited && <Badge>Edited ✎</Badge>}
                                <button
                                  type="button"
                                  onClick={() =>
                                    setEditingCell({
                                      entryId: entry.id,
                                      field: col.key,
                                      value: cell.value === "Not reported" ? "" : cell.value,
                                    })
                                  }
                                  className="opacity-0 transition group-hover:opacity-100"
                                  aria-label={`Edit ${col.label}`}
                                >
                                  <Pencil className="size-3 text-stone-400 hover:text-ink" />
                                </button>
                              </div>
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Synthesis Notes: Themes, Methodological Comparison & Potential Gaps */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="p-5">
              <h2 className="font-semibold">Recurring Themes &amp; Methodologies</h2>
              {activeMatrix.synthesis_notes.themes.length > 0 && (
                <ul className="mt-3 space-y-2 text-xs text-stone-700">
                  {activeMatrix.synthesis_notes.themes.map((t) => (
                    <li key={t.theme} className="rounded bg-stone-50 p-2.5">
                      <span className="font-semibold text-ink">{t.theme}:</span> {t.summary}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-3 text-xs leading-relaxed text-stone-600">
                <strong>Methodological comparison:</strong>{" "}
                {activeMatrix.synthesis_notes.methodological_comparison}
              </p>
            </Card>

            <Card className="p-5">
              <h2 className="font-semibold">Potential Research Gaps</h2>
              <p className="mt-1 text-xs text-stone-500">
                Candidate areas identified from missing or contrasting fields—always verify against
                full domain literature.
              </p>
              <ul className="mt-3 list-inside list-disc space-y-2 text-xs text-stone-700">
                {activeMatrix.synthesis_notes.potential_gaps.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}
