import { cn } from "cn";

type LogoProps = {
  variant?: "black" | "white";
  className?: string;
};

const sources = {
  black: "/logo-black.svg",
  white: "/logo-white.svg",
} as const;

export function Logo({ variant = "black", className }: LogoProps) {
  return (
    <img
      src={sources[variant]}
      alt="Orbiz"
      className={cn("h-12 w-12 shrink-0", className)}
    />
  );
}
