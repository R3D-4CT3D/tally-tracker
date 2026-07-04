import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useLogoutMutation, useMe } from "../features/auth/hooks";

const NAV_LINKS = [
  { to: "/dashboard", labelKey: "nav.dashboard" },
  { to: "/transactions", labelKey: "nav.transactions" },
  { to: "/accounts", labelKey: "nav.accounts" },
  { to: "/categories", labelKey: "nav.categories" },
  { to: "/import", labelKey: "nav.import" },
  { to: "/rules", labelKey: "nav.rules" },
] as const;

export function AuthenticatedShell() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const me = useMe();
  const logout = useLogoutMutation();

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
    <div className="min-h-screen bg-linen text-charcoal dark:bg-charcoal dark:text-linen">
      <header className="flex items-center justify-between border-b border-charcoal/10 px-6 py-4 dark:border-linen/10">
        <div className="flex items-baseline gap-3">
          <span className="font-display text-lg font-semibold tracking-tight">
            {t("app.title")}
          </span>
          {me.data ? (
            <span className="text-sm text-charcoal/60 dark:text-linen/60">
              {me.data.household_name}
            </span>
          ) : null}
        </div>
        <nav className="flex items-center gap-4">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors ${
                  isActive
                    ? "text-ember"
                    : "text-charcoal/70 hover:text-charcoal dark:text-linen/70 dark:hover:text-linen"
                }`
              }
            >
              {t(link.labelKey)}
            </NavLink>
          ))}
        </nav>
        <div className="flex items-center gap-4">
          {me.data ? (
            <span className="text-sm">{t("nav.greeting", { name: me.data.display_name })}</span>
          ) : null}
          <button
            type="button"
            onClick={handleLogout}
            disabled={logout.isPending}
            className="rounded-lg border border-charcoal/20 px-3 py-1.5 text-sm font-medium transition-colors hover:bg-charcoal/5 disabled:opacity-60 dark:border-linen/20 dark:hover:bg-linen/5"
          >
            {t("nav.logout")}
          </button>
        </div>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
