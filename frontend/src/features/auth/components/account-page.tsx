import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "@/components/ui/sonner";
import { ROUTES } from "@/constants/routes";
import {
  useChangePassword,
  useUpdateProfile,
} from "@/features/auth/api/auth.api";
import { AuthField } from "@/features/auth/components/auth-field";
import { AuthSubmit } from "@/features/auth/components/auth-submit";
import { useAuth } from "@/features/auth/context/use-auth";
import {
  applyFieldErrors,
  getErrorMessage,
} from "@/features/auth/utils/form-errors";
import { WorkspaceCard } from "@/features/stores/components/workspace-card";

const profileSchema = z.object({
  firstName: z.string().trim().min(1, "Enter your first name"),
  lastName: z.string().trim(),
});

const passwordSchema = z
  .object({
    currentPassword: z.string().min(1, "Enter your current password"),
    newPassword: z.string().min(8, "Password must be at least 8 characters"),
    newPasswordConfirm: z.string(),
  })
  .refine((values) => values.newPassword === values.newPasswordConfirm, {
    message: "Passwords do not match.",
    path: ["newPasswordConfirm"],
  });

type ProfileValues = z.infer<typeof profileSchema>;
type PasswordValues = z.infer<typeof passwordSchema>;

export function AccountPage() {
  const { user, clearSession } = useAuth();
  const updateProfile = useUpdateProfile();
  const changePassword = useChangePassword();
  const navigate = useNavigate();

  const profileForm = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      firstName: user?.first_name ?? "",
      lastName: user?.last_name ?? "",
    },
  });

  const passwordForm = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: {
      currentPassword: "",
      newPassword: "",
      newPasswordConfirm: "",
    },
  });

  const onSaveProfile = async (values: ProfileValues) => {
    try {
      await updateProfile.mutateAsync({
        first_name: values.firstName.trim(),
        last_name: values.lastName.trim(),
      });
      toast.success("Profile saved.");
    } catch (error) {
      if (!applyFieldErrors(error, profileForm.setError)) {
        toast.error(getErrorMessage(error, "Could not save your profile."));
      }
    }
  };

  const onChangePassword = async (values: PasswordValues) => {
    try {
      await changePassword.mutateAsync({
        current_password: values.currentPassword,
        new_password: values.newPassword,
        new_password_confirm: values.newPasswordConfirm,
      });
      toast.success("Password updated. Sign in with your new password.");
      clearSession();
      navigate(ROUTES.signIn(), { replace: true });
    } catch (error) {
      if (!applyFieldErrors(error, passwordForm.setError)) {
        toast.error(getErrorMessage(error, "Could not change the password."));
      }
    }
  };

  if (!user) {
    return null;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="font-sans text-[2rem] leading-tight font-semibold tracking-[-0.96px]">
          Account
        </h1>
        <p className="text-body">
          Profile, workspace, and password for {user.email}.
        </p>
      </div>

      <WorkspaceCard />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="rounded-[24px] bg-card py-0 ring-0">
          <CardHeader className="px-6 pt-6">
            <CardTitle className="text-xl font-semibold">Profile</CardTitle>
            <CardDescription>
              Your name is shown in the workspace.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-6 pb-6">
            <form
              className="space-y-4"
              onSubmit={profileForm.handleSubmit(onSaveProfile)}
              noValidate
            >
              <div className="grid gap-4 sm:grid-cols-2">
                <AuthField
                  id="account-first-name"
                  label="First name"
                  autoComplete="given-name"
                  error={profileForm.formState.errors.firstName?.message}
                  registration={profileForm.register("firstName")}
                />
                <AuthField
                  id="account-last-name"
                  label="Last name"
                  autoComplete="family-name"
                  error={profileForm.formState.errors.lastName?.message}
                  registration={profileForm.register("lastName")}
                />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-semibold">Email</p>
                <p className="text-sm text-body">{user.email}</p>
              </div>
              <AuthSubmit pending={updateProfile.isPending}>
                Save profile
              </AuthSubmit>
            </form>
          </CardContent>
        </Card>

        <Card className="rounded-[24px] bg-card py-0 ring-0">
          <CardHeader className="px-6 pt-6">
            <CardTitle className="text-xl font-semibold">Password</CardTitle>
            <CardDescription>
              Changing it signs you out of this browser.
            </CardDescription>
          </CardHeader>
          <CardContent className="px-6 pb-6">
            <form
              className="space-y-4"
              onSubmit={passwordForm.handleSubmit(onChangePassword)}
              noValidate
            >
              <AuthField
                id="current-password"
                label="Current password"
                type="password"
                autoComplete="current-password"
                error={passwordForm.formState.errors.currentPassword?.message}
                registration={passwordForm.register("currentPassword")}
              />
              <AuthField
                id="account-new-password"
                label="New password"
                type="password"
                autoComplete="new-password"
                error={passwordForm.formState.errors.newPassword?.message}
                registration={passwordForm.register("newPassword")}
              />
              <AuthField
                id="account-new-password-confirm"
                label="Confirm new password"
                type="password"
                autoComplete="new-password"
                error={
                  passwordForm.formState.errors.newPasswordConfirm?.message
                }
                registration={passwordForm.register("newPasswordConfirm")}
              />
              <AuthSubmit pending={changePassword.isPending}>
                Change password
              </AuthSubmit>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
