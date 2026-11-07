import type { UseQueryResult } from "@tanstack/react-query";

import { DEFAULT_PAGE_SIZE, getPageCount } from "@/components/pagination";
import type { Paginated } from "@/lib/api/types";

type StoreReadiness = {
  storeReady: boolean;
  isStoreLoading: boolean;
};

/**
 * Display state for a paginated, store-scoped list page (feeds ResourceListChrome).
 * `showEmpty` waits for real data — not the previous page kept as placeholder.
 */
export function getResourceListState<T>(
  listQuery: UseQueryResult<Paginated<T>>,
  { storeReady, isStoreLoading }: StoreReadiness,
  pageSize: number = DEFAULT_PAGE_SIZE,
) {
  const rows = listQuery.data?.results ?? [];
  const totalCount = listQuery.data?.count ?? 0;
  const showInitialLoading =
    isStoreLoading || (listQuery.isLoading && !listQuery.data);
  return {
    rows,
    totalCount,
    showPagination: getPageCount(totalCount, pageSize) > 1,
    showInitialLoading,
    isRefetching: listQuery.isFetching && !showInitialLoading,
    showEmpty:
      !showInitialLoading &&
      storeReady &&
      rows.length === 0 &&
      !listQuery.isPlaceholderData,
  };
}
