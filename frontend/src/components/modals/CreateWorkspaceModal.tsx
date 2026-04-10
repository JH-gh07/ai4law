import { useState } from "react";
import { ModalShell } from "../common/ModalShell";
import { useLang } from "../../lib/language";
import type { Jurisdiction, LaunchMode } from "../../lib/domain";

type CreateWorkspaceModalProps = {
  mode: LaunchMode;
  onClose: () => void;
  onCreate: (config: { mode: LaunchMode; name: string; jurisdiction: Jurisdiction }) => void;
};

export function CreateWorkspaceModal({ mode, onClose, onCreate }: CreateWorkspaceModalProps) {
  const { t, lang } = useLang();
  const [name, setName] = useState(lang === "zh" ? "跨境数据项目" : "Cross-Border Program");
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>("CN");

  return (
    <ModalShell title={t("createTitle")} subtitle={t("createDesc")} onClose={onClose}>
      <div className="space-y-3">
        <label className="field-wrap">
          <span>{t("nameLabel")}</span>
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>

        <label className="field-wrap">
          <span>{t("jurisdictionLabel")}</span>
          <select value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value as "CN" | "EU" | "US") }>
            <option value="CN">CN</option>
            <option value="EU">EU</option>
            <option value="US">US</option>
          </select>
        </label>
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <button className="pill-btn" onClick={onClose}>{t("cancelBtn")}</button>
        <button className="pill-btn-primary" onClick={() => onCreate({ mode, name, jurisdiction })}>{t("createBtn")}</button>
      </div>
    </ModalShell>
  );
}
