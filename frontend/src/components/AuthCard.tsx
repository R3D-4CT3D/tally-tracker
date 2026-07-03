import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function AuthCard({ title, subtitle, children }: AuthCardProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-linen px-4 py-12 dark:bg-charcoal">
      <div className="w-full max-w-md rounded-2xl border border-charcoal/10 bg-white/60 p-8 shadow-xl shadow-charcoal/5 backdrop-blur dark:border-linen/10 dark:bg-white/[0.03] dark:shadow-black/20">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-charcoal dark:text-linen">
          {title}
        </h1>
        {subtitle ? (
          <p className="mt-1 text-sm text-charcoal/60 dark:text-linen/60">{subtitle}</p>
        ) : null}
        <div className="mt-6">{children}</div>
      </div>
    </main>
  );
}
