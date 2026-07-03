import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AuthCard } from "../components/AuthCard";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { useLoginMutation } from "../features/auth/hooks";
import { errorMessage } from "../lib/errors";

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useLoginMutation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await login.mutateAsync({ email, password });
      navigate("/dashboard", { replace: true });
    } catch {
      // surfaced via login.error below
    }
  }

  return (
    <AuthCard title={t("login.title")} subtitle={t("login.subtitle")}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <FormField
          label={t("login.emailLabel")}
          name="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <FormField
          label={t("login.passwordLabel")}
          name="password"
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <ErrorBanner message={errorMessage(login.error, t("common.genericError"))} />
        <PrimaryButton type="submit" disabled={login.isPending}>
          {login.isPending ? t("login.submitting") : t("login.submit")}
        </PrimaryButton>
      </form>
    </AuthCard>
  );
}
