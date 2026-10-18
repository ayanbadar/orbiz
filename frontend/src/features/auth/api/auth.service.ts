import type {
  AuthSession,
  ChangePasswordRequest,
  ForgotPasswordResult,
  LoginRequest,
  RegisterRequest,
  ResetPasswordRequest,
  UpdateProfileRequest,
  UserProfile,
} from "@/features/auth/types";
import { api } from "@/lib/api";

const ROOT = "/api/v1/auth";

export class AuthService {
  static async register(body: RegisterRequest): Promise<AuthSession> {
    const response = await api.post<AuthSession>(`${ROOT}/register/`, body);
    return response.data;
  }

  static async login(body: LoginRequest): Promise<AuthSession> {
    const response = await api.post<AuthSession>(`${ROOT}/login/`, body);
    return response.data;
  }

  static async logout(refresh: string): Promise<void> {
    await api.post(`${ROOT}/logout/`, { refresh });
  }

  static async me(): Promise<UserProfile> {
    const response = await api.get<UserProfile>(`${ROOT}/me/`);
    return response.data;
  }

  static async updateProfile(body: UpdateProfileRequest): Promise<UserProfile> {
    const response = await api.patch<UserProfile>(`${ROOT}/me/`, body);
    return response.data;
  }

  static async changePassword(body: ChangePasswordRequest): Promise<void> {
    await api.post(`${ROOT}/change-password/`, body);
  }

  static async forgotPassword(email: string): Promise<ForgotPasswordResult> {
    const response = await api.post<ForgotPasswordResult>(
      `${ROOT}/forgot-password/`,
      { email },
    );
    return response.data;
  }

  static async resetPassword(body: ResetPasswordRequest): Promise<void> {
    await api.post(`${ROOT}/reset-password/`, body);
  }
}
