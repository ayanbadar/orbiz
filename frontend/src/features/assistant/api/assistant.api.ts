import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ASSISTANT_QUERY_KEYS } from "@/features/assistant/api/assistant.keys";
import { AssistantService } from "@/features/assistant/api/assistant.service";
import type { ActionConfirmOverrides } from "@/features/assistant/types";
import { ORDER_QUERY_KEYS } from "@/features/orders/api/orders.keys";
import { PRODUCT_QUERY_KEYS } from "@/features/products/api/products.keys";

async function invalidateAssistant(queryClient: ReturnType<typeof useQueryClient>) {
  await queryClient.invalidateQueries({ queryKey: ASSISTANT_QUERY_KEYS.all });
}

export function useAssistantConversations() {
  return useQuery({
    queryKey: ASSISTANT_QUERY_KEYS.conversations(),
    queryFn: () => AssistantService.listConversations(),
  });
}

export function useAssistantConversation(id: number | null) {
  return useQuery({
    queryKey: ASSISTANT_QUERY_KEYS.conversation(id ?? 0),
    queryFn: () => AssistantService.getConversation(id as number),
    enabled: id !== null,
  });
}

export function useCreateAssistantConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => AssistantService.createConversation(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ASSISTANT_QUERY_KEYS.conversations() });
    },
  });
}

export function useDeleteAssistantConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => AssistantService.deleteConversation(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ASSISTANT_QUERY_KEYS.conversations() });
    },
  });
}

export function useSendAssistantMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ message, conversationId }: { message: string; conversationId?: number }) =>
      AssistantService.sendMessage(message, conversationId),
    onSuccess: async () => {
      await invalidateAssistant(queryClient);
      await queryClient.invalidateQueries({ queryKey: ORDER_QUERY_KEYS.all });
      await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
    },
  });
}

export function usePendingAssistantActions() {
  return useQuery({
    queryKey: ASSISTANT_QUERY_KEYS.actions("pending"),
    queryFn: () => AssistantService.listActions("pending"),
  });
}

export function useConfirmAssistantAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, overrides }: { id: number; overrides?: ActionConfirmOverrides }) =>
      AssistantService.confirmAction(id, overrides),
    onSuccess: async () => {
      await invalidateAssistant(queryClient);
      await queryClient.invalidateQueries({ queryKey: ORDER_QUERY_KEYS.all });
      await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
    },
  });
}

export function useRejectAssistantAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => AssistantService.rejectAction(id),
    onSuccess: async () => {
      await invalidateAssistant(queryClient);
    },
  });
}

export function useAssistantDigest() {
  return useQuery({
    queryKey: ASSISTANT_QUERY_KEYS.digest(),
    queryFn: () => AssistantService.getDigest(),
  });
}

export function useAssistantActivity() {
  return useQuery({
    queryKey: ASSISTANT_QUERY_KEYS.activity(),
    queryFn: () => AssistantService.listActivity(),
  });
}
