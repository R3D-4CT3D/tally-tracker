import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

const MORE_LINKS = [
  { to: "/accounts", labelKey: "nav.accounts" },
  { to: "/categories", labelKey: "nav.categories" },
  { to: "/import", labelKey: "nav.import" },
  { to: "/rules", labelKey: "nav.rules" },
] as const;

interface MobileMoreSheetProps {
  open: boolean;
  onClose: () => void;
  onLogout: () => void;
  logoutPending: boolean;
}

// A simple slide-down panel from the mobile header, not a 6th bottom-nav
// tab -- the bottom bar stays exactly the 5 requested tabs (Dashboard/
// Transactions/Bills/Debts/Goals). Logout also lives here on mobile, since
// the header's logout button is hidden below md: to save space.
export function MobileMoreSheet({ open, onClose, onLogout, logoutPending }: MobileMoreSheetProps) {
  const { t } = useTranslation();
  if (!open) return null;

  return (
    <div className="absolute inset-x-0 top-full z-30 border-b border-border/10 bg-surface shadow-lg md:hidden">
      <ul className="flex flex-col p-2">
        {MORE_LINKS.map((link) => (
          <li key={link.to}>
            <NavLink
              to={link.to}
              onClick={onClose}
              className={({ isActive }) =>
                `flex min-h-11 items-center rounded-lg px-4 text-sm font-medium ${
                  isActive ? "text-green-500" : "text-text-primary/80 hover:bg-border/5"
                }`
              }
            >
              {t(link.labelKey)}
            </NavLink>
          </li>
        ))}
        <li>
          <button
            type="button"
            onClick={() => {
              onClose();
              onLogout();
            }}
            disabled={logoutPending}
            className="flex min-h-11 w-full items-center rounded-lg px-4 text-left text-sm font-medium text-text-primary/80 hover:bg-border/5 disabled:opacity-60"
          >
            {t("nav.logout")}
          </button>
        </li>
      </ul>
    </div>
  );
}
