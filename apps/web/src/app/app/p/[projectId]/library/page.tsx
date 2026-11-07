"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertCircle,
  BookOpen,
  CheckCircle2,
  FileText,
  Trash2,
  Upload,
} from "lucide-react";
import { Alert, Badge, Button, buttonClass, Card } from "@/components/ui";
import { ApiError, quotaMessage, type ProjectSource } from "@/lib/api";
import { browserApi } from "@/lib/api/browser";
import { formatRelative } from "@/lib/utils";

export default function LibraryPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [sources, setSources] = useState<ProjectSource[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSources = useCallback(async () => {
    setLoading(true);
    try {
      const list = await browserApi<ProjectSource[]>(`/projects/${projectId}/sources`);
      setSources(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load project library.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  async function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const file = fileList[0];
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      await browserApi<ProjectSource>(`/projects/${projectId}/sources/upload`, {
        method: "POST",
        body: formData,
      });
      await loadSources();
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not upload PDF.");
      }
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function removeSource(id: string, title: string) {
    if (!confirm(`Delete "${title}" from this project?`)) return;
    try {
      await browserApi(`/projects/${projectId}/sources/${id}`, { method: "DELETE" });
      setSources((prev) => prev.filter((s) => s.id !== id));
      router.refresh();
    } catch {
      setError("Could not delete source.");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold md:text-3xl">Project Library</h1>
          <p className="mt-1 text-sm text-stone-600">
            Upload PDF papers or inspect sources saved from Discover. Every indexed passage is ready
            for grounded Q&amp;A and literature synthesis.
          </p>
        </div>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <Button
            type="button"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="size-4" aria-hidden />
            {uploading ? "Uploading & indexing…" : "Upload PDF"}
          </Button>
        </div>
      </div>

      {/* Dropzone card */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          handleFiles(e.dataTransfer.files);
        }}
        className="rounded-xl border-2 border-dashed border-stone-300 bg-white p-6 text-center transition hover:border-brand-500"
      >
        <FileText className="mx-auto size-8 text-brand-600" aria-hidden />
        <p className="mt-2 text-sm font-medium text-ink">
          Drag and drop a text-based PDF here, or{" "}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="text-brand-600 underline"
          >
            browse your files
          </button>
        </p>
        <p className="mt-1 text-xs text-stone-500">
          Duplicate files in the same project are detected automatically.
        </p>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {loading ? (
        <p className="text-sm text-stone-500">Loading library…</p>
      ) : sources.length === 0 ? (
        <Card className="p-8 text-center">
          <p className="font-medium text-ink">Your project library is empty</p>
          <p className="mt-1 text-sm text-stone-600">
            Upload a PDF above or search scholarly works in{" "}
            <Link href={`/app/p/${projectId}/discover`} className="text-brand-600 underline">
              Discover
            </Link>
            .
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {sources.map((src) => {
            const doc = src.document;
            const authorsText =
              src.authors.length > 0
                ? src.authors.map((a) => a.name).slice(0, 3).join(", ") +
                  (src.authors.length > 3 ? " et al." : "")
                : "Authors not specified";

            return (
              <Card key={src.id} className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="max-w-3xl space-y-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="bg-brand-50 text-brand-800">
                        {src.source_kind === "document" ? "Uploaded PDF" : "Saved record"}
                      </Badge>
                      {doc && (
                        <Badge
                          className={
                            doc.status === "ready"
                              ? "bg-emerald-100 text-emerald-800"
                              : doc.status === "failed"
                                ? "bg-red-100 text-red-800"
                                : "bg-accent-100 text-accent-600"
                          }
                        >
                          {doc.status === "ready" ? (
                            <span className="inline-flex items-center gap-1">
                              <CheckCircle2 className="size-3" aria-hidden /> Ready ({doc.page_count}p)
                            </span>
                          ) : doc.status === "failed" ? (
                            <span className="inline-flex items-center gap-1">
                              <AlertCircle className="size-3" aria-hidden /> Failed
                            </span>
                          ) : (
                            doc.status
                          )}
                        </Badge>
                      )}
                      {src.publication_year && <Badge>{src.publication_year}</Badge>}
                    </div>

                    <Link
                      href={`/app/p/${projectId}/library/${src.id}`}
                      className="block font-display text-lg font-semibold text-ink hover:text-brand-700"
                    >
                      {src.title}
                    </Link>
                    <p className="text-sm text-stone-600">{authorsText}</p>
                    {doc?.error_message && (
                      <p className="text-xs font-medium text-red-600">{doc.error_message}</p>
                    )}
                    <p className="text-xs text-stone-400">
                      Added {formatRelative(src.created_at)}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link
                      href={`/app/p/${projectId}/library/${src.id}`}
                      className={buttonClass("secondary", "sm")}
                    >
                      <BookOpen className="size-3.5" aria-hidden /> Open Reader
                    </Link>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeSource(src.id, src.title)}
                      aria-label="Delete source"
                    >
                      <Trash2 className="size-3.5 text-red-600" aria-hidden />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
