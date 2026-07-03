import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import en from "./locales/en.json";

// English is the only V1 locale (spec §6b), but every user-facing string routes
// through this layer from day one — retrofitting i18n later is much more
// expensive than wiring it up now while there's almost no UI copy to migrate.
void i18n.use(initReactI18next).init({
  resources: { en: { translation: en } },
  lng: "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export default i18n;
