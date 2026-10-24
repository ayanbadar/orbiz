import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

/** Toggle chip for list filters (products, orders, etc.). */
export function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Button
      type="button"
      size="sm"
      variant={active ? "default" : "outline"}
      className="rounded-lg"
      onClick={onClick}
    >
      {children}
    </Button>
  );
}
