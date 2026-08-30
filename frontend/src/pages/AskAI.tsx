import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles, Send, User } from "lucide-react";
import { api } from "../services/api";
import { Card, PageHeader } from "../components/ui";
import { cn } from "../lib/utils";

interface Turn {
  question: string;
  answer?: string;
  provider?: string;
  tools?: string[];
  error?: string;
}

const SUGGESTIONS = [
  "How much did I spend on restaurants in March?",
  "Compare my spending in March vs April",
  "What are my biggest unusual transactions?",
  "How many subscriptions do I have?",
];

export default function AskAI() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  const ask = useMutation({
    mutationFn: api.query,
    onMutate: (question) => {
      setTurns((t) => [...t, { question }]);
    },
    onSuccess: (res) => {
      setTurns((t) => t.map((turn, i) =>
        i === t.length - 1 ? { ...turn, answer: res.answer, provider: res.provider, tools: res.tools_used } : turn));
    },
    onError: (err) => {
      setTurns((t) => t.map((turn, i) =>
        i === t.length - 1 ? { ...turn, error: (err as Error).message } : turn));
    },
  });

  const submit = (question: string) => {
    if (!question.trim() || ask.isPending) return;
    setInput("");
    ask.mutate(question);
  };

  return (
    <div>
      <PageHeader title="Ask AI" subtitle="Ask about your finances — answers are computed from your data." />

      {turns.length === 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => submit(s)}
              className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:border-brand-400 hover:text-brand-600"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-4">
        {turns.map((turn, i) => (
          <div key={i} className="space-y-2">
            <div className="flex items-start gap-2">
              <User className="mt-1 h-5 w-5 shrink-0 text-slate-400" />
              <p className="font-medium text-slate-700">{turn.question}</p>
            </div>
            <Card className="ml-7">
              <div className="flex items-start gap-2">
                <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-brand-500" />
                <div className="flex-1">
                  {turn.error ? (
                    <p className="text-sm text-red-600">{turn.error}</p>
                  ) : turn.answer ? (
                    <>
                      <p className="whitespace-pre-wrap text-sm text-slate-700">{turn.answer}</p>
                      <p className="mt-2 text-xs text-slate-400">
                        via {turn.provider}
                        {turn.tools && turn.tools.length > 0 && ` · ${turn.tools.join(", ")}`}
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-slate-400">Thinking…</p>
                  )}
                </div>
              </div>
            </Card>
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => { e.preventDefault(); submit(input); }}
        className="mt-4 flex gap-2"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your spending…"
          className="flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-brand-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={ask.isPending}
          className={cn(
            "inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700",
            ask.isPending && "opacity-50",
          )}
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
