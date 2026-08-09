/**
 * 工作区提示模态框组件
 * 用于在工作区中显示提示信息，并提供确认和取消操作
 * 
 * 函数：
 * - WorkspacePromptModal: 工作区提示模态框组件，接收一组属性并渲染模态框内容，模态框指的是在当前页面上方显示的对话框，用于提示用户进行某些操作或提供信息。该组件可以根据传入的属性动态显示标题、描述、输入框、错误提示等内容，并处理用户的确认和取消操作。
 * 
 * 
 * Props:
 * - open: 是否显示模态框
 * - title: 模态框标题
 * - description: 模态框描述信息
 * - confirmText: 确认按钮文本
 * - cancelText: 取消按钮文本
 * - onCancel: 取消操作回调函数
 * - onConfirm: 确认操作回调函数
 * - value: 输入框的值（可选）
 * - valueLabel: 输入框的标签（可选）
 * - valuePlaceholder: 输入框的占位符（可选）
 * - onValueChange: 输入框值变化回调函数（可选）
 * - confirmDisabled: 确认按钮是否禁用（可选，默认false）
 * - errorText: 错误提示文本（可选）
 * - modalClassName: 模态框自定义类名（可选）
 * - closeOnBackdrop: 点击背景是否关闭模态框（可选，默认true）
 * - allowEscapeClose: 是否允许按下Esc键关闭模态框（可选，默认true）
 */
import { useEffect, useId, useRef, type KeyboardEvent as ReactKeyboardEvent } from "react";

type WorkspacePromptModalProps = {// type 定义了一个名为WorkspacePromptModalProps的类型，用于描述WorkspacePromptModal组件的属性。类型是指在TypeScript中用于定义变量、函数参数、返回值等的结构和类型。它可以帮助开发者在编写代码时提供类型检查和自动补全功能，从而提高代码的可靠性和可维护性。跟python中的dataclass类似，都是用来定义数据结构的。
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
              name="workspacePromptValue"
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
