import { FormattedTime } from "@/components/formatted-time";
import type { PaymentRequestSummary } from "@/features/payments/types";

type Props = {
  request: PaymentRequestSummary | undefined;
};

/** One line on the latest payment email for the open request: sending, sent or failed. */
export function PaypalEmailStatus({ request }: Props) {
  if (!request || !request.last_email_status) return null;

  const to = request.recipient_email || "the buyer";

  if (request.last_email_status === "queued") {
    return (
      <p className="text-sm text-background/80" role="status">
        Sending email to {to}…
      </p>
    );
  }

  if (request.last_email_status === "failed") {
    return (
      <p className="text-sm text-destructive" role="alert">
        Email to {to} failed
        {request.last_email_error ? `: ${request.last_email_error}` : "."} Use
        Resend email to try again.
      </p>
    );
  }

  return (
    <p className="text-sm text-background/80">
      Email sent to {to}
      {request.last_emailed_at ? (
        <>
          {" · "}
          <FormattedTime value={request.last_emailed_at} variant="relative" />
        </>
      ) : null}
      .
    </p>
  );
}
