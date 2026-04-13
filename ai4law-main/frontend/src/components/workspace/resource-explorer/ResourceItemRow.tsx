import type { ReactNode } from "react";
import { StatusBadge } from "./StatusBadge";
import type { ResourceItemData } from "./types";

type ResourceItemRowProps = {
  item: ResourceItemData;
  trailing?: ReactNode;
  onClick?: () => void;
  onUpload?: () => void;
};

export function ResourceItemRow({ item, trailing, onClick, onUpload }: ResourceItemRowProps) {
  return (
    <article className={`rx-item ${item.highlight ? "is-highlight" : ""} ${item.blocked ? "is-blocked" : ""}`}>
      <button type="button" className="rx-item-main" onClick={onClick}>
        <div className="rx-item-copy">
          <strong>{item.label}</strong>
          {item.hint ? <p>{item.hint}</p> : null}
          {item.meta ? <small>{item.meta}</small> : null}
        </div>
        <StatusBadge status={item.status} />
      </button>
      <div className="rx-item-actions">
        {item.blocked && onUpload ? (
          <button type="button" className="rx-item-upload" onClick={onUpload}>
            去上传
          </button>
        ) : null}
        {trailing}
      </div>
    </article>
  );
}

