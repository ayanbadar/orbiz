import { Activity, Bell, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { cn } from "cn";

import { ConfirmDialog } from "@/components/confirm-dialog";
import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import {
  useAssistantConversations,
  useDeleteAssistantConversation,
} from "@/features/assistant/api/assistant.api";
import { getErrorMessage } from "@/features/auth/utils/form-errors";

export type AssistantView = "chat" | "attention" | "activity";

function formatWhen(iso: string): string {
  const date = new Date(iso);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  return sameDay
    ? date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    : date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function SidebarNavButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: typeof Bell;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm font-medium transition-colors",
        active
          ? "bg-muted text-foreground"
          : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
      )}
    >
      <Icon className="size-4 shrink-0" aria-hidden />
      {label}
    </button>
  );
}

type Props = {
  view: AssistantView;
  onViewChange: (view: AssistantView) => void;
  selectedId: number | null;
  onSelect: (id: number) => void;
  onNewConversation: () => void;
  onDeleted: (id: number) => void;
};

/** ChatGPT-style left rail for the Orbiz AI page: new chat, view switcher, then chat history. */
export function AssistantSidebar({
  view,
  onViewChange,
  selectedId,
  onSelect,
  onNewConversation,
  onDeleted,
}: Props) {
  const conversations = useAssistantConversations();
  const deleteConversation = useDeleteAssistantConversation();
  const items = conversations.data?.results ?? [];
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);

  const handleDelete = async () => {
    if (pendingDeleteId === null) return;
    const id = pendingDeleteId;
    try {
      await deleteConversation.mutateAsync(id);
      setPendingDeleteId(null);
      onDeleted(id);
    } catch (error) {
      setPendingDeleteId(null);
      toast.error(getErrorMessage(error, "Could not delete this conversation."));
    }
  };

  return (
    <div className="flex h-full w-64 shrink-0 flex-col border-r border-border">
      <div className="space-y-1 p-3">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-start gap-2"
          onClick={() => {
            onViewChange("chat");
            onNewConversation();
          }}
        >
          <Plus className="size-4" />
          New chat
        </Button>
      </div>

      <nav className="space-y-0.5 px-3 pb-2">
        <SidebarNavButton
          icon={Bell}
          label="Needs attention"
          active={view === "attention"}
          onClick={() => onViewChange("attention")}
        />
        <SidebarNavButton
          icon={Activity}
          label="Activity"
          active={view === "activity"}
          onClick={() => onViewChange("activity")}
        />
      </nav>

      <p className="px-4 pt-2 pb-1 text-xs font-semibold text-muted-foreground">Chats</p>

      <div className="scrollbar-slim min-h-0 flex-1 overflow-y-auto px-3 pb-3">
        <QueryState
          isLoading={conversations.isPending}
          isError={conversations.isError}
          isEmpty={!conversations.isPending && !conversations.isError && items.length === 0}
          errorMessage="Couldn't load conversations."
          emptyMessage="No conversations yet."
        >
          <ul className="space-y-0.5">
            {items.map((item) => (
              <li key={item.id} className="group relative">
                <button
                  type="button"
                  onClick={() => {
                    onViewChange("chat");
                    onSelect(item.id);
                  }}
                  className={cn(
                    "flex w-full flex-col items-start gap-0.5 rounded-lg py-2 pl-3 pr-8 text-left text-sm transition-colors",
                    view === "chat" && item.id === selectedId
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                  )}
                >
                  <span className="w-full truncate font-medium">{item.preview}</span>
                  <span className="text-xs text-muted-foreground">{formatWhen(item.updated_at)}</span>
                </button>
                <button
                  type="button"
                  aria-label="Delete conversation"
                  onClick={(event) => {
                    event.stopPropagation();
                    setPendingDeleteId(item.id);
                  }}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted-foreground opacity-0 transition-opacity hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 group-hover:opacity-100"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </QueryState>
      </div>

      <ConfirmDialog
        open={pendingDeleteId !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteId(null);
        }}
        title="Delete this conversation?"
        description="This removes the chat for everyone on your team. This can't be undone."
        confirmLabel={deleteConversation.isPending ? "Deleting…" : "Delete"}
        cancelLabel="Keep it"
        variant="destructive"
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}
