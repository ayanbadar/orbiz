import type { ReactNode } from "react";
import { cn } from "cn";

import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

/** Detail-page metric tile (product stock, customer orders, …). */
export function StatTile({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: ReactNode;
  valueClassName?: string;
}) {
  return (
    <Card size="sm" className="rounded-[24px] ring-0">
      <CardHeader className="gap-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle className={cn("text-xl font-semibold", valueClassName)}>
          {value}
        </CardTitle>
      </CardHeader>
    </Card>
  );
}
