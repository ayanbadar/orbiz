import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { cn } from "cn";

type PageBackLinkProps = {
  to: string;
  children: ReactNode;
  className?: string;
};

/** In-page back control for detail/edit screens under the app shell. */
export function PageBackLink({ to, children, className }: PageBackLinkProps) {
  return (
    <Link
      to={to}
      className={cn(
        "inline-flex w-fit items-center gap-1.5 text-sm font-semibold text-body underline-offset-4 transition-colors hover:text-foreground hover:underline",
        className,
      )}
    >
      <ArrowLeft className="size-4 shrink-0" aria-hidden />
      {children}
    </Link>
  );
}
