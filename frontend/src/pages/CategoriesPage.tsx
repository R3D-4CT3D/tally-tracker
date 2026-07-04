import { useState } from "react";
import type { FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { ErrorBanner } from "../components/ErrorBanner";
import { FormField } from "../components/FormField";
import { PrimaryButton } from "../components/PrimaryButton";
import { SelectField } from "../components/SelectField";
import {
  useCategories,
  useCreateCategoryMutation,
  useUpdateCategoryMutation,
} from "../features/categories/hooks";
import type { Category } from "../features/categories/types";
import { errorMessage } from "../lib/errors";

interface CategoryFormState {
  name: string;
  parentId: string;
  icon: string;
  color: string;
}

const EMPTY_FORM: CategoryFormState = { name: "", parentId: "", icon: "🏷️", color: "#71717A" };

function toFormState(category: Category): CategoryFormState {
  return {
    name: category.name,
    parentId: category.parent_id ?? "",
    icon: category.icon,
    color: category.color,
  };
}

export function CategoriesPage() {
  const { t } = useTranslation();
  const categories = useCategories();
  const createCategory = useCreateCategoryMutation();
  const updateCategory = useUpdateCategoryMutation();

  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<CategoryFormState>(EMPTY_FORM);

  const activeMutation = editingId ? updateCategory : createCategory;
  const topLevel = categories.data?.filter((c) => c.parent_id === null) ?? [];
  const childrenByParent = new Map<string, Category[]>();
  for (const category of categories.data ?? []) {
    if (category.parent_id) {
      const siblings = childrenByParent.get(category.parent_id) ?? [];
      siblings.push(category);
      childrenByParent.set(category.parent_id, siblings);
    }
  }

  function openCreateForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setIsFormOpen(true);
  }

  function openEditForm(category: Category) {
    setEditingId(category.id);
    setForm(toFormState(category));
    setIsFormOpen(true);
  }

  function closeForm() {
    setIsFormOpen(false);
    setEditingId(null);
    createCategory.reset();
    updateCategory.reset();
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const payload = {
      name: form.name,
      parent_id: form.parentId || null,
      icon: form.icon,
      color: form.color,
    };
    try {
      if (editingId) {
        await updateCategory.mutateAsync({ id: editingId, payload });
      } else {
        await createCategory.mutateAsync(payload);
      }
      closeForm();
    } catch {
      // surfaced via activeMutation.error below
    }
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl font-semibold">{t("categories.title")}</h2>
        <PrimaryButton type="button" className="w-auto px-4 py-2" onClick={openCreateForm}>
          {t("categories.addButton")}
        </PrimaryButton>
      </div>

      {isFormOpen ? (
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-2xl border border-charcoal/10 bg-white/60 p-6 dark:border-linen/10 dark:bg-white/[0.03]"
        >
          <FormField
            label={t("categories.nameLabel")}
            name="name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <SelectField
            label={t("categories.parentLabel")}
            name="parent"
            value={form.parentId}
            onChange={(e) => setForm({ ...form, parentId: e.target.value })}
          >
            <option value="">{t("categories.noParent")}</option>
            {topLevel
              .filter((c) => c.id !== editingId)
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
          </SelectField>
          <div className="grid grid-cols-2 gap-4">
            <FormField
              label={t("accounts.colorLabel")}
              name="color"
              type="color"
              value={form.color}
              onChange={(e) => setForm({ ...form, color: e.target.value })}
            />
            <FormField
              label={t("accounts.iconLabel")}
              name="icon"
              required
              value={form.icon}
              onChange={(e) => setForm({ ...form, icon: e.target.value })}
            />
          </div>
          <ErrorBanner message={errorMessage(activeMutation.error, t("common.genericError"))} />
          <div className="flex gap-3">
            <PrimaryButton
              type="submit"
              disabled={activeMutation.isPending}
              className="w-auto px-4"
            >
              {editingId ? t("categories.saveButton") : t("categories.createButton")}
            </PrimaryButton>
            <button
              type="button"
              onClick={closeForm}
              className="rounded-lg border border-charcoal/20 px-4 py-2.5 text-sm font-medium dark:border-linen/20"
            >
              {t("common.cancel")}
            </button>
          </div>
        </form>
      ) : null}

      <ul className="flex flex-col gap-3">
        {topLevel.map((category) => (
          <li key={category.id} className="flex flex-col gap-2">
            <div className="flex items-center justify-between rounded-xl border border-charcoal/10 bg-white/60 px-4 py-3 dark:border-linen/10 dark:bg-white/[0.03]">
              <div className="flex items-center gap-3">
                <span className="text-lg" aria-hidden>
                  {category.icon}
                </span>
                <span className="font-medium">{category.name}</span>
              </div>
              <button
                type="button"
                onClick={() => openEditForm(category)}
                className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
              >
                {t("common.edit")}
              </button>
            </div>
            {(childrenByParent.get(category.id) ?? []).map((child) => (
              <div
                key={child.id}
                className="ml-8 flex items-center justify-between rounded-xl border border-charcoal/10 bg-white/40 px-4 py-2 dark:border-linen/10 dark:bg-white/[0.02]"
              >
                <div className="flex items-center gap-3">
                  <span className="text-base" aria-hidden>
                    {child.icon}
                  </span>
                  <span className="text-sm">{child.name}</span>
                </div>
                <button
                  type="button"
                  onClick={() => openEditForm(child)}
                  className="text-sm text-charcoal/70 underline-offset-2 hover:underline dark:text-linen/70"
                >
                  {t("common.edit")}
                </button>
              </div>
            ))}
          </li>
        ))}
      </ul>
    </div>
  );
}
