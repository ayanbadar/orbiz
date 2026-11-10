import { zodResolver } from "@hookform/resolvers/zod";
import { useQueries } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/form-field";
import { SearchableSelect } from "@/components/searchable-select";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import { Textarea } from "@/components/ui/textarea";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import {
  useCreateCustomer,
  useCustomers,
} from "@/features/customers/api/customers.api";
import { useCreateOrder } from "@/features/orders/api/orders.api";
import { PRODUCT_QUERY_KEYS } from "@/features/products/api/products.keys";
import { useProducts } from "@/features/products/api/products.api";
import { ProductService } from "@/features/products/api/products.service";

const lineSchema = z.object({
  product_id: z.number().int().positive("Pick a product."),
  quantity: z.number().int().min(1, "Quantity must be at least 1."),
});

const schema = z.object({
  customer_id: z.number().int().positive("Pick a customer."),
  delivery_notes: z.string().optional(),
  internal_notes: z.string().optional(),
  source_message: z.string().optional(),
  lines: z.array(lineSchema).min(1, "Add at least one line."),
});

type FormValues = z.infer<typeof schema>;

const inputClassName =
  "h-12 w-full min-w-0 rounded-xl border-foreground bg-card px-4 text-base";

const PICKER_PAGE_SIZE = 50;

