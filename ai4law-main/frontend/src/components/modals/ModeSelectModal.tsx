import { ModalShell } from "../common/ModalShell";
import { useLang } from "../../lib/language";
import type { LaunchMode } from "../../lib/domain";

type ModeSelectModalProps = {
  onClose: () => void;
  onSelect: (mode: LaunchMode) => void;
};

export function ModeSelectModal({ onClose, onSelect }: ModeSelectModalProps) {
  const { t } = useLang();

  const modes: Array<{ id: LaunchMode; title: string; desc: string; badge: string }> = [
    { id: "rapid", title: t("modeQuick"), desc: t("modeQuickDesc"), badge: "R-01" },
    { id: "draft", title: t("modeDraft"), desc: t("modeDraftDesc"), badge: "D-02" },
    { id: "matrix", title: t("modeMatrix"), desc: t("modeMatrixDesc"), badge: "M-03" }
  ];

  return (
    <ModalShell title={t("modeTitle")} subtitle={t("modeDesc")} onClose={onClose}>
      <div className="grid gap-3 md:grid-cols-3">
        {modes.map((mode) => (
          <button key={mode.id} className="mode-card" onClick={() => onSelect(mode.id)}>
            <span className="mode-badge">{mode.badge}</span>
            <h4 className="font-display text-lg text-ink">{mode.title}</h4>
            <p className="text-sm text-scientific-800/80">{mode.desc}</p>
          </button>
        ))}
      </div>
    </ModalShell>
  );
}
