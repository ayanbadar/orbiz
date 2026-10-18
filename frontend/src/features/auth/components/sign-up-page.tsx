import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import { useRegister } from "@/features/auth/api/auth.api";
import { AuthField } from "@/features/auth/components/auth-field";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { AuthSubmit } from "@/features/auth/components/auth-submit";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";

const signUpSchema = z
  .object({
    firstName: z.string().trim().min(1, "Enter your first name"),
    lastName: z.string().trim(),
    email: z.email("Enter a valid email address"),
    password: z.string().min(8, "Password must be at least 8 characters"),
    passwordConfirm: z.string(),
  })
  .refine((values) => values.password === values.passwordConfirm, {
    message: "Passwords do not match.",
    path: ["passwordConfirm"],
  });

type SignUpValues = z.infer<typeof signUpSchema>;

export function SignUpPage() {
  const registerAccount = useRegister();
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<SignUpValues>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      passwordConfirm: "",
    },
  });

  const onSubmit = async (values: SignUpValues) => {
    try {
      await registerAccount.mutateAsync({
        email: values.email.trim().toLowerCase(),
        password: values.password,
        password_confirm: values.passwordConfirm,
        first_name: values.firstName.trim(),
        last_name: values.lastName.trim(),
      });
      navigate(ROUTES.account(), { replace: true });
    } catch (error) {
      if (!applyFieldErrors(error, setError)) {
        toast.error(getErrorMessage(error, "Could not create the account."));
      }
    }
  };

  return (
    <AuthLayout
      title="Open your workspace."
      subtitle="Create an account to turn customer messages into orders you can review."
    >
      <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="space-y-1">
          <h2 className="font-sans text-2xl font-semibold tracking-tight">
            Create account
          </h2>
          <p className="text-sm text-body">Use an email you can open later.</p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <AuthField
            id="first-name"
            label="First name"
            autoComplete="given-name"
            error={errors.firstName?.message}
            registration={register("firstName")}
          />
          <AuthField
            id="last-name"
            label="Last name"
            autoComplete="family-name"
            error={errors.lastName?.message}
            registration={register("lastName")}
          />
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
          autoComplete="new-password"
          error={errors.password?.message}
          registration={register("password")}
        />
        <AuthField
          id="password-confirm"
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          error={errors.passwordConfirm?.message}
          registration={register("passwordConfirm")}
        />

        <AuthSubmit pending={registerAccount.isPending}>
          Create account
        </AuthSubmit>

        <p className="text-sm text-body">
          Already have an account?{" "}
          <Link
            to={ROUTES.signIn()}
            className="font-semibold text-foreground underline-offset-4 hover:underline"
          >
            Sign in
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}
