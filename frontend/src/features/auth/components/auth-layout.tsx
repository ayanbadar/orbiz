import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Logo } from "@/components/logo";
import { ROUTES } from "@/constants/routes";

type AuthLayoutProps = {
  title: string;
  subtitle: string;
  children: ReactNode;
};

export function AuthLayout({ title, subtitle, children }: AuthLayoutProps) {
  return (
    <div className="min-h-dvh bg-background text-foreground">
      <div className="mx-auto flex min-h-dvh w-full max-w-[1100px] flex-col lg:flex-row">
        <section className="flex flex-col px-5 pt-8 sm:px-10 lg:w-1/2 lg:justify-between lg:py-16 lg:pr-12">
          <Link to={ROUTES.signIn()} className="inline-flex w-fit">
            <Logo />
          </Link>
          <div className="mt-8 lg:mt-0">
            <h1 className="max-w-xl font-heading text-[2.5rem] leading-[0.9] font-black tracking-tight sm:text-6xl lg:text-[4.5rem]">
              {title}
            </h1>
            <p className="mt-4 max-w-md text-base leading-7 text-body sm:text-lg">
              {subtitle}
            </p>
          </div>
          <p className="mt-8 hidden text-sm text-muted-foreground lg:block">
            Orders, stock, and sandbox payments in one workspace.
          </p>
        </section>
        <section className="flex flex-1 items-start px-4 py-8 sm:px-10 lg:items-center lg:py-16">
          <div className="w-full rounded-[24px] bg-card p-6 text-card-foreground sm:p-8">
            {children}
          </div>
        </section>
      </div>
    </div>
  );
}
