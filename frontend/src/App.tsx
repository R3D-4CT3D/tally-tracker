import { Navigate, Route, Routes } from "react-router-dom";

import { AuthenticatedShell } from "./components/AuthenticatedShell";
import { DashboardPage } from "./pages/DashboardPage";
import { InviteAcceptPage } from "./pages/InviteAcceptPage";
import { LoginPage } from "./pages/LoginPage";
import { SetupPage } from "./pages/SetupPage";
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
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
