import { Navigate, Outlet } from "react-router-dom";

import { PageSpinner } from "../components/PageSpinner";
import { useSetupStatus } from "../features/auth/hooks";

/** Setup only ever succeeds once per instance — once it's done, this page
 * should never be reachable again; send visitors to /login instead. */
export function SetupGate() {
  const { data, isLoading } = useSetupStatus();
  if (isLoading) return <PageSpinner />;
  if (data?.is_setup) return <Navigate to="/login" replace />;
  return <Outlet />;
}
