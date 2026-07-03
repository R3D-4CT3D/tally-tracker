import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AuthCard } from "../components/AuthCard";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { useAcceptInviteMutation } from "../features/auth/hooks";
import { errorMessage } from "../lib/errors";

export function InviteAcceptPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const accept = useAcceptInviteMutation();

  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    try {
      await accept.mutateAsync({ token, email, display_name: displayName, password });
      navigate("/dashboard", { replace: true });
    } catch {
      // surfaced via accept.error below
    }
  }

  if (!token) {
    return (
      <AuthCard title={t("invite.title")}>
        <ErrorBanner message={t("invite.missingToken")} />
      </AuthCard>
    );
  }

  return (
    <AuthCard title={t("invite.title")} subtitle={t("invite.subtitle")}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <FormField
          label={t("invite.displayNameLabel")}
          name="display_name"
          required
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
        <FormField
          label={t("invite.emailLabel")}
          name="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <FormField
          label={t("invite.passwordLabel")}
          name="password"
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <ErrorBanner message={errorMessage(accept.error, t("common.genericError"))} />
        <PrimaryButton type="submit" disabled={accept.isPending}>
          {accept.isPending ? t("invite.submitting") : t("invite.submit")}
        </PrimaryButton>
      </form>
    </AuthCard>
  );
}
