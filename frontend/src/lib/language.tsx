import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { MESSAGES, type Language, type MessageKey } from "./i18n";

const STORAGE_KEY = "ai4law_ui_lang";

type LangContextValue = {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: MessageKey) => string;
};

const LangContext = createContext<LangContextValue | null>(null);

const detectLanguage = (): Language => {
  const local = globalThis.localStorage?.getItem(STORAGE_KEY);
  if (local === "zh" || local === "en") return local;
  return globalThis.navigator?.language?.toLowerCase().startsWith("zh") ? "zh" : "en";
};

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Language>(() => detectLanguage());

  const setLang = (value: Language) => {
    globalThis.localStorage?.setItem(STORAGE_KEY, value);
    setLangState(value);
  };

  const value = useMemo(
    () => ({
      lang,
      setLang,
      t: (key: keyof typeof MESSAGES) => MESSAGES[key][lang]
    }),
    [lang]
  );

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang() {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used inside LanguageProvider");
  return ctx;
}
