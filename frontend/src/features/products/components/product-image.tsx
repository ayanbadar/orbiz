import { useEffect, useState } from "react";

import { cn } from "cn";

type Size = "sm" | "md" | "lg";
type Fit = "cover" | "contain";

const SIZE_CLASS: Record<Size, string> = {
  // Slightly larger than size-10 so cover crops read more clearly in lists.
  sm: "size-12",
  md: "size-16",
  // Portrait frame: Channel3 apparel is usually taller than wide.
  lg: "h-44 w-36 sm:h-52 sm:w-40",
};

/** Thumbs fill the tile; detail shows the full product. */
function defaultFit(size: Size): Fit {
  return size === "lg" ? "contain" : "cover";
}

type Props = {
  src?: string | null;
  alt: string;
  size?: Size;
  /** Override size-based default (`sm`/`md` → cover, `lg` → contain). */
  fit?: Fit;
  className?: string;
};

/**
 * Displays a product image from a public HTTPS URL.
 *
 * Storage contract (S3-ready): persist only `image_url` (string). Today that may be
 * a Channel3 CDN or pasted URL; later an upload flow can write an S3/CloudFront URL
 * into the same field — UI stays `src={image_url}`.
 */
export function ProductImage({
  src,
  alt,
  size = "md",
  fit,
  className,
}: Props) {
  const [failed, setFailed] = useState(false);
  const url = (src || "").trim();
  const objectFit = fit ?? defaultFit(size);

  useEffect(() => {
    setFailed(false);
  }, [url]);

  const showImage = Boolean(url) && !failed;

  return (
    <div
      className={cn(
        "relative shrink-0 overflow-hidden rounded-[12px] bg-card ring-1 ring-border/70",
        SIZE_CLASS[size],
        className,
      )}
    >
      {showImage ? (
        <img
          src={url}
          alt={alt}
          className={cn(
            "size-full",
            objectFit === "cover"
              ? "object-cover object-center"
              : "object-contain p-1.5",
          )}
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => setFailed(true)}
        />
      ) : (
        <div
          className="flex size-full items-center justify-center text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
          aria-hidden={Boolean(alt)}
        >
          No image
        </div>
      )}
    </div>
  );
}
