import { Sparkles } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { QueryState } from "@/components/query-state";
import {
  useAssistantConversation,
  useSendAssistantMessage,
} from "@/features/assistant/api/assistant.api";
import {
  AssistantComposer,
  type AssistantComposerHandle,
} from "@/features/assistant/components/assistant-composer";
import { AssistantMessageList } from "@/features/assistant/components/assistant-message-list";
import { AssistantSuggestionBanner } from "@/features/assistant/components/assistant-suggestion-banner";

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

type Props = {
  conversationId: number | null;
  onConversationChange: (id: number) => void;
};

/**
 * The message history + composer, filling whatever height its parent gives it. No sidebar, no
 * page header — AssistantPage owns conversation selection and renders the shared sidebar once
 * alongside this; "Ask Orbiz AI" only ever appears as the message list's own empty state, the
 * same way a fresh ChatGPT chat has no separate page title either.
 */
export function ChatPanel({ conversationId, onConversationChange }: Props) {
  const conversation = useAssistantConversation(conversationId);
  const sendMessage = useSendAssistantMessage();
  const scrollRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<AssistantComposerHandle>(null);
  // Shown immediately on submit, before the round trip — the sent message appears in the chat
  // right away instead of waiting for the full turn to resolve. Cleared once the real message
  // comes back from the refetch (success) or the send fails (the composer restores it instead).
  const [pendingMessage, setPendingMessage] = useState<string | null>(null);

  const handleSend = async (message: string) => {
    setPendingMessage(message);
    try {
      const result = await sendMessage.mutateAsync({
        message,
        conversationId: conversationId ?? undefined,
      });
      onConversationChange(result.conversation_id);
    } finally {
      setPendingMessage(null);
    }
  };

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [
    conversation.data?.messages.length,
    conversation.data?.actions.length,
    conversation.data?.orders.length,
    pendingMessage,
    sendMessage.isPending,
  ]);

  return (
    <div className="flex h-full min-h-0 min-w-0 flex-1 flex-col bg-card">
      <div className="flex shrink-0 items-center gap-2.5 border-b border-border px-4 py-3 sm:px-8">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-muted text-foreground">
          <Sparkles className="size-3.5" aria-hidden />
        </span>
        <span className="font-heading text-sm font-semibold text-foreground">Orbiz AI</span>
      </div>

      <div ref={scrollRef} className="scrollbar-slim min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-8">
        <QueryState
          isLoading={conversationId !== null && conversation.isPending}
          isError={conversation.isError}
          errorMessage="Couldn't load the conversation."
        >
          <div className="mx-auto w-full max-w-3xl space-y-6 pb-4">
            <AssistantMessageList
              messages={conversation.data?.messages ?? []}
              actions={conversation.data?.actions ?? []}
              orders={conversation.data?.orders ?? []}
            />

            {pendingMessage ? (
              <div className="flex justify-end">
                <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-foreground px-4 py-2.5 text-sm leading-6 text-card opacity-70">
                  {pendingMessage}
                </p>
              </div>
            ) : null}

            {sendMessage.isPending ? <ThinkingIndicator /> : null}
          </div>
        </QueryState>
      </div>

      <div className="shrink-0 space-y-2 border-t border-border px-4 py-3 sm:px-8">
        {!conversation.data?.messages.length ? (
          <AssistantSuggestionBanner onPick={(prompt) => composerRef.current?.fill(prompt)} />
        ) : null}
        <AssistantComposer onSend={handleSend} isSending={sendMessage.isPending} handleRef={composerRef} />
      </div>
    </div>
  );
}
