import { Sparkles } from "lucide-react";

import { ActionProposalCard } from "@/features/assistant/components/action-proposal-card";
import { AssistantMarkdown } from "@/features/assistant/components/assistant-markdown";
import { AssistantResultsTable } from "@/features/assistant/components/assistant-results-table";
import { DraftOrderCard } from "@/features/assistant/components/draft-order-card";
import type { AssistantAction, AssistantMessage } from "@/features/assistant/types";
import type { Order } from "@/features/orders/types";

function AssistantAvatar() {
  return (
    <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-foreground">
      <Sparkles className="size-3.5" aria-hidden />
    </span>
  );
}

type TimelineItem =
  | { kind: "message"; key: string; createdAt: string; message: AssistantMessage }
  | { kind: "action"; key: string; createdAt: string; action: AssistantAction }
  | { kind: "order"; key: string; createdAt: string; order: Order };

function buildTimeline(
  messages: AssistantMessage[],
  actions: AssistantAction[],
  orders: Order[],
): TimelineItem[] {
  const items: TimelineItem[] = [
    ...messages.map(
      (message): TimelineItem => ({
        kind: "message",
        key: `message-${message.id}`,
        createdAt: message.created_at,
        message,
      }),
    ),
    ...actions.map(
      (action): TimelineItem => ({
        kind: "action",
        key: `action-${action.id}`,
        createdAt: action.created_at,
        action,
      }),
    ),
    ...orders.map(
      (order): TimelineItem => ({
        kind: "order",
        key: `order-${order.id}`,
        createdAt: order.created_at,
        order,
      }),
    ),
  ];
  // A proposal/order and the reply that introduced it land in the same second, so fall back
  // to kind order (cards sort after the message that introduced them) for a stable sequence.
  return items.sort((a, b) => {
    const byTime = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
    if (byTime !== 0) return byTime;
    return a.kind === "message" ? -1 : b.kind === "message" ? 1 : 0;
  });
}

export function AssistantMessageList({
  messages,
  actions = [],
  orders = [],
}: {
  messages: AssistantMessage[];
  actions?: AssistantAction[];
  orders?: Order[];
}) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-center">
        <span className="flex size-12 items-center justify-center rounded-full bg-muted text-foreground">
          <Sparkles className="size-6" aria-hidden />
        </span>
        <div className="space-y-1">
          <p className="font-heading text-base font-semibold text-foreground">Ask Orbiz AI</p>
          <p className="max-w-sm text-sm text-muted-foreground">
            Paste a customer&apos;s message to draft an order, or ask about unpaid orders, low
            stock, or a specific order number.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ul className="mx-auto w-full max-w-3xl space-y-6">
      {buildTimeline(messages, actions, orders).map((item) => {
        if (item.kind === "action") {
          return (
            <li key={item.key} className="pl-10">
              <ActionProposalCard action={item.action} />
            </li>
          );
        }

        if (item.kind === "order") {
          return (
            <li key={item.key} className="pl-10">
              <DraftOrderCard order={item.order} />
            </li>
          );
        }

        const { message } = item;
        return message.role === "user" ? (
          <li key={item.key} className="flex justify-end">
            <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-foreground px-4 py-2.5 text-sm leading-6 text-card">
              {message.content}
            </p>
          </li>
        ) : (
          <li key={item.key} className="flex items-start gap-3">
            <AssistantAvatar />
            <div className="min-w-0 flex-1 space-y-2 pt-0.5">
              <AssistantMarkdown content={message.content} />
              {message.result_tables.map((table, index) => (
                <AssistantResultsTable key={`${table.tool}-${index}`} table={table} />
              ))}
              {message.source_records.length > 0 ? (
                <p className="text-xs text-muted-foreground">
                  Checked: {message.source_records.join(", ")}
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
