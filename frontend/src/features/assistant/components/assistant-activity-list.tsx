import { Link } from "react-router-dom";

import { QueryState } from "@/components/query-state";
import { ROUTES } from "@/constants/routes";
import { useAssistantActivity } from "@/features/assistant/api/assistant.api";

export function AssistantActivityList() {
  const activity = useAssistantActivity();
  const items = activity.data?.results ?? [];

  return (
    <QueryState
      isLoading={activity.isPending}
      isError={activity.isError}
      isEmpty={!activity.isPending && !activity.isError && items.length === 0}
      errorMessage="Couldn't load Orbiz AI activity."
      emptyMessage="No AI-confirmed actions yet."
    >
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="border-b border-border pb-3 text-sm last:border-0 last:pb-0">
            <div className="flex items-center justify-between gap-2">
              <Link
                to={ROUTES.orders.detail(item.order_id)}
                className="font-medium text-foreground underline-offset-4 hover:underline"
              >
                {item.order_number}
              </Link>
              <time className="text-xs text-muted-foreground" dateTime={item.created_at}>
                {new Date(item.created_at).toLocaleString()}
              </time>
            </div>
            <p className="text-muted-foreground">{item.message}</p>
          </li>
        ))}
      </ul>
    </QueryState>
  );
}
