import { useState } from "react";
import { ResourceItemRow } from "./ResourceItemRow";
import type { ResourceItemData, ResourceSectionData } from "./types";
import { useLang } from "../../../lib/language";

type ResourceSectionProps = {
  section: ResourceSectionData;
  onItemClick?: (item: ResourceItemData) => void;
  onUploadMissing?: (item: ResourceItemData) => void;
};

export function ResourceSection({ section, onItemClick, onUploadMissing }: ResourceSectionProps) {
  const { lang } = useLang();
  const [open, setOpen] = useState(section.defaultOpen ?? true);

  return (
    <section className="rx-section">
      <header className="rx-section-head">
        <h4>{section.title}</h4>
        {section.collapsible !== false ? (
          <button type="button" className="rx-section-toggle" onClick={() => setOpen((value) => !value)}>
            {open ? (lang === "zh" ? "收起" : "Collapse") : lang === "zh" ? "展开" : "Expand"}
          </button>
        ) : null}
      </header>
      {open ? (
        <div className="rx-item-list">
          {section.items.map((item) => (
            <ResourceItemRow
              key={item.id}
              item={item}
              onClick={onItemClick ? () => onItemClick(item) : undefined}
              onUpload={onUploadMissing ? () => onUploadMissing(item) : undefined}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
