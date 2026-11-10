import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { CUSTOMER_QUERY_KEYS } from "@/features/customers/api/customers.keys";
import { DASHBOARD_QUERY_KEYS } from "@/features/dashboard/api/dashboard.keys";
import { ORDER_QUERY_KEYS } from "@/features/orders/api/orders.keys";
import { OrderService } from "@/features/orders/api/orders.service";
import { isPaymentEmailInFlight } from "@/features/orders/utils/paypal-order";
import { PRODUCT_QUERY_KEYS } from "@/features/products/api/products.keys";
import type {
  FulfilmentStatus,
  Order,
  OrderConfirmRequest,
  OrderCreateRequest,
  OrderListParams,
  OrderUpdateRequest,
} from "@/features/orders/types";

async function invalidateOrders(
  queryClient: ReturnType<typeof useQueryClient>,
) {
  await queryClient.invalidateQueries({ queryKey: ORDER_QUERY_KEYS.all });
  await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
  // Customer order counts / last-order dates move with order writes.
  await queryClient.invalidateQueries({ queryKey: CUSTOMER_QUERY_KEYS.all });
  // Dashboard totals are built from orders.
  await queryClient.invalidateQueries({ queryKey: DASHBOARD_QUERY_KEYS.all });
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

export function useOrder(id: number, options?: { initialData?: Order }) {
  return useQuery({
    queryKey: ORDER_QUERY_KEYS.detail(id),
    queryFn: () => OrderService.get(id),
    enabled: Number.isFinite(id) && id > 0,
    initialData: options?.initialData,
    // The email goes out on a worker after the request returns; follow it to sent/failed.
    refetchInterval: (query) =>
      isPaymentEmailInFlight(query.state.data) ? 2000 : false,
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
    mutationFn: (body: OrderConfirmRequest) => OrderService.confirm(id, body),
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
