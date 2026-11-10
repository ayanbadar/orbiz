export const ASSISTANT_QUERY_KEYS = {
  all: ["assistant"] as const,
  conversations: () => [...ASSISTANT_QUERY_KEYS.all, "conversations"] as const,
  conversation: (id: number) => [...ASSISTANT_QUERY_KEYS.all, "conversation", id] as const,
  actions: (status?: string) =>
    [...ASSISTANT_QUERY_KEYS.all, "actions", status ?? "all"] as const,
  digest: () => [...ASSISTANT_QUERY_KEYS.all, "digest"] as const,
  activity: () => [...ASSISTANT_QUERY_KEYS.all, "activity"] as const,
};
