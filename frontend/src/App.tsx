import { Navigate, Route, Routes } from "react-router-dom";

import { AuthenticatedShell } from "./components/AuthenticatedShell";
import { AccountsPage } from "./pages/AccountsPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { DashboardPage } from "./pages/DashboardPage";
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
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/transactions" element={<TransactionsPage />} />
          <Route path="/transactions/new" element={<TransactionFormPage />} />
          <Route path="/transactions/:transactionId/edit" element={<TransactionFormPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/import/history" element={<ImportHistoryPage />} />
          <Route path="/rules" element={<RulesPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
