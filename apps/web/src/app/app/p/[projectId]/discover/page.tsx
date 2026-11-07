"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Bookmark, Check, ExternalLink, Search } from "lucide-react";
import { Alert, Badge, Button, Card, Input, Label, Select } from "@/components/ui";
import {
  ApiError,
  quotaMessage,
  type DiscoveredWork,
  type DiscoverySearchResponse,
  type ProjectSource,
} from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

export default function DiscoverPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQ = searchParams.get("q") ?? "";
  const [query, setQuery] = useState(initialQ);
  const [provider, setProvider] = useState("openalex");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [openAccessOnly, setOpenAccessOnly] = useState(false);
  const [pubType, setPubType] = useState("");
  const [perPage, setPerPage] = useState(20);
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<DiscoveredWork[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [savedMap, setSavedMap] = useState<Record<string, ProjectSource>>({});
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [savingId, setSavingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    browserApi<ProjectSource[]>(`/projects/${projectId}/sources`)
      .then((sources) => {
        const map: Record<string, ProjectSource> = {};
        sources.forEach((s) => {
          if (s.doi) map[`doi:${s.doi.toLowerCase()}`] = s;
          map[`title:${s.title.toLowerCase()}`] = s;
        });
        setSavedMap(map);
      })
      .catch(() => {});
  }, [projectId]);

  useEffect(() => {
    if (initialQ.trim().length >= 2) {
      setLoading(true);
      browserApi<DiscoverySearchResponse>(
        `/discovery/search?q=${encodeURIComponent(initialQ.trim())}`,
      )
        .then((data) => {
          setResults(data.results);
          setTotal(data.total);
        })
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [initialQ]);

  function getSavedSource(w: DiscoveredWork): ProjectSource | null {
    if (w.doi && savedMap[`doi:${w.doi.toLowerCase()}`]) {
      return savedMap[`doi:${w.doi.toLowerCase()}`];
    }
    return savedMap[`title:${w.title.toLowerCase()}`] ?? null;
  }

  function buildSearchParams(targetPage: number, safePerPage = perPage) {
    const qs = new URLSearchParams({
      q: query.trim(),
      provider,
      page: String(targetPage),
      per_page: String(safePerPage),
    });
    if (yearFrom) qs.set("year_from", yearFrom);
    if (yearTo) qs.set("year_to", yearTo);
    if (openAccessOnly) qs.set("open_access_only", "true");
    if (pubType) qs.set("publication_type", pubType);
    return qs;
  }

  async function fetchSearchWithFallback(targetPage: number): Promise<DiscoverySearchResponse> {
    try {
      const qs = buildSearchParams(targetPage, perPage);
      return await browserApi<DiscoverySearchResponse>(`/discovery/search?${qs.toString()}`);
    } catch (err) {
      // Fallback to per_page=25 if the backend container hasn't updated its per_page cap yet
      if (err instanceof ApiError && err.status === 422 && perPage > 25) {
        const fallbackQs = buildSearchParams(targetPage, 25);
        return await browserApi<DiscoverySearchResponse>(
          `/discovery/search?${fallbackQs.toString()}`,
        );
      }
      throw err;
    }
  }

  async function onSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    setLoading(true);
    setError(null);
    setPage(1);

    try {
      const data = await fetchSearchWithFallback(1);
      setResults(data.results);
      setTotal(data.total);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not search academic works.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function loadMorePapers() {
    if (loadingMore || query.trim().length < 2) return;
    const nextPage = page + 1;
    setLoadingMore(true);
    setError(null);

    try {
      const data = await fetchSearchWithFallback(nextPage);
      setResults((prev) => {
        const seen = new Set(prev.map((w) => w.external_id));
        const nextItems = data.results.filter((w) => !seen.has(w.external_id));
        return [...prev, ...nextItems];
      });
      setPage(nextPage);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not load more papers.");
      }
    } finally {
      setLoadingMore(false);
    }
  }

  async function saveToProject(work: DiscoveredWork) {
    setSavingId(work.external_id);
    setError(null);
    try {
      const created = await browserApi<ProjectSource>(
        `/projects/${projectId}/sources/from-discovery`,
        {
          method: "POST",
          body: JSON.stringify({ ...work, auto_import_pdf: true }),
        },
      );
      setSavedMap((prev) => {
        const next = { ...prev };
        if (work.doi) next[`doi:${work.doi.toLowerCase()}`] = created;
        next[`title:${work.title.toLowerCase()}`] = created;
        return next;
      });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save source to project.");
    } finally {
      setSavingId(null);
    }
  }

  function toggleAbstract(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold md:text-3xl">Academic Discovery</h1>
        <p className="mt-1 text-sm text-stone-600">
          Search scholarly literature via OpenAlex or paste a DOI directly. Saved records are added
          to your project library and references.
        </p>
      </div>

      <Card className="p-5">
        <form onSubmit={onSearch} className="space-y-4">
          <div className="flex flex-col gap-3 sm:flex-row">
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by keywords, title, author, or paste a DOI (e.g. 10.1016/…)"
              aria-label="Academic search query"
              required
            />
            <Button type="submit" disabled={loading} className="shrink-0">
              <Search className="size-4" aria-hidden />
              {loading ? "Searching…" : "Search"}
            </Button>
          </div>

          <div className="grid gap-3 pt-1 sm:grid-cols-6">
            <div className="sm:col-span-2">
              <Label htmlFor="provider" className="text-xs">Database source</Label>
              <Select
                id="provider"
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
              >
                <option value="all">All Databases (OpenAlex + S2 + Crossref)</option>
                <option value="openalex">OpenAlex (250M+ global works)</option>
                <option value="semantic_scholar">Semantic Scholar (214M+ papers)</option>
                <option value="crossref">Crossref (150M+ publisher DOIs)</option>
                <option value="arxiv">arXiv (Full-text preprints)</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="yearFrom" className="text-xs">Year from</Label>
              <Input
                id="yearFrom"
                type="number"
                min={1800}
                max={2100}
                placeholder="e.g. 2018"
                value={yearFrom}
                onChange={(e) => setYearFrom(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="yearTo" className="text-xs">Year to</Label>
              <Input
                id="yearTo"
                type="number"
                min={1800}
                max={2100}
                placeholder="e.g. 2026"
                value={yearTo}
                onChange={(e) => setYearTo(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="pubType" className="text-xs">Publication type</Label>
              <Select id="pubType" value={pubType} onChange={(e) => setPubType(e.target.value)}>
                <option value="">All types</option>
                <option value="article">Journal article</option>
                <option value="book">Book / chapter</option>
                <option value="preprint">Preprint</option>
                <option value="dissertation">Dissertation</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="perPage" className="text-xs">Results per page</Label>
              <Select
                id="perPage"
                value={String(perPage)}
                onChange={(e) => setPerPage(Number(e.target.value))}
              >
                <option value="15">15 per page</option>
                <option value="20">20 per page</option>
                <option value="35">35 per page</option>
                <option value="50">50 per page</option>
              </Select>
            </div>
          </div>
          <div className="flex items-center justify-between pt-1">
            <label className="inline-flex cursor-pointer items-center gap-2 text-xs text-stone-700">
              <input
                type="checkbox"
                checked={openAccessOnly}
                onChange={(e) => setOpenAccessOnly(e.target.checked)}
                className="size-4 rounded border-stone-300 text-brand-600"
              />
              Open-access full-text only (uncheck to include subscription/paywalled papers too)
            </label>
          </div>
        </form>
      </Card>

      {error && <Alert tone="error">{error}</Alert>}

      {total !== null && (
        <p className="text-xs text-stone-500">
          Showing {results.length} of {total.toLocaleString()} matching works
        </p>
      )}

      <div className="space-y-4">
        {results.map((work) => {
          const savedSource = getSavedSource(work);
          const saved = Boolean(savedSource);
          const isOpen = expanded.has(work.external_id);
          const authorsText =
            work.authors.length > 0
              ? work.authors.map((a) => a.name).slice(0, 5).join(", ") +
                (work.authors.length > 5 ? " et al." : "")
              : "Authors not reported";

          return (
            <Card key={work.external_id} className="p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="max-w-3xl space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      className={
                        work.is_open_access
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-stone-100 text-stone-600"
                      }
                    >
                      {work.is_open_access ? "Open access" : "Subscription / Metadata"}
                    </Badge>
                    <Badge className="bg-stone-100 text-stone-700 uppercase">
                      {work.provider.replace("_", " ")}
                    </Badge>
                    {work.publication_year && <Badge>{work.publication_year}</Badge>}
                    {work.citation_count != null && (
                      <span className="text-xs text-stone-500">
                        Cited by {work.citation_count.toLocaleString()}
                      </span>
                    )}
                    {savedSource?.document?.status === "ready" && (
                      <Badge className="bg-emerald-50 text-emerald-700">
                        Full-text PDF indexed ({savedSource.document.page_count}p)
                      </Badge>
                    )}
                  </div>
                  <h2 className="font-display text-lg font-semibold text-ink">{work.title}</h2>
                  <p className="text-sm text-stone-600">{authorsText}</p>
                  <p className="text-xs text-stone-500">
                    {work.venue ?? "Venue not reported"}
                    {work.doi ? ` · DOI: ${work.doi}` : ""}
                  </p>
                </div>

                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    variant={saved ? "secondary" : "primary"}
                    size="sm"
                    disabled={saved || savingId === work.external_id}
                    onClick={() => saveToProject(work)}
                  >
                    {saved ? (
                      <>
                        <Check className="size-3.5 text-emerald-600" aria-hidden />{" "}
                        {savedSource?.document?.status === "ready"
                          ? `Saved (${savedSource.document.page_count}p PDF)`
                          : "Saved"}
                      </>
                    ) : (
                      <>
                        <Bookmark className="size-3.5" aria-hidden />
                        {savingId === work.external_id
                          ? work.oa_pdf_url
                            ? "Saving & fetching PDF…"
                            : "Saving…"
                          : work.oa_pdf_url
                            ? "Save + Fetch Full PDF"
                            : "Save to project"}
                      </>
                    )}
                  </Button>
                  {savedSource && (
                    <Link
                      href={`/app/p/${projectId}/library/${savedSource.id}`}
                      className="inline-flex h-8 items-center gap-1 rounded-lg border border-brand-300 bg-brand-50 px-2.5 text-xs font-medium text-brand-800 hover:bg-brand-100"
                    >
                      Open in Reader →
                    </Link>
                  )}
                  {work.source_url && (
                    <a
                      href={work.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex h-8 items-center gap-1 rounded-lg border border-stone-300 px-2.5 text-xs font-medium text-stone-700 hover:bg-stone-50"
                    >
                      Source <ExternalLink className="size-3" aria-hidden />
                    </a>
                  )}
                  {work.oa_pdf_url && (
                    <a
                      href={work.oa_pdf_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex h-8 items-center gap-1 rounded-lg border border-emerald-300 bg-emerald-50 px-2.5 text-xs font-medium text-emerald-800 hover:bg-emerald-100"
                    >
                      Full-text PDF <ExternalLink className="size-3" aria-hidden />
                    </a>
                  )}
                </div>
              </div>

              {work.abstract ? (
                <div className="mt-3 border-t border-stone-100 pt-3">
                  <p className={`text-sm text-stone-700 ${isOpen ? "" : "line-clamp-3"}`}>
                    {work.abstract}
                  </p>
                  {work.abstract.length > 260 && (
                    <button
                      type="button"
                      onClick={() => toggleAbstract(work.external_id)}
                      className="mt-1 text-xs font-medium text-brand-600 hover:underline"
                    >
                      {isOpen ? "Show less" : "Read full abstract"}
                    </button>
                  )}
                </div>
              ) : (
                <p className="mt-3 text-xs italic text-stone-400">
                  Abstract not available from provider.
                </p>
              )}
            </Card>
          );
        })}
      </div>

      {results.length > 0 && (total === null || results.length < total) && (
        <div className="flex justify-center pt-2">
          <Button
            type="button"
            variant="secondary"
            disabled={loadingMore}
            onClick={loadMorePapers}
          >
            {loadingMore
              ? "Loading more papers…"
              : `Load more papers (${results.length} loaded so far)`}
          </Button>
        </div>
      )}
    </div>
  );
}
