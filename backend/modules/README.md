# Business modules

`backend/modules/` is the current compatibility implementation location. It is
not the long-term jurisdiction hierarchy and new callers must not infer legal
jurisdiction from the directory name.

Use `backend.modules.catalog` for stable module IDs and jurisdiction metadata.
The catalog separates identifiers such as `cn.scc_review` and `eu.scc_review`
while preserving the existing Python imports, frontend keys and `/api/v1`
routes. Physical migration to `backend/domains/{cn,eu,us}/` must be performed
one module at a time with compatibility tests; do not add another unregistered
top-level module here.

`v0_task_gateway` is an active compatibility adapter and is intentionally not a
legal-domain module. Its version-like name is not evidence that it is unused.
