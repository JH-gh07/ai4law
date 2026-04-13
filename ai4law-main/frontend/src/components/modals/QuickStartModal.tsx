import { useLang } from "../../lib/language";

type QuickStartModalProps = {
  onClose: () => void;
  onNeverRemind: () => void;
  onStart: () => void;
  onGuided: () => void;
};

export function QuickStartModal({ onClose, onNeverRemind, onStart, onGuided }: QuickStartModalProps) {
  const { t } = useLang();

  return (
    <div className="modal-backdrop quickstart-backdrop" role="dialog" aria-modal="true">
      <div className="quickstart-modal">
        <div className="quickstart-head">
          <div>
            <div className="quickstart-kicker">{t("quickStartKicker")}</div>
            <h3>{t("quickStartTitle")}</h3>
            <p>{t("quickStartDesc")}</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="close quick start">
            ×
          </button>
        </div>

        <div className="quickstart-grid">
          <section className="quickstart-step quickstart-step-dark">
            <span className="mode-badge">STEP 1</span>
            <h4>{t("quickStartStep1Title")}</h4>
            <p>{t("quickStartStep1Desc")}</p>
            <button className="pill-btn-primary" onClick={onStart}>
              {t("quickStartStep1Cta")}
            </button>
          </section>

          <section className="quickstart-step">
            <span className="mode-badge">STEP 2</span>
            <h4>{t("quickStartStep2Title")}</h4>
            <p>{t("quickStartStep2Desc")}</p>
            <button className="pill-btn" onClick={onGuided}>
              {t("quickStartStep2Cta")}
            </button>
          </section>
        </div>

        <div className="quickstart-foot">
          <button className="pill-btn" onClick={onClose}>
            {t("quickStartLater")}
          </button>
          <button className="pill-btn" onClick={onNeverRemind}>
            {t("quickStartNever")}
          </button>
        </div>
      </div>
    </div>
  );
}
