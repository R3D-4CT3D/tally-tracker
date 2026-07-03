import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { AuthCard } from "../components/AuthCard";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { useSetupMutation } from "../features/auth/hooks";
import { errorMessage } from "../lib/errors";

export function SetupPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const setup = useSetupMutation();

  const [householdName, setHouseholdName] = useState("");
  const [ownerDisplayName, setOwnerDisplayName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [ownerPassword, setOwnerPassword] = useState("");

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await setup.mutateAsync({
        household_name: householdName,
        owner_display_name: ownerDisplayName,
        owner_email: ownerEmail,
        owner_password: ownerPassword,
      });
      navigate("/dashboard", { replace: true });
    } catch {
      // surfaced via setup.error below
    }
  }

  return (
    <AuthCard title={t("setup.title")} subtitle={t("setup.subtitle")}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <FormField
          label={t("setup.householdNameLabel")}
          name="household_name"
          required
          value={householdName}
          onChange={(e) => setHouseholdName(e.target.value)}
        />
        <FormField
          label={t("setup.ownerDisplayNameLabel")}
          name="owner_display_name"
          required
          value={ownerDisplayName}
          onChange={(e) => setOwnerDisplayName(e.target.value)}
        />
        <FormField
          label={t("setup.ownerEmailLabel")}
          name="owner_email"
          type="email"
          required
          value={ownerEmail}
          onChange={(e) => setOwnerEmail(e.target.value)}
        />
        <FormField
          label={t("setup.ownerPasswordLabel")}
          name="owner_password"
          type="password"
          required
          minLength={8}
          value={ownerPassword}
          onChange={(e) => setOwnerPassword(e.target.value)}
        />
        <ErrorBanner message={errorMessage(setup.error, t("common.genericError"))} />
        <PrimaryButton type="submit" disabled={setup.isPending}>
          {setup.isPending ? t("setup.submitting") : t("setup.submit")}
        </PrimaryButton>
      </form>
    </AuthCard>
  );
}
