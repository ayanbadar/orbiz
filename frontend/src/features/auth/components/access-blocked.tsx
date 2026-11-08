import { Ban, CreditCard, ShieldAlert, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { ROUTES } from "@/constants/routes";

export type AccessBlockedKind = "suspended" | "unpaid" | "forbidden";

const COPY: Record<
  AccessBlockedKind,
  { icon: LucideIcon; title: string; body: string }
> = {
  suspended: {
    icon: Ban,
    title: "This store is suspended",
    body: "Access has been paused by the platform administrator. Contact them to restore it.",
  },
  unpaid: {
    icon: CreditCard,
    title: "This store's plan is unpaid",
    body: "Ask your store admin to renew the $5/month plan. You'll regain access as soon as it's paid.",
  },
  forbidden: {
    icon: ShieldAlert,
    title: "You don't have access to this page",
    body: "Your role doesn't include this area. Ask your store admin if you need it.",
  },
};

/** Full-width notice shown instead of a page the user can't use right now. */
export function AccessBlocked({ kind }: { kind: AccessBlockedKind }) {
  const { icon: Icon, title, body } = COPY[kind];
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-[24px] bg-card px-6 py-12 text-center">
      <span className="flex size-14 items-center justify-center rounded-full bg-muted">
        <Icon className="size-6 text-foreground" aria-hidden />
      </span>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="text-body">{body}</p>
      <Button asChild variant="secondary" className="rounded-[24px]">
        <Link to={ROUTES.account()}>Go to my account</Link>
      </Button>
    </div>
  );
}
