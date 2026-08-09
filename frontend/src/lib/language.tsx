/**
 * 语言上下文模块
 *
 * 函数：
 * - LanguageProvider: 语言上下文提供者组件，接收子组件作为参数，并提供语言状态和翻译函数给子组件使用。
 * - useLang: 自定义Hook，用于在子组件中访问语言上下文的值，包括当前语言、设置语言的函数和翻译函数。
 *
 * 类型：
 * - LangContextValue: 语言上下文的值类型，包含当前语言、设置语言的函数和翻译函数。
 */ 
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
