import { useState } from "react";
import { ResourceItemRow } from "./ResourceItemRow";
import type { ResourceItemData, ResourceSectionData } from "./types";

type WorkspaceSectionProps = {
  section: ResourceSectionData;
  onSwitchWorkspace: (item: ResourceItemData) => void;
};

export function WorkspaceSection({ section, onSwitchWorkspace }: WorkspaceSectionProps) {
  const [open, setOpen] = useState(section.defaultOpen ?? true);

  return (
    <section className="rx-section rx-workspace-section">
      <header className="rx-section-head">
        <h4>{section.title}</h4>
        <button type="button" className="rx-section-toggle" onClick={() => setOpen((value) => !value)}>
          {open ? "收起" : "展开"}
        </button>
      </header>
      {open ? (
        <div className="rx-item-list">
          {section.items.map((item) => (
            <ResourceItemRow key={item.id} item={item} onClick={() => onSwitchWorkspace(item)} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

