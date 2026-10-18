import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { z } from "zod";

import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useLogin } from "@/features/auth/api/auth.api";
import { AuthField } from "@/features/auth/components/auth-field";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { AuthSubmit } from "@/features/auth/components/auth-submit";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import { safeReturnPath } from "@/features/auth/utils/return-path";

const signInSchema = z.object({
  email: z.email("Enter a valid email address"),
  password: z.string().min(1, "Enter your password"),
});

type SignInValues = z.infer<typeof signInSchema>;

export function SignInPage() {
  const login = useLogin();
  const navigate = useNavigate();
  const location = useLocation();
  const returnPath = safeReturnPath(
    location.state && typeof location.state === "object"
      ? (location.state as { from?: unknown }).from
      : null,
  );

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { email: "", password: "" },
  });

  const onSubmit = async (values: SignInValues) => {
    try {
      await login.mutateAsync({
        email: values.email.trim().toLowerCase(),
        password: values.password,
      });
      navigate(returnPath ?? ROUTES.account(), { replace: true });
    } catch (error) {
      if (!applyFieldErrors(error, setError)) {
        toast.error(getErrorMessage(error, "Could not sign in."));
      }
    }
  };

  return (
    <AuthLayout
      title="Welcome back."
      subtitle="Sign in to review orders, stock, and payments from one workspace."
    >
      <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="space-y-1">
          <h2 className="font-sans text-2xl font-semibold tracking-tight">
            Sign in
          </h2>
          <p className="text-sm text-body">
            Use the email for your Orbiz account.
          </p>
        </div>

        <AuthField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          registration={register("email")}
        />
        <AuthField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          registration={register("password")}
        />

        <div className="flex justify-end">
          <Link
            to={ROUTES.forgotPassword()}
            className="text-sm font-semibold underline-offset-4 hover:underline"
          >
            Forgot password?
          </Link>
        </div>

        <AuthSubmit pending={login.isPending}>Sign in</AuthSubmit>

        <p className="text-sm text-body">
          New to Orbiz?{" "}
          <Link
            to={ROUTES.signUp()}
            className="font-semibold text-foreground underline-offset-4 hover:underline"
          >
            Create an account
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
