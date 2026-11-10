/** DRF PageNumberPagination envelope — reuse across feature services. */
export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
