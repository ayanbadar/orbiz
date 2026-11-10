import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { ORDER_QUERY_KEYS } from "@/features/orders/api/orders.keys";
import { PAYMENT_QUERY_KEYS } from "@/features/payments/api/payments.keys";
import { PaymentService } from "@/features/payments/api/payments.service";
import type {
  EmailLinkRequest,
  InvoiceRequest,
  RefundRequest,
} from "@/features/payments/types";

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

export function useRefundPaypalOrder(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: RefundRequest) =>
      PaymentService.refundOrder(orderId, body),
    onSuccess: async () => {
      await invalidatePaymentQueries(queryClient, orderId);
    },
  });
}

export function useSendPaypalInvoice(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: InvoiceRequest) =>
      PaymentService.sendInvoice(orderId, body),
    onSuccess: async () => {
      await invalidatePaymentQueries(queryClient, orderId);
    },
  });
}

export function useEmailPaymentLink(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: EmailLinkRequest) =>
      PaymentService.emailLink(orderId, body),
    onSuccess: async () => {
      await invalidatePaymentQueries(queryClient, orderId);
    },
  });
}

export function useCancelPaypalInvoice(orderId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => PaymentService.cancelInvoice(orderId),
    onSuccess: async () => {
      await invalidatePaymentQueries(queryClient, orderId);
    },
  });
}
