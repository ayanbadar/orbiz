import { useMutation } from "@tanstack/react-query";

import { AuthService } from "@/features/auth/api/auth.service";
import { useAuth } from "@/features/auth/context/use-auth";
import type {
  ChangePasswordRequest,
  LoginRequest,
  RegisterRequest,
  ResetPasswordRequest,
  UpdateProfileRequest,
} from "@/features/auth/types";
import { getRefreshToken } from "@/lib/auth-token";
import { queryClient } from "@/lib/query-client";
import { AUTH_QUERY_KEYS } from "@/features/auth/api/auth.keys";

export function useLogin() {
  const { setSession } = useAuth();
  return useMutation({
    mutationFn: (body: LoginRequest) => AuthService.login(body),
    onSuccess: (session) => setSession(session),
  });
}

export function useRegister() {
  const { setSession } = useAuth();
  return useMutation({
    mutationFn: (body: RegisterRequest) => AuthService.register(body),
    onSuccess: (session) => setSession(session),
  });
}

export function useLogout() {
  const { clearSession } = useAuth();
  return useMutation({
    mutationFn: async () => {
      const refresh = getRefreshToken();
      if (!refresh) {
        return;
      }
      try {
        await AuthService.logout(refresh);
      } catch {
        // The local session still ends if the server token is already gone.
      }
    },
    onSettled: () => clearSession(),
  });
}

export function useUpdateProfile() {
  return useMutation({
    mutationFn: (body: UpdateProfileRequest) => AuthService.updateProfile(body),
    onSuccess: (user) => {
      queryClient.setQueryData(AUTH_QUERY_KEYS.session(), user);
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (body: ChangePasswordRequest) =>
      AuthService.changePassword(body),
  });
}

export function useForgotPassword() {
  return useMutation({
    mutationFn: (email: string) => AuthService.forgotPassword(email),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: (body: ResetPasswordRequest) => AuthService.resetPassword(body),
  });
}
