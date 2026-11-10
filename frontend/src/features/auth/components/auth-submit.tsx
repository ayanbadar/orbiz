import { Button } from "@/components/ui/button";

type AuthSubmitProps = {
  pending: boolean;
  children: string;
};

export function AuthSubmit({ pending, children }: AuthSubmitProps) {
  return (
    <Button
      type="submit"
      disabled={pending}
      className="h-12 w-full rounded-[24px] text-base font-semibold hover:bg-primary-active"
    >
      {pending ? "Please wait…" : children}
    </Button>
  );
}
