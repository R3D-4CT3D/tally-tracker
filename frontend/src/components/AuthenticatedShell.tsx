import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useTheme } from "../design-system/useTheme";
import { useLogoutMutation, useMe } from "../features/auth/hooks";
import { MobileBottomNav } from "./MobileBottomNav";
import { MobileMoreSheet } from "./MobileMoreSheet";

const NAV_LINKS = [
  { to: "/dashboard", labelKey: "nav.dashboard" },
  { to: "/transactions", labelKey: "nav.transactions" },
  { to: "/accounts", labelKey: "nav.accounts" },
  { to: "/categories", labelKey: "nav.categories" },
  { to: "/import", labelKey: "nav.import" },
  { to: "/rules", labelKey: "nav.rules" },
  { to: "/bills", labelKey: "nav.bills" },
  { to: "/debts", labelKey: "nav.debts" },
  { to: "/goals", labelKey: "nav.goals" },
] as const;

function SunIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-4 w-4">
      <circle cx="12" cy="12" r="4" />
      <path
        strokeLinecap="round"
        d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
      <path d="M20.354 15.354A9 9 0 0 1 8.646 3.646 9.003 9.003 0 1 0 20.354 15.354Z" />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

export function AuthenticatedShell() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const me = useMe();
  const logout = useLogoutMutation();
  const { theme, toggleTheme } = useTheme();
  const [moreOpen, setMoreOpen] = useState(false);

  async function handleLogout() {
    // Navigate explicitly rather than relying on RequireAuth reacting to the
    // `me` query invalidating — queryClient.removeQueries() doesn't force
    // already-mounted observers to refetch immediately, so the dashboard
    // kept rendering stale "logged in" state after a real, successful
    // server-side logout until something else (e.g. a manual reload)
    // triggered a fresh fetch. Logout is a known, deliberate action; we
    // don't need to infer it reactively.
    await logout.mutateAsync();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen bg-surface text-text-primary">
      <header className="relative flex items-center justify-between gap-3 border-b border-border/10 px-4 py-4 md:px-6">
        <div className="flex shrink-0 items-baseline gap-3">
          <span className="font-display text-lg font-semibold tracking-tight">
            {t("app.title")}
          </span>
          {me.data ? (
            <span className="hidden text-sm text-text-primary/60 lg:inline">
              {me.data.household_name}
            </span>
          ) : null}
        </div>
        <nav className="hidden min-w-0 items-center gap-4 overflow-x-auto md:flex">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `shrink-0 text-sm font-medium transition-colors ${
                  isActive ? "text-green-500" : "text-text-primary/70 hover:text-text-primary"
                }`
              }
            >
              {t(link.labelKey)}
            </NavLink>
          ))}
        </nav>
        <div className="flex shrink-0 items-center gap-2 md:gap-4">
          {me.data ? (
            <span className="hidden text-sm lg:inline">
              {t("nav.greeting", { name: me.data.display_name })}
            </span>
          ) : null}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={t(theme === "dark" ? "nav.switchToLight" : "nav.switchToDark")}
            className="flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-border/20 transition-colors hover:bg-border/5"
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
          </button>
          <button
            type="button"
            onClick={handleLogout}
            disabled={logout.isPending}
            className="hidden min-h-11 items-center rounded-lg border border-border/20 px-3 text-sm font-medium transition-colors hover:bg-border/5 disabled:opacity-60 md:flex"
          >
            {t("nav.logout")}
          </button>
          <button
            type="button"
            onClick={() => setMoreOpen((open) => !open)}
            aria-label={t("nav.more")}
            aria-expanded={moreOpen}
            className="flex min-h-11 min-w-11 items-center justify-center rounded-lg border border-border/20 transition-colors hover:bg-border/5 md:hidden"
          >
            <MoreIcon />
          </button>
        </div>
        <MobileMoreSheet
          open={moreOpen}
          onClose={() => setMoreOpen(false)}
          onLogout={handleLogout}
          logoutPending={logout.isPending}
        />
      </header>
      <main className="p-4 pb-24 md:p-6 md:pb-6">
        <Outlet />
      </main>
      <MobileBottomNav />
    </div>
  );
}
