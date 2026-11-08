export type InvitationKind = "store_admin" | "staff";

export type Invitation = {
  id: number;
  email: string;
  kind: InvitationKind;
  role_name: string | null;
  store_name: string;
  expires_at: string;
  created_at: string;
  /** Only returned in development, where the console is the only inbox. */
  invite_url: string | null;
};

export type InviteStaffRequest = { email: string; role_id: number };

export type InviteStoreAdminRequest = { email: string; store_name: string };

/** What the invitee sees before choosing a password. */
export type InvitationPreview = {
  email: string;
  kind: InvitationKind;
  store_name: string;
  role_name: string | null;
};

export type AcceptInvitationRequest = {
  first_name: string;
  last_name: string;
  password: string;
  password_confirm: string;
};
