"""Task067 T09 — shadow render + diff audit for the BCR IR switch.

Backward-compatible re-export of the shared task068 T11 shadow primitive in
``backend.common.reporting.shadow_render``. The BCR service and its tests keep
importing from this module; the implementation is now shared with CPRA / EO /
DPIA / Review so the switch/rollback discipline is identical across modules.
"""

from __future__ import annotations

from backend.common.reporting.shadow_render import (
    CollectionAudit,
    RenderingMode,
    audit_ir_vs_legacy,
    render_ir_artifacts,
    write_audit_json,
)

__all__ = [
    "CollectionAudit",
    "RenderingMode",
    "audit_ir_vs_legacy",
    "render_ir_artifacts",
    "write_audit_json",
]
