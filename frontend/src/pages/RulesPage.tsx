import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { RowActionLink } from "../components/RowActionLink";
import { SecondaryButton } from "../components/SecondaryButton";
import { SelectField } from "../components/SelectField";
import { useAccounts } from "../features/accounts/hooks";
import { useCategories } from "../features/categories/hooks";
import {
  useCreateRuleMutation,
  useDeleteRuleMutation,
  useReorderRulesMutation,
  useRules,
  useUpdateRuleMutation,
} from "../features/rules/hooks";
import type { MatchType, Rule } from "../features/rules/types";
import { errorMessage } from "../lib/errors";

interface RuleFormState {
  matchType: MatchType;
  matchValue: string;
  categoryId: string;
  accountId: string;
  displayName: string;
}

const EMPTY_FORM: RuleFormState = {
  matchType: "contains",
  matchValue: "",
  categoryId: "",
  accountId: "",
  displayName: "",
};

export function RulesPage() {
  const { t } = useTranslation();
  const rules = useRules();
  const categories = useCategories();
  const accounts = useAccounts();
  const createRule = useCreateRuleMutation();
  const updateRule = useUpdateRuleMutation();
  const deleteRule = useDeleteRuleMutation();
  const reorderRules = useReorderRulesMutation();

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [form, setForm] = useState<RuleFormState>(EMPTY_FORM);

  const categoryById = new Map((categories.data ?? []).map((c) => [c.id, c]));
  const accountById = new Map((accounts.data ?? []).map((a) => [a.id, a]));

  function closeForm() {
    setIsFormOpen(false);
    setForm(EMPTY_FORM);
    createRule.reset();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    try {
      await createRule.mutateAsync({
        match_type: form.matchType,
        match_value: form.matchValue,
        set_category_id: form.categoryId,
        account_id: form.accountId || null,
        set_display_name: form.displayName || null,
      });
      closeForm();
    } catch {
      // surfaced via createRule.error below
    }
  }

  async function handleToggleEnabled(rule: Rule) {
    await updateRule.mutateAsync({ id: rule.id, payload: { enabled: !rule.enabled } });
  }

  async function handleDelete(id: string) {
    await deleteRule.mutateAsync(id);
  }

  async function handleMove(index: number, direction: -1 | 1) {
    const list = rules.data ?? [];
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= list.length) return;
    const orderedIds = list.map((r) => r.id);
    [orderedIds[index], orderedIds[targetIndex]] = [orderedIds[targetIndex], orderedIds[index]];
    await reorderRules.mutateAsync(orderedIds);
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("rules.title")}</h2>
        <PrimaryButton type="button" className="px-4 py-2" onClick={() => setIsFormOpen(true)}>
          {t("rules.addButton")}
        </PrimaryButton>
      </div>

      {isFormOpen ? (
        <Card size="form">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <SelectField
            label={t("rules.matchTypeLabel")}
            name="match_type"
            value={form.matchType}
            onChange={(e) => setForm({ ...form, matchType: e.target.value as MatchType })}
          >
            <option value="contains">{t("rules.matchTypeContains")}</option>
            <option value="starts_with">{t("rules.matchTypeStartsWith")}</option>
            <option value="regex">{t("rules.matchTypeRegex")}</option>
          </SelectField>
          <FormField
            label={t("rules.matchValueLabel")}
            name="match_value"
            required
            value={form.matchValue}
            onChange={(e) => setForm({ ...form, matchValue: e.target.value })}
          />
          <SelectField
            label={t("rules.categoryLabel")}
            name="category_id"
            required
            value={form.categoryId}
            onChange={(e) => setForm({ ...form, categoryId: e.target.value })}
          >
            <option value="" disabled>
              {t("rules.selectCategory")}
            </option>
            {(categories.data ?? []).map((c) => (
              <option key={c.id} value={c.id}>
                {c.icon} {c.name}
              </option>
            ))}
          </SelectField>
          <SelectField
            label={t("rules.accountLabel")}
            name="account_id"
            value={form.accountId}
            onChange={(e) => setForm({ ...form, accountId: e.target.value })}
          >
            <option value="">{t("rules.anyAccount")}</option>
            {(accounts.data ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </SelectField>
          <FormField
            label={t("rules.displayNameLabel")}
            name="display_name"
            value={form.displayName}
            onChange={(e) => setForm({ ...form, displayName: e.target.value })}
          />
          <ErrorBanner message={errorMessage(createRule.error, t("common.genericError"))} />
          <div className="flex gap-3">
            <PrimaryButton type="submit" disabled={createRule.isPending} className="px-4">
              {t("rules.createButton")}
            </PrimaryButton>
            <SecondaryButton onClick={closeForm}>{t("common.cancel")}</SecondaryButton>
          </div>
          </form>
        </Card>
      ) : null}

      <ul className="flex flex-col gap-2">
        {(rules.data ?? []).map((rule, index) => {
          const category = categoryById.get(rule.set_category_id);
          const account = rule.account_id ? accountById.get(rule.account_id) : undefined;
          return (
            <li key={rule.id}>
              <Card size="row" className="flex items-center justify-between">
                <div>
                  <p className="font-medium">
                    {t(`rules.matchTypeLabelShort.${rule.match_type}`)} "{rule.match_value}"
                    {account ? ` · ${account.name}` : ""}
                  </p>
                  <p className="text-xs text-text-primary/60">
                    {t("rules.setsCategory")} {category ? `${category.icon} ${category.name}` : ""}
                    {rule.set_display_name ? ` · "${rule.set_display_name}"` : ""}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleMove(index, -1)}
                    disabled={index === 0}
                    className="text-sm disabled:opacity-30"
                    aria-label={t("rules.moveUp")}
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    onClick={() => handleMove(index, 1)}
                    disabled={index === (rules.data?.length ?? 0) - 1}
                    className="text-sm disabled:opacity-30"
                    aria-label={t("rules.moveDown")}
                  >
                    ↓
                  </button>
                  <label className="flex items-center gap-1 text-sm">
                    <input
                      type="checkbox"
                      checked={rule.enabled}
                      onChange={() => handleToggleEnabled(rule)}
                    />
                    {t("rules.enabled")}
                  </label>
                  <RowActionLink onClick={() => handleDelete(rule.id)}>
                    {t("common.delete")}
                  </RowActionLink>
                </div>
              </Card>
            </li>
          );
        })}
      </ul>
      {(rules.data ?? []).length === 0 ? <EmptyState message={t("rules.empty")} /> : null}
    </div>
  );
}
