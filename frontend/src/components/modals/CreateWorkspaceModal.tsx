import { useState } from "react";
import { ModalShell } from "../common/ModalShell";
import { useLang } from "../../lib/language";
import type { Jurisdiction, LaunchMode } from "../../lib/domain";
import {
  buildSuggestedTaskName,
  getDefaultTaskTemplate,
  getTaskTemplateInputHint,
  getTaskTemplateOutputHint,
  getTaskTemplateSubtitle,
  getTaskTemplateTitle,
  listTaskTemplatesByJurisdiction
} from "../../lib/task-templates";

type CreateWorkspaceModalProps = {
  mode: LaunchMode;
  onClose: () => void;
  onCreate: (config: { mode: LaunchMode; name: string; jurisdiction: Jurisdiction; taskTemplateId: string }) => void;
};

export function CreateWorkspaceModal({ mode, onClose, onCreate }: CreateWorkspaceModalProps) {
  const { t, lang } = useLang();
  const [jurisdiction, setJurisdiction] = useState<Jurisdiction>("CN");
  const [nameEdited, setNameEdited] = useState(false);
  const [taskTemplateId, setTaskTemplateId] = useState(getDefaultTaskTemplate("CN").id);
  const [name, setName] = useState(buildSuggestedTaskName(getDefaultTaskTemplate("CN"), lang));

  const templates = listTaskTemplatesByJurisdiction(jurisdiction);
  const selectedTemplate = templates.find((item) => item.id === taskTemplateId) ?? templates[0] ?? getDefaultTaskTemplate(jurisdiction);

  const onJurisdictionChange = (next: Jurisdiction) => {
    setJurisdiction(next);
    const defaultTemplate = getDefaultTaskTemplate(next);
    setTaskTemplateId(defaultTemplate.id);
    if (!nameEdited) {
      setName(buildSuggestedTaskName(defaultTemplate, lang));
    }
  };

  const onSelectTemplate = (templateId: string) => {
    setTaskTemplateId(templateId);
    if (!nameEdited) {
      const picked = templates.find((item) => item.id === templateId);
      if (picked) {
        setName(buildSuggestedTaskName(picked, lang));
      }
    }
  };

  return (
    <ModalShell title={t("createTitle")} subtitle={t("createDesc")} onClose={onClose}>
      <div className="space-y-3">
        <label className="field-wrap">
          <span>{t("nameLabel")}</span>
          <input
            value={name}
            onChange={(e) => {
              setName(e.target.value);
              setNameEdited(true);
            }}
          />
        </label>

        <label className="field-wrap">
          <span>{t("jurisdictionLabel")}</span>
          <select value={jurisdiction} onChange={(e) => onJurisdictionChange(e.target.value as "CN" | "EU" | "US") }>
            <option value="CN">CN</option>
            <option value="EU">EU</option>
            <option value="US">US</option>
          </select>
        </label>

        <div className="create-template-section">
          <span className="create-template-label">{t("taskTemplateLabel")}</span>
          <p className="create-template-hint">{t("taskTemplateBackendHint")}</p>
          <div className="create-template-grid">
            {templates.map((template) => (
              <button
                key={template.id}
                className={`create-template-card ${template.id === selectedTemplate.id ? "active" : ""}`}
                onClick={() => onSelectTemplate(template.id)}
                type="button"
              >
                <strong>{getTaskTemplateTitle(template, lang)}</strong>
                <p>{getTaskTemplateSubtitle(template, lang)}</p>
                <small>{getTaskTemplateInputHint(template, lang)}</small>
                <small>{getTaskTemplateOutputHint(template, lang)}</small>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-6 flex justify-end gap-2">
        <button className="pill-btn" onClick={onClose}>{t("cancelBtn")}</button>
        <button
          className="pill-btn-primary"
          onClick={() =>
            onCreate({
              mode,
              name: name.trim() || buildSuggestedTaskName(selectedTemplate, lang),
              jurisdiction,
              taskTemplateId: selectedTemplate.id
            })
          }
        >
          {t("createBtn")}
        </button>
      </div>
    </ModalShell>
  );
}