/** Create a draft order in a dialog. */
export function OrderDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const createOrder = useCreateOrder();
  const [customerSearch, setCustomerSearch] = useState("");
  const [productSearch, setProductSearch] = useState("");
  const deferredCustomerSearch = useDeferredValue(customerSearch);
  const deferredProductSearch = useDeferredValue(productSearch);
  const customersQuery = useCustomers({
    q: deferredCustomerSearch || undefined,
    page_size: PICKER_PAGE_SIZE,
  });
  const productsQuery = useProducts({
    q: deferredProductSearch || undefined,
    page_size: PICKER_PAGE_SIZE,
    is_active: true,
  });
  const createCustomer = useCreateCustomer();
  const [newCustomerName, setNewCustomerName] = useState("");

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      customer_id: 0,
      delivery_notes: "",
      internal_notes: "",
      source_message: "",
      lines: [{ product_id: 0, quantity: 1 }],
    },
  });
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "lines",
  });
  const watchedLines = form.watch("lines");

  const productsById = useMemo(() => {
    const map = new Map<
      number,
      { name: string; price: string; stock: number }
    >();
    for (const p of productsQuery.data?.results ?? []) {
      map.set(p.id, {
        name: p.name,
        price: p.price,
        stock: p.stock_quantity,
      });
    }
    return map;
  }, [productsQuery.data]);

  const stockQueries = useQueries({
    queries: fields.map((field, index) => {
      const line = watchedLines[index];
      const productId = line?.product_id ?? 0;
      const quantity = line?.quantity ?? 0;
      return {
        // Include field.id so remove/reorder cannot show another line's hint.
        queryKey: [
          ...PRODUCT_QUERY_KEYS.checkStock(productId, quantity),
          field.id,
        ] as const,
        queryFn: () => ProductService.checkStock(productId, quantity),
        enabled: productId > 0 && quantity >= 1,
        retry: false,
        staleTime: 5_000,
      };
    }),
  });

  const stockHintByFieldId = useMemo(() => {
    const map = new Map<string, string>();
    fields.forEach((field, index) => {
      const stockQuery = stockQueries[index];
      if (stockQuery?.isError) {
        map.set(
          field.id,
          getErrorMessage(stockQuery.error, "Insufficient stock."),
        );
      }
    });
    return map;
  }, [fields, stockQueries]);

  useEffect(() => {
    if (open) {
      form.reset();
      setCustomerSearch("");
      setProductSearch("");
      setNewCustomerName("");
    }
  }, [open, form]);

  const estimatedTotal = watchedLines.reduce((sum, line) => {
    const product = productsById.get(line.product_id);
    if (!product) return sum;
    return sum + Number(product.price) * line.quantity;
  }, 0);

  const saveDraft = form.handleSubmit(async (values) => {
    try {
      await createOrder.mutateAsync(values);
      toast.success("Draft created.");
      onClose();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not save order."));
      }
    }
  });

  const onCreateCustomer = async () => {
    const name = newCustomerName.trim();
    if (!name) {
      toast.error("Enter a customer name.");
      return;
    }
    try {
      const customer = await createCustomer.mutateAsync({ name });
      form.setValue("customer_id", customer.id, { shouldValidate: true });
      setNewCustomerName("");
      toast.success("Customer added.");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not create customer."));
    }
  };

  const customerResults = customersQuery.data?.results ?? [];
  const productResults = productsQuery.data?.results ?? [];
  const customerCount = customersQuery.data?.count ?? customerResults.length;
  const productCount = productsQuery.data?.count ?? productResults.length;

  const customerOptions = useMemo(() => {
    const nameCounts = new Map<string, number>();
    for (const customer of customerResults) {
      const key = customer.name.trim().toLowerCase();
      nameCounts.set(key, (nameCounts.get(key) ?? 0) + 1);
    }
    return customerResults.map((customer) => {
      const duplicate =
        (nameCounts.get(customer.name.trim().toLowerCase()) ?? 0) > 1;
      const label =
        duplicate && customer.email
          ? `${customer.name} · ${customer.email}`
          : customer.name;
      return {
        value: String(customer.id),
        label,
        primary: customer.name,
        secondary: customer.email || undefined,
        keywords: [customer.name, customer.email, customer.phone]
          .filter(Boolean)
          .join(" "),
      };
    });
  }, [customerResults]);

  const productOptions = useMemo(() => {
    const nameCounts = new Map<string, number>();
    for (const product of productResults) {
      const key = product.name.trim().toLowerCase();
      nameCounts.set(key, (nameCounts.get(key) ?? 0) + 1);
    }
    return productResults.map((product) => {
      const duplicate =
        (nameCounts.get(product.name.trim().toLowerCase()) ?? 0) > 1;
      return {
        value: String(product.id),
        label: duplicate ? `${product.name} · ${product.sku}` : product.name,
        primary: product.name,
        secondary: `${product.sku} · stock ${product.stock_quantity}`,
        keywords: `${product.name} ${product.sku}`,
      };
    });
  }, [productResults]);

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Create order</DialogTitle>
          <DialogDescription>
            Save as draft first. Confirm on the detail page to deduct stock.
          </DialogDescription>
        </DialogHeader>
        <form className="space-y-6" onSubmit={saveDraft} noValidate>
          <SearchableSelect
            id="customer_id"
            label="Customer"
            name="customer_id"
            control={form.control}
            error={form.formState.errors.customer_id?.message}
            placeholder="Search customers…"
            searchValue={customerSearch}
            onSearchChange={setCustomerSearch}
            parseValue={(value) => Number(value)}
            isEmpty={(value) => Number(value) <= 0}
            options={customerOptions}
            footer={
              customersQuery.isError ? (
                <p className="text-sm text-destructive" role="alert">
                  {getErrorMessage(
                    customersQuery.error,
                    "Could not load customers.",
                  )}
                </p>
              ) : customerCount > customerResults.length ? (
                <p className="text-sm text-muted-foreground">
                  Showing {customerResults.length} of {customerCount}. Refine
                  search to find others.
                </p>
              ) : null
            }
          />

          <div className="flex flex-wrap items-end gap-3">
            <FormField
              id="new_customer"
              label="Or create customer"
              className="flex-1"
            >
              <Input
                className={inputClassName}
                value={newCustomerName}
                onChange={(e) => setNewCustomerName(e.target.value)}
                placeholder="Customer name"
              />
            </FormField>
            <Button
              type="button"
              variant="outline"
              className="h-12 rounded-[24px]"
              onClick={() => {
                void onCreateCustomer();
              }}
              disabled={createCustomer.isPending}
            >
              Add customer
            </Button>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-sm font-semibold">Line items</h2>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={() => append({ product_id: 0, quantity: 1 })}
              >
                <Plus className="size-4" />
                Add line
              </Button>
            </div>
            {productsQuery.isError ? (
              <p className="text-sm text-destructive" role="alert">
                {getErrorMessage(
                  productsQuery.error,
                  "Could not load products.",
                )}
              </p>
            ) : productCount > productResults.length ? (
              <p className="text-sm text-muted-foreground">
                Showing {productResults.length} of {productCount} products.
                Refine search to find others.
              </p>
            ) : null}
            {form.formState.errors.lines?.message ||
            form.formState.errors.lines?.root?.message ? (
              <p className="text-sm text-destructive" role="alert">
                {form.formState.errors.lines?.message ??
                  form.formState.errors.lines?.root?.message}
              </p>
            ) : null}
            {fields.map((field, index) => {
              const stockHint = stockHintByFieldId.get(field.id);
              return (
                <div
                  key={field.id}
                  className="grid min-w-0 gap-3 rounded-[24px] bg-card p-4 ring-1 ring-border sm:grid-cols-[minmax(0,1fr)_7.5rem_auto]"
                >
                  <SearchableSelect
                    id={`lines.${index}.product_id`}
                    label="Product"
                    name={`lines.${index}.product_id`}
                    control={form.control}
                    className="min-w-0"
                    error={
                      form.formState.errors.lines?.[index]?.product_id?.message
                    }
                    placeholder="Search products…"
                    searchValue={productSearch}
                    onSearchChange={setProductSearch}
                    parseValue={(value) => Number(value)}
                    isEmpty={(value) => !value || Number(value) <= 0}
                    options={productOptions}
                  />
                  <FormField
                    id={`lines.${index}.quantity`}
                    label="Qty"
                    error={
                      form.formState.errors.lines?.[index]?.quantity?.message
                    }
                  >
                    <Input
                      type="number"
                      min={1}
                      className={inputClassName}
                      {...form.register(`lines.${index}.quantity`, {
                        valueAsNumber: true,
                      })}
                    />
                  </FormField>
                  <div className="flex items-end">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="mb-1"
                      disabled={fields.length <= 1}
                      onClick={() => remove(index)}
                      aria-label="Remove line"
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                  {stockHint ? (
                    <p
                      className="text-sm text-warning-content sm:col-span-3"
                      role="status"
                    >
                      {stockHint}
                    </p>
                  ) : null}
                </div>
              );
            })}
            <p className="text-sm text-muted-foreground">
              Estimated total:{" "}
              <span className="font-semibold tabular-nums text-foreground">
                {estimatedTotal.toFixed(2)}
              </span>{" "}
              (server recalculates on save)
            </p>
          </div>

          <FormField
            id="delivery_notes"
            label="Delivery notes"
            error={form.formState.errors.delivery_notes?.message}
          >
            <Textarea
              className="min-h-24 rounded-xl border-foreground bg-card px-4 py-3 text-base"
              {...form.register("delivery_notes")}
            />
          </FormField>

          <FormField
            id="source_message"
            label="Customer message (optional)"
            error={form.formState.errors.source_message?.message}
          >
            <Textarea
              className="min-h-24 rounded-xl border-foreground bg-card px-4 py-3 text-base"
              placeholder="Paste the chat request for the demo…"
              {...form.register("source_message")}
            />
          </FormField>

          <FormField
            id="internal_notes"
            label="Internal notes"
            error={form.formState.errors.internal_notes?.message}
          >
            <Textarea
              className="min-h-20 rounded-xl border-foreground bg-card px-4 py-3 text-base"
              {...form.register("internal_notes")}
            />
          </FormField>

          <div className="flex flex-wrap justify-end gap-3">
            <Button
              type="submit"
              className="rounded-[24px] px-6"
              disabled={form.formState.isSubmitting || createOrder.isPending}
            >
              Save draft
            </Button>
            <Button
              type="button"
              variant="outline"
              className="rounded-[24px]"
              onClick={onClose}
            >
              Cancel
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
