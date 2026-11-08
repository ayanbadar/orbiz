export const INVITATION_QUERY_KEYS = {
  all: ["invitations"] as const,
  staff: () => [...INVITATION_QUERY_KEYS.all, "staff"] as const,
  storeAdmins: () => [...INVITATION_QUERY_KEYS.all, "store-admins"] as const,
  preview: (token: string | null) =>
    [...INVITATION_QUERY_KEYS.all, "preview", token] as const,
};
