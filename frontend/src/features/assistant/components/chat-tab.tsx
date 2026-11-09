import { Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { QueryState } from "@/components/query-state";
import {
  useAssistantConversation,
  useAssistantConversations,
  useCreateAssistantConversation,
  useSendAssistantMessage,
} from "@/features/assistant/api/assistant.api";
import { AssistantComposer } from "@/features/assistant/components/assistant-composer";
import { AssistantMessageList } from "@/features/assistant/components/assistant-message-list";
import { ConversationSidebar } from "@/features/assistant/components/conversation-sidebar";

function ThinkingIndicator() {
  return (
    <div className="mx-auto flex w-full max-w-3xl items-center gap-3">
      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-foreground">
        <Sparkles className="size-3.5" aria-hidden />
      </span>
      <span className="flex gap-1" aria-label="Orbiz AI is thinking" role="status">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 animate-bounce rounded-full bg-muted-foreground"
            style={{ animationDelay: `${i * 0.12}s` }}
          />
        ))}
      </span>
    </div>
  );
}

export function ChatTab() {
  const conversations = useAssistantConversations();
  // Nothing explicitly picked yet → fall back to the most recent conversation already
  // loaded, derived at render time rather than synced via an effect.
  const [explicitId, setExplicitId] = useState<number | null>(null);
  const selectedId = explicitId ?? conversations.data?.results[0]?.id ?? null;
  const conversation = useAssistantConversation(selectedId);
  const sendMessage = useSendAssistantMessage();
  const createConversation = useCreateAssistantConversation();
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleSelect = (id: number) => {
    setExplicitId(id);
  };

  const handleNewConversation = async () => {
    const created = await createConversation.mutateAsync();
    setExplicitId(created.conversation_id);
  };

  const handleSend = async (message: string) => {
    const result = await sendMessage.mutateAsync({
      message,
      conversationId: selectedId ?? undefined,
    });
    setExplicitId(result.conversation_id);
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [
    conversation.data?.messages.length,
    conversation.data?.actions.length,
    conversation.data?.orders.length,
    sendMessage.isPending,
  ]);

  return (
    <div className="flex h-[70vh] min-h-[480px] gap-4">
      <ConversationSidebar
        selectedId={selectedId}
        onSelect={handleSelect}
        onNewConversation={() => void handleNewConversation()}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto rounded-2xl border border-border bg-card px-3 py-5 sm:px-6"
        >
          <QueryState
            isLoading={selectedId !== null && conversation.isPending}
            isError={conversation.isError}
            errorMessage="Couldn't load the conversation."
          >
            <div className="space-y-6 pb-4">
              <AssistantMessageList
                messages={conversation.data?.messages ?? []}
                actions={conversation.data?.actions ?? []}
                orders={conversation.data?.orders ?? []}
              />

              {sendMessage.isPending ? <ThinkingIndicator /> : null}
            </div>
          </QueryState>
        </div>

        <div className="pt-3">
          <AssistantComposer onSend={handleSend} isSending={sendMessage.isPending} />
        </div>
      </div>
    </div>
  );
}
