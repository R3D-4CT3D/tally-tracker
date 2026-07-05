import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthenticatedShell } from "./components/AuthenticatedShell";
import { PageSpinner } from "./components/PageSpinner";
import { AccountsPage } from "./pages/AccountsPage";
import { BillsPage } from "./pages/BillsPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { DebtsPage } from "./pages/DebtsPage";
import { GoalsPage } from "./pages/GoalsPage";
import { ImportHistoryPage } from "./pages/ImportHistoryPage";
import { ImportPage } from "./pages/ImportPage";
import { InviteAcceptPage } from "./pages/InviteAcceptPage";
import { LoginPage } from "./pages/LoginPage";
import { RulesPage } from "./pages/RulesPage";
import { SetupPage } from "./pages/SetupPage";
import { TransactionFormPage } from "./pages/TransactionFormPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { LoginGate } from "./routes/LoginGate";
import { RequireAuth } from "./routes/RequireAuth";
import { RootRedirect } from "./routes/RootRedirect";
import { SetupGate } from "./routes/SetupGate";

// Lazy-loaded: Recharts (and the dashboard's aggregation hooks) shouldn't
// inflate the login/setup bundle -- that's the actual "<2s on a mid-range
// phone" path, not the dashboard itself.
const DashboardPage = lazy(() =>
  import("./pages/DashboardPage").then((m) => ({ default: m.DashboardPage })),
);

function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />

      <Route element={<SetupGate />}>
        <Route path="/setup" element={<SetupPage />} />
      </Route>

      <Route element={<LoginGate />}>
        <Route path="/login" element={<LoginPage />} />
      </Route>

      <Route path="/invite/accept" element={<InviteAcceptPage />} />

      <Route element={<RequireAuth />}>
        <Route element={<AuthenticatedShell />}>
          <Route
            path="/dashboard"
            element={
              <Suspense fallback={<PageSpinner />}>
                <DashboardPage />
              </Suspense>
            }
          />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/transactions/new" element={<TransactionFormPage />} />
          <Route path="/transactions/:transactionId/edit" element={<TransactionFormPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/import/history" element={<ImportHistoryPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/bills" element={<BillsPage />} />
          <Route path="/debts" element={<DebtsPage />} />
          <Route path="/goals" element={<GoalsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
