import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PRODUCT_QUERY_KEYS } from "@/features/products/api/products.keys";
import { ProductService } from "@/features/products/api/products.service";
import type {
  ProductCreateRequest,
  ProductListParams,
  ProductUpdateRequest,
} from "@/features/products/types";

export function useProducts(
  params: ProductListParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: PRODUCT_QUERY_KEYS.list(params),
    queryFn: () => ProductService.list(params),
    enabled: options?.enabled ?? true,
  });
}

export function useProduct(id: number) {
  return useQuery({
    queryKey: PRODUCT_QUERY_KEYS.detail(id),
    queryFn: () => ProductService.get(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useProductAdjustments(id: number) {
  return useQuery({
    queryKey: PRODUCT_QUERY_KEYS.adjustments(id),
    queryFn: () => ProductService.adjustments(id),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useCreateProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ProductCreateRequest) => ProductService.create(body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
    },
  });
}

export function useUpdateProduct(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ProductUpdateRequest) => ProductService.update(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
    },
  });
}

export function useAdjustStock(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { delta: number; reason: string }) =>
      ProductService.adjustStock(id, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
    },
  });
}

export function useChannel3Search() {
  return useMutation({
    mutationFn: (query: string) => ProductService.channel3Search(query),
  });
}

export function useImportFromChannel3() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ProductService.importFromChannel3,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PRODUCT_QUERY_KEYS.all });
    },
  });
}
