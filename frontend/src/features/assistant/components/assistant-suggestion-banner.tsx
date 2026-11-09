import { Sparkles } from "lucide-react";

import { useAssistantDigest } from "@/features/assistant/api/assistant.api";

type Suggestion = { label: string; prompt: string };

/**
 * Proactive next-action suggestions for a brand-new, empty chat — built from the existing
 * zero-LLM-call digest (services.digest(), the same data "Needs attention" already shows), not
 * a fresh model call. Clicking one only fills the composer; the seller still presses Send, same
 * "never silently act" rule as everywhere else in Orbiz AI.
 */
export function AssistantSuggestionBanner({ onPick }: { onPick: (prompt: string) => void }) {
  const digest = useAssistantDigest();
  const unpaidCount = digest.data?.stale_unpaid_orders.length ?? 0;
  const lowStockCount = digest.data?.low_stock_products.length ?? 0;

  if (digest.isPending || digest.isError || (unpaidCount === 0 && lowStockCount === 0)) {
    return null;
  }

  const suggestions: Suggestion[] = [];
  if (unpaidCount > 0) {
    suggestions.push({
      label: `${unpaidCount} order${unpaidCount === 1 ? " has" : "s have"} been waiting 2+ days for payment`,
      prompt: "Show me the orders that have been waiting on payment the longest.",
    });
  }
  if (lowStockCount > 0) {
    suggestions.push({
      label: `${lowStockCount} product${lowStockCount === 1 ? " is" : "s are"} low on stock`,
      prompt: "Which products are running low on stock right now?",
    });
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-2 rounded-2xl border border-border bg-muted/40 p-3">
      <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
        <Sparkles className="size-3.5" aria-hidden />
        Worth a look
      </p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion) => (
          <button
            key={suggestion.prompt}
            type="button"
            onClick={() => onPick(suggestion.prompt)}
            className="rounded-full border border-border bg-card px-3 py-1.5 text-left text-sm text-foreground transition-colors hover:bg-muted"
          >
            {suggestion.label}
          </button>
        ))}
      </div>
    </div>
  );
}
