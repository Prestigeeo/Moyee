"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  BookOpenCheck,
  Check,
  ChevronDown,
  ChevronUp,
  Copy,
  Download,
  HelpCircle,
  Plus,
  Quote,
  Save,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { Alert, Badge, Button, Card, Input, Textarea } from "@/components/ui";
import {
  ApiError,
  quotaMessage,
  type ChapterGuide,
  type DocumentSectionItem,
  type ProjectSource,
  type ResearchDocument,
  type WritingActionType,
  type WritingAssistResult,
} from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

const WRITING_ACTIONS: { id: WritingActionType; label: string }[] = [
  { id: "clarity", label: "Improve clarity" },
  { id: "grammar", label: "Fix grammar" },
  { id: "academic_tone", label: "Academic tone" },
  { id: "shorten", label: "Shorten" },
];

export default function WritePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [doc, setDoc] = useState<ResearchDocument | null>(null);
  const [sections, setSections] = useState<DocumentSectionItem[]>([]);
  const [citedIds, setCitedIds] = useState<string[]>([]);
  const [activeSecId, setActiveSecId] = useState<string>("");
  const [sources, setSources] = useState<ProjectSource[]>([]);
  const [assistResult, setAssistResult] = useState<WritingAssistResult | null>(null);
  const [assisting, setAssisting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [copiedDoc, setCopiedDoc] = useState(false);
  const [savedNotice, setSavedNotice] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);
  const [chapterGuide, setChapterGuide] = useState<ChapterGuide | null>(null);
  const [loadingGuide, setLoadingGuide] = useState(false);
  const [customGuideQuestion, setCustomGuideQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadStudio = useCallback(async () => {
    try {
      const [loadedDoc, srcs] = await Promise.all([
        browserApi<ResearchDocument>(`/projects/${projectId}/writing`),
        browserApi<ProjectSource[]>(`/projects/${projectId}/sources`),
      ]);
      setDoc(loadedDoc);
      setSections(loadedDoc.sections);
      setCitedIds(loadedDoc.cited_source_ids);
      setSources(srcs);
      if (loadedDoc.sections.length > 0) {
        setActiveSecId((prev) => prev || loadedDoc.sections[0].id);
      }
    } catch {
      setError("Could not load Writing Studio.");
    }
  }, [projectId]);

  useEffect(() => {
    loadStudio();
  }, [loadStudio]);

  const activeSection = sections.find((s) => s.id === activeSecId) ?? sections[0] ?? null;

  function updateActiveContent(content: string) {
    if (!activeSection) return;
    setSections((prev) =>
      prev.map((s) => (s.id === activeSection.id ? { ...s, content } : s)),
    );
  }

  function updateActiveTitle(title: string) {
    if (!activeSection) return;
    setSections((prev) =>
      prev.map((s) => (s.id === activeSection.id ? { ...s, title } : s)),
    );
  }

  function addSection() {
    const newId = `sec-${Date.now()}`;
    const next: DocumentSectionItem = {
      id: newId,
      title: `New Section ${sections.length + 1}`,
      content: "",
    };
    setSections((prev) => [...prev, next]);
    setActiveSecId(newId);
  }

  function removeSection(id: string) {
    if (sections.length <= 1) return;
    const filtered = sections.filter((s) => s.id !== id);
    setSections(filtered);
    if (activeSecId === id) setActiveSecId(filtered[0].id);
  }

  async function saveManuscript(nextSections = sections, nextCitedIds = citedIds) {
    if (!doc) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await browserApi<ResearchDocument>(
        `/projects/${projectId}/writing/${doc.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            title: doc.title,
            sections: nextSections,
            cited_source_ids: nextCitedIds,
          }),
        },
      );
      setDoc(updated);
      setSavedNotice("Saved");
      setTimeout(() => setSavedNotice(null), 2000);
    } catch {
      setError("Could not save document.");
    } finally {
      setSaving(false);
    }
  }

  function insertCitation(src: ProjectSource) {
    if (!activeSection) return;
    const nextContent =
      activeSection.content.trimEnd() +
      (activeSection.content.trim() ? " " : "") +
      src.inline_citation +
      " ";
    const nextSections = sections.map((s) =>
      s.id === activeSection.id ? { ...s, content: nextContent } : s,
    );
    const nextCited = citedIds.includes(src.id) ? citedIds : [...citedIds, src.id];
    setSections(nextSections);
    setCitedIds(nextCited);
    saveManuscript(nextSections, nextCited);
  }

  async function runWritingAssist(action: WritingActionType) {
    if (!activeSection || activeSection.content.trim().length < 5) return;
    setAssisting(true);
    setError(null);
    try {
      const res = await browserApi<WritingAssistResult>(
        `/projects/${projectId}/writing/assist`,
        {
          method: "POST",
          body: JSON.stringify({ action, text: activeSection.content }),
        },
      );
      setAssistResult(res);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not run writing assistant.");
      }
    } finally {
      setAssisting(false);
    }
  }

  function acceptSuggestion() {
    if (!assistResult || !activeSection) return;
    const nextSections = sections.map((s) =>
      s.id === activeSection.id ? { ...s, content: assistResult.suggestion } : s,
    );
    setSections(nextSections);
    setAssistResult(null);
    saveManuscript(nextSections, citedIds);
  }

  async function downloadDocx() {
    if (!doc) return;
    await saveManuscript();
    try {
      const blob = await browserApi<Blob>(`/projects/${projectId}/writing/${doc.id}/docx`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${doc.title.toLowerCase().replace(/\s+/g, "-")}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Could not export DOCX.");
    }
  }

  async function copyFullManuscript() {
    if (!doc) return;
    const secBlocks = sections
      .map((s) => `## ${s.title}\n\n${s.content.trim() || "(Empty section)"}`)
      .join("\n\n");
    const bibBlock =
      doc.bibliography.length > 0
        ? `\n\n## References\n\n${doc.bibliography.map((r, i) => `${i + 1}. ${r}`).join("\n")}`
        : "";
    await navigator.clipboard.writeText(`# ${doc.title}\n\n${secBlocks}${bibBlock}`);
    setCopiedDoc(true);
    setTimeout(() => setCopiedDoc(false), 2500);
  }

  async function requestChapterGuide(useAi: boolean) {
    if (!activeSection) return;
    setShowGuide(true);
    setLoadingGuide(true);
    setError(null);
    try {
      const guide = await browserApi<ChapterGuide>(
        `/projects/${projectId}/writing/chapter-guide`,
        {
          method: "POST",
          body: JSON.stringify({
            section_title: activeSection.title,
            custom_question: customGuideQuestion.trim() || null,
            use_ai: useAi,
          }),
        },
      );
      setChapterGuide(guide);
    } catch {
      setError("Could not load chapter writing guide.");
    } finally {
      setLoadingGuide(false);
    }
  }

  function insertTextIntoActiveSection(snippet: string, extraCitedIds: string[] = []) {
    if (!activeSection) return;
    const existing = activeSection.content.trimEnd();
    const nextContent = existing ? `${existing}\n\n${snippet.trim()}` : snippet.trim();
    const nextSections = sections.map((s) =>
      s.id === activeSection.id ? { ...s, content: nextContent } : s,
    );
    const nextCited = Array.from(new Set([...citedIds, ...extraCitedIds]));
    setSections(nextSections);
    setCitedIds(nextCited);
    saveManuscript(nextSections, nextCited);
  }

  if (!doc) {
    return <p className="text-sm text-stone-500">{error ?? "Opening Writing Studio…"}</p>;
  }

  const totalWords = sections.reduce(
    (sum, s) => sum + (s.content.trim() ? s.content.trim().split(/\s+/).length : 0),
    0,
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold md:text-3xl">
            Research Writing Studio
          </h1>
          <p className="mt-1 text-sm text-stone-600">
            Draft chapters, insert formatted citations, refine prose responsibly and export to Word
            (.docx).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge>{totalWords.toLocaleString()} words</Badge>
          {savedNotice && <Badge className="bg-emerald-100 text-emerald-800">{savedNotice}</Badge>}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={copyFullManuscript}
          >
            {copiedDoc ? (
              <>
                <Check className="size-4 text-emerald-600" aria-hidden /> Copied!
              </>
            ) : (
              <>
                <Copy className="size-4" aria-hidden /> Copy Manuscript
              </>
            )}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={saving}
            onClick={() => saveManuscript()}
          >
            <Save className="size-4" aria-hidden /> {saving ? "Saving…" : "Save"}
          </Button>
          <Button type="button" size="sm" onClick={downloadDocx}>
            <Download className="size-4" aria-hidden /> Export DOCX
          </Button>
        </div>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Left: Chapter Outline */}
        <Card className="p-4 lg:col-span-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              Outline
            </p>
            <button
              type="button"
              onClick={addSection}
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:underline"
            >
              <Plus className="size-3.5" aria-hidden /> Add section
            </button>
          </div>
          <ul className="mt-3 space-y-1">
            {sections.map((sec) => {
              const active = activeSection?.id === sec.id;
              const secWords = sec.content.trim() ? sec.content.trim().split(/\s+/).length : 0;
              return (
                <li
                  key={sec.id}
                  className={`flex items-center justify-between rounded-lg px-2.5 py-2 text-xs ${
                    active
                      ? "bg-brand-50 font-semibold text-brand-800"
                      : "text-stone-700 hover:bg-stone-100"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => {
                      setAssistResult(null);
                      setActiveSecId(sec.id);
                      if (showGuide) {
                        setChapterGuide(null);
                      }
                    }}
                    className="flex-1 truncate text-left"
                  >
                    {sec.title}
                  </button>
                  <span className="ml-2 text-[11px] text-stone-400">{secWords}w</span>
                  {sections.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeSection(sec.id)}
                      aria-label={`Delete ${sec.title}`}
                      className="ml-1.5 text-stone-400 hover:text-red-600"
                    >
                      <Trash2 className="size-3" aria-hidden />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </Card>

        {/* Centre: Section Editor + Responsible AI Diff + Auto Bibliography */}
        <div className="space-y-5 lg:col-span-6">
          {activeSection && (
            <Card className="space-y-4 p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stone-100 pb-3">
                <Input
                  value={activeSection.title}
                  onChange={(e) => updateActiveTitle(e.target.value)}
                  aria-label="Section title"
                  className="font-display text-lg font-semibold"
                />
                <div className="flex flex-wrap gap-1.5">
                  {WRITING_ACTIONS.map((a) => (
                    <Button
                      key={a.id}
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={assisting || activeSection.content.trim().length < 5}
                      onClick={() => runWritingAssist(a.id)}
                    >
                      <Sparkles className="size-3 text-accent-600" aria-hidden />
                      {a.label}
                    </Button>
                  ))}
                </div>
              </div>

              {/* Optional Beginner & Project-Tailored Chapter Writing Guide Bar */}
              <div className="rounded-xl border border-stone-200 bg-stone-50/80 p-3.5 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <HelpCircle className="size-4 text-brand-600" aria-hidden />
                    <span className="font-medium text-ink">
                      Need guidance on how to write{" "}
                      <span className="font-semibold text-brand-800">{activeSection.title}</span>?
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      disabled={loadingGuide}
                      onClick={() => requestChapterGuide(false)}
                    >
                      <BookOpenCheck className="size-3.5" aria-hidden />
                      Standard Guide (No AI)
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      disabled={loadingGuide}
                      onClick={() => requestChapterGuide(true)}
                    >
                      <Sparkles className="size-3.5" aria-hidden />
                      {loadingGuide ? "Tailoring with AI…" : "Ask AI for Tailored Guide"}
                    </Button>
                    {showGuide && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowGuide(false)}
                      >
                        <ChevronUp className="size-3.5" aria-hidden /> Hide
                      </Button>
                    )}
                    {!showGuide && chapterGuide && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowGuide(true)}
                      >
                        <ChevronDown className="size-3.5" aria-hidden /> Show
                      </Button>
                    )}
                  </div>
                </div>

                {showGuide && (
                  <div className="mt-3 space-y-3 border-t border-stone-200/80 pt-3">
                    <div className="flex flex-col gap-2 sm:flex-row">
                      <Input
                        value={customGuideQuestion}
                        onChange={(e) => setCustomGuideQuestion(e.target.value)}
                        placeholder={`Optional: Ask a specific question about writing ${activeSection.title}…`}
                        className="bg-white text-xs"
                      />
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        disabled={loadingGuide}
                        onClick={() => requestChapterGuide(true)}
                        className="shrink-0"
                      >
                        <Sparkles className="size-3.5 text-brand-600" aria-hidden />
                        Update AI Coaching
                      </Button>
                    </div>

                    {loadingGuide ? (
                      <p className="py-4 text-center text-xs text-stone-500">
                        Preparing tailored guidance for {activeSection.title}…
                      </p>
                    ) : (
                      chapterGuide && (
                        <div className="space-y-3">
                          <div className="rounded-lg border border-brand-200 bg-white p-3">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <span className="font-semibold text-brand-800">
                                Chapter Goal ({chapterGuide.section_title})
                              </span>
                              <Badge className="bg-brand-50 text-brand-800">
                                {chapterGuide.provider === "extractive"
                                  ? "Standard Template Guide"
                                  : `AI Tailored (${chapterGuide.provider})`}
                              </Badge>
                            </div>
                            <p className="mt-1 leading-relaxed text-stone-700">
                              {chapterGuide.chapter_goal}
                            </p>
                          </div>

                          <div className="space-y-2">
                            <p className="font-semibold text-ink">
                              Recommended Sub-Sections &amp; Starter Sentences:
                            </p>
                            {chapterGuide.subsections.map((sub) => (
                              <div
                                key={sub.heading}
                                className="rounded-lg border border-stone-200 bg-white p-3"
                              >
                                <div className="flex flex-wrap items-center justify-between gap-2">
                                  <span className="font-semibold text-ink">{sub.heading}</span>
                                  <Button
                                    type="button"
                                    variant="secondary"
                                    size="sm"
                                    onClick={() =>
                                      insertTextIntoActiveSection(
                                        `### ${sub.heading}\n\n${sub.starter_sentence}`,
                                        chapterGuide.cited_source_ids,
                                      )
                                    }
                                    className="h-6 px-2 text-[11px]"
                                  >
                                    + Insert sub-section
                                  </Button>
                                </div>
                                <p className="mt-1 text-stone-600">{sub.guidance}</p>
                                <p className="mt-1.5 rounded bg-stone-50 p-2 font-reading italic text-stone-700">
                                  “{sub.starter_sentence}”
                                </p>
                              </div>
                            ))}
                          </div>

                          {chapterGuide.common_mistakes.length > 0 && (
                            <div className="rounded-lg border border-accent-300/80 bg-accent-100/50 p-3">
                              <p className="font-semibold text-stone-800">
                                Common Beginner Mistakes to Avoid:
                              </p>
                              <ul className="mt-1 list-inside list-disc space-y-1 text-stone-700">
                                {chapterGuide.common_mistakes.map((m) => (
                                  <li key={m}>{m}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
                            <Button
                              type="button"
                              size="sm"
                              onClick={() =>
                                insertTextIntoActiveSection(
                                  chapterGuide.tailored_draft,
                                  chapterGuide.cited_source_ids,
                                )
                              }
                            >
                              <Plus className="size-3.5" aria-hidden />
                              Insert Full Chapter Scaffold into Editor
                            </Button>
                          </div>
                        </div>
                      )
                    )}
                  </div>
                )}
              </div>

              {assistResult && (
                <div className="rounded-lg border border-brand-200 bg-brand-50/70 p-4 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-brand-800">
                      Móyee Writing Suggestion ({assistResult.action})
                    </span>
                    <div className="flex gap-1.5">
                      <Button type="button" size="sm" onClick={acceptSuggestion}>
                        <Check className="size-3.5" aria-hidden /> Accept
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setAssistResult(null)}
                      >
                        <X className="size-3.5" aria-hidden /> Reject
                      </Button>
                    </div>
                  </div>
                  <p className="mt-2 font-reading text-sm leading-relaxed text-ink">
                    {assistResult.suggestion}
                  </p>
                  <p className="mt-1.5 text-[11px] text-stone-500">{assistResult.note}</p>
                </div>
              )}

              <Textarea
                rows={14}
                value={activeSection.content}
                onChange={(e) => updateActiveContent(e.target.value)}
                onBlur={() => saveManuscript()}
                placeholder={`Write "${activeSection.title}" here. Click any source on the right to insert an inline citation…`}
                className="font-reading text-[15px] leading-relaxed"
              />
            </Card>
          )}

          {/* Auto-generated Bibliography */}
          <Card className="p-5">
            <h2 className="font-semibold text-ink">Auto-Generated Bibliography</h2>
            <p className="mt-0.5 text-xs text-stone-500">
              Automatically included at the end of your exported DOCX manuscript.
            </p>
            {doc.bibliography.length === 0 ? (
              <p className="mt-3 text-xs italic text-stone-400">
                No references in this project yet.
              </p>
            ) : (
              <ol className="mt-3 space-y-2 font-reading text-xs leading-relaxed text-stone-700">
                {doc.bibliography.map((ref) => (
                  <li key={ref} className="rounded bg-stone-50 px-3 py-2">
                    {ref}
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>

        {/* Right: Quick Citation Picker */}
        <Card className="p-4 lg:col-span-3">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-stone-500">
            <Quote className="size-3.5 text-brand-600" aria-hidden /> Insert Citation
          </p>
          {sources.length === 0 ? (
            <p className="mt-3 text-xs text-stone-500">
              Save papers in Discover or upload PDFs in Library to cite them here.
            </p>
          ) : (
            <ul className="mt-3 space-y-2">
              {sources.map((src) => (
                <li
                  key={src.id}
                  className="rounded-lg border border-stone-200 p-2.5 text-xs hover:border-brand-300"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-brand-700">{src.inline_citation}</span>
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => insertCitation(src)}
                      className="h-6 px-2 text-[11px]"
                    >
                      Cite
                    </Button>
                  </div>
                  <p className="mt-1 line-clamp-2 text-stone-600">{src.title}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
