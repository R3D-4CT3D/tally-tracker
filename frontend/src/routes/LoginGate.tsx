import { Navigate, Outlet } from "react-router-dom";

import { PageSpinner } from "../components/PageSpinner";
import { useMe } from "../features/auth/hooks";

export function LoginGate() {
  const { isLoading, isSuccess } = useMe();
  if (isLoading) return <PageSpinner />;
  if (isSuccess) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}
