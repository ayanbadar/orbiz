import { useState } from "react";

import {
  useAssistantConversations,
  useCreateAssistantConversation,
} from "@/features/assistant/api/assistant.api";
import { AssistantActivityList } from "@/features/assistant/components/assistant-activity-list";
import { AssistantDigestPanel } from "@/features/assistant/components/assistant-digest-panel";
import { type AssistantView, AssistantSidebar } from "@/features/assistant/components/assistant-sidebar";
import { ChatPanel } from "@/features/assistant/components/chat-panel";

export function AssistantPage() {
  const [view, setView] = useState<AssistantView>("chat");
  const conversations = useAssistantConversations();
  // Nothing explicitly picked yet → fall back to the most recent conversation already loaded,
  // derived at render time rather than synced via an effect.
  const [explicitId, setExplicitId] = useState<number | null>(null);
  const selectedId = explicitId ?? conversations.data?.results[0]?.id ?? null;
  const createConversation = useCreateAssistantConversation();

  const handleDeleted = (id: number) => {
    if (id === selectedId) {
      setExplicitId(null);
    }
  };

  const handleNewConversation = async () => {
    const created = await createConversation.mutateAsync();
    setExplicitId(created.conversation_id);
  };

  return (
    <div className="flex h-full min-h-0">
      <AssistantSidebar
        view={view}
        onViewChange={setView}
        selectedId={selectedId}
        onSelect={setExplicitId}
        onNewConversation={() => void handleNewConversation()}
        onDeleted={handleDeleted}
      />

      {view === "chat" ? (
        <ChatPanel conversationId={selectedId} onConversationChange={setExplicitId} />
      ) : (
        <div className="scrollbar-slim min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
          <h2 className="mb-4 font-heading text-lg font-semibold text-foreground">
            {view === "attention" ? "Needs attention" : "Activity"}
          </h2>
          {view === "attention" ? <AssistantDigestPanel /> : <AssistantActivityList />}
        </div>
      )}
    </div>
  );
}
