import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useResetPassword } from "@/features/auth/api/auth.api";
import { AuthField } from "@/features/auth/components/auth-field";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { AuthSubmit } from "@/features/auth/components/auth-submit";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";

const resetSchema = z
  .object({
    newPassword: z.string().min(8, "Password must be at least 8 characters"),
    newPasswordConfirm: z.string(),
  })
  .refine((values) => values.newPassword === values.newPasswordConfirm, {
    message: "Passwords do not match.",
    path: ["newPasswordConfirm"],
  });

type ResetValues = z.infer<typeof resetSchema>;

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const reset = useResetPassword();
  const [done, setDone] = useState(false);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    defaultValues: { newPassword: "", newPasswordConfirm: "" },
  });

  const onSubmit = async (values: ResetValues) => {
    try {
      await reset.mutateAsync({
        uid,
        token,
        new_password: values.newPassword,
        new_password_confirm: values.newPasswordConfirm,
      });
      setDone(true);
    } catch (error) {
      if (!applyFieldErrors(error, setError)) {
        toast.error(getErrorMessage(error, "Could not reset the password."));
      }
    }
  };

  return (
    <AuthLayout
      title="Choose a new password."
      subtitle="This link works once. After that, sign in with the new password."
    >
      <div className="space-y-5">
        <h2 className="font-sans text-2xl font-semibold tracking-tight">
          New password
        </h2>

        {!uid || !token ? (
          <div className="space-y-4">
            <p className="text-sm text-destructive" role="alert">
              This reset link is missing details. Request a new one.
            </p>
            <Link
              to={ROUTES.forgotPassword()}
              className="inline-block text-sm font-semibold underline-offset-4 hover:underline"
            >
              Request a new link
            </Link>
          </div>
        ) : done ? (
          <div className="space-y-4">
            <p
              className="rounded-xl bg-accent px-4 py-3 text-sm text-accent-foreground"
              role="status"
            >
              Password updated. You can sign in now.
            </p>
            <Link
              to={ROUTES.signIn()}
              className="inline-block text-sm font-semibold underline-offset-4 hover:underline"
            >
              Sign in
            </Link>
          </div>
        ) : (
          <form
            className="space-y-5"
            onSubmit={handleSubmit(onSubmit)}
            noValidate
          >
            <AuthField
              id="new-password"
              label="New password"
              type="password"
              autoComplete="new-password"
              error={errors.newPassword?.message}
              registration={register("newPassword")}
            />
            <AuthField
              id="new-password-confirm"
              label="Confirm new password"
              type="password"
              autoComplete="new-password"
              error={errors.newPasswordConfirm?.message}
              registration={register("newPasswordConfirm")}
            />
            <AuthSubmit pending={reset.isPending}>Update password</AuthSubmit>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}
