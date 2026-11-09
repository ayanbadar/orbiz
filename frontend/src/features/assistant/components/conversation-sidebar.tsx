import { Plus } from "lucide-react";
import { cn } from "cn";

import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { useAssistantConversations } from "@/features/assistant/api/assistant.api";

function formatWhen(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  return sameDay
    ? date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

type Props = {
  selectedId: number | null;
  onSelect: (id: number) => void;
  onNewConversation: () => void;
};

export function ConversationSidebar({ selectedId, onSelect, onNewConversation }: Props) {
  const conversations = useAssistantConversations();
  const items = conversations.data?.results ?? [];

  return (
    <div className="flex h-full w-64 shrink-0 flex-col gap-2 border-r border-border pr-3">
      <Button
        variant="outline"
        size="sm"
        className="justify-start gap-2"
        onClick={onNewConversation}
      >
        <Plus className="size-4" />
        New chat
      </Button>

      <div className="flex-1 overflow-y-auto">
        <QueryState
          isLoading={conversations.isPending}
          isError={conversations.isError}
          isEmpty={!conversations.isPending && !conversations.isError && items.length === 0}
          errorMessage="Couldn't load conversations."
          emptyMessage="No conversations yet."
        >
          <ul className="space-y-0.5">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item.id)}
                  className={cn(
                    "flex w-full flex-col items-start gap-0.5 rounded-lg px-3 py-2 text-left text-sm transition-colors",
                    item.id === selectedId
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                  )}
                >
                  <span className="w-full truncate font-medium">{item.preview}</span>
                  <span className="text-xs text-muted-foreground">{formatWhen(item.updated_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        </QueryState>
      </div>
    </div>
  );
}
