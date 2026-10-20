import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";
import { cn } from "cn";

import { FormField } from "@/components/form-field";
import { PageBackLink } from "@/components/page-back-link";
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
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import {
  useActivateProduct,
  useAdjustStock,
  useDeactivateProduct,
  useProduct,
  useProductAdjustments,
} from "@/features/products/api/products.api";
import { ProductImage } from "@/features/products/components/product-image";
import { ProductAvailabilityBadge } from "@/features/products/components/product-availability-badge";

const adjustSchema = z.object({
  delta: z
    .number()
    .int()
    .refine((v) => v !== 0, "Delta must be non-zero."),
  reason: z.string().trim().min(1, "Enter a reason."),
});

type AdjustValues = z.infer<typeof adjustSchema>;

const inputClassName =
  "h-12 rounded-xl border-foreground bg-card px-4 text-base";

export function ProductDetailPage() {
  const { id } = useParams();
  const productId = Number(id);
  const productQuery = useProduct(productId);
  const adjustmentsQuery = useProductAdjustments(productId);
  const adjustStock = useAdjustStock(productId);
  const deactivateProduct = useDeactivateProduct(productId);
  const activateProduct = useActivateProduct(productId);
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

  const onDeactivate = async () => {
    if (
      !window.confirm(
        "Deactivate this product? It will stay in your catalog as inactive.",
      )
    ) {
      return;
    }
    try {
      await deactivateProduct.mutateAsync();
      toast.success("Product deactivated.");
      await productQuery.refetch();
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not deactivate product."));
    }
  };

  const onActivate = async () => {
    try {
      await activateProduct.mutateAsync();
      toast.success("Product activated.");
      await productQuery.refetch();
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not activate product."));
    }
  };

  const product = productQuery.data;

  return (
    <div className="space-y-6">
      <PageBackLink to={ROUTES.products.root()}>Products</PageBackLink>

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
              <div className="flex min-w-0 flex-1 items-start gap-4">
                <ProductImage
                  src={product.image_url}
                  alt={product.name}
                  size="lg"
                />
                <div className="min-w-0 space-y-1.5">
                  <h1 className="text-[28px] font-semibold tracking-tight text-foreground sm:text-[32px]">
                    {product.name}
                  </h1>
                  <p className="text-body">
                    <span className="font-mono text-sm">{product.sku}</span>
                    <span className="mx-1.5 text-muted-foreground">·</span>
                    <span className="tabular-nums">
                      {product.currency} {product.price}
                    </span>
                  </p>
                  {product.channel3_product_id ? (
                    <p className="text-xs text-muted-foreground">
                      Channel3 ·{" "}
                      <span className="font-mono">
                        {product.channel3_product_id}
                      </span>
                    </p>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  asChild
                  variant="secondary"
                  className="h-12 rounded-[24px] px-6 text-base font-semibold"
                >
                  <Link to={ROUTES.products.edit(product.id)}>Edit</Link>
                </Button>
                {product.is_active ? (
                  <Button
                    type="button"
                    variant="outline"
                    className="h-12 rounded-[24px] px-6 text-base font-semibold"
                    disabled={deactivateProduct.isPending}
                    onClick={() => void onDeactivate()}
                  >
                    {deactivateProduct.isPending
                      ? "Deactivating…"
                      : "Deactivate"}
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="outline"
                    className="h-12 rounded-[24px] px-6 text-base font-semibold"
                    disabled={activateProduct.isPending}
                    onClick={() => void onActivate()}
                  >
                    {activateProduct.isPending ? "Activating…" : "Activate"}
                  </Button>
                )}
              </div>
            </header>

            <div className="grid gap-3 sm:grid-cols-3">
              <Stat
                label="Stock"
                value={String(product.stock_quantity)}
                valueClassName="tabular-nums"
              />
              <Stat
                label="Low-stock at"
                value={String(product.low_stock_threshold)}
                valueClassName="tabular-nums"
              />
              <Card size="sm" className="rounded-[24px] ring-0">
                <CardHeader className="gap-2">
                  <CardDescription>Status</CardDescription>
                  <ProductAvailabilityBadge product={product} />
                </CardHeader>
              </Card>
            </div>

            <Card className="max-w-md rounded-[24px] ring-0">
              <CardHeader>
                <CardTitle>Adjust stock</CardTitle>
                <CardDescription>
                  Positive adds inventory; negative removes it. Stock cannot go
                  below zero.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={onAdjust} className="space-y-3">
                  <FormField
                    id="adjust-delta"
                    label="Delta"
                    error={form.formState.errors.delta?.message}
                  >
                    <Input
                      type="number"
                      className={inputClassName}
                      {...form.register("delta", { valueAsNumber: true })}
                    />
                  </FormField>
                  <FormField
                    id="adjust-reason"
                    label="Reason"
                    error={form.formState.errors.reason?.message}
                  >
                    <Input
                      className={inputClassName}
                      placeholder="e.g. Received shipment"
                      {...form.register("reason")}
                    />
                  </FormField>
                  <Button
                    type="submit"
                    disabled={adjustStock.isPending}
                    className="h-12 rounded-[24px] px-6 text-base font-semibold"
                  >
                    {adjustStock.isPending ? "Saving…" : "Apply adjustment"}
                  </Button>
                </form>
              </CardContent>
            </Card>

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
                      className="rounded-[24px] bg-card px-4 py-3 text-sm"
                    >
                      <span className="font-semibold tabular-nums">
                        {row.delta > 0 ? `+${row.delta}` : row.delta}
                      </span>{" "}
                      <span className="text-muted-foreground">→</span>{" "}
                      <span className="tabular-nums">{row.quantity_after}</span>
                      <span className="text-muted-foreground"> · </span>
                      {row.reason}
                    </li>
                  ))}
                </ul>
              </QueryState>
            </section>

            <Card className="rounded-[24px] ring-0">
              <CardHeader>
                <CardTitle>Recent order usage</CardTitle>
                <CardDescription>
                  Available after Orders (§2.4). Sales will show here once order
                  lines reference this product.
                </CardDescription>
              </CardHeader>
            </Card>
          </>
        ) : null}
      </QueryState>
    </div>
  );
}

/** Detail metric tile — built on shared Card so list/detail stay consistent. */
function Stat({
  label,
  value,
  valueClassName,
}: {
  label: string;
  value: string;
  valueClassName?: string;
}) {
  return (
    <Card size="sm" className="rounded-[24px] ring-0">
      <CardHeader className="gap-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle className={cn("text-xl font-semibold", valueClassName)}>
          {value}
        </CardTitle>
      </CardHeader>
    </Card>
  );
}
