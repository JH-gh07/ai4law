import type { ReactNode } from "react";

type ModalShellProps = {
  title: string;
  subtitle: string;
  onClose: () => void;
  children: ReactNode;
};

export function ModalShell({ title, subtitle, onClose, children }: ModalShellProps) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal-panel">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <h3 className="font-display text-2xl text-ink">{title}</h3>
            <p className="text-sm text-scientific-800/70">{subtitle}</p>
          </div>
          <button className="icon-btn" onClick={onClose} aria-label="close modal">
            ×
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
