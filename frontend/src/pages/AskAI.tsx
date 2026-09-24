import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check, ChevronDown, History, MessageSquare, Plus, RotateCw, Send, Sparkles, Trash2, X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, isDemo } from "../services/api";
import { Spark } from "../components/ui";
import { BalancePanel, BalanceStrip } from "../components/Accounts";
import { useBalances } from "../hooks/useBalances";
import { cn } from "../lib/utils";
import type { ChatMessage, ChatStyle, ConversationSummary } from "../types";

// A message plus a transient client-side error state (Gemini unavailable → retry).
type UiMessage = ChatMessage & { error?: string };

// Jo replies in markdown (bold figures, bullet lists) — render it, don't show raw
// `**`/`*`. Bold runs are money, so they get the tabular figure face.
function JoMarkdown({ text }: { text: string }) {
  return (
    <div
      className={cn(
        "space-y-2 text-[15px] leading-relaxed text-text",
        "[&_strong]:font-semibold [&_strong]:text-text [&_strong]:[font-variant-numeric:tabular-nums]",
        "[&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5",
        "[&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5",
        "[&_a]:text-accent-ink [&_a]:underline",
      )}
    >
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}

/** The grounding, made visible: which data tools Jo actually called for this answer. */
function ToolTrace({ tools, provider }: { tools?: string[] | null; provider?: string | null }) {
  if (!tools?.length) return null;
  return (
    <div className="mt-2.5 flex flex-wrap items-center gap-1.5 border-t border-line-soft pt-2.5">
      <span className="text-xs text-muted">
        {provider === "rule-based" ? "Computed offline via" : "Computed via"}
      </span>
      {tools.map((t) => (
        <code
          key={t}
          className="rounded-md bg-accent-a/10 px-1.5 py-0.5 font-mono text-[11px] text-accent-ink"
        >
          {t}()
        </code>
      ))}
    </div>
  );
}

const BASE_SUGGESTIONS = [
  "How much did I spend on restaurants in March?",
  "Which subscriptions am I paying for?",
  "Did anything unusual show up in my spending?",
  "Compare my spending in March vs April",
];
const BALANCE_SUGGESTION = "How much money do I have across my accounts?";

const STYLES: { id: ChatStyle; label: string; hint: string }[] = [
  { id: "friendly", label: "Friendly", hint: "Warm, explains the jargon" },
  { id: "numbers", label: "Just the numbers", hint: "Figures first, minimal prose" },
  { id: "coach", label: "Coach", hint: "Adds one next step to try" },
];
const STYLE_KEY = "finance_ai_style";

function readStyle(): ChatStyle {
  try {
    const s = localStorage.getItem(STYLE_KEY);
    if (s === "friendly" || s === "numbers" || s === "coach") return s;
  } catch { /* storage blocked */ }
  return "friendly";
}

/** One compact control for Jo's voice, instead of three always-visible buttons. */
function VoiceMenu({ style, onChange }: { style: ChatStyle; onChange: (s: ChatStyle) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = STYLES.find((s) => s.id === style)!;

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="inline-flex min-h-11 items-center gap-1.5 rounded-xl border border-line bg-card px-3 text-sm text-muted transition-colors hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
      >
        <span className="hidden sm:inline">Voice:</span>
        <span className="font-medium text-text">{current.label}</span>
        <ChevronDown className={cn("h-4 w-4 transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div role="menu" aria-label="Jo's voice" className="absolute right-0 top-full z-30 mt-2 w-64 rounded-2xl border border-line bg-card p-1.5 shadow-card">
          {STYLES.map((s) => (
            <button
              key={s.id}
              role="menuitemradio"
              aria-checked={s.id === style}
              onClick={() => { onChange(s.id); setOpen(false); }}
              className="flex min-h-12 w-full items-center gap-3 rounded-xl px-3 text-left transition-colors hover:bg-line-soft focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
            >
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium text-text">{s.label}</span>
                <span className="block text-xs text-muted">{s.hint}</span>
              </span>
              {s.id === style && <Check className="h-4 w-4 shrink-0 text-accent-a" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Saved conversations (real users only). A column on desktop, a sheet on phones. */
function ThreadList({
  convos, activeId, onSelect, onNew, onDelete,
}: {
  convos: ConversationSummary[] | undefined; activeId: number | null;
  onSelect: (id: number) => void; onNew: () => void; onDelete: (id: number) => void;
}) {
  return (
    <>
      <button
        onClick={onNew}
        className="grad mb-3 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl px-3 text-sm font-medium text-white shadow-pop hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
      >
        <Plus className="h-4 w-4" /> New chat
      </button>
      <div className="space-y-1">
        {convos?.map((c) => (
          <div
            key={c.id}
            className={cn(
              "group flex items-center rounded-xl text-sm transition-colors",
              c.id === activeId ? "bg-accent-a/[0.14] text-text" : "text-muted hover:bg-line-soft hover:text-text",
            )}
          >
            <button
              onClick={() => onSelect(c.id)}
              aria-current={c.id === activeId ? "true" : undefined}
              className="flex min-h-11 min-w-0 flex-1 items-center gap-2 rounded-xl px-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
            >
              <MessageSquare className="h-4 w-4 shrink-0 opacity-70" />
              <span className="truncate">{c.title}</span>
            </button>
            <button
              onClick={() => onDelete(c.id)}
              aria-label={`Delete “${c.title}”`}
              className="grid size-11 shrink-0 place-items-center rounded-xl text-muted transition-opacity hover:text-down focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 [@media(hover:hover)]:opacity-0 [@media(hover:hover)]:group-hover:opacity-100"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
        {convos?.length === 0 && <p className="px-3 py-2 text-sm text-muted">No saved chats yet.</p>}
      </div>
    </>
  );
}

export default function AskAI() {
  const demo = isDemo();
  const qc = useQueryClient();
  const balances = useBalances();

  const [style, setStyle] = useState<ChatStyle>(readStyle);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const [threadsOpen, setThreadsOpen] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    try { localStorage.setItem(STYLE_KEY, style); } catch { /* ignore */ }
  }, [style]);
  useEffect(() => {
    if (messages.length) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  // Persisted threads (real users only; the demo keeps its chat in memory).
  const convos = useQuery({
    queryKey: ["conversations"],
    queryFn: api.listConversations,
    enabled: !demo,
  });

  const newChat = useCallback(() => {
    setActiveId(null);
    setMessages([]);
    setThreadsOpen(false);
    inputRef.current?.focus();
  }, []);

  const selectConversation = async (id: number) => {
    setThreadsOpen(false);
    if (id === activeId) return;
    setActiveId(id);
    const detail = await api.getConversation(id);
    setMessages(detail.messages);
  };

  const remove = useMutation({
    mutationFn: (id: number) => api.deleteConversation(id),
    onSuccess: (_res, id) => {
      if (id === activeId) newChat();
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  const send = useMutation({
    mutationFn: async (question: string): Promise<ChatMessage & { conversation_id: number | null }> => {
      if (demo) {
        const res = await api.query(question, messages, style);
        return { role: "assistant", content: res.answer, tools_used: res.tools_used, provider: res.provider, conversation_id: null };
      }
      const res = await api.sendMessage(question, activeId, style);
      return { ...res.message, conversation_id: res.conversation_id };
    },
    onMutate: (question: string) => {
      setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);
    },
    onSuccess: ({ conversation_id, ...reply }) => {
      setMessages((m) => m.map((msg, i) => (i === m.length - 1 ? { ...reply, role: "assistant" } : msg)));
      if (!demo && conversation_id) {
        if (activeId == null) setActiveId(conversation_id);
        qc.invalidateQueries({ queryKey: ["conversations"] });
      }
    },
    onError: (err) => {
      // Keep the user's message and mark Jo's reply as a retryable error, so
      // nothing is lost and the user can resend with one tap.
      setMessages((m) =>
        m.map((msg, i) => (i === m.length - 1 ? { ...msg, error: (err as Error).message } : msg)),
      );
    },
  });

  const submit = (q: string) => {
    const question = q.trim();
    if (!question || send.isPending) return;
    setInput("");
    send.mutate(question);
  };

  // Resend the failed question: drop the failed user+assistant pair, then re-ask.
  const retry = (question: string) => {
    if (send.isPending) return;
    setMessages((m) => m.slice(0, -2));
    send.mutate(question);
  };

  const empty = messages.length === 0 && !send.isPending;
  const hasAccounts = (balances.data?.count ?? 0) > 0;
  // With accounts, lead with a balance question; the anomaly one always stays
  // (it's the detector's showcase).
  const suggestions = hasAccounts
    ? [BALANCE_SUGGESTION, ...BASE_SUGGESTIONS.slice(0, 3)]
    : BASE_SUGGESTIONS;

  return (
    <div className="flex gap-6">
      {/* Thread list: a column from lg (real users only) */}
      {!demo && (
        <aside className="hidden w-56 shrink-0 lg:block">
          <ThreadList
            convos={convos.data} activeId={activeId}
            onSelect={selectConversation} onNew={newChat} onDelete={(id) => remove.mutate(id)}
          />
        </aside>
      )}

      {/* Chat column: fills the viewport so the composer rests at the bottom */}
      <div className="flex min-h-[calc(100dvh-5.75rem-env(safe-area-inset-bottom))] min-w-0 flex-1 flex-col md:min-h-[calc(100dvh-4rem)]">
        <header className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <h1 className="font-display text-2xl font-bold tracking-tight text-text">Ask Jo</h1>
            <p className="mt-0.5 truncate text-sm text-muted">
              {demo ? "Demo chat · nothing is saved" : "Every figure is computed from your data"}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {!demo && (
              <button
                onClick={() => setThreadsOpen(true)}
                aria-label="Saved chats"
                className="grid size-11 place-items-center rounded-xl border border-line bg-card text-muted hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 lg:hidden"
              >
                <History className="h-5 w-5" />
              </button>
            )}
            <VoiceMenu style={style} onChange={setStyle} />
          </div>
        </header>

        <BalanceStrip className="mt-4 xl:hidden" />

        <div className="flex-1 pt-6">
          {empty ? (
            <div className="flex h-full flex-col justify-end gap-4 pb-2 sm:justify-start">
              <div className="flex items-start gap-2.5">
                <Spark className="mt-0.5 h-7 w-7 shrink-0" />
                <div className="rounded-2xl rounded-tl-md border border-line bg-card px-4 py-3 text-[15px] leading-relaxed text-text shadow-card">
                  Hi, I’m Jo. Ask me anything about your money. I look up every number in your
                  transactions, so nothing is guessed.
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => submit(s)}
                    className="flex min-h-12 items-center rounded-2xl border border-line bg-card px-4 py-2.5 text-left text-sm text-text transition-colors hover:border-accent-a/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div role="log" aria-live="polite" aria-label="Conversation with Jo" className="space-y-5">
              {messages.map((msg, i) =>
                msg.role === "user" ? (
                  <div key={i} className="flex justify-end">
                    <div className="grad max-w-[85%] rounded-2xl rounded-br-md px-4 py-2.5 text-[15px] text-white">
                      {msg.content}
                    </div>
                  </div>
                ) : (
                  <div key={i} className="flex items-start gap-2.5">
                    <Spark className="mt-0.5 h-7 w-7 shrink-0" />
                    <div className="min-w-0 max-w-[85%] rounded-2xl rounded-tl-md border border-line bg-card px-4 py-3 shadow-card">
                      {msg.error ? (
                        <div className="space-y-2.5">
                          <p className="text-sm leading-relaxed text-muted">{msg.error}</p>
                          <button
                            onClick={() => retry(messages[i - 1]?.content ?? "")}
                            disabled={send.isPending}
                            className="inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-line px-3 text-sm font-medium text-text transition-colors hover:border-accent-a/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 disabled:opacity-50"
                          >
                            <RotateCw className="h-4 w-4" /> Retry
                          </button>
                        </div>
                      ) : msg.content ? (
                        <>
                          <JoMarkdown text={msg.content} />
                          <ToolTrace tools={msg.tools_used} provider={msg.provider} />
                        </>
                      ) : (
                        <p className="flex items-center gap-2 text-sm text-muted">
                          <Sparkles className="h-4 w-4 motion-safe:animate-pulse" /> Jo is looking it up…
                        </p>
                      )}
                    </div>
                  </div>
                ),
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {/* Composer: pinned just above the phone tab bar, bottom of the column on desktop */}
        <form
          onSubmit={(e) => { e.preventDefault(); submit(input); }}
          className="sticky bottom-[calc(4.5rem+env(safe-area-inset-bottom))] mt-4 bg-gradient-to-t from-bg from-60% to-transparent pt-3 md:bottom-8"
        >
          <div className="flex items-center gap-2 rounded-2xl border border-line bg-card p-1.5 pl-4 shadow-card transition-shadow focus-within:border-accent-a focus-within:ring-2 focus-within:ring-accent-a/25">
            <label htmlFor="ask-input" className="sr-only">Ask Jo a question</label>
            <input
              id="ask-input"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={500}
              autoComplete="off"
              enterKeyHint="send"
              placeholder="Ask about your money…"
              className="min-w-0 flex-1 border-0 bg-transparent text-base text-text placeholder:text-muted focus:outline-none"
            />
            <button
              type="submit"
              disabled={send.isPending || !input.trim()}
              aria-label="Send"
              className="grad grid size-11 shrink-0 place-items-center rounded-xl text-white shadow-pop transition hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60 focus-visible:ring-offset-2 focus-visible:ring-offset-card disabled:opacity-40 disabled:shadow-none"
            >
              <Send className="h-[18px] w-[18px]" />
            </button>
          </div>
        </form>
      </div>

      {/* Balances beside the chat on wide screens (a strip above it otherwise) */}
      <BalancePanel className="hidden xl:block" />

      {/* Saved chats as a sheet below lg */}
      {threadsOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" onClick={() => setThreadsOpen(false)}>
          <div className="absolute inset-0 bg-black/50 motion-safe:animate-[fade-in_160ms_ease-out]" />
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Saved chats"
            onClick={(e) => e.stopPropagation()}
            className="absolute inset-x-0 bottom-0 max-h-[75dvh] overflow-y-auto rounded-t-3xl border-t border-line bg-card px-3 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2 shadow-card motion-safe:animate-[sheet-up_220ms_cubic-bezier(0.16,1,0.3,1)]"
          >
            <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line" aria-hidden />
            <div className="flex items-center justify-between px-1 pb-2">
              <h2 className="font-display text-base font-semibold text-text">Saved chats</h2>
              <button onClick={() => setThreadsOpen(false)} aria-label="Close" className="grid size-11 place-items-center rounded-xl text-muted hover:text-text">
                <X className="h-5 w-5" />
              </button>
            </div>
            <ThreadList
              convos={convos.data} activeId={activeId}
              onSelect={selectConversation} onNew={newChat} onDelete={(id) => remove.mutate(id)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
