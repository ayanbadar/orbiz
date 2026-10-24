import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { ORDER_QUERY_KEYS } from "@/features/orders/api/orders.keys";
import { OrderService } from "@/features/orders/api/orders.service";
import { PRODUCT_QUERY_KEYS } from "@/features/products/api/products.keys";
import type {
  FulfilmentStatus,
  OrderCreateRequest,
  OrderListParams,
  OrderUpdateRequest,
} from "@/features/orders/types";

async function invalidateOrders(queryClient: ReturnType<typeof useQueryClient>) {
  await queryClient.invalidateQueries({ queryKey: ORDER_QUERY_KEYS.all });
  await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
}

export function useOrders(
  params: OrderListParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ORDER_QUERY_KEYS.list(params),
    queryFn: () => OrderService.list(params),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  });
}

export function useOrder(id: number) {
  return useQuery({
    queryKey: ORDER_QUERY_KEYS.detail(id),
    queryFn: () => OrderService.get(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: OrderCreateRequest) => OrderService.create(body),
    onSuccess: async () => {
      await invalidateOrders(queryClient);
    },
  });
}

export function useUpdateOrder(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: OrderUpdateRequest) => OrderService.update(id, body),
    onSuccess: async () => {
      await invalidateOrders(queryClient);
    },
  });
}

export function useConfirmOrder(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => OrderService.confirm(id),
    onSuccess: async () => {
      await invalidateOrders(queryClient);
    },
  });
}

export function useCancelOrder(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => OrderService.cancel(id),
    onSuccess: async () => {
      await invalidateOrders(queryClient);
    },
  });
}

export function useTransitionOrder(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (fulfilment_status: FulfilmentStatus) =>
      OrderService.transition(id, fulfilment_status),
    onSuccess: async () => {
      await invalidateOrders(queryClient);
    },
  });
}

export function useMarkOrderPaid(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => OrderService.markPaid(id),
    onSuccess: async () => {
      await invalidateOrders(queryClient);
    },
  });
}

export function useAbandonPayment(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => OrderService.abandonPayment(id),
    onSuccess: async () => {
      await invalidateOrders(queryClient);
    },
  });
}
