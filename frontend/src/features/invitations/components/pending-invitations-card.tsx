import { Mail } from "lucide-react";

import { FormattedTime } from "@/components/formatted-time";
import { STATUS_TONES, StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";
import type { Invitation } from "@/features/invitations/types";

/** Shared list of invites that haven't been accepted yet (team page and platform admin). */
export function PendingInvitationsCard({
  title,
  invitations,
  badge,
  onRevoke,
}: {
  title: string;
  invitations: Invitation[];
  /** Short label shown next to each invite, e.g. the role or the store name. */
  badge: (invitation: Invitation) => string;
  /** Omit to hide the revoke button (the user may not revoke). */
  onRevoke?: (invitation: Invitation) => void;
}) {
  if (invitations.length === 0) return null;
  return (
    <Card className="rounded-[24px] bg-card py-0 ring-0">
      <CardHeader className="px-6 pt-6">
        <CardTitle className="flex items-center gap-2 text-xl font-semibold">
          <Mail className="size-5" aria-hidden /> {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="px-2 pb-4">
        <Table>
          <TableBody>
            {invitations.map((invitation) => (
              <TableRow key={invitation.id}>
                <TableCell>
                  <p className="font-semibold">{invitation.email}</p>
                  <p className="text-xs text-muted-foreground">
                    Expires{" "}
                    <FormattedTime
                      value={invitation.expires_at}
                      variant="date"
                    />
                  </p>
                </TableCell>
                <TableCell>
                  <StatusBadge toneClassName={STATUS_TONES.warning}>
                    {badge(invitation)}
                  </StatusBadge>
                </TableCell>
                <TableCell className="text-right">
                  {onRevoke ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="rounded-lg"
                      onClick={() => onRevoke(invitation)}
                    >
                      Revoke
                    </Button>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
