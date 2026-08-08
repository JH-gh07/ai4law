# EU SCC Compliance Review Report — Gesundheitsforschung GmbH
**Date**: 20260808 | **Rating**: HIGH

## 文件概要
## 文件概要

- SCC 模块: 声明=Module Two, 预期=Module Two, 正确=是
- 条款数: 3
- Annex I.A 主体数: 0
- Annex II 措施数: 0
- Annex III 子处理者数: 0



## 总体合规评级
## 总体合规评级: HIGH

- 模块选择: 正确
- 标准条款偏离: 1处
- 第三国传输: 是 (India)
- TIA: 缺失
- Schrems II 补充措施: 不足 [1]

*References: EDPB Recommendations 01/2020 Step 3*

## 条款级审查发现
## 条款级审查发现

### 1. [HIGH] Clause 15(a) notification

- 问题类型: clause_weakened
- 风险分析: Clause 15 deviation detected: 修改为'法律许可时'通知，而非'立即(promptly)'
- 法规依据: EU 2021/914, Recital 3 (invariability of Clauses); GDPR Article 46
- 修改建议: restore 'promptly notify'
- 建议文本: Restore the standard EU 2021/914 text for this provision.

### 2. [MEDIUM] Annex I.A

- 问题类型: annex_incomplete
- 风险分析: Less than 2 parties identified in Annex I.A. Docking Clause (Clause 7) parties may also be missing.
- 法规依据: EU 2021/914 Annex I.A; Clause 7
- 修改建议: Complete Annex I.A with all data exporters and importers, including any additional parties via Docking Clause.

### 3. [HIGH] Annex I.B

- 问题类型: specialcategorymisclassified
- 风险分析: Transfer description contains health/medical data terms but special category data is NOT declared. Under GDPR Article 9, health data requires explicit consent or another exemption, and SCCs alone may not be sufficient.
- 法规依据: GDPR Article 9; EU 2021/914; EDPB Recommendations 01/2020
- 修改建议: (1) Verify whether the data includes special categories; (2) If yes, declare them explicitly in Annex I.B; (3) Assess whether supplementary measures are needed for special category data transfers.

### 4. [HIGH] Annex II

- 问题类型: annex_incomplete
- 风险分析: Annex II (Technical and Organisational Measures) appears empty or could not be parsed. Without specified TOMs, the SCC does not demonstrate adequate data protection safeguards.
- 法规依据: EU 2021/914 Annex II; GDPR Articles 32, 46
- 修改建议: Complete Annex II with specific technical and organisational measures, including encryption standards, access controls, incident response, and data minimization practices.

### 5. [HIGH] Clause 14

- 问题类型: tia_missing
- 风险分析: Third country transfer identified to: India. No Transfer Impact Assessment (TIA) has been provided. Under GDPR and Schrems II (C-311/18), a documented TIA is required before transferring personal data to a third country without an adequacy decision.
- 法规依据: GDPR Article 46; Schrems II C-311/18; EDPB Recommendations 01/2020; EU 2021/914 Clause 14
- 修改建议: Complete a TIA for transfers to India. The TIA must: (1) assess the laws and practices of the destination country; (2) evaluate whether they impinge on the SCCs' effectiveness; (3) identify and implement supplementary measures as needed.

### 6. [HIGH] Annex II

- 问题类型: supplementarymeasuresinsufficient
- 风险分析: Third country transfer to non-adequate jurisdiction 'India' requires Schrems II supplementary measures. Technical: NOT FOUND. Contractual: NOT FOUND. Organizational: NOT FOUND.
- 法规依据: Schrems II C-311/18; EDPB Recommendations 01/2020; EU 2021/914 Annex II
- 修改建议: Implement Schrems II supplementary measures: (1) Technical — end-to-end encryption with EU-held keys, zero-access architecture; (2) Contractual — government access notification obligation, commitment to challenge unlawful requests, transparency reporting; (3) Organizational — independent annual audit, data minimization.

### 7. [HIGH] Clause 15

- 问题类型: clause_weakened
- 风险分析: Semantic weakening (information_provision): Information provision made discretionary
- 法规依据: EU 2021/914 Recital 3; SCC Clause 15; GDPR Article 46
- 修改建议: Restore the standard EU 2021/914 text for this provision.

### 8. [HIGH] Annex II / TIA

- 问题类型: supplementarymeasuresinsufficient
- 风险分析: Technical: insufficient (Technical measures are limited or not detected.). Contractual: missing. Organizational: missing. Overall: insufficient.
- 法规依据: Schrems II C-311/18; EDPB Recommendations 01/2020; GDPR Article 46
- 修改建议: Technical: implement e2eeeukeys, basicencryptiononly, accesscontrols | Contractual: add govaccess, onwardrestrictions | Organizational: establish audit, logging, keymanagement [2]

*References: Commission Implementing Decision (EU) 2021/914 Recital (22) / Clause 15*

## 法规依据与修改建议
## 法规依据与修改建议

- EU 2021/914, Recital 3 (invariability of Clauses); GDPR Article 46
- EU 2021/914 Annex I.A; Clause 7
- GDPR Article 9; EU 2021/914; EDPB Recommendations 01/2020
- EU 2021/914 Annex II; GDPR Articles 32, 46
- GDPR Article 46; Schrems II C-311/18; EDPB Recommendations 01/2020; EU 2021/914 Clause 14
- Schrems II C-311/18; EDPB Recommendations 01/2020; EU 2021/914 Annex II
- EU 2021/914 Recital 3; SCC Clause 15; GDPR Article 46
- Schrems II C-311/18; EDPB Recommendations 01/2020; GDPR Article 46

### 修改建议汇总

- [HIGH] Clause 15(a) notification: restore 'promptly notify'
- [MEDIUM] Annex I.A: Complete Annex I.A with all data exporters and importers, including any additional parties via Docking Clause.
- [HIGH] Annex I.B: (1) Verify whether the data includes special categories; (2) If yes, declare them explicitly in Annex I.B; (3) Assess whether supplementary measures are needed for special category data transfers.
- [HIGH] Annex II: Complete Annex II with specific technical and organisational measures, including encryption standards, access controls, incident response, and data minimization practices.
- [HIGH] Clause 14: Complete a TIA for transfers to India. The TIA must: (1) assess the laws and practices of the destination country; (2) evaluate whether they impinge on the SCCs' effectiveness; (3) identify and implement supplementary measures as needed.
- [HIGH] Annex II: Implement Schrems II supplementary measures: (1) Technical — end-to-end encryption with EU-held keys, zero-access architecture; (2) Contractual — government access notification obligation, commitment to challenge unlawful requests, transparency reporting; (3) Organizational — independent annual audit, data minimization.
- [HIGH] Clause 15: Restore the standard EU 2021/914 text for this provision.
- [HIGH] Annex II / TIA: Technical: implement e2eeeukeys, basicencryptiononly, accesscontrols | Contractual: add govaccess, onwardrestrictions | Organizational: establish audit, logging, keymanagement [3]

*References: Commission Implementing Decision (EU) 2021/914 Recital (21) / Clause 14*
