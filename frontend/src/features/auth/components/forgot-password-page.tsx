import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useForgotPassword } from "@/features/auth/api/auth.api";
import { AuthField } from "@/features/auth/components/auth-field";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { AuthSubmit } from "@/features/auth/components/auth-submit";
import type { ForgotPasswordResult } from "@/features/auth/types";
import { getErrorMessage } from "@/features/auth/utils/form-errors";

const forgotSchema = z.object({
  email: z.email("Enter a valid email address"),
});

type ForgotValues = z.infer<typeof forgotSchema>;

export function ForgotPasswordPage() {
  const forgot = useForgotPassword();
  const [result, setResult] = useState<ForgotPasswordResult | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotValues>({
    resolver: zodResolver(forgotSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (values: ForgotValues) => {
    try {
      const response = await forgot.mutateAsync(
        values.email.trim().toLowerCase(),
      );
      setResult(response);
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not send reset instructions."));
    }
  };

  return (
    <AuthLayout
      title="Reset your password."
      subtitle="We will email a link if an account exists for that address."
    >
      <div className="space-y-5">
        <div className="space-y-1">
          <h2 className="font-sans text-2xl font-semibold tracking-tight">
            Forgot password
          </h2>
          <p className="text-sm text-body">
            The message is the same whether or not the email is registered.
          </p>
        </div>

        {result ? (
          <div className="space-y-4">
            <p
              className="rounded-xl bg-accent px-4 py-3 text-sm text-accent-foreground"
              role="status"
            >
              {result.message}
            </p>
            {result.debug_reset_url ? (
              <p className="text-sm text-body">
                Development only:{" "}
                <a
                  href={result.debug_reset_url}
                  className="font-semibold break-all text-foreground underline-offset-4 hover:underline"
                >
                  open the reset link
                </a>
              </p>
            ) : null}
          </div>
        ) : (
          <form
            className="space-y-5"
            onSubmit={handleSubmit(onSubmit)}
            noValidate
          >
            <AuthField
              id="email"
              label="Email"
              type="email"
              autoComplete="email"
              error={errors.email?.message}
              registration={register("email")}
            />
            <AuthSubmit pending={forgot.isPending}>Send reset link</AuthSubmit>
          </form>
        )}

        <Link
          to={ROUTES.signIn()}
          className="inline-block text-sm font-semibold underline-offset-4 hover:underline"
        >
          Back to sign in
        </Link>
      </div>
    </AuthLayout>
  );
}
