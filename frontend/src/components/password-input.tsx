import { Eye, EyeOff } from "lucide-react";
import { useState, type ComponentProps } from "react";
import { cn } from "cn";

import { Clickable } from "@/components/clickable";
import { Input } from "@/components/ui/input";

type PasswordInputProps = Omit<ComponentProps<"input">, "type">;

export function PasswordInput({
  className,
  disabled,
  id,
  ...props
}: PasswordInputProps) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="relative">
      <Input
        id={id}
        type={visible ? "text" : "password"}
        disabled={disabled}
        className={cn(
          className,
          "pr-12 [&::-ms-clear]:hidden [&::-ms-reveal]:hidden",
        )}
        {...props}
      />
      <Clickable
        type="button"
        disabled={disabled}
        aria-label={visible ? "Hide password" : "Show password"}
        aria-pressed={visible}
        aria-controls={id}
        onClick={() => {
          setVisible((current) => !current);
        }}
        className="absolute top-1/2 right-2 flex size-8 -translate-y-1/2 items-center justify-center rounded-full text-foreground outline-none hover:bg-secondary focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50"
      >
        {visible ? (
          <EyeOff className="size-4" aria-hidden />
        ) : (
          <Eye className="size-4" aria-hidden />
        )}
      </Clickable>
    </div>
  );
}
