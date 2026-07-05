import type { ReactNode } from "react";

interface AuthCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export function AuthCard({ title, subtitle, children }: AuthCardProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-border/10 bg-surface-card p-8 shadow-xl shadow-charcoal-950/5 backdrop-blur dark:shadow-black/20">
        <h1 className="font-display text-2xl font-semibold tracking-tight text-text-primary">
          {title}
        </h1>
        {subtitle ? <p className="mt-1 text-sm text-text-primary/60">{subtitle}</p> : null}
        <div className="mt-6">{children}</div>
      </div>
    </main>
  );
}
