import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  useChannel3Search,
  useImportFromChannel3,
} from "@/features/products/api/products.api";
import type { Channel3Result } from "@/features/products/types";
import { ApiError } from "@/lib/api";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

function resolveImportPrice(
  price: string,
  suggested: string | null | undefined,
): string | null {
  const trimmed = price.trim();
  if (trimmed) {
    return trimmed;
  }
  if (suggested && suggested.trim()) {
    return suggested.trim();
  }
  return null;
}

export function Channel3SearchDialog({ open, onOpenChange }: Props) {
  const [query, setQuery] = useState("");
  const [sku, setSku] = useState("");
  const [price, setPrice] = useState("");
  const [stock, setStock] = useState(10);
  const [selected, setSelected] = useState<Channel3Result | null>(null);
  const search = useChannel3Search();
  const importProduct = useImportFromChannel3();
  const navigate = useNavigate();

  const importPrice = selected
    ? resolveImportPrice(price, selected.suggested_price)
    : null;
  const canImport = Boolean(selected && sku.trim() && importPrice);

  const onSearch = async () => {
    try {
      await search.mutateAsync(query);
      setSelected(null);
    } catch (error) {
      toast.error(
        error instanceof ApiError
          ? error.message
          : "Channel3 search failed. You can still add products manually.",
      );
    }
  };

  const onImport = async () => {
    if (!selected) {
      return;
    }
    const resolved = resolveImportPrice(price, selected.suggested_price);
    if (!resolved) {
      toast.error("Enter a selling price before importing.");
      return;
    }
    if (!sku.trim()) {
      toast.error("Enter a SKU before importing.");
      return;
    }
    try {
      const product = await importProduct.mutateAsync({
        channel3_product_id: selected.channel3_product_id,
        sku: sku.trim().toUpperCase(),
        price: resolved,
        stock_quantity: Number.isFinite(stock) ? Math.max(0, stock) : 0,
      });
      toast.success("Imported into your Orbiz catalog.");
      onOpenChange(false);
      navigate(ROUTES.products.detail(product.id));
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Import failed.");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between gap-3">
            <div>
              <DialogTitle>Search Channel3</DialogTitle>
              <DialogDescription>
                Enrich your catalog from Channel3. Checkout stays on Orbiz +
                PayPal Sandbox — external buy links are not used.
              </DialogDescription>
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={() => onOpenChange(false)}
            >
              Close
            </Button>
          </div>
        </DialogHeader>

        <div className="flex flex-wrap gap-2">
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. black hoodie"
            className="min-w-[200px] flex-1"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                void onSearch();
              }
            }}
          />
          <Button
            type="button"
            onClick={() => void onSearch()}
            disabled={search.isPending || !query.trim()}
          >
            {search.isPending ? "Searching…" : "Search"}
          </Button>
        </div>

        <ul className="mt-2 space-y-2">
          {(search.data?.results ?? []).map((item) => (
            <li key={item.channel3_product_id}>
              <button
                type="button"
                className={`w-full rounded-[16px] border px-4 py-3 text-left ${
                  selected?.channel3_product_id === item.channel3_product_id
                    ? "border-foreground bg-muted"
                    : "border-border"
                }`}
                onClick={() => {
                  setSelected(item);
                  setPrice(item.suggested_price || "");
                  setSku(
                    item.title
                      .slice(0, 12)
                      .toUpperCase()
                      .replace(/[^A-Z0-9]+/g, "-")
                      .replace(/^-|-$/g, "") || "SKU",
                  );
                }}
              >
                <p className="font-semibold">{item.title}</p>
                <p className="text-sm text-body">
                  {item.currency} {item.suggested_price ?? "—"}
                  {item.brand ? ` · ${item.brand}` : ""}
                </p>
              </button>
            </li>
          ))}
        </ul>

        {search.isSuccess && (search.data?.results?.length ?? 0) === 0 ? (
          <p className="text-sm text-body">No Channel3 matches for that query.</p>
        ) : null}

        {selected ? (
          <div className="mt-2 space-y-3 border-t border-border pt-4">
            <p className="text-sm font-semibold">Import as Orbiz product</p>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1">
                <Label htmlFor="import-sku">SKU</Label>
                <Input
                  id="import-sku"
                  value={sku}
                  onChange={(e) => setSku(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="import-price">Your price</Label>
                <Input
                  id="import-price"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="Required"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="import-stock">Stock</Label>
                <Input
                  id="import-stock"
                  type="number"
                  value={Number.isFinite(stock) ? stock : 0}
                  onChange={(e) => {
                    const next = Number(e.target.value);
                    setStock(Number.isFinite(next) ? next : 0);
                  }}
                />
              </div>
            </div>
            <Button
              type="button"
              className="rounded-[24px] font-semibold"
              disabled={importProduct.isPending || !canImport}
              onClick={() => void onImport()}
            >
              {importProduct.isPending ? "Importing…" : "Import to Orbiz"}
            </Button>
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
