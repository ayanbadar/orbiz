import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { ORDER_QUERY_KEYS } from "@/features/orders/api/orders.keys";
import { PAYMENT_QUERY_KEYS } from "@/features/payments/api/payments.keys";
import { PaymentService } from "@/features/payments/api/payments.service";

async function invalidatePaymentQueries(
  queryClient: ReturnType<typeof useQueryClient>,
  orderId: number,
) {
  await queryClient.invalidateQueries({ queryKey: ORDER_QUERY_KEYS.all });
  await queryClient.invalidateQueries({
    queryKey: PAYMENT_QUERY_KEYS.checkout(orderId),
  });
}

export function usePaypalCheckout(
  orderId: number,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: PAYMENT_QUERY_KEYS.checkout(orderId),
    queryFn: () => PaymentService.getCheckout(orderId),
    enabled: (options?.enabled ?? true) && Number.isFinite(orderId) && orderId > 0,
  });
}

export function useCreatePaypalCheckout(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => PaymentService.createCheckout(orderId),
    onSuccess: async () => {
      await invalidatePaymentQueries(queryClient, orderId);
    },
  });
}

export function useCapturePaypalCheckout(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => PaymentService.captureCheckout(orderId),
    onSuccess: async () => {
      await invalidatePaymentQueries(queryClient, orderId);
    },
  });
}
