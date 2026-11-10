import { FormattedTime } from "@/components/formatted-time";
import type { OrderEvent } from "@/features/orders/types";

export function OrderTimeline({ events }: { events: OrderEvent[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-muted-foreground">No activity yet.</p>;
  }

  return (
    <ol className="relative space-y-6 border-l-2 border-border pl-6">
      {events.map((event) => (
        <li key={event.id} className="relative text-sm">
          <span
            aria-hidden
            className="absolute top-1.5 -left-[1.95rem] size-3 rounded-full bg-primary ring-4 ring-background"
          />
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="font-semibold capitalize text-foreground">
              {event.event_type.replaceAll("_", " ")}
            </span>
            <FormattedTime
              value={event.created_at}
              variant="relative"
              className="text-xs text-muted-foreground"
            />
          </div>
          {event.message ? (
            <p className="mt-1 text-muted-foreground">{event.message}</p>
          ) : null}
          {event.from_value || event.to_value ? (
            <p className="mt-1 text-xs text-muted-foreground">
              {[event.from_value, event.to_value].filter(Boolean).join(" → ")}
            </p>
          ) : null}
        </li>
      ))}
    </ol>
  );
}
