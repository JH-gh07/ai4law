# 测试任务归档总览

本目录用于集中保存项目中已经用于测试运行结果展示的代表性输入、输出、截图与参考测试脚本，便于团队后续复核、补材料和统一演示。

## 目录结构

```text
doc/test_cases/
  cn/
  eu/
  us/
  reference/tests/
```

说明：
- `cn/`、`eu/`、`us/` 按法域分类。
- 每个任务目录下按 `input/`、`output/`、`screenshots/` 归档。
- `reference/tests/` 收录了来自 `C:\Users\sataxisama\Desktop\agent individual\AI4law\tests` 的参考测试脚本。

## 参考测试脚本

- `doc/test_cases/reference/tests/test_diagnosis.py`
- `doc/test_cases/reference/tests/test_review.py`
- `doc/test_cases/reference/tests/test_rag.py`

## CN

### 1. 合规路径诊断

- 目录：`doc/test_cases/cn/01_合规路径诊断`
- 输入说明：该任务主要是表单问答输入，当前仓库内未保留完整上传型输入文件；输入字段设计可参考 `reference/tests/test_diagnosis.py`
- 输入文件地址：
  - `doc/test_cases/reference/tests/test_diagnosis.py`
- 输出文件地址：
  - `doc/test_cases/cn/01_合规路径诊断/output/DemoDiag033725_diagnosis_report.html`
  - `doc/test_cases/cn/01_合规路径诊断/output/DemoDiag033725_diagnosis_report.pdf`
- 截图情况：
  - 当前归档中未找到现成完整截图，保留 HTML/PDF 输出供直接预览

### 2. 安全评估

- 目录：`doc/test_cases/cn/02_安全评估`
- 输入说明：以安全评估模板文档作为参考输入，实际任务通常还会结合问卷字段与企业事实信息
- 输入文件地址：
  - `doc/test_cases/cn/02_安全评估/input/数据出境风险自评估报告（模板）.docx`
- 输出文件地址：
  - `doc/test_cases/cn/02_安全评估/output/DemoAssess025810_数据出境风险自评估报告_草案_20260416.docx`
  - `doc/test_cases/cn/02_安全评估/output/DemoAssess025810_数据出境风险自评估报告_草案_20260416.md`
  - `doc/test_cases/cn/02_安全评估/output/DemoAssess025810_安全评估路径输出包_草案_20260416.zip`
- 截图情况：
  - 当前归档中未找到现成完整截图

### 3. PIPIA

- 目录：`doc/test_cases/cn/03_PIPIA`
- 输入说明：个人信息保护影响评估模板作为参考输入
- 输入文件地址：
  - `doc/test_cases/cn/03_PIPIA/input/个人信息保护影响评估报告（模板）.docx`
- 输出文件地址：
  - `doc/test_cases/cn/03_PIPIA/output/测试公司_PIPIA_报告_草案_20260412.docx`
  - `doc/test_cases/cn/03_PIPIA/output/测试公司_PIPIA_报告_草案_20260412.md`
  - `doc/test_cases/cn/03_PIPIA/output/测试公司_PIPIA_输出包_草案_20260412.zip`
- 截图地址：
  - `doc/test_cases/cn/03_PIPIA/screenshots/2.3.1.png`

### 4. SCC 合规审查

- 目录：`doc/test_cases/cn/04_SCC合规审查`
- 输入说明：标准合同模板与 SCC 文本样例共同作为输入参考
- 输入文件地址：
  - `doc/test_cases/cn/04_SCC合规审查/input/个人信息出境标准合同【模板】.docx`
  - `doc/test_cases/cn/04_SCC合规审查/input/regen_sample_scc.txt`
- 输出文件地址：
  - `doc/test_cases/cn/04_SCC合规审查/output/DemoSCC161208_SCC_合规审查报告_草案_20260413.docx`
  - `doc/test_cases/cn/04_SCC合规审查/output/DemoSCC161208_SCC_合规审查报告_草案_20260413.md`
  - `doc/test_cases/cn/04_SCC合规审查/output/测试公司_SCC_批注修订版_20260413.docx`
- 截图情况：
  - 当前归档中未找到现成完整截图

### 5. 通用合同审查（批注修订）

- 目录：`doc/test_cases/cn/05_通用合同审查_批注修订`
- 输入说明：同一份合同分别用于文本分析与批注修订测试
- 输入文件地址：
  - `doc/test_cases/cn/05_通用合同审查_批注修订/input/测试使用的同一个合同.docx`
- 输出文件地址：
  - `doc/test_cases/cn/05_通用合同审查_批注修订/output/合同审查功能输出的结果（批注修订版.docx`
  - `doc/test_cases/cn/05_通用合同审查_批注修订/output/文本分析功能输出的结果（审查报告docx.docx`
  - `doc/test_cases/cn/05_通用合同审查_批注修订/output/得理AI 双功能使用差异总结.docx`
- 截图地址：
  - `doc/test_cases/cn/05_通用合同审查_批注修订/screenshots/合同审查功能的使用输入界面.png`

## EU

### 1. DPIA

- 目录：`doc/test_cases/eu/01_DPIA`
- 输入说明：DPIA 模板文档作为参考输入
- 输入文件地址：
  - `doc/test_cases/eu/01_DPIA/input/2.2 ICO_DPIA_Temple.docx`
