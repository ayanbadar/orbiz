export type UserProfile = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
};

export type AuthSession = {
  access: string;
  refresh: string;
  user: UserProfile;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = LoginRequest & {
  password_confirm: string;
  first_name: string;
  last_name: string;
};

export type UpdateProfileRequest = {
  first_name: string;
  last_name: string;
};

export type ChangePasswordRequest = {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
};

export type ForgotPasswordResult = {
  message: string;
  debug_reset_url?: string;
};

export type ResetPasswordRequest = {
  uid: string;
  token: string;
  new_password: string;
  new_password_confirm: string;
};
