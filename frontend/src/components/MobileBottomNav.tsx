import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

const TABS = [
  { to: "/dashboard", labelKey: "nav.dashboard", Icon: HomeIcon },
  { to: "/transactions", labelKey: "nav.transactions", Icon: ListIcon },
  { to: "/bills", labelKey: "nav.bills", Icon: ReceiptIcon },
  { to: "/debts", labelKey: "nav.debts", Icon: CardIcon },
  { to: "/goals", labelKey: "nav.goals", Icon: FlagIcon },
] as const;

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 11.5 12 4l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />
    </svg>
  );
}

function ListIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path strokeLinecap="round" d="M4 6h16M4 12h16M4 18h10" />
    </svg>
  );
}

function ReceiptIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 3h12v18l-3-2-3 2-3-2-3 2Z" />
      <path strokeLinecap="round" d="M9 8h6M9 12h6" />
    </svg>
  );
}

function CardIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <rect x="3" y="6" width="18" height="12" rx="2" />
      <path strokeLinecap="round" d="M3 10h18" />
    </svg>
  );
}

function FlagIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 21V4m0 0h13l-3 4 3 4H5" />
    </svg>
  );
}

// Exactly 5 tabs, fixed to the bottom below md: -- Accounts/Categories/
// Import/Rules live behind the mobile header's "More" sheet instead of a
// 6th tab (see MobileMoreSheet.tsx).
export function MobileBottomNav() {
  const { t } = useTranslation();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 flex border-t border-border/10 bg-surface md:hidden">
      {TABS.map(({ to, labelKey, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `flex min-h-11 flex-1 flex-col items-center justify-center gap-0.5 py-2 text-xs font-medium ${
              isActive ? "text-green-500" : "text-text-primary/60"
            }`
          }
        >
          <Icon />
          {t(labelKey)}
        </NavLink>
      ))}
    </nav>
  );
}
