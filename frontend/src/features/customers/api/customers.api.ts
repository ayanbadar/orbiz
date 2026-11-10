import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { CUSTOMER_QUERY_KEYS } from "@/features/customers/api/customers.keys";
import { CustomerService } from "@/features/customers/api/customers.service";
import type {
  CustomerCreateRequest,
  CustomerListParams,
  CustomerUpdateRequest,
} from "@/features/customers/types";
import { ORDER_QUERY_KEYS } from "@/features/orders/api/orders.keys";

export function useCustomers(
  params: CustomerListParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: CUSTOMER_QUERY_KEYS.list(params),
    queryFn: () => CustomerService.list(params),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  });
}

export function useCustomer(id: number) {
  return useQuery({
    queryKey: CUSTOMER_QUERY_KEYS.detail(id),
    queryFn: () => CustomerService.get(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CustomerCreateRequest) => CustomerService.create(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CUSTOMER_QUERY_KEYS.all });
    },
  });
}

export function useUpdateCustomer(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CustomerUpdateRequest) => CustomerService.update(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CUSTOMER_QUERY_KEYS.all });
      // Orders embed the customer (name/email on detail, PayPal invoice prefill).
      await queryClient.invalidateQueries({ queryKey: ORDER_QUERY_KEYS.all });
    },
  });
}
