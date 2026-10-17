import { parseAsString, parseAsStringEnum, useQueryStates } from "nuqs";

import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useGetAllDemo } from "@/features/demo/api/demo.api";
import { DemoForm } from "@/features/demo/components/demo-form";

const categoryValues = ["all", "furniture", "decor", "lighting"] as const;

export function DemoPage() {
  const [filters, setFilters] = useQueryStates({
    search: parseAsString.withDefault(""),
    category: parseAsStringEnum([...categoryValues]).withDefault("all"),
  });

  const { data, isLoading, isError, error, refetch, isFetching } =
    useGetAllDemo({
      search: filters.search || undefined,
      category: filters.category,
    });

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-8 p-6">
      <header className="space-y-2">
        <p className="text-sm font-medium text-muted-foreground">
          Meraki Interiors
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Frontend foundation
        </h1>
        <p className="text-muted-foreground">
          Routing, TanStack Query, shadcn/ui, forms, and URL state wired
          together.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Catalog filters</CardTitle>
          <CardDescription>
            Filter state lives in the URL via nuqs.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="search">Search</Label>
              <Input
                id="search"
                value={filters.search}
                placeholder="Search items…"
                onChange={(event) => {
                  void setFilters({ search: event.target.value });
                }}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="category">Category</Label>
              <div className="flex flex-wrap gap-2" id="category">
                {categoryValues.map((category) => (
                  <Button
                    key={category}
                    type="button"
                    size="sm"
                    variant={
                      filters.category === category ? "default" : "outline"
                    }
                    onClick={() => {
                      void setFilters({ category });
                    }}
                  >
                    {category}
                  </Button>
                ))}
              </div>
            </div>
          </div>

          <QueryState
            isLoading={isLoading}
            isError={isError}
            isEmpty={!isLoading && !isError && (data?.length ?? 0) === 0}
            errorMessage={
              error instanceof Error ? error.message : "Failed to load items."
            }
            emptyMessage="No items match these filters."
            onRetry={() => {
              void refetch();
            }}
          >
            <ul className="divide-y divide-border rounded-lg border border-border">
              {data?.map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between px-4 py-3 text-sm"
                >
                  <span className="font-medium text-foreground">
                    {item.name}
                  </span>
                  <span className="text-muted-foreground">{item.category}</span>
                </li>
              ))}
            </ul>
            {isFetching && !isLoading ? (
              <p className="text-xs text-muted-foreground">Updating…</p>
            ) : null}
          </QueryState>
        </CardContent>
      </Card>

      <DemoForm />
    </div>
  );
}