- 输出文件地址：
  - `doc/test_cases/eu/01_DPIA/output/EU用户行为分析系统_DPIA_报告_草案_20260412.docx`
  - `doc/test_cases/eu/01_DPIA/output/EU用户行为分析系统_DPIA_报告_草案_20260412.md`
  - `doc/test_cases/eu/01_DPIA/output/EU用户行为分析系统_DPIA_输出包_草案_20260412.zip`
- 截图地址：
  - `doc/test_cases/eu/01_DPIA/screenshots/2.2.1.png`

### 2. TIA

- 目录：`doc/test_cases/eu/02_TIA`
- 输入说明：TIA 模板文档作为参考输入
- 输入文件地址：
  - `doc/test_cases/eu/02_TIA/input/TIA - Template.docx`
- 输出文件地址：
  - `doc/test_cases/eu/02_TIA/output/EU_Exporter_A_scc_TIA_报告_草案_20260412.docx`
  - `doc/test_cases/eu/02_TIA/output/EU_Exporter_A_scc_TIA_报告_草案_20260412.md`
  - `doc/test_cases/eu/02_TIA/output/EU_Exporter_A_scc_TIA_输出包_草案_20260412.zip`
- 截图地址：
  - `doc/test_cases/eu/02_TIA/screenshots/3.4.png`

### 3. BCR 审查

- 目录：`doc/test_cases/eu/03_BCR审查`
- 输入说明：BCR 审查参考材料使用 EDPB 相关文档
- 输入文件地址：
  - `doc/test_cases/eu/03_BCR审查/input/recommendations_20221_bcr-c_edpb_en.pdf`
- 输出文件地址：
  - `doc/test_cases/eu/03_BCR审查/output/示例集团_BCR-C_合规审查报告_草案_20260412.docx`
  - `doc/test_cases/eu/03_BCR审查/output/示例集团_BCR-C_合规审查报告_草案_20260412.md`
  - `doc/test_cases/eu/03_BCR审查/output/示例集团_BCR-C_输出包_草案_20260412.zip`
- 截图地址：
  - `doc/test_cases/eu/03_BCR审查/screenshots/3.2.png`

## US

### 1. CPRA 全景评估

- 目录：`doc/test_cases/us/01_CPRA全景评估`
- 输入说明：当前归档中未保留独立输入文档，任务更偏表单/规则组合输入；可结合输出内容与参考测试脚本理解字段设计
- 输入文件地址：
  - `doc/test_cases/reference/tests/test_review.py`
  - `doc/test_cases/reference/tests/test_rag.py`
- 输出文件地址：
  - `doc/test_cases/us/01_CPRA全景评估/output/测试企业_CPRA_合规全景报告_草案_20260412.docx`
  - `doc/test_cases/us/01_CPRA全景评估/output/测试企业_CPRA_合规全景报告_草案_20260412.md`
  - `doc/test_cases/us/01_CPRA全景评估/output/测试企业_CPRA_合规全景报告_草案_20260412.pdf`
  - `doc/test_cases/us/01_CPRA全景评估/output/测试企业_CPRA_整改路线图_草案_20260412.xlsx`
  - `doc/test_cases/us/01_CPRA全景评估/output/测试企业_CPRA_输出包_草案_20260412.zip`
- 截图地址：
  - `doc/test_cases/us/01_CPRA全景评估/screenshots/4.2.png`
  - `doc/test_cases/us/01_CPRA全景评估/screenshots/4.2.2.png`

### 2. EO 14117 风险评估

- 目录：`doc/test_cases/us/02_EO14117风险评估`
- 输入说明：该任务主要依赖数据清单和实体清单类材料
- 输入文件地址：
  - `doc/test_cases/us/02_EO14117风险评估/input/cn_regen_data_inventory_20260408_134644.csv`
  - `doc/test_cases/us/02_EO14117风险评估/input/cn_regen_entity_inventory_20260408_134644.csv`
- 输出文件地址：
  - `doc/test_cases/us/02_EO14117风险评估/output/测试企业_14117_风险评估结论报告_草案_20260412.docx`
  - `doc/test_cases/us/02_EO14117风险评估/output/测试企业_14117_风险评估结论报告_草案_20260412.md`
  - `doc/test_cases/us/02_EO14117风险评估/output/测试企业_14117_风险评估结论报告_草案_20260412.pdf`
  - `doc/test_cases/us/02_EO14117风险评估/output/测试企业_14117_风险清单_草案_20260412.xlsx`
  - `doc/test_cases/us/02_EO14117风险评估/output/测试企业_14117_输出包_草案_20260412.zip`
- 截图地址：
  - `doc/test_cases/us/02_EO14117风险评估/screenshots/4.1.png`
  - `doc/test_cases/us/02_EO14117风险评估/screenshots/4.1.2.png`

## 备注

- 本次归档以“已有代表性测试文件可直接复用”为优先，没有强行补造新样例。
- 某些任务天然以问卷/表单输入为主，因此会用参考测试脚本替代单独的上传文件。
- 如果后续要继续补齐“完整截图”，建议优先从前端工作台中分别导出：
  - 输入页截图
  - 输出预览页截图
  - 文件树展开截图
