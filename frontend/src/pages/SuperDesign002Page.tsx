import { useEffect } from "react";
import SuperDesignWorkspace from "../integrations/superdesign002/Component.jsx";
import embeddedStyles from "../integrations/superdesign002/superdesign-embedded.css?raw";

const STYLE_ID = "superdesign-002-inline-style";

export function SuperDesign002Page() {
  useEffect(() => {
    let style = document.getElementById(STYLE_ID) as HTMLStyleElement | null;
    if (!style) {
      style = document.createElement("style");
      style.id = STYLE_ID;
      style.textContent = embeddedStyles;
      document.head.appendChild(style);
    }

    return () => {
      style?.remove();
    };
  }, []);

  return (
    <section className="page-shell" style={{ padding: "8px", maxWidth: "none", width: "100%" }}>
      <SuperDesignWorkspace />
    </section>
  );
}
