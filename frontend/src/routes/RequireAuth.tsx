import { Navigate, Outlet } from "react-router-dom";

import { PageSpinner } from "../components/PageSpinner";
import { useMe } from "../features/auth/hooks";

export function RequireAuth() {
  const { isLoading, isError } = useMe();
  if (isLoading) return <PageSpinner />;
  if (isError) return <Navigate to="/login" replace />;
  return <Outlet />;
}
