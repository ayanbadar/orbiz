import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { QueryState } from "@/components/query-state";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import {
  useAdjustStock,
  useProduct,
  useProductAdjustments,
} from "@/features/products/api/products.api";

const adjustSchema = z.object({
  delta: z
    .number()
    .int()
    .refine((v) => v !== 0, "Delta must be non-zero."),
  reason: z.string().trim().min(1, "Enter a reason."),
});

type AdjustValues = z.infer<typeof adjustSchema>;

export function ProductDetailPage() {
  const { id } = useParams();
  const productId = Number(id);
  const productQuery = useProduct(productId);
  const adjustmentsQuery = useProductAdjustments(productId);
  const adjustStock = useAdjustStock(productId);
  const form = useForm<AdjustValues>({
    resolver: zodResolver(adjustSchema),
    defaultValues: { delta: -1, reason: "" },
  });

  const onAdjust = form.handleSubmit(async (values) => {
    try {
      await adjustStock.mutateAsync(values);
      toast.success("Stock updated.");
      form.reset({ delta: -1, reason: "" });
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Adjust failed."));
      }
    }
  });

  const product = productQuery.data;

  return (
    <div className="space-y-6">
      <Link to={ROUTES.products.root()} className="text-sm font-semibold underline-offset-4 hover:underline">
        ← Products
      </Link>

      <QueryState
        isLoading={productQuery.isLoading}
        isError={productQuery.isError}
        errorMessage="Product not found."
        isEmpty={!product}
        emptyMessage="Product not found."
      >
        {product ? (
          <>
            <header className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-2">
                <h1 className="text-[32px] font-semibold tracking-tight text-foreground">
                  {product.name}
                </h1>
                <p className="text-body">
                  {product.sku} · {product.currency} {product.price}
                </p>
                {product.channel3_product_id ? (
                  <p className="text-xs text-muted-foreground">
                    Imported from Channel3 ({product.channel3_product_id})
                  </p>
                ) : null}
              </div>
              <Button asChild variant="secondary" className="rounded-[24px]">
                <Link to={ROUTES.products.edit(product.id)}>Edit</Link>
              </Button>
            </header>

            <div className="grid gap-4 sm:grid-cols-3">
              <Stat label="Stock" value={String(product.stock_quantity)} />
              <Stat label="Low-stock at" value={String(product.low_stock_threshold)} />
              <Stat
                label="Status"
                value={
                  product.is_low_stock
                    ? "Low stock"
                    : product.is_active
                      ? "Active"
                      : "Inactive"
                }
              />
            </div>

            <form
              onSubmit={onAdjust}
              className="space-y-3 rounded-[24px] bg-card p-6 sm:max-w-md"
            >
              <h2 className="text-lg font-semibold">Adjust stock</h2>
              <div className="space-y-2">
                <Label htmlFor="delta">Delta</Label>
                <Input
                  id="delta"
                  type="number"
                  {...form.register("delta", { valueAsNumber: true })}
                />
                {form.formState.errors.delta ? (
                  <p className="text-sm text-destructive" role="alert">
                    {form.formState.errors.delta.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="reason">Reason</Label>
                <Input id="reason" {...form.register("reason")} />
                {form.formState.errors.reason ? (
                  <p className="text-sm text-destructive" role="alert">
                    {form.formState.errors.reason.message}
                  </p>
                ) : null}
              </div>
              <Button
                type="submit"
                disabled={adjustStock.isPending}
                className="rounded-[24px] font-semibold"
              >
                {adjustStock.isPending ? "Saving…" : "Apply adjustment"}
              </Button>
            </form>

            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Recent adjustments</h2>
              <QueryState
                isLoading={adjustmentsQuery.isLoading}
                isEmpty={!adjustmentsQuery.data?.length}
                emptyMessage="No adjustments yet."
              >
                <ul className="space-y-2">
                  {(adjustmentsQuery.data ?? []).map((row) => (
                    <li
                      key={row.id}
                      className="rounded-[16px] bg-card px-4 py-3 text-sm"
                    >
                      <span className="font-semibold">
                        {row.delta > 0 ? `+${row.delta}` : row.delta}
                      </span>{" "}
                      → {row.quantity_after} · {row.reason}
                    </li>
                  ))}
                </ul>
              </QueryState>
            </section>
          </>
        ) : null}
      </QueryState>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[24px] bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold text-foreground">{value}</p>
    </div>
  );
}
