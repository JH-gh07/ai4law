# AI4Law Frontend (Research Blue UI)

## Run

```bash
cd frontend
npm install
npm run dev
```

App runs at `http://127.0.0.1:5173`.

## Delivered Scope (V1)

- Narrative landing page with atmospheric hero and primary CTA
- Modal-first launch flow: `Start -> Mode Select -> Create Workspace`
- Three-pane workspace shell: `Evidence Shelf / Draft Studio / Live Assistant`
- Collapsible top bar + collapsible left/right side panels
- System-level i18n (zh/en) with local persistence (`localStorage`)
- Step onboarding overlay for first entry into workspace
- Scientific blue design tokens (paper background + low-saturation glass)
- Center panel now connected to real APIs:
  - `/api/v1/diagnosis/report`
  - `/api/v1/assessment/generate`
  - `/api/v1/scc/generate`
  - `/api/v1/pipia/generate`
  - `/api/v1/cn-flow/generate`

## Key Files

- `frontend/src/App.tsx`
- `frontend/src/lib/i18n.ts`
- `frontend/src/lib/language.tsx`
- `frontend/src/components/landing/LandingPage.tsx`
- `frontend/src/components/modals/ModeSelectModal.tsx`
- `frontend/src/components/modals/CreateWorkspaceModal.tsx`
- `frontend/src/components/workspace/WorkspaceShell.tsx`
- `frontend/src/components/onboarding/OnboardingOverlay.tsx`
- `frontend/src/styles/tokens.css`
- `frontend/src/styles/app.css`

## Notes

- This V1 is intentionally a UI shell; backend module pages can be embedded into the center panel incrementally.
- Vite dev server proxies `/api` to `http://127.0.0.1:8000` to avoid CORS issues during local dev.
- Existing Streamlit frontend remains unchanged and can run in parallel.
