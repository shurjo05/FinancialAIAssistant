import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles, Send, Plus, Trash2, MessageSquare, RotateCw } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { api, isDemo } from "../services/api";
import { PageHeader, Spark } from "../components/ui";
import { BalancePanel, BalanceStrip } from "../components/Accounts";
import { useBalances } from "../hooks/useBalances";
import { cn } from "../lib/utils";
import type { ChatMessage, ChatStyle } from "../types";

// A message plus a transient client-side error state (Gemini unavailable → retry).
type UiMessage = ChatMessage & { error?: string };

// Jo replies in markdown (bold figures, bullet lists) — render it, don't show raw
// `**`/`*`. Child-element styles keep it on-brand via Tailwind arbitrary variants.
function JoMarkdown({ text }: { text: string }) {
  return (
    <div
      className={cn(
        "space-y-2 text-sm leading-relaxed text-text",
        "[&_strong]:font-semibold [&_strong]:text-text",
        "[&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5",
        "[&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5",
        "[&_a]:text-accent-a [&_a]:underline",
      )}
    >
      <ReactMarkdown>{text}</ReactMarkdown>
    </div>
  );
}

const SUGGESTIONS = [
  "How much did I spend on restaurants in March?",
  "Compare my spending in March vs April",
  "Which subscriptions am I paying for?",
  "Anything unusual last month?",
];

const BALANCE_SUGGESTION = "How much money do I have across my accounts?";

const STYLES: { id: ChatStyle; label: string }[] = [
  { id: "friendly", label: "Friendly" },
  { id: "numbers", label: "Just the numbers" },
  { id: "coach", label: "Coach" },
];
const STYLE_KEY = "finance_ai_style";

