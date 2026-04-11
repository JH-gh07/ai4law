import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import SuperDesignWorkspace from "../integrations/superdesign002/Component.jsx";
import type { TaskSpace } from "../lib/domain";
import embeddedStyles from "../integrations/superdesign002/superdesign-embedded.css?raw";

const STYLE_ID = "superdesign-002-inline-style";

type SuperDesign002PageProps = {
  taskSpace?: TaskSpace;
};

const WORKSPACE_TABS = [
  { id: "details", label: "Details" },
  { id: "canvas", label: "Canvas" },
  { id: "report", label: "报告" },
  { id: "terminal", label: "Terminal" }
];

export function SuperDesign002Page({ taskSpace }: SuperDesign002PageProps) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("details");

  const workspaceName = useMemo(() => {
    if (!taskSpace) return "工作台";
    return taskSpace.name;
  }, [taskSpace]);

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
    <section style={{ padding: "8px", width: "100%", maxWidth: "none" }}>
      <SuperDesignWorkspace
        appName="AI4Law"
        workspaceName={workspaceName}
        tabs={WORKSPACE_TABS}
        activeTabId={activeTab}
        onSelectTab={(tabId: string) => setActiveTab(tabId)}
        onBackToTasks={() => navigate("/tasks")}
        onOpenReports={() => navigate("/reports")}
        onOpenEvidence={() => navigate("/evidence")}
        onOpenDocs={() => navigate("/docs")}
      />
    </section>
  );
}
