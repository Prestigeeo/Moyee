"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  Check,
  Copy,
  MessageSquarePlus,
  PenTool,
  Send,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Trash2,
} from "lucide-react";
import { Alert, Badge, Button, Card, Select, Textarea } from "@/components/ui";
import {
  ApiError,
  quotaMessage,
  type AssistantMessage,
  type AssistantMode,
  type Conversation,
  type ConversationDetail,
  type DocumentSectionItem,
  type ProjectSource,
  type ResearchDocument,
} from "@/lib/api";
import { browserApi } from "@/lib/api/browser";

const MODES: { id: AssistantMode; label: string; hint: string }[] = [
  {
    id: "qa",
    label: "Research Q&A",
    hint: "Ask specific questions answered with page citations from your sources.",
  },
  {
    id: "topic",
    label: "Topic & Questions",
    hint: "Refine research topics, objectives, variables and scope grounded in your library.",
  },
  {
    id: "methodology",
    label: "Methodology Advisor",
    hint: "Compare qualitative, quantitative and mixed designs used in your sources.",
  },
  {
    id: "explain",
    label: "Explain Concept",
    hint: "Understand complex terminology, statistical findings or theoretical frameworks.",
  },
];

export default function AssistantPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConv, setActiveConv] = useState<ConversationDetail | null>(null);
  const [sources, setSources] = useState<ProjectSource[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>("all");
  const [mode, setMode] = useState<AssistantMode>("qa");
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [docSections, setDocSections] = useState<DocumentSectionItem[]>([]);
  const [targetSectionByMsg, setTargetSectionByMsg] = useState<Record<string, string>>({});
  const [copiedMsgId, setCopiedMsgId] = useState<string | null>(null);
  const [addingMsgId, setAddingMsgId] = useState<string | null>(null);
  const [addedNoticeByMsg, setAddedNoticeByMsg] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);

  const openConversation = useCallback(
    async (convId: string) => {
      try {
        const detail = await browserApi<ConversationDetail>(
          `/projects/${projectId}/conversations/${convId}`,
        );
        setActiveConv(detail);
        setMode(detail.mode);
      } catch {
        setError("Could not load conversation.");
      }
    },
    [projectId],
  );

  useEffect(() => {
    Promise.all([
      browserApi<Conversation[]>(`/projects/${projectId}/conversations`),
      browserApi<ProjectSource[]>(`/projects/${projectId}/sources`),
      browserApi<ResearchDocument>(`/projects/${projectId}/writing`).catch(() => null),
    ])
      .then(([convs, srcs, writingDoc]) => {
        setConversations(convs);
        setSources(srcs);
        if (writingDoc?.sections) {
          setDocSections(writingDoc.sections);
        }
        if (convs.length > 0) {
          openConversation(convs[0].id);
        }
      })
      .catch(() => setError("Could not load assistant workspace."));
  }, [projectId, openConversation]);

  async function createNewConversation() {
    setError(null);
    try {
      const created = await browserApi<Conversation>(`/projects/${projectId}/conversations`, {
        method: "POST",
        body: JSON.stringify({ title: "New Research Conversation", mode }),
      });
      setConversations((prev) => [created, ...prev]);
      setActiveConv({ ...created, messages: [] });
      return created.id;
    } catch {
      setError("Could not create conversation.");
      return null;
    }
  }

  async function removeConversation(convId: string) {
    try {
      await browserApi(`/projects/${projectId}/conversations/${convId}`, {
        method: "DELETE",
      });
      const remaining = conversations.filter((c) => c.id !== convId);
      setConversations(remaining);
      if (activeConv?.id === convId) {
        if (remaining.length > 0) openConversation(remaining[0].id);
        else setActiveConv(null);
      }
    } catch {
      setError("Could not delete conversation.");
    }
  }

  async function onSend(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (question.trim().length < 2 || sending) return;
    setSending(true);
    setError(null);

    try {
      let convId = activeConv?.id ?? null;
      if (!convId) {
        convId = await createNewConversation();
      }
      if (!convId) return;

      const qText = question.trim();
      setQuestion("");
      await browserApi(`/projects/${projectId}/conversations/${convId}/messages`, {
        method: "POST",
        body: JSON.stringify({
          question: qText,
          mode,
          source_ids: selectedSourceId === "all" ? null : [selectedSourceId],
        }),
      });
      await openConversation(convId);
      const updatedList = await browserApi<Conversation[]>(
        `/projects/${projectId}/conversations`,
      );
      setConversations(updatedList);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.isQuota ? quotaMessage(err) : err.message);
      } else {
        setError("Could not send message.");
      }
    } finally {
      setSending(false);
    }
  }

  async function sendFeedback(messageId: string, value: 1 | -1) {
    try {
      await browserApi(`/projects/${projectId}/conversations/messages/${messageId}/feedback`, {
        method: "POST",
        body: JSON.stringify({ feedback: value }),
      });
      if (activeConv) openConversation(activeConv.id);
    } catch {
      // ignore feedback errors
    }
  }

  function formatMessageWithInlineCitations(msg: AssistantMessage): string {
    let text = msg.content;
    for (const c of msg.citations) {
      const pagePart = c.page_number ? `, p. ${c.page_number}` : "";
      const inline = c.inline_label.endsWith(")")
        ? `${c.inline_label.slice(0, -1)}${pagePart})`
        : `${c.inline_label}${pagePart}`;
      text = text.replaceAll(`[${c.citation_number}]`, inline);
    }
    return text;
  }

  async function copyAssistantResponse(msg: AssistantMessage) {
    const formattedAnswer = formatMessageWithInlineCitations(msg);
    const refsBlock =
      msg.citations.length > 0
        ? "\n\nSources:\n" +
          msg.citations
            .map(
              (c) =>
                `[${c.citation_number}] ${c.inline_label} ${c.source_title} (${
                  c.page_number ? `p. ${c.page_number}` : "abstract"
                })`,
            )
            .join("\n")
        : "";
    const interpBlock = msg.interpretation
      ? `\n\nInterpretation & Guidance:\n${msg.interpretation}`
      : "";
    await navigator.clipboard.writeText(`${formattedAnswer}${refsBlock}${interpBlock}`);
    setCopiedMsgId(msg.id);
    setTimeout(() => setCopiedMsgId((prev) => (prev === msg.id ? null : prev)), 2500);
  }

  async function addResponseToWritingStudio(msg: AssistantMessage) {
    setAddingMsgId(msg.id);
    setError(null);
    try {
      const defaultSec =
        docSections.find((s) => /literature|related work/i.test(s.title))?.id ??
        docSections[0]?.id ??
        null;
      const chosenSecId = targetSectionByMsg[msg.id] ?? defaultSec;
      const formattedBody = formatMessageWithInlineCitations(msg);
      const updatedDoc = await browserApi<ResearchDocument>(
        `/projects/${projectId}/writing/append`,
        {
          method: "POST",
          body: JSON.stringify({
            section_id: chosenSecId,
            content: formattedBody,
            cited_source_ids: msg.citations.map((c) => c.project_source_id),
          }),
        },
      );
      setDocSections(updatedDoc.sections);
      const secTitle =
        updatedDoc.sections.find((s) => s.id === chosenSecId)?.title ?? "Writing Studio";
      setAddedNoticeByMsg((prev) => ({ ...prev, [msg.id]: secTitle }));
    } catch {
      setError("Could not add response to Writing Studio.");
    } finally {
      setAddingMsgId(null);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-2xl font-semibold md:text-3xl">
            Móyee Research Assistant
          </h1>
          <p className="mt-1 text-sm text-stone-600">
            Research assistance with source references. Click any citation to inspect
            the source passage in the Reader.
          </p>
        </div>
        <Button type="button" variant="secondary" size="sm" onClick={createNewConversation}>
          <MessageSquarePlus className="size-4" aria-hidden /> New conversation
        </Button>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      <div className="grid gap-6 lg:grid-cols-12">
        {/* Conversation list */}
        <Card className="p-3 lg:col-span-3">
          <p className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wider text-stone-500">
            Conversations
          </p>
          {conversations.length === 0 ? (
            <p className="px-2 py-4 text-xs text-stone-500">
              Ask a question on the right to start your first project conversation.
            </p>
          ) : (
            <ul className="mt-1 space-y-1">
              {conversations.map((c) => {
                const active = activeConv?.id === c.id;
                return (
                  <li
                    key={c.id}
                    className={`flex items-center justify-between rounded-lg px-2.5 py-2 text-xs ${
                      active ? "bg-brand-50 font-medium text-brand-800" : "text-stone-700 hover:bg-stone-100"
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => openConversation(c.id)}
                      className="flex-1 truncate text-left"
                    >
                      {c.title}
                    </button>
                    <button
                      type="button"
                      onClick={() => removeConversation(c.id)}
                      aria-label="Delete conversation"
                      className="ml-2 rounded p-1 text-stone-400 hover:text-red-600"
                    >
                      <Trash2 className="size-3" aria-hidden />
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        {/* Chat thread + composer */}
        <div className="flex flex-col gap-4 lg:col-span-9">
          <Card className="min-h-[420px] flex-1 space-y-6 p-6">
            {!activeConv || activeConv.messages.length === 0 ? (
              <div className="py-12 text-center">
                <Sparkles className="mx-auto size-8 text-brand-600" aria-hidden />
                <h2 className="mt-3 font-display text-lg font-semibold">
                  Ask a research question grounded in your project
                </h2>
                <p className="mx-auto mt-1 max-w-md text-xs text-stone-500">
                  {MODES.find((m) => m.id === mode)?.hint}
                </p>
              </div>
            ) : (
              activeConv.messages.map((msg) =>
                msg.role === "user" ? (
                  <div key={msg.id} className="flex justify-end">
                    <div className="max-w-2xl rounded-2xl bg-brand-600 px-4 py-2.5 text-sm text-white">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div key={msg.id} className="space-y-3 rounded-xl border border-stone-200 bg-stone-50/40 p-5">
                    {msg.provider === "extractive" ? (
                      <Alert>
                        Limited mode — AI generation was unavailable. This response uses source
                        excerpts or starter templates, not AI synthesis.
                      </Alert>
                    ) : msg.provider && msg.provider !== "moyee" ? (
                      <p className="text-xs text-stone-500">
                        Generated with {msg.provider}{msg.model ? ` · ${msg.model}` : ""}
                      </p>
                    ) : null}
                    {msg.insufficient_evidence && (
                      <div className="flex items-center gap-2 rounded-lg border border-accent-300 bg-accent-100 px-3 py-2 text-xs font-medium text-stone-800">
                        <AlertTriangle className="size-4 text-accent-600" aria-hidden />
                        Insufficient evidence in your current project sources.
                      </div>
                    )}

                    {/* 1. Direct grounded answer */}
                    <p className="whitespace-pre-wrap font-reading text-[15px] leading-relaxed text-ink">
                      {msg.content}
                    </p>

                    {/* 2. Verified Source Citations ("From your sources") */}
                    {msg.citations.length > 0 && (
                      <div className="rounded-lg border border-brand-200 bg-brand-50/80 p-3.5 text-xs">
                        <p className="flex items-center gap-1.5 font-semibold text-brand-800">
                          <ShieldCheck className="size-4" aria-hidden /> Source references
                        </p>
                        <p className="mt-1 text-stone-600">
                          References link to retrieved passages. Check whether each passage supports
                          the associated claim.
                        </p>
                        <ul className="mt-2 space-y-2">
                          {msg.citations.map((c) => (
                            <li key={c.citation_number} className="flex flex-wrap items-start justify-between gap-2 border-t border-brand-100 pt-2">
                              <div className="max-w-2xl">
                                <span className="font-semibold text-brand-800">
                                  [{c.citation_number}] {c.source_title}{" "}
                                </span>
                                <span className="text-stone-600">
                                  ({c.page_number ? `p. ${c.page_number}` : "abstract"}) — “{c.quote}”
                                </span>
                              </div>
                              <Link
                                href={`/app/p/${projectId}/library/${c.project_source_id}?page=${c.page_number ?? 1}&q=${encodeURIComponent(c.quote.slice(0, 60))}`}
                                aria-label={`Source ${c.citation_number}: ${c.source_title}, page ${c.page_number ?? 1}`}
                                className="shrink-0 rounded bg-accent-100 px-2 py-0.5 font-semibold text-accent-600 hover:bg-accent-300/60"
                              >
                                Open p. {c.page_number ?? 1} →
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 3. Móyee's Interpretation */}
                    {msg.interpretation && (
                      <div className="rounded-lg border border-stone-200 bg-white p-3.5 text-xs text-stone-700">
                        <Badge className="mb-1.5 bg-stone-100 text-stone-700">
                          Móyee’s interpretation &amp; guidance
                        </Badge>
                        <p className="leading-relaxed">{msg.interpretation}</p>
                      </div>
                    )}

                    {/* 4. Copy, Add to Writing Studio & Feedback Actions */}
                    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-stone-200/80 pt-3 text-xs text-stone-500">
                      <div className="flex flex-wrap items-center gap-2">
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => copyAssistantResponse(msg)}
                        >
                          {copiedMsgId === msg.id ? (
                            <>
                              <Check className="size-3.5 text-emerald-600" aria-hidden /> Copied
                            </>
                          ) : (
                            <>
                              <Copy className="size-3.5" aria-hidden /> Copy response
                            </>
                          )}
                        </Button>

                        {docSections.length > 0 && (
                          <Select
                            aria-label="Target section in Writing Studio"
                            value={
                              targetSectionByMsg[msg.id] ??
                              docSections.find((s) => /literature|related work/i.test(s.title))
                                ?.id ??
                              docSections[0]?.id ??
                              ""
                            }
                            onChange={(e) =>
                              setTargetSectionByMsg((prev) => ({
                                ...prev,
                                [msg.id]: e.target.value,
                              }))
                            }
                            className="h-8 py-1 text-xs"
                          >
                            {docSections.map((sec) => (
                              <option key={sec.id} value={sec.id}>
                                Section: {sec.title}
                              </option>
                            ))}
                          </Select>
                        )}

                        <Button
                          type="button"
                          size="sm"
                          disabled={addingMsgId === msg.id}
                          onClick={() => addResponseToWritingStudio(msg)}
                        >
                          <PenTool className="size-3.5" aria-hidden />
                          {addingMsgId === msg.id ? "Adding…" : "Add to Writing Studio"}
                        </Button>

                        {addedNoticeByMsg[msg.id] && (
                          <Link
                            href={`/app/p/${projectId}/write`}
                            className="inline-flex items-center gap-1 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 hover:bg-emerald-100"
                          >
                            ✓ Added to {addedNoticeByMsg[msg.id]} · Open Writing Studio →
                          </Link>
                        )}
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="hidden sm:inline">{msg.limitations}</span>
                        <button
                          type="button"
                          onClick={() => sendFeedback(msg.id, 1)}
                          aria-label="Helpful answer"
                          className={`rounded p-1 ${
                            msg.feedback === 1 ? "text-emerald-600" : "hover:text-ink"
                          }`}
                        >
                          <ThumbsUp className="size-3.5" aria-hidden />
                        </button>
                        <button
                          type="button"
                          onClick={() => sendFeedback(msg.id, -1)}
                          aria-label="Unhelpful answer"
                          className={`rounded p-1 ${
                            msg.feedback === -1 ? "text-red-600" : "hover:text-ink"
                          }`}
                        >
                          <ThumbsDown className="size-3.5" aria-hidden />
                        </button>
                      </div>
                    </div>
                  </div>
                ),
              )
            )}
          </Card>

          {/* Composer */}
          <Card className="p-4">
            <form onSubmit={onSend} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <Select
                  value={mode}
                  onChange={(e) => setMode(e.target.value as AssistantMode)}
                  aria-label="Assistant mode"
                >
                  {MODES.map((m) => (
                    <option key={m.id} value={m.id}>
                      Mode: {m.label}
                    </option>
                  ))}
                </Select>
                <Select
                  value={selectedSourceId}
                  onChange={(e) => setSelectedSourceId(e.target.value)}
                  aria-label="Evidence scope"
                >
                  <option value="all">Scope: Whole project ({sources.length} sources)</option>
                  {sources.map((s) => (
                    <option key={s.id} value={s.id}>
                      Source: {s.title.slice(0, 60)}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="flex gap-2">
                <Textarea
                  rows={2}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Ask a research question, compare studies, or refine your methodology…"
                  required
                />
                <Button type="submit" disabled={sending} className="h-auto shrink-0">
                  <Send className="size-4" aria-hidden />
                  {sending ? "Thinking…" : "Ask"}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
