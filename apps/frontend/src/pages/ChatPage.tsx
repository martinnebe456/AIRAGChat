import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiClient } from "../api/client";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { useChatRouteShell } from "../components/ChatRouteShell";
import { ProviderBadge } from "../components/Ui";
import { useUiStore } from "../store/uiStore";

type ChatSession = {
  id: string;
  title: string;
  project_id?: string | null;
  last_message_at?: string | null;
};

type ProjectRow = {
  id: string;
  name: string;
  my_role?: string | null;
};

type ChatCitation = {
  filename?: string;
  chunk_id?: string;
  snippet?: string;
  score?: number;
};

type ChatMessage = {
  id: string;
  role: string;
  content: string;
  citations_json?: ChatCitation[];
  provider?: string | null;
  model_category?: string | null;
};

type ChatAskResponse = {
  answer: string;
  citations: Array<{ filename: string; chunk_id: string; snippet: string; score?: number }>;
  provider: string;
  resolved_model_id: string;
  answer_mode: string;
  latency_ms: number;
  session_id: string;
  message_id: string;
  project_id?: string | null;
};

function SourcesDisclosure({
  citations,
  open,
  onToggle,
}: {
  citations: ChatCitation[];
  open: boolean;
  onToggle: () => void;
}) {
  const sourceCount = citations.length;
  const docCount = new Set(citations.map((c) => c.filename || "unknown")).size;

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={onToggle}
        className="inline-flex items-center gap-2 rounded-full border border-ink/10 bg-white/70 px-3 py-1 text-xs font-medium text-ink transition hover:bg-white/90"
      >
        <span>Sources ({sourceCount})</span>
        <span className="text-ink/55">{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <div className="mt-2 max-h-60 overflow-y-auto overscroll-contain rounded-xl border border-ink/10 bg-white/75 p-2">
          <div className="mb-2 px-1 text-[11px] uppercase tracking-[0.12em] text-ink/55">
            {sourceCount} citation{sourceCount === 1 ? "" : "s"} from {docCount} document{docCount === 1 ? "" : "s"}
          </div>
          <div className="space-y-2">
            {citations.map((c, idx) => (
              <div key={`${c.chunk_id ?? "chunk"}-${idx}`} className="rounded-lg border border-ink/8 bg-white/85 p-2">
                <div className="text-xs font-medium text-ink">
                  {c.filename ?? "Unknown document"}{" "}
                  {c.chunk_id ? <span className="text-ink/45">({c.chunk_id})</span> : null}
                </div>
                {c.snippet ? <div className="mt-1 text-xs leading-relaxed text-ink/70">{c.snippet}</div> : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}

function computeDistanceFromBottom(element: HTMLDivElement) {
  return element.scrollHeight - element.scrollTop - element.clientHeight;
}

function bucketSessionDate(lastMessageAt?: string | null) {
  if (!lastMessageAt) return "Older";
  const d = new Date(lastMessageAt);
  if (Number.isNaN(d.getTime())) return "Older";
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startSevenDays = new Date(startToday);
  startSevenDays.setDate(startSevenDays.getDate() - 7);
  if (d >= startToday) return "Today";
  if (d >= startSevenDays) return "Previous 7 Days";
  return "Older";
}

function formatSessionTime(value?: string | null) {
  if (!value) return "No messages yet";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "No messages yet";
  return d.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ChatPage() {
  const qc = useQueryClient();
  const addToast = useUiStore((s) => s.addToast);
  const { openNavDrawer } = useChatRouteShell();

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [draftProjectId, setDraftProjectId] = useState<string | null>(null);
  const [isDraftMode, setIsDraftMode] = useState<boolean>(false);
  const [question, setQuestion] = useState("");
  const [chatToDelete, setChatToDelete] = useState<ChatSession | null>(null);
  const [sourcesOpenByMessageId, setSourcesOpenByMessageId] = useState<Record<string, boolean>>({});
  const [isAtBottom, setIsAtBottom] = useState(true);

  const messageListRef = useRef<HTMLDivElement | null>(null);
  const bottomSentinelRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const lastSessionRef = useRef<string | null>(null);
  const lastMessagesCountRef = useRef(0);
  const shouldAutoscrollRef = useRef(true);

  const projectsQuery = useQuery({
    queryKey: ["projects"],
    queryFn: async () => apiClient.get<{ items: ProjectRow[] }>("/projects"),
  });

  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions"],
    queryFn: async () => apiClient.get<{ items: ChatSession[] }>("/chat/sessions"),
  });

  useEffect(() => {
    if (!draftProjectId && projectsQuery.data?.items?.length) {
      setDraftProjectId(projectsQuery.data.items[0].id);
    }
  }, [draftProjectId, projectsQuery.data]);

  useEffect(() => {
    if (isDraftMode) return;
    if (!selectedSessionId && sessionsQuery.data?.items?.length) {
      const firstSession = sessionsQuery.data.items[0];
      setSelectedSessionId(firstSession.id);
      if (firstSession.project_id) {
        setDraftProjectId(firstSession.project_id);
      }
    }
  }, [isDraftMode, selectedSessionId, sessionsQuery.data]);

  const messagesQuery = useQuery({
    queryKey: ["chat-messages", selectedSessionId],
    queryFn: async () =>
      selectedSessionId
        ? apiClient.get<{ items: ChatMessage[] }>(`/chat/sessions/${selectedSessionId}/messages`)
        : { items: [] as ChatMessage[] },
    enabled: !!selectedSessionId,
  });

  const deleteSessionMutation = useMutation({
    mutationFn: async (session: ChatSession) =>
      apiClient.delete<{ message: string }>(`/chat/sessions/${session.id}`),
    onSuccess: async (_response, deletedSession) => {
      setChatToDelete(null);
      const currentItems = sessionsQuery.data?.items ?? [];
      const remaining = currentItems.filter((s) => s.id !== deletedSession.id);
      if (selectedSessionId === deletedSession.id) {
        const nextSession = remaining[0] ?? null;
        if (nextSession) {
          setSelectedSessionId(nextSession.id);
          setIsDraftMode(false);
          if (nextSession.project_id) {
            setDraftProjectId(nextSession.project_id);
          }
        } else {
          setSelectedSessionId(null);
          setIsDraftMode(true);
          if (deletedSession.project_id) {
            setDraftProjectId(deletedSession.project_id);
          }
        }
      }
      addToast({ title: "Chat archived", message: "Chat session was archived.", kind: "success" });
      await qc.invalidateQueries({ queryKey: ["chat-sessions"] });
      await qc.invalidateQueries({ queryKey: ["chat-messages", deletedSession.id] });
    },
    onError: (error) => {
      addToast({ title: "Delete failed", message: (error as Error).message, kind: "error" });
    },
  });

  const askMutation = useMutation({
    mutationFn: async () => {
      if (!selectedSessionId && !draftProjectId) {
        throw new Error("Select a project before starting chat.");
      }
      return apiClient.post<ChatAskResponse>("/chat/ask", {
        question,
        session_id: selectedSessionId,
        project_id: selectedSessionId ? undefined : draftProjectId,
      });
    },
    onSuccess: async (data) => {
      setQuestion("");
      setSelectedSessionId(data.session_id);
      setIsDraftMode(false);
      if (data.project_id) {
        setDraftProjectId(data.project_id);
      }
      await qc.invalidateQueries({ queryKey: ["chat-sessions"] });
      await qc.invalidateQueries({ queryKey: ["chat-messages", data.session_id] });
    },
    onError: (error) => {
      addToast({ title: "Chat request failed", message: (error as Error).message, kind: "error" });
    },
  });

  const messages = useMemo(() => messagesQuery.data?.items ?? [], [messagesQuery.data]);
  const projectNameById = useMemo(
    () => new Map((projectsQuery.data?.items ?? []).map((p) => [p.id, p.name])),
    [projectsQuery.data],
  );
  const selectedSession = useMemo(
    () => (sessionsQuery.data?.items ?? []).find((s) => s.id === selectedSessionId) ?? null,
    [sessionsQuery.data, selectedSessionId],
  );
  const groupedSessions = useMemo(() => {
    const buckets = new Map<string, ChatSession[]>();
    for (const session of sessionsQuery.data?.items ?? []) {
      const label = bucketSessionDate(session.last_message_at);
      const list = buckets.get(label) ?? [];
      list.push(session);
      buckets.set(label, list);
    }
    return ["Today", "Previous 7 Days", "Older"]
      .map((label) => ({ label, items: buckets.get(label) ?? [] }))
      .filter((group) => group.items.length > 0);
  }, [sessionsQuery.data]);
  const isDraftChat = isDraftMode || !selectedSessionId;
  const activeProjectId = selectedSession?.project_id ?? draftProjectId;
  const projectSelectorLocked = !isDraftChat && !!selectedSession;
  const showJumpToLatest = messages.length > 0 && !isAtBottom;

  const submitQuestion = () => {
    if (!question.trim()) return;
    if (askMutation.isPending) return;
    if (isDraftChat && !draftProjectId) return;
    shouldAutoscrollRef.current = isAtBottom || messages.length === 0;
    askMutation.mutate();
  };

  const scrollToBottom = (behavior: ScrollBehavior = "auto") => {
    if (bottomSentinelRef.current) {
      bottomSentinelRef.current.scrollIntoView({ block: "end", behavior });
    } else if (messageListRef.current) {
      messageListRef.current.scrollTo({ top: messageListRef.current.scrollHeight, behavior });
    }
    setIsAtBottom(true);
  };

  useEffect(() => {
    if (!sessionsQuery.data) return;
    if (selectedSessionId && !sessionsQuery.data.items.some((s) => s.id === selectedSessionId)) {
      const firstSession = sessionsQuery.data.items[0] ?? null;
      if (firstSession) {
        setSelectedSessionId(firstSession.id);
        setIsDraftMode(false);
        if (firstSession.project_id) setDraftProjectId(firstSession.project_id);
      } else {
        setSelectedSessionId(null);
        setIsDraftMode(true);
      }
    }
  }, [selectedSessionId, sessionsQuery.data]);

  useEffect(() => {
    const minHeight = 96;
    const maxHeight = 192;
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    const nextHeight = Math.max(minHeight, Math.min(maxHeight, textarea.scrollHeight));
    textarea.style.height = `${nextHeight}px`;
    textarea.style.overflowY = textarea.scrollHeight > maxHeight ? "auto" : "hidden";
  }, [question]);

  useEffect(() => {
    if (lastSessionRef.current === selectedSessionId) return;
    lastSessionRef.current = selectedSessionId;
    lastMessagesCountRef.current = 0;
    shouldAutoscrollRef.current = true;
    setIsAtBottom(true);
    setSourcesOpenByMessageId({});
    requestAnimationFrame(() => scrollToBottom("auto"));
  }, [selectedSessionId]);

  useEffect(() => {
    const currentCount = messages.length;
    const previousCount = lastMessagesCountRef.current;
    if (currentCount === previousCount) return;
    lastMessagesCountRef.current = currentCount;

    if (!messagesQuery.isSuccess) return;
    if (!(shouldAutoscrollRef.current || isAtBottom)) return;

    requestAnimationFrame(() => {
      scrollToBottom(previousCount > 0 ? "smooth" : "auto");
      shouldAutoscrollRef.current = false;
    });
  }, [isAtBottom, messages.length, messagesQuery.isSuccess]);

  useEffect(() => {
    const container = messageListRef.current;
    if (!container) return;
    setIsAtBottom(computeDistanceFromBottom(container) <= 56);
  }, [messages.length, selectedSessionId]);

  return (
    <>
      <div className="grid h-full min-h-0 grid-rows-[minmax(180px,26dvh)_minmax(0,1fr)] gap-3 lg:grid-cols-[300px_minmax(0,1fr)] lg:grid-rows-1">
        <section className="rail-dark flex min-h-0 flex-col overflow-hidden rounded-[1.35rem] border border-white/8 p-3 md:p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-[11px] uppercase tracking-[0.16em] text-white/52">Chat History</div>
              <h1 className="truncate text-base font-semibold text-white">Project Sessions</h1>
            </div>
            <button
              type="button"
              onClick={() => {
                setSelectedSessionId(null);
                setIsDraftMode(true);
              }}
              className="rounded-full border border-white/14 bg-white/12 px-3 py-1.5 text-xs font-semibold text-white hover:bg-white/18"
            >
              New Chat
            </button>
          </div>

          <div className="separator-soft mb-3 opacity-60" />

          <div className="min-h-0 space-y-3 overflow-y-auto overscroll-contain pr-1">
            {groupedSessions.length === 0 ? (
              <div className="rail-card rounded-xl p-4 text-sm text-white/70">
                No chat sessions yet. Start a new project-scoped chat.
              </div>
            ) : (
              groupedSessions.map((group) => (
                <div key={group.label}>
                  <div className="mb-2 px-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-white/45">
                    {group.label}
                  </div>
                  <div className="space-y-2">
                    {group.items.map((session) => {
                      const isActive = selectedSessionId === session.id && !isDraftChat;
                      return (
                        <div key={session.id} className="group flex items-stretch gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedSessionId(session.id);
                              setIsDraftMode(false);
                              if (session.project_id) setDraftProjectId(session.project_id);
                            }}
                            className={`rail-card min-w-0 flex-1 rounded-xl border px-3 py-2.5 text-left transition ${
                              isActive
                                ? "border-white/20 bg-white/16 shadow-[0_0_0_1px_rgba(87,143,202,0.25),0_10px_26px_rgba(54,116,181,0.22)]"
                                : "border-white/8 bg-white/6 hover:bg-white/10"
                            }`}
                          >
                            <div className="truncate text-sm font-medium text-white">
                              {session.title || "New Chat"}
                            </div>
                            <div className="mt-1 flex items-center gap-2">
                              {session.project_id ? (
                                <span className="truncate rounded-full border border-white/10 bg-white/7 px-2 py-0.5 text-[11px] text-white/70">
                                  {projectNameById.get(session.project_id) ?? `Project ${session.project_id.slice(0, 8)}`}
                                </span>
                              ) : null}
                              <span className="truncate text-[11px] text-white/45">
                                {formatSessionTime(session.last_message_at)}
                              </span>
                            </div>
                          </button>
                          <button
                            type="button"
                            disabled={askMutation.isPending || deleteSessionMutation.isPending}
                            onClick={(e) => {
                              e.stopPropagation();
                              setChatToDelete(session);
                            }}
                            className={`rounded-xl border border-white/12 bg-white/8 px-2 py-2 text-[11px] font-medium text-white/90 transition ${
                              isActive
                                ? "opacity-100"
                                : "pointer-events-none opacity-0 group-hover:pointer-events-auto group-hover:opacity-100 group-focus-within:pointer-events-auto group-focus-within:opacity-100"
                            } disabled:pointer-events-none disabled:opacity-50`}
                            title="Archive chat session"
                          >
                            Delete
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="chat-surface grid h-full min-h-0 grid-rows-[auto_minmax(0,1fr)_auto] gap-3 overflow-hidden rounded-[1.35rem] border border-white/55 p-3 md:p-4">
          <div className="chat-toolbar rounded-2xl border border-ink/8 px-3 py-2.5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2">
                <button
                  type="button"
                  onClick={openNavDrawer}
                  className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-ink/10 bg-white/75 text-ink transition hover:bg-white"
                  aria-label="Open navigation"
                >
                  <span className="block h-[2px] w-4 rounded bg-current shadow-[0_-5px_0_0_currentColor,0_5px_0_0_currentColor]" />
                </button>
                <div className="min-w-0">
                  <div className="truncate text-base font-semibold text-ink">RAG Chat</div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs">
                    <span className="rounded-full border border-ink/8 bg-white/75 px-2 py-1 text-ink">
                      {activeProjectId
                        ? projectNameById.get(activeProjectId) ?? `Project ${activeProjectId.slice(0, 8)}`
                        : "Select project"}
                    </span>
                    <span className="rounded-full border border-ink/8 bg-white/60 px-2 py-1 text-ink/75">
                      {isDraftChat ? "Draft" : "Pinned"}
                    </span>
                    {!isDraftChat ? (
                      <span className="text-ink/55">Use New Chat to switch project.</span>
                    ) : null}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <label className="text-xs text-ink/55">Project</label>
                <select
                  value={activeProjectId ?? ""}
                  onChange={(e) => setDraftProjectId(e.target.value || null)}
                  disabled={projectSelectorLocked}
                  className="rounded-xl border border-ink/12 bg-white/85 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:bg-white/60 disabled:text-ink/60"
                >
                  <option value="">Select project</option>
                  {(projectsQuery.data?.items ?? []).map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="relative min-h-0">
            <div
              ref={messageListRef}
              onScroll={() => {
                const element = messageListRef.current;
                if (!element) return;
                setIsAtBottom(computeDistanceFromBottom(element) <= 56);
              }}
              className="h-full min-h-0 overflow-y-auto overscroll-contain rounded-2xl border border-ink/8 bg-white/42 p-3 md:p-4"
            >
              <div className="flex min-h-full flex-col justify-end gap-3">
                {messages.length === 0 ? (
                  <div className="flex h-full min-h-[220px] items-center justify-center">
                    <div className="w-full max-w-xl rounded-2xl border border-dashed border-ink/10 bg-white/35 px-5 py-6 text-center">
                      <div className="text-sm font-semibold text-ink">
                        {isDraftChat ? "Start a new project chat" : "No messages yet"}
                      </div>
                      <div className="mt-2 text-sm leading-relaxed text-ink/65">
                        {isDraftChat
                          ? "Step 1: choose a project. Step 2: ask your first question. The session will be created automatically."
                          : "Ask a question and the assistant will answer using indexed documents from this project only."}
                      </div>
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => {
                    const isUser = msg.role === "user";
                    const isAssistant = msg.role === "assistant";
                    const citations = msg.citations_json ?? [];
                    const sourcesOpen = !!sourcesOpenByMessageId[msg.id];
                    return (
                      <div key={msg.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                        <article
                          className={`w-full max-w-[92%] rounded-2xl border p-3 md:max-w-[84%] ${
                            isUser
                              ? "chat-bubble-user border-ink/8 bg-white/88"
                              : "chat-bubble-assistant border-ink/8 bg-white/66"
                          }`}
                        >
                          <div className="mb-2 flex items-center justify-between gap-2">
                            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-ink/55">
                              {isUser ? "You" : "Assistant"}
                            </div>
                            {isAssistant && msg.provider ? (
                              <ProviderBadge provider={msg.provider} category={msg.model_category} />
                            ) : null}
                          </div>

                          <div className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{msg.content}</div>

                          {isAssistant && citations.length > 0 ? (
                            <SourcesDisclosure
                              citations={citations}
                              open={sourcesOpen}
                              onToggle={() =>
                                setSourcesOpenByMessageId((prev) => ({
                                  ...prev,
                                  [msg.id]: !prev[msg.id],
                                }))
                              }
                            />
                          ) : null}
                        </article>
                      </div>
                    );
                  })
                )}
                <div ref={bottomSentinelRef} />
              </div>
            </div>

            {showJumpToLatest ? (
              <button
                type="button"
                onClick={() => scrollToBottom("smooth")}
                className="absolute bottom-4 right-4 rounded-full border border-[#3674B5]/20 bg-white/90 px-3 py-1.5 text-xs font-medium text-ink shadow-soft hover:bg-white"
              >
                Jump to latest
              </button>
            ) : null}
          </div>

          <form
            className="shrink-0 rounded-2xl border border-ink/8 bg-white/60 p-3"
            onSubmit={(e) => {
              e.preventDefault();
              submitQuestion();
            }}
            style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
          >
            <textarea
              ref={textareaRef}
              rows={3}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key !== "Enter" || e.shiftKey) return;
                if (e.nativeEvent.isComposing) return;
                e.preventDefault();
                submitQuestion();
              }}
              className="block min-h-[96px] max-h-48 w-full resize-none overflow-y-hidden overscroll-contain rounded-xl border border-ink/10 bg-white/88 px-3 py-2.5 text-sm outline-none focus:border-ink/25"
              placeholder={isDraftChat ? "Choose a project and ask your first question..." : "Ask a question over project documents..."}
            />
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
              <div className="text-xs text-ink/55">
                OpenAI-only mode · Retrieval is filtered to the active chat project.
              </div>
              <button
                type="submit"
                disabled={askMutation.isPending || (isDraftChat && !draftProjectId)}
                className="rounded-xl bg-ember px-4 py-2 text-sm font-semibold text-white shadow-[0_10px_20px_rgba(250,218,122,0.22)] disabled:opacity-60"
              >
                {askMutation.isPending ? "Submitting..." : "Ask"}
              </button>
            </div>
          </form>
        </section>
      </div>

      <ConfirmDialog
        open={!!chatToDelete}
        onOpenChange={(open) => {
          if (!open) setChatToDelete(null);
        }}
        title="Archive chat session"
        description={
          chatToDelete
            ? `Archive chat "${chatToDelete.title || "New Chat"}"? The session will be hidden from the list.`
            : undefined
        }
        confirmLabel="Archive"
        tone="warning"
        isPending={deleteSessionMutation.isPending}
        onConfirm={() => {
          if (!chatToDelete) return;
          deleteSessionMutation.mutate(chatToDelete);
        }}
      />
    </>
  );
}
