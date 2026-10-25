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
} from "@/features/customers/types";

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

export function useCreateCustomer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CustomerCreateRequest) => CustomerService.create(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: CUSTOMER_QUERY_KEYS.all });
    },
  });
}
