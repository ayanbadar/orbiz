import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export type ConfirmDialogOptions = {
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Use destructive for irreversible / cancel-order style actions. */
  variant?: "default" | "destructive";
};

type ConfirmDialogProps = ConfirmDialogOptions & {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
};

/** Shared confirmation modal built on shadcn AlertDialog. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="rounded-[24px]">
            {cancelLabel}
          </AlertDialogCancel>
          <AlertDialogAction
            variant={variant}
            className="rounded-[24px]"
            onClick={(event) => {
              event.preventDefault();
              onConfirm();
            }}
          >
            {confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

type PendingConfirm = ConfirmDialogOptions & {
  resolve: (confirmed: boolean) => void;
};

/**
 * Promise-based confirm for pages that previously used `window.confirm`.
 * Render `{dialog}` once near the page root.
 */
export function useConfirmDialog(): {
  confirm: (options: ConfirmDialogOptions) => Promise<boolean>;
  dialog: ReactNode;
} {
  const [pending, setPending] = useState<PendingConfirm | null>(null);
  const pendingRef = useRef<PendingConfirm | null>(null);
  const intentRef = useRef<"confirm" | "cancel" | null>(null);

  useEffect(() => {
    pendingRef.current = pending;
  }, [pending]);

  useEffect(() => {
    return () => {
      const current = pendingRef.current;
      if (current) {
        current.resolve(false);
        pendingRef.current = null;
      }
    };
  }, []);

  const settle = useCallback((confirmed: boolean) => {
    const current = pendingRef.current;
    if (!current) return;
    pendingRef.current = null;
    intentRef.current = null;
    setPending(null);
    current.resolve(confirmed);
  }, []);

  const confirm = useCallback(
    (options: ConfirmDialogOptions) => {
      return new Promise<boolean>((resolve) => {
        const previous = pendingRef.current;
        if (previous) {
          previous.resolve(false);
        }
        intentRef.current = null;
        const next = { ...options, resolve };
        pendingRef.current = next;
        setPending(next);
      });
    },
    [],
  );

  const dialog = (
    <ConfirmDialog
      open={pending != null}
      onOpenChange={(open) => {
        if (open) return;
        if (intentRef.current === "confirm") {
          settle(true);
          return;
        }
        settle(false);
      }}
      title={pending?.title ?? ""}
      description={pending?.description ?? ""}
      confirmLabel={pending?.confirmLabel}
      cancelLabel={pending?.cancelLabel}
      variant={pending?.variant}
      onConfirm={() => {
        intentRef.current = "confirm";
        settle(true);
      }}
    />
  );

  return { confirm, dialog };
}
