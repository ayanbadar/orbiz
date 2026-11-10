import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowDown,
  ArrowUp,
  Boxes,
  ChevronRight,
  History,
  Pencil,
  ShoppingBag,
  Tag,
} from "lucide-react";
import type { ReactNode } from "react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useParams } from "react-router-dom";
import { z } from "zod";

import { useConfirmDialog } from "@/components/confirm-dialog";
import { FormField } from "@/components/form-field";
import { FormattedTime } from "@/components/formatted-time";
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
  useProductOrderUsage,
} from "@/features/products/api/products.api";
import { EditProductDialog } from "@/features/products/components/edit-product-dialog";
import { ProductImage } from "@/features/products/components/product-image";
import { ProductAvailabilityBadge } from "@/features/products/components/product-availability-badge";
import { getFulfilmentLabel } from "@/features/orders/utils/order-status";
import { Can } from "@/features/auth/components/can";
import { cn } from "cn";

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

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1 px-6 py-4">
      <dt className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        {label}
      </dt>
      <dd>{children}</dd>
    </div>
  );
}

export function ProductDetailPage() {
  const { id } = useParams();
  const productId = Number(id);
  const { confirm, dialog: confirmDialog } = useConfirmDialog();
  const [editOpen, setEditOpen] = useState(false);
  const productQuery = useProduct(productId);
  const adjustmentsQuery = useProductAdjustments(productId);
  const orderUsageQuery = useProductOrderUsage(productId);
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
    const ok = await confirm({
      title: "Deactivate this product?",
      description: "It will stay in your catalog as inactive.",
      confirmLabel: "Deactivate",
      variant: "destructive",
    });
    if (!ok) return;
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
      {confirmDialog}
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
            <EditProductDialog
              product={product}
              open={editOpen}
              onClose={() => setEditOpen(false)}
            />
            <header className="overflow-hidden rounded-[24px] bg-card ring-1 ring-border">
              <div className="flex flex-wrap items-start justify-between gap-4 p-6">
                <div className="flex min-w-0 flex-1 items-start gap-5">
                  <ProductImage
                    src={product.image_url}
                    alt={product.name}
                    size="lg"
                  />
                  <div className="min-w-0 space-y-3">
                    <div className="flex flex-wrap items-center gap-3">
                      <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-foreground sm:text-[32px]">
                        {product.name}
                      </h1>
                      <ProductAvailabilityBadge product={product} />
                    </div>
                    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-body">
                      <span className="inline-flex items-center gap-1.5 rounded-md bg-muted px-2 py-1 font-mono text-xs">
                        <Tag className="size-3.5" aria-hidden />
                        {product.sku}
                      </span>
                      {product.channel3_product_id ? (
                        <span className="text-xs text-muted-foreground">
                          Channel3 ·{" "}
                          <span className="font-mono">
                            {product.channel3_product_id}
                          </span>
                        </span>
                      ) : null}
                    </p>
                    {product.description ? (
                      <p className="max-w-prose text-sm whitespace-pre-wrap text-muted-foreground">
                        {product.description}
                      </p>
                    ) : null}
                  </div>
                </div>
                <Can permission="products.update">
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      variant="secondary"
                      size="cta"
                      onClick={() => setEditOpen(true)}
                    >
                      <Pencil className="size-4" aria-hidden />
                      Edit
                    </Button>
                    {product.is_active ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="cta"
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
                        size="cta"
                        disabled={activateProduct.isPending}
                        onClick={() => void onActivate()}
                      >
                        {activateProduct.isPending ? "Activating…" : "Activate"}
                      </Button>
                    )}
                  </div>
                </Can>
              </div>

              <dl className="grid grid-cols-2 divide-x divide-y divide-border border-t border-border bg-muted/40 sm:grid-cols-4 sm:divide-y-0">
                <Stat label="Price">
                  <span className="text-lg font-semibold tabular-nums">
                    {product.currency} {product.price}
                  </span>
                </Stat>
                <Stat label="In stock">
                  <span className="text-lg font-semibold tabular-nums">
                    {product.stock_quantity}
                  </span>
                </Stat>
                <Stat label="Low-stock at">
                  <span className="text-lg font-semibold tabular-nums">
                    {product.low_stock_threshold}
                  </span>
                </Stat>
                <Stat label="Updated">
                  <FormattedTime
                    value={product.updated_at}
                    variant="relative"
                    className="text-sm font-medium"
                  />
                </Stat>
              </dl>
            </header>

            <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
              <div className="min-w-0 space-y-6">
                <Card className="rounded-[24px] ring-1 ring-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <ShoppingBag
                        className="size-4 text-muted-foreground"
                        aria-hidden
                      />
                      Recent order usage
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <QueryState
                      isLoading={orderUsageQuery.isLoading}
                      isError={orderUsageQuery.isError}
                      errorMessage={
                        orderUsageQuery.error instanceof Error
                          ? orderUsageQuery.error.message
                          : "Failed to load order usage."
                      }
                      onRetry={() => {
                        void orderUsageQuery.refetch();
                      }}
                    >
                      {(orderUsageQuery.data ?? []).length === 0 ? (
                        <div className="flex flex-col items-center gap-2 rounded-2xl bg-muted/50 px-4 py-10 text-center">
                          <ShoppingBag
                            className="size-8 text-muted-foreground"
                            aria-hidden
                          />
                          <p className="font-semibold">No sales yet</p>
                          <p className="text-sm text-muted-foreground">
                            Confirmed order lines for this product will show
                            here.
                          </p>
                        </div>
                      ) : (
                        <ul className="divide-y divide-border">
                          {(orderUsageQuery.data ?? []).map((row) => (
                            <li key={`${row.order_id}-${row.created_at}`}>
                              <Link
                                to={ROUTES.orders.detail(row.order_id)}
                                className="-mx-2 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl px-2 py-3 text-sm transition-colors hover:bg-muted/60"
                              >
                                <div className="min-w-0 flex-1">
                                  <p className="font-semibold">
                                    {row.order_number}
                                  </p>
                                  <FormattedTime
                                    value={row.created_at}
                                    variant="relative"
                                    className="text-xs text-muted-foreground"
                                  />
                                </div>
                                <span className="text-muted-foreground">
                                  {getFulfilmentLabel(
                                    row.fulfilment_status as Parameters<
                                      typeof getFulfilmentLabel
                                    >[0],
                                  )}
                                </span>
                                <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-semibold tabular-nums">
                                  × {row.quantity}
                                </span>
                                <ChevronRight
                                  className="size-4 text-muted-foreground"
                                  aria-hidden
                                />
                              </Link>
                            </li>
                          ))}
                        </ul>
                      )}
                    </QueryState>
                  </CardContent>
                </Card>

                <Card className="rounded-[24px] ring-1 ring-border">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <History
                        className="size-4 text-muted-foreground"
                        aria-hidden
                      />
                      Recent adjustments
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <QueryState
                      isLoading={adjustmentsQuery.isLoading}
                      isEmpty={!adjustmentsQuery.data?.length}
                      emptyMessage="No adjustments yet."
                    >
                      <ul className="divide-y divide-border">
                        {(adjustmentsQuery.data ?? []).map((row) => (
                          <li
                            key={row.id}
                            className="flex items-center gap-3 py-3 text-sm"
                          >
                            <span
                              className={cn(
                                "grid size-9 shrink-0 place-items-center rounded-full",
                                row.delta > 0
                                  ? "bg-positive/15 text-positive-deep"
                                  : "bg-negative-bg text-destructive",
                              )}
                              aria-hidden
                            >
                              {row.delta > 0 ? (
                                <ArrowUp className="size-4" />
                              ) : (
                                <ArrowDown className="size-4" />
                              )}
                            </span>
                            <div className="min-w-0 flex-1">
                              <p className="font-semibold tabular-nums">
                                {row.delta > 0 ? `+${row.delta}` : row.delta}
                              </p>
                              <p className="truncate text-muted-foreground">
                                {row.reason}
                              </p>
                            </div>
                            <p className="text-xs text-muted-foreground tabular-nums">
                              Now {row.quantity_after}
                            </p>
                          </li>
                        ))}
                      </ul>
                    </QueryState>
                  </CardContent>
                </Card>
              </div>

              <Can permission="products.update">
                <Card className="rounded-[24px] ring-1 ring-border lg:sticky lg:top-6">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Boxes
                        className="size-4 text-muted-foreground"
                        aria-hidden
                      />
                      Adjust stock
                    </CardTitle>
                    <CardDescription>
                      Positive adds inventory; negative removes it. Stock cannot
                      go below zero.
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
                        size="cta"
                        className="w-full"
                      >
                        {adjustStock.isPending ? "Saving…" : "Apply adjustment"}
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              </Can>
            </div>
          </>
        ) : null}
      </QueryState>
    </div>
  );
}
