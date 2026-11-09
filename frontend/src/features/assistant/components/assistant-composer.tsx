import { ArrowUp } from "lucide-react";
import { useEffect, useImperativeHandle, useRef, useState, type FormEvent, type Ref } from "react";

import { Button } from "@/components/ui/button";
import { getErrorMessage } from "@/features/auth/utils/form-errors";

const MAX_HEIGHT_PX = 200;

export type AssistantComposerHandle = {
  /** Fills the composer with text and focuses it, without sending — used by suggestion chips. */
  fill: (text: string) => void;
};

type Props = {
  onSend: (message: string) => Promise<void> | void;
  isSending: boolean;
  handleRef?: Ref<AssistantComposerHandle>;
};

export function AssistantComposer({ onSend, isSending, handleRef }: Props) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useImperativeHandle(handleRef, () => ({
    fill: (text: string) => {
      setValue(text);
      textareaRef.current?.focus();
    },
  }));

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT_PX)}px`;
  }, [value]);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const message = value.trim();
    if (!message || isSending) {
      return;
    }
    setError("");
    // Clear (and the textarea disables via isSending) immediately — the message shows up in the
    // chat as soon as it's sent, it doesn't sit in the box while the reply is pending. Only put
    // it back if sending genuinely fails (a real network/offline error — the backend itself now
    // always closes a turn with a reply, even when the model call fails, so this path is rare).
    setValue("");
    try {
      await onSend(message);
    } catch (sendError) {
      setValue(message);
      setError(getErrorMessage(sendError, "Couldn't send that — try again."));
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto w-full max-w-3xl space-y-2">
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <div className="flex items-end gap-2 rounded-[24px] border border-border bg-card p-2 pl-4 focus-within:border-foreground/30">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Ask Orbiz AI, or paste a customer's message…"
          rows={1}
          disabled={isSending}
          aria-label="Message to Orbiz AI"
          className="max-h-[200px] flex-1 resize-none self-center bg-transparent py-2 text-sm leading-6 text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-50"
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void handleSubmit(event);
            }
          }}
        />
        <Button
          type="submit"
          size="icon"
          className="mb-0.5 shrink-0 rounded-full"
          disabled={isSending || !value.trim()}
          aria-label="Send message"
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>
    </form>
  );
}
