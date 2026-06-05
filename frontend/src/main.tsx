import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { LanguageProvider } from "./lib/language";
import type { Language } from "./lib/i18n";
import { TraceProbe } from "./TraceProbe";
import "./styles/tokens.css";
import "./styles/app.css";

const params = new URLSearchParams(globalThis.location.search);
const traceProbeEnabled = params.get("trace_probe") === "1";
const traceProbeLang = params.get("lang") === "zh" ? "zh" : "en";

function TraceProbeApp({ lang }: { lang: Language }) {
  globalThis.localStorage?.setItem("ai4law_ui_lang", lang);
  return (
    <LanguageProvider>
      <TraceProbe lang={lang} />
    </LanguageProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {traceProbeEnabled ? <TraceProbeApp lang={traceProbeLang} /> : <App />}
  </React.StrictMode>
);