export default function AskAI() {
  const demo = isDemo();
  const qc = useQueryClient();
  const balances = useBalances();

  const [style, setStyle] = useState<ChatStyle>(
    () => (localStorage.getItem(STYLE_KEY) as ChatStyle) || "friendly",
  );
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(STYLE_KEY, style);
  }, [style]);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Persisted threads (real users only; the demo keeps its chat in memory).
  const convos = useQuery({
    queryKey: ["conversations"],
    queryFn: api.listConversations,
    enabled: !demo,
  });

  const newChat = () => {
    setActiveId(null);
    setMessages([]);
  };

  const selectConversation = async (id: number) => {
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
    mutationFn: async (question: string) => {
      if (demo) {
        const res = await api.query(question, messages, style);
        return { answer: res.answer, conversation_id: null as number | null };
      }
      const res = await api.sendMessage(question, activeId, style);
      return { answer: res.message.content, conversation_id: res.conversation_id };
    },
    onMutate: (question: string) => {
      setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);
    },
    onSuccess: (res) => {
      setMessages((m) => m.map((msg, i) => (i === m.length - 1 ? { ...msg, content: res.answer } : msg)));
      if (!demo && res.conversation_id) {
        if (activeId == null) setActiveId(res.conversation_id);
        qc.invalidateQueries({ queryKey: ["conversations"] });
      }
    },
    onError: (err) => {
      // Keep the user's message and mark Jo's reply as a retryable error, so
      // nothing is lost and the user can resend with one click.
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

  const showSuggestions = messages.length === 0 && !send.isPending;
  // Offer a balances question once there are accounts to ask about.
  const hasAccounts = (balances.data?.count ?? 0) > 0;
  const suggestions = hasAccounts ? [BALANCE_SUGGESTION, ...SUGGESTIONS.slice(0, 3)] : SUGGESTIONS;

  return (
    <div className="flex gap-6">
      {/* Thread list — real users only */}
      {!demo && (
        <aside className="hidden w-56 shrink-0 lg:block">
          <button
            onClick={newChat}
            className="grad mb-3 flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-white shadow-pop hover:brightness-110"
          >
            <Plus className="h-4 w-4" /> New chat
          </button>
          <div className="space-y-1">
            {convos.data?.map((c) => (
              <div
                key={c.id}
                className={cn(
                  "group flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors",
                  c.id === activeId ? "bg-accent-a/[0.14] text-text" : "text-muted hover:bg-line-soft hover:text-text",
                )}
              >
                <button onClick={() => selectConversation(c.id)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
                  <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-70" />
                  <span className="truncate">{c.title}</span>
                </button>
                <button
                  onClick={() => remove.mutate(c.id)}
                  aria-label="Delete conversation"
                  className="shrink-0 text-faint opacity-0 transition-opacity hover:text-down group-hover:opacity-100"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
            {convos.data?.length === 0 && (
              <p className="px-2.5 py-2 text-xs text-faint">No conversations yet.</p>
            )}
          </div>
        </aside>
      )}

      {/* Chat column */}
      <div className="min-w-0 flex-1">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
          <PageHeader
            title="Ask Jo"
            subtitle={
              demo
                ? "Demo chat — remembers this session only. Answers come straight from your transactions."
                : "Ask anything about your spending — answers come straight from your transactions."
            }
          />
          <div className="mb-6 flex items-center gap-1 rounded-xl border border-line bg-card p-1">
            {STYLES.map((s) => (
              <button
                key={s.id}
                onClick={() => setStyle(s.id)}
                title={`Jo's voice: ${s.label}`}
                className={cn(
                  "rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors",
                  style === s.id ? "grad text-white shadow-pop" : "text-muted hover:text-text",
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>

        <BalanceStrip className="mb-5 xl:hidden" />

        {showSuggestions && (
          <div className="mb-5 flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => submit(s)}
                className="rounded-full border border-line bg-card px-3.5 py-1.5 text-sm text-muted transition-colors hover:border-accent-a/40 hover:text-text"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="space-y-5">
          {messages.map((msg, i) =>
            msg.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="grad max-w-[80%] rounded-2xl rounded-br-md px-4 py-2.5 text-sm text-white">
                  {msg.content}
                </div>
              </div>
            ) : (
              <div key={i} className="flex items-start gap-2.5">
                <Spark className="mt-0.5 h-7 w-7 shrink-0" />
                <div className="max-w-[80%] rounded-2xl rounded-tl-md border border-line bg-card px-4 py-3 shadow-card">
                  {msg.error ? (
                    <div className="space-y-2.5">
                      <p className="text-sm leading-relaxed text-muted">{msg.error}</p>
                      <button
                        onClick={() => retry(messages[i - 1]?.content ?? "")}
                        disabled={send.isPending}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-line px-2.5 py-1.5 text-xs font-medium text-text transition-colors hover:border-accent-a/40 disabled:opacity-50"
                      >
                        <RotateCw className="h-3.5 w-3.5" /> Retry
                      </button>
                    </div>
                  ) : msg.content ? (
                    <JoMarkdown text={msg.content} />
                  ) : (
                    <p className="flex items-center gap-2 text-sm text-faint">
                      <Sparkles className="h-4 w-4 animate-pulse" /> Jo is thinking…
                    </p>
                  )}
                </div>
              </div>
            ),
          )}
          <div ref={endRef} />
        </div>

        <form onSubmit={(e) => { e.preventDefault(); submit(input); }} className="sticky bottom-4 mt-6">
          <div className="flex items-center gap-2 rounded-2xl border border-line bg-card p-2 pl-4 shadow-card">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={500}
              placeholder="Ask Jo about your spending…"
              className="flex-1 border-0 bg-transparent text-[15px] text-text placeholder:text-faint focus:outline-none"
            />
            <button
              type="submit"
              disabled={send.isPending}
              aria-label="Send"
              className="grad grid h-10 w-10 place-items-center rounded-xl text-white shadow-pop disabled:opacity-50"
            >
              <Send className="h-[18px] w-[18px]" />
            </button>
          </div>
        </form>
      </div>

      {/* Balances preview beside the chat on wide screens (a strip above it otherwise) */}
      <BalancePanel className="hidden xl:block" />
    </div>
  );
}
