import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import fr from "./fr.json";
import ar from "./ar.json";

const RTL_LANGS = new Set(["ar"]);

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      fr: { translation: fr },
      ar: { translation: ar },
    },
    fallbackLng: "fr",
    supportedLngs: ["fr", "ar"],
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "vita_form_lang",
      caches: ["localStorage"],
    },
  });

const applyDir = (lng) => {
  const dir = RTL_LANGS.has(lng) ? "rtl" : "ltr";
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("lang", lng);
    document.documentElement.setAttribute("dir", dir);
  }
};

applyDir(i18n.resolvedLanguage || i18n.language || "fr");
i18n.on("languageChanged", applyDir);

export const isRtl = (lng) => RTL_LANGS.has(lng);

export default i18n;
