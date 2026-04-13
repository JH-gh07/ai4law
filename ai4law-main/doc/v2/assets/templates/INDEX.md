# 模板素材库索引（v2）

## 状态说明
- `official`：已拿到官方模板并完成入库
- `placeholder`：当前占位模板，可运行但需后续替换
- `missing`：仍未补齐

## 依据等级说明（相对于 `doc/v2/整体统筹开发文档.docx`）
- `A`：原文对输入/输出/结构有明确描述，模板可直接回挂
- `B`：原文只明确部分要素（如输入或报告名），其余由工程补齐
- `C`：原文仅给“见模板/见表格”，具体字段仍需后补

## 模板清单

| 模块 | 模板文件（md） | 模板文件（docx） | 当前状态 | 依据等级 | 替换优先级 | 备注 |
|---|---|---|---|---|---|---|
| 2.2 安全评估路径 | `2.2_risk_assessment_template_v0.md` | `2.2_risk_assessment_template_v0.docx` | placeholder | A | P0 | 原文已明确输入材料、输出命名、交付方式 |
| 2.3 认证/标准合同路径 | `2.3_pipia_template_v0.md` | `2.3_pipia_template_v0.docx` | placeholder | A | P0 | 原文已明确报告名/格式/样式要求 |
| 3.1 SCC审查 | `3.1_scc_review_template_v0.md` | `3.1_scc_review_template_v0.docx` | placeholder | A | P1 | 原文已明确条款级审查字段 |
| 3.2 BCR审核 | `3.2_bcr_review_template_v0.md` | `3.2_bcr_review_template_v0.docx` | placeholder | A | P1 | 原文已明确评级和优先级结构 |
| 3.3 DPIA草案 | `3.3_dpia_template_v0.md` | `3.3_dpia_template_v0.docx` | placeholder | B | P0 | 已补 `addition/2.2 ICO_DPIA_Temple.docx` 与字段截图，待替换正式模板 |
| 3.4 TIA草案 | `3.4_tia_template_v0.md` | `3.4_tia_template_v0.docx` | placeholder | B | P0 | 已补 `addition/TIA - Template.docx` 与字段截图，待替换正式模板 |
| 4.1 对华数据流动 | `4.1_cn_flow_compliance_template_v0.md` | `4.1_cn_flow_compliance_template_v0.docx` | placeholder | B | P1 | 原文明确输入，输出结构留白 |
| 4.2 CPRA合规 | `4.2_cpra_panorama_template_v0.md` | `4.2_cpra_panorama_template_v0.docx` | placeholder | B | P1 | 原文明确报告名，字段留白 |

## 依据映射
- 详细映射请看：`doc/v2/assets/templates/BASIS_MAP.md`

## 管理规则
1. 每次替换模板必须提升版本号（`v0 -> v1`），旧版归档到 `archive/`。
2. 模板字段变更必须同步更新对应 schema 与 example。
3. 模板状态从 `placeholder` 到 `official` 时，需在模块文档中更新引用路径与版本。
4. 每个模板文件必须保留“依据文档/依据段落/依据等级”头信息，避免脱离主文档演化。
5. `doc/v2/schemas/raw/` 是截图字段的结构化落地目录，模板替换时必须同步核对该目录字段。
