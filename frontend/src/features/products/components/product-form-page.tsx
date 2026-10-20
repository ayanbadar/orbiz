import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import { FormField } from "@/components/form-field";
import { PageBackLink } from "@/components/page-back-link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import {
  useCreateProduct,
  useProduct,
  useUpdateProduct,
} from "@/features/products/api/products.api";
import { ProductImage } from "@/features/products/components/product-image";

const schema = z.object({
  name: z.string().trim().min(1, "Enter a name."),
  sku: z.string().trim().min(1, "Enter a SKU."),
  description: z.string().optional(),
  price: z.string().regex(/^\d+(\.\d{1,2})?$/, "Enter a valid price."),
  stock_quantity: z.number().int().min(0).optional(),
  low_stock_threshold: z.number().int().min(0),
  image_url: z.union([z.string().url(), z.literal("")]).optional(),
  is_active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

const inputClassName =
  "h-12 rounded-xl border-foreground bg-card px-4 text-base";

export function ProductFormPage() {
  const { id } = useParams();
  const productId = id ? Number(id) : null;
  const isEdit = Number.isFinite(productId) && (productId as number) > 0;
  const navigate = useNavigate();
  const existing = useProduct(isEdit ? (productId as number) : 0);
  const createProduct = useCreateProduct();
  const updateProduct = useUpdateProduct(isEdit ? (productId as number) : 0);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      sku: "",
      description: "",
      price: "",
      stock_quantity: 0,
      low_stock_threshold: 5,
      image_url: "",
      is_active: true,
    },
  });
  const imageUrl = form.watch("image_url");
  const productName = form.watch("name");

  useEffect(() => {
    if (existing.data) {
      form.reset({
        name: existing.data.name,
        sku: existing.data.sku,
        description: existing.data.description,
        price: existing.data.price,
        stock_quantity: existing.data.stock_quantity,
        low_stock_threshold: existing.data.low_stock_threshold,
        image_url: existing.data.image_url || "",
        is_active: existing.data.is_active,
      });
    }
  }, [existing.data, form]);

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      if (isEdit) {
        const product = await updateProduct.mutateAsync({
          name: values.name,
          sku: values.sku,
          description: values.description,
          price: values.price,
          low_stock_threshold: values.low_stock_threshold,
          image_url: values.image_url || "",
          is_active: values.is_active,
        });
        toast.success("Product updated.");
        navigate(ROUTES.products.detail(product.id));
      } else {
        const product = await createProduct.mutateAsync({
          name: values.name,
          sku: values.sku,
          description: values.description,
          price: values.price,
          stock_quantity: values.stock_quantity ?? 0,
          low_stock_threshold: values.low_stock_threshold,
          image_url: values.image_url || "",
          is_active: values.is_active,
        });
        toast.success("Product created.");
        navigate(ROUTES.products.detail(product.id));
      }
    } catch (error) {
      if (!applyFieldErrors(error, form.setError)) {
        toast.error(getErrorMessage(error, "Save failed."));
      }
    }
  });

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <header className="space-y-3">
        <PageBackLink to={ROUTES.products.root()}>Products</PageBackLink>
        <h1 className="text-[32px] font-semibold tracking-tight text-foreground">
          {isEdit ? "Edit product" : "Add product"}
        </h1>
      </header>

      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-[24px] bg-card p-6"
      >
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
            disabled={isEdit}
            {...form.register("sku")}
          />
        </FormField>
        <FormField id="product-description" label="Description">
          <Input className={inputClassName} {...form.register("description")} />
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
          {!isEdit ? (
            <FormField id="product-stock" label="Initial stock">
              <Input
                type="number"
                className={inputClassName}
                {...form.register("stock_quantity", { valueAsNumber: true })}
              />
            </FormField>
          ) : null}
          <FormField id="product-low-stock" label="Low-stock threshold">
            <Input
              type="number"
              className={inputClassName}
              {...form.register("low_stock_threshold", { valueAsNumber: true })}
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
            <div className="min-w-0 flex-1 space-y-1">
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
              <p className="text-xs text-muted-foreground">
                Public HTTPS URL for now (Channel3 or paste). Later, S3 uploads
                will fill this same field — no schema change.
              </p>
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
        <Button
          type="submit"
          disabled={form.formState.isSubmitting}
          className="h-12 rounded-[24px] px-6 text-base font-semibold"
        >
          {form.formState.isSubmitting ? "Saving…" : "Save product"}
        </Button>
      </form>
    </div>
  );
}
