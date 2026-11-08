import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  useAcceptInvitation,
  useInvitationPreview,
} from "@/features/invitations/api/invitations.api";
import { AuthField } from "@/features/auth/components/auth-field";
import { AuthLayout } from "@/features/auth/components/auth-layout";
import { AuthSubmit } from "@/features/auth/components/auth-submit";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";

const schema = z
  .object({
    firstName: z.string().trim().min(1, "Enter your first name"),
    lastName: z.string().trim(),
    password: z.string().min(8, "Password must be at least 8 characters"),
    passwordConfirm: z.string(),
  })
  .refine((values) => values.password === values.passwordConfirm, {
    message: "Passwords do not match.",
    path: ["passwordConfirm"],
  });

type Values = z.infer<typeof schema>;

export function AcceptInvitePage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const invitation = useInvitationPreview(token);

  return (
    <AuthLayout
      title="You're invited."
      subtitle="Set a password to join your team on Orbiz."
    >
      {!token || invitation.isError ? (
        <div className="space-y-4">
          <h2 className="text-2xl font-semibold tracking-tight">
            This invitation isn&apos;t valid
          </h2>
          <p className="text-sm text-body">
            The link may have expired or already been used. Ask for a new
            invitation.
          </p>
          <Button asChild variant="secondary" className="rounded-[24px]">
            <Link to={ROUTES.signIn()}>Back to sign in</Link>
          </Button>
        </div>
      ) : invitation.isLoading || !invitation.data ? (
        <p className="text-sm text-muted-foreground" role="status">
          Checking your invitation…
        </p>
      ) : (
        <AcceptForm
          token={token}
          email={invitation.data.email}
          storeName={invitation.data.store_name}
          roleName={invitation.data.role_name}
          isStoreAdmin={invitation.data.kind === "store_admin"}
        />
      )}
    </AuthLayout>
  );
}

function AcceptForm({
  token,
  email,
  storeName,
  roleName,
  isStoreAdmin,
}: {
  token: string;
  email: string;
  storeName: string;
  roleName: string | null;
  isStoreAdmin: boolean;
}) {
  const accept = useAcceptInvitation(token);
  const navigate = useNavigate();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      firstName: "",
      lastName: "",
      password: "",
      passwordConfirm: "",
    },
  });

  const onSubmit = async (values: Values) => {
    try {
      await accept.mutateAsync({
        first_name: values.firstName.trim(),
        last_name: values.lastName.trim(),
        password: values.password,
        password_confirm: values.passwordConfirm,
      });
      // Store admins finish store setup and pay; staff go straight to work.
      navigate(isStoreAdmin ? ROUTES.stores.onboarding() : ROUTES.root(), {
        replace: true,
      });
    } catch (error) {
      if (!applyFieldErrors(error, setError)) {
        toast.error(getErrorMessage(error, "Could not accept the invitation."));
      }
    }
  };

  return (
    <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="space-y-1">
        <h2 className="text-2xl font-semibold tracking-tight">
          Join {storeName}
        </h2>
        <p className="text-sm text-body">
          {isStoreAdmin
            ? "You'll be the admin of this store."
            : `Your role: ${roleName ?? "Staff"}.`}{" "}
          Signing up as <span className="font-semibold">{email}</span>.
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
      <AuthSubmit pending={accept.isPending}>Accept invitation</AuthSubmit>
    </form>
  );
}
