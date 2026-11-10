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
    storeName: z.string().trim().min(1, "Enter your store name"),
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
      storeName: "",
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
        store_name: values.storeName.trim(),
      });
      navigate(ROUTES.stores.onboarding(), { replace: true });
    } catch (error) {
      if (!applyFieldErrors(error, setError)) {
        toast.error(getErrorMessage(error, "Could not create the account."));
      }
    }
  };

  return (
    <AuthLayout
      title="Open your store."
      subtitle="Create your store admin account. Activate it with the $5/month plan, then invite your team."
    >
      <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
        <div className="space-y-1">
          <h2 className="font-sans text-2xl font-semibold tracking-tight">
            Create your store
          </h2>
          <p className="text-sm text-body">
            You&apos;ll be the admin of this store.
          </p>
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
          id="store-name"
          label="Store name"
          autoComplete="organization"
          error={errors.storeName?.message}
          registration={register("storeName")}
        />
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
          Create your store
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
