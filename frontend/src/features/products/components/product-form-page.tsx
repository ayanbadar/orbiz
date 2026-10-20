import { zodResolver } from "@hookform/resolvers/zod";
import type { ReactNode } from "react";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

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
      <header className="space-y-1">
        <Link to={ROUTES.products.root()} className="text-sm font-semibold underline-offset-4 hover:underline">
          ← Products
        </Link>
        <h1 className="text-[32px] font-semibold tracking-tight text-foreground">
          {isEdit ? "Edit product" : "Add product"}
        </h1>
      </header>

      <form onSubmit={onSubmit} className="space-y-4 rounded-[24px] bg-card p-6">
        <Field label="Name" error={form.formState.errors.name?.message}>
          <Input {...form.register("name")} />
        </Field>
        <Field label="SKU" error={form.formState.errors.sku?.message}>
          <Input {...form.register("sku")} disabled={isEdit} />
        </Field>
        <Field label="Description">
          <Input {...form.register("description")} />
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Price" error={form.formState.errors.price?.message}>
            <Input {...form.register("price")} />
          </Field>
          {!isEdit ? (
            <Field label="Initial stock">
              <Input
                type="number"
                {...form.register("stock_quantity", { valueAsNumber: true })}
              />
            </Field>
          ) : null}
          <Field label="Low-stock threshold">
            <Input
              type="number"
              {...form.register("low_stock_threshold", { valueAsNumber: true })}
            />
          </Field>
        </div>
        <Field label="Image URL">
          <div className="flex flex-wrap items-start gap-3">
            <ProductImage
              src={imageUrl}
              alt={productName || "Product preview"}
              size="md"
            />
            <div className="min-w-0 flex-1 space-y-1">
              <Input
                {...form.register("image_url")}
                placeholder="https://…"
              />
              <p className="text-xs text-muted-foreground">
                Public HTTPS URL for now (Channel3 or paste). Later, S3 uploads
                will fill this same field — no schema change.
              </p>
            </div>
          </div>
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...form.register("is_active")} />
          Active
        </label>
        <Button
          type="submit"
          disabled={form.formState.isSubmitting}
          className="h-12 rounded-[24px] px-6 font-semibold"
        >
          {form.formState.isSubmitting ? "Saving…" : "Save product"}
        </Button>
      </form>
    </div>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      {children}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
