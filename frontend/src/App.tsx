import { useTranslation } from "react-i18next";

function App() {
  const { t } = useTranslation();

  return (
    <main className="flex min-h-screen items-center justify-center bg-linen text-charcoal dark:bg-charcoal dark:text-linen">
      <h1 className="font-display text-3xl">{t("app.title")}</h1>
    </main>
  );
}

export default App;
