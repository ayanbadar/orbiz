import { Slot } from "radix-ui";
import type { ComponentProps } from "react";
import { cn } from "cn";

type ClickableProps = ComponentProps<"button"> & {
  asChild?: boolean;
};

function Clickable({
  asChild = false,
  className,
  type,
  ...props
}: ClickableProps) {
  const classes = cn("cursor-pointer disabled:cursor-not-allowed", className);

  if (asChild) {
    return <Slot.Root className={classes} {...props} />;
  }

  return <button type={type} className={classes} {...props} />;
}

export { Clickable };
