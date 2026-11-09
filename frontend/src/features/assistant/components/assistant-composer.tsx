import { ArrowUp } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";

const MAX_HEIGHT_PX = 200;

type Props = {
  onSend: (message: string) => Promise<void> | void;
  isSending: boolean;
};

export function AssistantComposer({ onSend, isSending }: Props) {
  const [value, setValue] = useState("");
  const [error, setError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
    try {
      await onSend(message);
      setValue("");
    } catch {
      // Leave the seller's typed message in place so they don't lose it.
      setError("Couldn't send that — try again.");
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
          placeholder="Paste a customer's message…"
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
