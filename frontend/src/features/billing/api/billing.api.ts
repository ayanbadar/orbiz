import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { BILLING_QUERY_KEYS } from "@/features/billing/api/billing.keys";
import { BillingService } from "@/features/billing/api/billing.service";
import type { CheckoutRequest } from "@/features/billing/types";
import { STORE_QUERY_KEYS } from "@/features/stores/api/stores.keys";

export function useBilling() {
  return useQuery({
    queryKey: BILLING_QUERY_KEYS.status(),
    queryFn: () => BillingService.get(),
  });
}

/** A payment or cancellation can change the store status, so refresh both. */
function useRefreshAfterBillingChange() {
  const queryClient = useQueryClient();
  return async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: BILLING_QUERY_KEYS.all }),
      queryClient.invalidateQueries({ queryKey: STORE_QUERY_KEYS.all }),
    ]);
  };
}

export function useCheckout() {
  const refresh = useRefreshAfterBillingChange();
  return useMutation({
    mutationFn: (body: CheckoutRequest) => BillingService.checkout(body),
    onSuccess: refresh,
  });
}

export function useCancelSubscription() {
  const refresh = useRefreshAfterBillingChange();
  return useMutation({
    mutationFn: () => BillingService.cancel(),
    onSuccess: refresh,
  });
}
