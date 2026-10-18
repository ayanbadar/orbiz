import { Logo } from "@/components/logo";

export function AuthLoading() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-4 bg-background px-6">
      <Logo />
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    </div>
  );
}
