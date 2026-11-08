import { Route, Routes } from "react-router-dom";

import { ROUTES } from "@/constants/routes";
import { AccountPage } from "@/features/auth/components/account-page";
import { AdminUsersPage } from "@/features/auth/components/admin-users-page";
import { ForgotPasswordPage } from "@/features/auth/components/forgot-password-page";
import { ResetPasswordPage } from "@/features/auth/components/reset-password-page";
import {
  GuestOnly,
  HomeRedirect,
  ProtectedLayout,
  RequirePermission,
  RequirePlatformAdmin,
  RequireStoreAdmin,
  StoreGate,
} from "@/features/auth/components/route-guards";
import { SignInPage } from "@/features/auth/components/sign-in-page";
import { SignUpPage } from "@/features/auth/components/sign-up-page";
import { BillingPage } from "@/features/billing/components/billing-page";
import { CustomerDetailPage } from "@/features/customers/components/customer-detail-page";
import { CustomerFormPage } from "@/features/customers/components/customer-form-page";
import { CustomersPage } from "@/features/customers/components/customers-page";
import { AcceptInvitePage } from "@/features/invitations/components/accept-invite-page";
import { DemoPage } from "@/features/demo/components/demo-page";
import { OrderDetailPage } from "@/features/orders/components/order-detail-page";
import { OrderFormPage } from "@/features/orders/components/order-form-page";
import { OrdersPage } from "@/features/orders/components/orders-page";
import { ProductDetailPage } from "@/features/products/components/product-detail-page";
import { ProductFormPage } from "@/features/products/components/product-form-page";
import { PaymentReturnPage } from "@/features/payments/components/payment-return-page";
import { ProductsPage } from "@/features/products/components/products-page";
import { AdminStoresPage } from "@/features/stores/components/admin-stores-page";
import { StoreOnboardingPage } from "@/features/stores/components/store-onboarding-page";
import { RolesPage } from "@/features/team/components/roles-page";
import { TeamUsersPage } from "@/features/team/components/team-users-page";

/**
 * Route tree. Layers, outermost first:
 *   ProtectedLayout  – must be signed in, renders the app shell
 *   StoreGate        – store must be usable (not suspended / unpaid)
 *   Require*         – role permission checks (the API enforces them too)
 */
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
      <Route path={ROUTES.acceptInvite()} element={<AcceptInvitePage />} />
      <Route path={ROUTES.pay.return()} element={<PaymentReturnPage />} />

      <Route element={<ProtectedLayout />}>
        <Route path={ROUTES.account()} element={<AccountPage />} />

        {/* Setup and billing stay reachable while the store is unpaid. */}
        <Route element={<StoreGate allowUnpaid />}>
          <Route
            path={ROUTES.stores.onboarding()}
            element={<StoreOnboardingPage />}
          />
          <Route element={<RequireStoreAdmin />}>
            <Route path={ROUTES.billing()} element={<BillingPage />} />
          </Route>
        </Route>

        <Route element={<StoreGate />}>
          <Route element={<RequirePermission permission="orders.read" />}>
            <Route path={ROUTES.orders.root()} element={<OrdersPage />} />
            <Route
              path={ROUTES.orders.detail(":id")}
              element={<OrderDetailPage />}
            />
          </Route>
          <Route element={<RequirePermission permission="orders.update" />}>
            <Route
              path={ROUTES.orders.edit(":id")}
              element={<OrderFormPage />}
            />
          </Route>

          <Route element={<RequirePermission permission="products.read" />}>
            <Route path={ROUTES.products.root()} element={<ProductsPage />} />
            <Route
              path={ROUTES.products.detail(":id")}
              element={<ProductDetailPage />}
            />
          </Route>
          <Route element={<RequirePermission permission="products.update" />}>
            <Route
              path={ROUTES.products.edit(":id")}
              element={<ProductFormPage />}
            />
          </Route>

          <Route element={<RequirePermission permission="users.read" />}>
            <Route path={ROUTES.team.users()} element={<TeamUsersPage />} />
          </Route>
          <Route element={<RequireStoreAdmin />}>
            <Route path={ROUTES.team.roles()} element={<RolesPage />} />
          </Route>

          <Route element={<RequirePermission permission="customers.read" />}>
            <Route path={ROUTES.customers.root()} element={<CustomersPage />} />
            <Route
              path={ROUTES.customers.detail(":id")}
              element={<CustomerDetailPage />}
            />
          </Route>
          <Route element={<RequirePermission permission="customers.create" />}>
            <Route
              path={ROUTES.customers.new()}
              element={<CustomerFormPage />}
            />
          </Route>
          <Route element={<RequirePermission permission="customers.update" />}>
            <Route
              path={ROUTES.customers.edit(":id")}
              element={<CustomerFormPage />}
            />
          </Route>

          <Route path={ROUTES.demo.root()} element={<DemoPage />} />
        </Route>

        <Route element={<RequirePlatformAdmin />}>
          <Route path={ROUTES.admin.stores()} element={<AdminStoresPage />} />
          <Route path={ROUTES.admin.users()} element={<AdminUsersPage />} />
        </Route>
      </Route>

      <Route path="*" element={<HomeRedirect />} />
    </Routes>
  );
}
