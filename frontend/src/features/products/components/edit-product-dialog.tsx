import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { FormField } from "@/components/form-field";
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
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import { useUpdateProduct } from "@/features/products/api/products.api";
import { ProductImage } from "@/features/products/components/product-image";
import type { Product } from "@/features/products/types";

const schema = z.object({
  name: z.string().trim().min(1, "Enter a name."),
  sku: z.string().trim().min(1, "Enter a SKU."),
  description: z.string().optional(),
  price: z.string().regex(/^\d+(\.\d{1,2})?$/, "Enter a valid price."),
  low_stock_threshold: z.number().int().min(0),
  image_url: z.union([z.string().url(), z.literal("")]).optional(),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

const inputClassName =
  "h-12 rounded-xl border-foreground bg-card px-4 text-base";

function toFormValues(product: Product): FormValues {
  return {
    name: product.name,
    sku: product.sku,
    description: product.description,
    price: product.price,
    low_stock_threshold: product.low_stock_threshold,
    image_url: product.image_url || "",
    is_active: product.is_active,
  };
}

/** Edit a product without leaving its detail page. */
export function EditProductDialog({
  product,
  open,
  onClose,
}: {
  product: Product;
  open: boolean;
  onClose: () => void;
}) {
  const updateProduct = useUpdateProduct(product.id);
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: toFormValues(product),
  });
  const imageUrl = form.watch("image_url");
  const productName = form.watch("name");

  // Start every opening from the latest saved values.
  useEffect(() => {
    if (open) form.reset(toFormValues(product));
  }, [open, product, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await updateProduct.mutateAsync({
        name: values.name,
        sku: values.sku,
        description: values.description,
        price: values.price,
        low_stock_threshold: values.low_stock_threshold,
        image_url: values.image_url || "",
        is_active: values.is_active,
      });
      toast.success("Product updated.");
      onClose();
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Could not update the product."));
      }
    }
  });

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="max-h-[90dvh] max-w-xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Edit product</DialogTitle>
          <DialogDescription>
            Update {product.name}. Use Adjust stock to change inventory.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4" noValidate>
          <FormField
            id="product-name"
            label="Name"
            error={form.formState.errors.name?.message}
          >
            <Input className={inputClassName} {...form.register("name")} />
          </FormField>
          <FormField
            id="product-sku"
            label="SKU"
            error={form.formState.errors.sku?.message}
          >
            <Input
              className={inputClassName}
              disabled
              {...form.register("sku")}
            />
          </FormField>
          <FormField id="product-description" label="Description">
            <Input
              className={inputClassName}
              {...form.register("description")}
            />
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField
              id="product-price"
              label="Price"
              error={form.formState.errors.price?.message}
            >
              <Input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                className={inputClassName}
                {...form.register("price")}
              />
            </FormField>
            <FormField id="product-low-stock" label="Low-stock threshold">
              <Input
                type="number"
                className={inputClassName}
                {...form.register("low_stock_threshold", {
                  valueAsNumber: true,
                })}
              />
            </FormField>
          </div>
          <FormField
            id="product-image-url"
            label="Image URL"
            error={form.formState.errors.image_url?.message}
          >
            <div className="flex flex-wrap items-start gap-3">
              <ProductImage
                src={imageUrl}
                alt={productName || "Product preview"}
                size="md"
              />
              <div className="min-w-0 flex-1">
                <Input
                  id="product-image-url"
                  className={inputClassName}
                  placeholder="https://…"
                  aria-invalid={
                    Boolean(form.formState.errors.image_url) || undefined
                  }
                  aria-describedby={
                    form.formState.errors.image_url
                      ? "product-image-url-error"
                      : undefined
                  }
                  {...form.register("image_url")}
                />
              </div>
            </div>
          </FormField>
          <label className="flex items-center gap-2 text-sm font-semibold">
            <input
              id="product-is-active"
              type="checkbox"
              className="size-4"
              {...form.register("is_active")}
            />
            Active
          </label>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              className="rounded-[24px]"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={form.formState.isSubmitting}
              className="rounded-[24px] font-semibold"
            >
              {form.formState.isSubmitting ? "Saving…" : "Save product"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
