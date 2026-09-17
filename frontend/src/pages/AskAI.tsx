import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles, Send } from "lucide-react";
import { api } from "../services/api";
import { PageHeader, Spark } from "../components/ui";

interface Turn {
  question: string;
  answer?: string;
  error?: string;
}

const SUGGESTIONS = [
  "How much did I spend on restaurants in March?",
  "Compare my spending in March vs April",
  "Which subscriptions am I paying for?",
  "Anything unusual last month?",
];

export default function AskAI() {
  const [input, setInput] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);

  const ask = useMutation({
    mutationFn: api.query,
    onMutate: (question) => setTurns((t) => [...t, { question }]),
    onSuccess: (res) =>
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, answer: res.answer } : turn))),
    onError: (err) =>
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, error: (err as Error).message } : turn))),
  });

  const submit = (question: string) => {
    if (!question.trim() || ask.isPending) return;
    setInput("");
    ask.mutate(question);
  };

  return (
    <div>
      <PageHeader title="Ask Jo" subtitle="Ask anything about your spending — answers come straight from your transactions." />

      {turns.length === 0 && (
        <div className="mb-5 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
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
        {turns.map((turn, i) => (
          <div key={i} className="space-y-2.5">
            <div className="flex justify-end">
              <div className="grad max-w-[80%] rounded-2xl rounded-br-md px-4 py-2.5 text-sm text-white">
                {turn.question}
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <Spark className="mt-0.5 h-7 w-7 shrink-0" />
              <div className="max-w-[80%] rounded-2xl rounded-tl-md border border-line bg-card px-4 py-3 shadow-card">
                {turn.error ? (
                  <p className="text-sm text-down">{turn.error}</p>
                ) : turn.answer ? (
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-text">{turn.answer}</p>
                ) : (
                  <p className="flex items-center gap-2 text-sm text-faint">
                    <Sparkles className="h-4 w-4 animate-pulse" /> Jo is thinking…
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); submit(input); }} className="sticky bottom-4 mt-6">
        <div className="flex items-center gap-2 rounded-2xl border border-line bg-card p-2 pl-4 shadow-card">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Jo about your spending…"
            className="flex-1 border-0 bg-transparent text-[15px] text-text placeholder:text-faint focus:outline-none"
          />
          <button
            type="submit"
            disabled={ask.isPending}
            aria-label="Send"
            className="grad grid h-10 w-10 place-items-center rounded-xl text-white shadow-pop disabled:opacity-50"
          >
            <Send className="h-[18px] w-[18px]" />
          </button>
        </div>
      </form>
    </div>
  );
}
