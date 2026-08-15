# Font assets

Redistributable font assets tracked for the IR → PDF fixed-layout renderer.
The PDF font gate (`pdf_font_embedding`) stays `pass` only when a CJK-capable
TrueType font embeds with `emb=yes`; Latin text uses the Liberation Sans fonts
already shipped with the repo's PDF.js assets.

## Noto Sans SC (Regular)

- File: `NotoSansSC-Regular.ttf`
- sha256: `b21066bd748d341d1a1424490dde49e5f6ed7c043a21cc9d9985f002fc3ac074`
- License: [SIL Open Font License 1.1](https://openfontlicense.org/)
- Source: Google Fonts `ofl/notosanssc/NotoSansSC[wght].ttf`, instantiated at
  `wght=400` (Regular) and renamed via `fontTools.varLib.instancer` / name-table
  rewrite so ReportLab embeds a static Regular instance.

The renderer (`backend/common/reporting/renderers/pdf.py`) resolves this asset
through `get_cjk_font()` by the `noto` filename hint; do not rename it without
updating `_CJK_FONT_HINTS` in `backend/common/reporting/render_profiles/__init__.py`.
