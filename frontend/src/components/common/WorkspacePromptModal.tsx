import { useEffect, useId, useRef, type KeyboardEvent as ReactKeyboardEvent } from "react";

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
  errorText?: string;
  modalClassName?: string;
  closeOnBackdrop?: boolean;
  allowEscapeClose?: boolean;
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
  confirmDisabled = false,
  errorText,
  modalClassName,
  closeOnBackdrop = true,
  allowEscapeClose = true
}: WorkspacePromptModalProps) {
  const titleId = useId();
  const descId = useId();
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open || !allowEscapeClose) return;
    const onEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      onCancel();
    };
    globalThis.addEventListener("keydown", onEscape);
    return () => globalThis.removeEventListener("keydown", onEscape);
  }, [allowEscapeClose, onCancel, open]);

  useEffect(() => {
    if (!open || !onValueChange) return;
    const timer = globalThis.setTimeout(() => {
      inputRef.current?.focus();
      const length = inputRef.current?.value.length ?? 0;
      inputRef.current?.setSelectionRange(length, length);
    }, 0);
    return () => globalThis.clearTimeout(timer);
  }, [onValueChange, open]);

  if (!open) return null;

  const onInputKeyDown = (event: ReactKeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && !confirmDisabled) {
      event.preventDefault();
      onConfirm();
    }
  };

  const onBackdropClick = () => {
    if (!closeOnBackdrop) return;
    onCancel();
  };

  return (
    <div className="action-modal-backdrop" role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={descId} onClick={onBackdropClick}>
      <div className={`action-modal ${modalClassName ?? ""}`.trim()} onClick={(event) => event.stopPropagation()}>
        <div className="action-modal-head">
          <h4 id={titleId}>{title}</h4>
          <button type="button" className="icon-btn" onClick={onCancel} aria-label="close modal">
            ×
          </button>
        </div>
        <p id={descId} className="action-modal-desc">{description}</p>
        {onValueChange ? (
          <label className="action-modal-field">
            {valueLabel ? <span>{valueLabel}</span> : null}
            <input
              ref={inputRef}
              value={value ?? ""}
              onChange={(event) => onValueChange(event.target.value)}
              onKeyDown={onInputKeyDown}
              placeholder={valuePlaceholder}
            />
          </label>
        ) : null}
        {errorText ? <p className="action-modal-error">{errorText}</p> : null}
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
