"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { ArrowLeft, ChevronLeft, ChevronRight, Search, Sparkles } from "lucide-react";
import { Alert, Badge, Button, Card, Input } from "@/components/ui";
import { ApiError, quotaMessage, type ReaderView, type SourceSummary } from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

const SECTION_LABELS: { key: string; title: string }[] = [
  { key: "aim", title: "Research Aim & Objective" },
  { key: "methodology", title: "Methodology & Design" },
  { key: "sample", title: "Population & Sample" },
  { key: "findings", title: "Key Findings" },
  { key: "limitations", title: "Stated Limitations" },
];

export default function DocumentReaderPage() {
  const { projectId, sourceId } = useParams<{ projectId: string; sourceId: string }>();
  const searchParams = useSearchParams();
  const initialPage = Number(searchParams.get("page") || "1") || 1;
  const initialHighlight = searchParams.get("q") || "";

  const [view, setView] = useState<ReaderView | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(initialPage);
  const [highlightQuote, setHighlightQuote] = useState<string>(initialHighlight);
  const [searchTerm, setSearchTerm] = useState("");
  const [summarizing, setSummarizing] = useState(false);
  const [importingPdf, setImportingPdf] = useState(false);
  const [customPdfUrl, setCustomPdfUrl] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadReader = useCallback(async () => {
    try {
      const data = await browserApi<ReaderView>(
        `/projects/${projectId}/sources/${sourceId}/reader`,
      );
      setView(data);
      if (data.pages.length > 0 && pageNumber > data.pages.length) {
        setPageNumber(1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load document reader.");
    }
  }, [projectId, sourceId, pageNumber]);

  useEffect(() => {
    loadReader();
  }, [loadReader]);

  async function generateSummary() {
    setSummarizing(true);
    setError(null);
    try {
      const summary = await browserApi<SourceSummary>(
        `/projects/${projectId}/sources/${sourceId}/summarize`,
        { method: "POST" },
      );
      setView((prev) => (prev ? { ...prev, summary } : prev));
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not generate summary.");
      }
    } finally {
      setSummarizing(false);
    }
  }

  async function importFullTextPdf() {
    setImportingPdf(true);
    setError(null);
    try {
      await browserApi(`/projects/${projectId}/sources/${sourceId}/import-pdf`, {
        method: "POST",
        body: JSON.stringify({ pdf_url: customPdfUrl.trim() || null }),
      });
      setCustomPdfUrl("");
      await loadReader();
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not import full-text PDF.");
      }
    } finally {
      setImportingPdf(false);
    }
  }

  function jumpToCitation(targetPage: number | null, quote: string | null) {
    if (targetPage) setPageNumber(targetPage);
    if (quote) setHighlightQuote(quote.slice(0, 120));
  }

  function renderHighlightedText(text: string) {
    const needle = (highlightQuote || searchTerm).trim();
    if (!needle || needle.length < 4) return text;
    const idx = text.toLowerCase().indexOf(needle.toLowerCase());
    if (idx === -1) return text;
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + needle.length);
    const after = text.slice(idx + needle.length);
    return (
      <>
        {before}
        <mark className="rounded bg-accent-300/70 px-1 py-0.5 text-ink">{match}</mark>
        {after}
      </>
    );
  }

  if (!view) {
    return <p className="text-sm text-stone-500">{error ?? "Opening reader…"}</p>;
  }

  const totalPages = view.pages.length;
  const currentPage =
    view.pages.find((p) => p.page_number === pageNumber) ?? view.pages[0] ?? null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link
            href={`/app/p/${projectId}/library`}
            className="inline-flex items-center gap-1.5 text-xs text-stone-500 hover:text-ink"
          >
            <ArrowLeft className="size-3.5" aria-hidden /> Back to project library
          </Link>
          <h1 className="mt-1 font-display text-xl font-semibold md:text-2xl">
            {view.source.title}
          </h1>
          <p className="text-xs text-stone-500">{view.source.formatted_reference}</p>
        </div>
        <Badge className="bg-brand-50 text-brand-800">{view.source.inline_citation}</Badge>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {!view.source.document && (
        <Card className="border-amber-200 bg-amber-50/50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-1">
              <p className="text-xs font-semibold text-amber-900">
                Currently showing Abstract Only (1 page) from OpenAlex metadata
              </p>
              <p className="text-xs text-stone-600">
                Fetch the full-text Open-Access PDF automatically, or paste a direct PDF link
                (e.g. arXiv, PMC, institutional repository) to index all pages of this paper.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                value={customPdfUrl}
                onChange={(e) => setCustomPdfUrl(e.target.value)}
                placeholder={view.source.oa_pdf_url || "Optional direct PDF URL (https://…/paper.pdf)"}
                className="h-8 w-64 bg-white text-xs"
              />
              <Button
                type="button"
                size="sm"
                disabled={importingPdf}
                onClick={importFullTextPdf}
              >
                {importingPdf ? "Fetching & indexing PDF…" : "Fetch Full-Text PDF"}
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: Page viewer */}
        <Card className="flex flex-col lg:col-span-7">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-200 px-4 py-3">
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={pageNumber <= 1}
                onClick={() => {
                  setHighlightQuote("");
                  setPageNumber((p) => Math.max(1, p - 1));
                }}
                aria-label="Previous page"
              >
                <ChevronLeft className="size-4" aria-hidden />
              </Button>
              <span className="text-xs font-medium text-stone-700">
                Page {currentPage?.page_number ?? 1} of {Math.max(1, totalPages)}
              </span>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={pageNumber >= totalPages}
                onClick={() => {
                  setHighlightQuote("");
                  setPageNumber((p) => Math.min(totalPages, p + 1));
                }}
                aria-label="Next page"
              >
                <ChevronRight className="size-4" aria-hidden />
              </Button>
            </div>

            <div className="relative w-48">
              <Search
                className="pointer-events-none absolute left-2.5 top-2.5 size-3.5 text-stone-400"
                aria-hidden
              />
              <Input
                value={searchTerm}
                onChange={(e) => {
                  setHighlightQuote("");
                  setSearchTerm(e.target.value);
                }}
                placeholder="Find on page…"
                className="h-8 pl-8 text-xs"
                aria-label="Find on page"
              />
            </div>
          </div>

          <div className="min-h-[480px] flex-1 p-6">
            {currentPage ? (
              <div className=" whitespace-pre-wrap font-reading text-[15px] leading-relaxed text-ink">
                {renderHighlightedText(currentPage.text_content)}
              </div>
            ) : (
              <p className="text-sm italic text-stone-400">
                No extractable text available for this source.
              </p>
            )}
          </div>
        </Card>

        {/* Right: Cited Summary & Evidence Intelligence */}
        <Card className="flex flex-col p-5 lg:col-span-5">
          <div className="flex items-center justify-between border-b border-stone-100 pb-3">
            <div>
              <h2 className="font-semibold text-ink">Grounded Document Summary</h2>
              <p className="text-xs text-stone-500">
                Click any page badge to jump to the supporting passage.
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              disabled={summarizing || totalPages === 0}
              onClick={generateSummary}
            >
              <Sparkles className="size-3.5" aria-hidden />
              {summarizing
                ? "Extracting…"
                : view.summary
                  ? "Refresh"
                  : "Extract summary"}
            </Button>
          </div>

          {!view.summary ? (
            <div className="py-12 text-center">
              <p className="text-sm text-stone-600">
                Generate a structured extraction of this paper’s aim, methodology, sample, findings
                and limitations—with page references for every claim.
              </p>
            </div>
          ) : (
            <div className="mt-4 space-y-4">
              {SECTION_LABELS.map(({ key, title }) => {
                const sec = view.summary?.sections[key];
                if (!sec) return null;
                return (
                  <div key={key} className="rounded-lg border border-stone-200 bg-stone-50/60 p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-stone-600">
                        {title}
                      </span>
                      {sec.page_number != null ? (
                        <button
                          type="button"
                          onClick={() => jumpToCitation(sec.page_number, sec.quote)}
                          aria-label={`Jump to page ${sec.page_number}`}
                          className="rounded bg-accent-100 px-2 py-0.5 text-xs font-semibold text-accent-600 hover:bg-accent-300/60"
                        >
                          [p. {sec.page_number}]
                        </button>
                      ) : (
                        <Badge>Unreported</Badge>
                      )}
                    </div>
                    <p className="mt-1.5 text-sm leading-relaxed text-ink">{sec.text}</p>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
