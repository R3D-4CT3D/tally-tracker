import { Navigate } from "react-router-dom";

import { PageSpinner } from "../components/PageSpinner";
import { useMe, useSetupStatus } from "../features/auth/hooks";

export function RootRedirect() {
  const setupStatus = useSetupStatus();
  const me = useMe();

  if (setupStatus.isLoading) return <PageSpinner />;
  if (!setupStatus.data?.is_setup) return <Navigate to="/setup" replace />;

  if (me.isLoading) return <PageSpinner />;
  if (me.isError) return <Navigate to="/login" replace />;
  return <Navigate to="/dashboard" replace />;
}
