import { Route, Routes } from "react-router-dom";

import { ROUTES } from "@/constants/routes";
import { AccountPage } from "@/features/auth/components/account-page";
import { AppShell } from "@/features/auth/components/app-shell";
import { ForgotPasswordPage } from "@/features/auth/components/forgot-password-page";
import { ResetPasswordPage } from "@/features/auth/components/reset-password-page";
import {
  GuestOnly,
  HomeRedirect,
  RequireAuth,
} from "@/features/auth/components/route-guards";
import { SignInPage } from "@/features/auth/components/sign-in-page";
import { SignUpPage } from "@/features/auth/components/sign-up-page";
import { DemoPage } from "@/features/demo/components/demo-page";
import { ProductDetailPage } from "@/features/products/components/product-detail-page";
import { ProductFormPage } from "@/features/products/components/product-form-page";
import { ProductsPage } from "@/features/products/components/products-page";
import { StoreOnboardingPage } from "@/features/stores/components/store-onboarding-page";

export function App() {
  return (
    <Routes>
      <Route path={ROUTES.root()} element={<HomeRedirect />} />
      <Route
        path={ROUTES.signIn()}
        element={
          <GuestOnly>
            <SignInPage />
          </GuestOnly>
        }
      />
      <Route
        path={ROUTES.signUp()}
        element={
          <GuestOnly>
            <SignUpPage />
          </GuestOnly>
        }
      />
      <Route
        path={ROUTES.forgotPassword()}
        element={
          <GuestOnly>
            <ForgotPasswordPage />
          </GuestOnly>
        }
      />
      <Route path={ROUTES.resetPassword()} element={<ResetPasswordPage />} />
      <Route
        path={ROUTES.account()}
        element={
          <RequireAuth>
            <AppShell>
              <AccountPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path={ROUTES.stores.onboarding()}
        element={
          <RequireAuth>
            <AppShell>
              <StoreOnboardingPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path={ROUTES.products.root()}
        element={
          <RequireAuth>
            <AppShell>
              <ProductsPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path={ROUTES.products.new()}
        element={
          <RequireAuth>
            <AppShell>
              <ProductFormPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path={ROUTES.products.edit(":id")}
        element={
          <RequireAuth>
            <AppShell>
              <ProductFormPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path={ROUTES.products.detail(":id")}
        element={
          <RequireAuth>
            <AppShell>
              <ProductDetailPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route
        path={ROUTES.demo.root()}
        element={
          <RequireAuth>
            <AppShell>
              <DemoPage />
            </AppShell>
          </RequireAuth>
        }
      />
      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  );
}
