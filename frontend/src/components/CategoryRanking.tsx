import { useState } from "react";
import { Link } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { capitalize, colorFor, fmtUSD } from "../lib/utils";
import { Card } from "./ui";

/**
 * Ranked spend per category with proportional bars. Readable on touch (unlike a
 * donut's hover tooltips), and credits the trained model that did the sorting.
 */
export function CategoryRanking({
  data, limit, title = "Where it went",
}: { data: Record<string, number>; limit?: number; title?: string }) {
  const [showAll, setShowAll] = useState(false);
  const rows = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const total = rows.reduce((s, [, v]) => s + v, 0);
  const max = rows[0]?.[1] ?? 1;
  const visible = limit && !showAll ? rows.slice(0, limit) : rows;

  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-display font-semibold text-text">{title}</h2>
        <span className="num text-sm text-muted">{fmtUSD(total)}</span>
      </div>
      <p className="mt-1 flex items-start gap-1.5 text-xs leading-relaxed text-muted">
        <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-a" />
        <span>
          Sorted by JoMoney’s own trained model, 95.8% accurate on merchants it never saw.{" "}
          <Link to="/how-it-works" className="font-medium text-accent-ink underline-offset-2 hover:underline">How it works</Link>
        </span>
      </p>
      <ul className="mt-4 space-y-3">
        {visible.map(([cat, amt]) => (
          <li key={cat}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="flex min-w-0 items-center gap-2 text-text">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: colorFor(cat) }} aria-hidden />
                <span className="truncate">{capitalize(cat)}</span>
              </span>
              <span className="shrink-0">
                <span className="num font-semibold text-text">{fmtUSD(amt)}</span>
                <span className="num ml-2 inline-block w-9 text-right text-xs text-muted">{Math.round((amt / total) * 100)}%</span>
              </span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-line-soft" aria-hidden>
              <div className="h-full rounded-full" style={{ width: `${(amt / max) * 100}%`, backgroundColor: colorFor(cat) }} />
            </div>
          </li>
        ))}
      </ul>
      {limit && rows.length > limit && (
        <button
          onClick={() => setShowAll((s) => !s)}
          className="mt-3 min-h-10 rounded-lg text-sm font-medium text-accent-ink hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-a/60"
        >
          {showAll ? "Show fewer" : `Show all ${rows.length} categories`}
        </button>
      )}
    </Card>
  );
}
