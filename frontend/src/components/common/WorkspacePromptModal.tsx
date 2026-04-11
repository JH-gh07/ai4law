import type { KeyboardEvent as ReactKeyboardEvent } from "react";

type WorkspacePromptModalProps = {
  open: boolean;
  title: string;
  description: string;
  confirmText: string;
  cancelText: string;
  onCancel: () => void;
  onConfirm: () => void;
  value?: string;
  valueLabel?: string;
  valuePlaceholder?: string;
  onValueChange?: (value: string) => void;
  confirmDisabled?: boolean;
};

export function WorkspacePromptModal({
  open,
  title,
  description,
  confirmText,
  cancelText,
  onCancel,
  onConfirm,
  value,
  valueLabel,
  valuePlaceholder,
  onValueChange,
  confirmDisabled = false
}: WorkspacePromptModalProps) {
  if (!open) return null;

  const onInputKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !confirmDisabled) {
      event.preventDefault();
      onConfirm();
    }
  };

  return (
    <div className="action-modal-backdrop" role="dialog" aria-modal="true" onClick={onCancel}>
      <div className="action-modal" onClick={(event) => event.stopPropagation()}>
        <div className="action-modal-head">
          <h4>{title}</h4>
          <button type="button" className="icon-btn" onClick={onCancel} aria-label="close modal">
            ×
          </button>
        </div>
        <p className="action-modal-desc">{description}</p>
        {onValueChange ? (
          <label className="action-modal-field">
            {valueLabel ? <span>{valueLabel}</span> : null}
            <input
              value={value ?? ""}
              onChange={(event) => onValueChange(event.target.value)}
              onKeyDown={onInputKeyDown}
              placeholder={valuePlaceholder}
            />
          </label>
        ) : null}
        <div className="action-modal-actions">
          <button type="button" className="pill-btn" onClick={onCancel}>
            {cancelText}
          </button>
          <button type="button" className="pill-btn-primary" disabled={confirmDisabled} onClick={onConfirm}>
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
