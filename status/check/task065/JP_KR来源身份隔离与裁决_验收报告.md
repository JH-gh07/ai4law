# JP/KR 来源身份隔离与裁决 验收报告

> 日期：2026-08-13
> 范围：本地开发/测试/验收；未连接远程、未部署、未修改远程数据
> 依据：task065 实施方案 + JP/KR 资料包「整体错位」专项处置方案

## 一、结论

JP/KR 资料包存在 title↔PDF 系统性错位（非简单 CSV 改名可修复）。本轮按「先冻结、核对，再统一修复」执行完成，并经**首页原文逐 PDF 事实审核**，在用户原始 8 项之外**新增发现 2 项误绑 + 2 项元数据问题**：

- **第一阶段（隔离风险）已完成**：10 个错位 source 已标记 `metadata_review_required`，从正式法律结论与「可直接引用条文号」来源中隔离；原始 PDF 全部保留。
- **第二阶段（专项核对表）已完成**：人工审核表初稿已由代码生成（14 行），等待专家签署。
- **第三阶段（逐项裁决）待人工签署**：本轮不替专家做法律裁决，不改标题、不改条文、不重建错误绑定。
- **第四阶段（统一重建链）待签署后执行**：只有专家签署后才按 `裁决表 → sources.csv → registry → JSONL → 索引 → 前端` 统一重建。
- **第五阶段（自动门禁）已完成**：新增只读内容身份门禁，能发现新异常，不自动做法律裁决。

### 一.1 本次审核新增发现（相对用户原始清单）

| 新增发现 | 严重度 | 事实依据 |
|---|---|---|
| `KR-LAW-007`『网络利用促进与信息保护法』误绑到 `B01`『정보통신기반 보호법（信息通信基础保护法）』 | **高**（可能引用错误法律） | 二者为两部不同韩国法律；B01 首页明确为 `정보통신기반 보호법` |
| `JP-GUIDE-006`『第三方提供记录指南』误绑到 `A06`『外国第三者提供編（境外提供）』 | 中（JP 指南块整体偏移一位） | A06 首页为 `ガイドライン（外国第三者提供編）`，应归属 `JP-GUIDE-005` |
| `JP-REG-003` 政令号陈旧 | 低（绑定正确，元数据错） | CSV『2021年政令第311号』vs PDF 首页『平成15年政令第507号』 |
| `KR-GUIDE-003` 标题/doc_type 误 | 低（主题正确，类型错） | PDF 首页为 `개인정보 국외 이전 운영 등에 관한 규정`（规定/고시），非『指南』 |

## 一.2 审核结论（事实层，逐 PDF 首页原文核验）

以下为抽取全部 JP/KR 参考 PDF 首页原文后的**身份核验结果**。这是事实核对，不是法律裁决。

### JP（日本）9 份 PDF 的真实身份

| PDF | 首页原文身份 | 当前绑定 | 审核判定 |
|---|---|---|---|
| A01 | 個人情報の保護に関する法律 | JP-LAW-001 | ✅ 正确 |
| A02 | 個人情報の保護に関する法律施行令（平成15年政令第507号） | JP-REG-003『实施令』 | ⚠️ 绑定正确，政令号陈旧 |
| A03 | 個人情報の保護に関する法律施行規則（委員会規則第3号） | JP-REG-002『委员会规则第3号』 | ✅ 正确 |
| A04 | 個人情報の保護に関する基本方針（阁议决定） | JP-GUIDE-004『通则指南』 | ❌ 基本方针≠通则；需另建 source |
| A05 | ガイドライン（通則編） | JP-GUIDE-005『境外提供指南』 | ❌ 应归属 JP-GUIDE-004 |
| A06 | ガイドライン（外国第三者提供編） | JP-GUIDE-006『第三方提供记录』 | ❌ 应归属 JP-GUIDE-005 |
| A07 | Supplementary Rules（EU/UK Adequacy） | JP-GUIDE-007『匿名加工信息』 | ❌ 完全无关；需另建 source |
| B01_1 | サイバーセキュリティ基本法（失效版） | 无（孤立） | ⚠️ 应作为 B01_2 历史版本 |
| B01_2 | サイバーセキュリティ基本法（生效版） | JP-LAW-008『电气通信事业法』 | ❌ 两部不同法律；需另建 source |

**JP 指南块系统性偏移一位**：`JP-GUIDE-004→A05、JP-GUIDE-005→A06`，且 `JP-GUIDE-006`（第三方提供记录）、`JP-GUIDE-007`（匿名加工）的正确 PDF 缺失；`A04`（基本方针）、`A07`（欧盟/英国充分性）是真实存在但缺 source 的 PDF。

### KR（韩国）7 份 PDF 的真实身份

| PDF | 首页原文身份 | 当前绑定 | 审核判定 |
|---|---|---|---|
| A01 | 개인정보 보호법 | KR-LAW-001 | ✅ 正确 |
| A02 | 개인정보 보호법 시행령 | KR-REG-002 | ✅ 正确 |
| A03 | 개인정보 국외 이전 운영 등에 관한 규정（고시） | KR-GUIDE-003『跨境传输指南』 | ⚠️ 主题正确，doc_type/标题误 |
| A04_1 | 【별표】위험 감소 보호조치 예시（附表） | 无（孤立） | ⚠️ 应作为 A04_2 附件 |
| A04_2 | 개인정보의 안전성 확보조치 기준（安全措施标准） | KR-GUIDE-004『个人信息处理指南』 | ❌ 类型/内容不符；需另建 source |
| A06 | 표준 개인정보 보호지침（标准指针） | KR-GUIDE-005『移动App指南』 | ❌ 疑似错绑；需另建 source |
| B01 | 정보통신기반 보호법（信息通信基础保护法） | KR-LAW-007『网络利用促进与信息保护法』 | ❌ **两部不同法律**；需另建 source |

## 二、改动清单

| 文件 | 改动 |
|---|---|
| `resources/legal/catalog/sources.csv` | 新增 `review_status` 列；10 个错位 source 标记 `metadata_review_required`，其余 110 行 `published` |
| `backend/common/knowledge/registry.py` | 新增 `_citation_policy_for_row()`；`build_source_registry_from_sources_csv()` 依据 `review_status` 输出 `can_be_cited`/`can_enter_external_report`/`allowed_usage`；`_source_kind_from_row()` 新增 `policy`/`technical_standard` 到 `SourceKind` 的映射 |
| `backend/common/knowledge/builders_v2.py` | `build_legal_chunks_intl()`（及 CN builder）由 registry 透传 `can_be_cited`/`can_enter_external_report`，不再硬编码 `True` |
| `backend/services/knowledge_projection.py` | Evidence Center 投影：隔离源强制 `usage=仅供内部参考`、`report_usage=不直接写入正式报告`，覆盖陈旧 CSV 文本 |
| `scripts/build_jp_kr_adjudication.py` | 新增：生成人工审核表初稿（保留专家签署列，重跑不覆盖人审列） |
| `scripts/build_jp_kr_pending_source_proposals.py` | 新增：生成待建 source 提议表（8 份真实 PDF 的 source/版本/附件提议，保留专家签署列） |
| `scripts/check_regional_source_identity.py` | 新增：JP/KR 来源身份只读门禁（一对一绑定、孤立 PDF、可抽取文本、隔离执行、处置合法性） |
| `status/check/task065/jp_kr_source_adjudication.csv` | 新增：14 行裁决表初稿（10 隔离 source + 2 元数据复核 + 2 孤立 PDF），含 PDF SHA-256 与首页原文标题 |
| `status/check/task065/jp_kr_pending_source_proposals.csv` | 新增：8 行待建 source 提议表，含 PDF SHA-256、建议 source_id/title/doc_type 与 relation |
| `backend/common/knowledge/tests/test_regional_knowledge.py` | 新增 3 条隔离契约测试 |
| `backend/common/knowledge/tests/test_registry.py` | 新增 `policy`/`technical_standard` 到 `SourceKind` 映射的回归测试 |
| `backend/services/tests/test_knowledge_projection.py` | 新增 2 条前端投影隔离测试 |
| `scripts/README.md` | 登记三个新脚本入口 |

## 三、隔离范围（第一阶段）

10 个 source 已标记 `metadata_review_required`：

```text
JP-LAW-008  JP-LAW-009  JP-GUIDE-004  JP-GUIDE-005  JP-GUIDE-006
JP-GUIDE-007  KR-GUIDE-004  KR-GUIDE-005  KR-GUIDE-006  KR-LAW-007
```

隔离效果（逐项核验通过）：

| 层面 | 隔离后表现 |
|---|---|
| registry | `review_status=metadata_review_required`、`can_be_cited=False`、`can_enter_external_report=False`、`allowed_usage=["internal_review"]` |
| `legal_index_intl` chunk | 同源透传 `can_be_cited=False`（7 个有正文的隔离源，共 143 chunk） |
| Evidence Center 投影 | `usage=仅供内部参考`、`report_usage=不直接写入正式报告` |
| 原始 PDF | 全部保留，未删除（门禁断言 `quarantine_pdf_deleted` 不触发） |

3 个无正文隔离源（`JP-GUIDE-007`、`JP-LAW-009`、`KR-GUIDE-006`）无 PDF/无抽取条文，本就不产生 chunk；其中 `JP-LAW-009`、`KR-GUIDE-006` 为 metadata-only，Evidence Center 按既有设计排除（不展示为可引用）。

## 四、人工审核表初稿（第二阶段）

`status/check/task065/jp_kr_source_adjudication.csv` 共 14 行，列含：

```text
source_id / CSV title / CSV doc_type / CSV authority / CSV publish_date / CSV effective_date
/ PDF path / PDF SHA-256 / PDF 首页原文标题 / PDF 发布机关 / PDF 版本/生效日期
/ 当前绑定结论 / 建议处置 / 专家意见 / 审核人 / 审核日期
```

`建议处置` 枚举：`confirm_binding / correct_metadata / replace_pdf / create_new_source / link_as_version / link_as_annex / quarantine / retire`。

初稿建议（**仅初稿，待专家签署**）：

| source_id | 建议处置 | 关键依据 |
|---|---|---|
| JP-LAW-008 | create_new_source | CSV『电气通信事业法』vs PDF『サイバーセキュリティ基本法』，为两部不同法律 |
| JP-LAW-009 | quarantine | 有 metadata 无 PDF，正文无法核验 |
| JP-GUIDE-004 | correct_metadata | CSV『通则指南』vs PDF『基本方針』；正确 PDF 应为 A05 通则，指南块偏移一位 |
| JP-GUIDE-005 | correct_metadata | CSV『境外提供指南』vs PDF『通則編』；正确 PDF 应为 A06 境外提供 |
| JP-GUIDE-006 | correct_metadata | CSV『第三方提供记录』vs PDF『外国第三者提供編』；正确 PDF 缺失 |
| JP-GUIDE-007 | correct_metadata | CSV『匿名加工信息』vs PDF『欧盟/英国充分性』，完全无关 |
| KR-GUIDE-004 | correct_metadata | CSV『个人信息处理指南』vs PDF『安全措施标准（正文）』 |
| KR-GUIDE-005 | correct_metadata | CSV『移动App指南』vs PDF『표준 개인정보 보호지침』 |
| KR-GUIDE-006 | quarantine | 有 metadata 无 PDF；A06 不能充当儿童指南 |
| KR-LAW-007 | create_new_source | CSV『网络利用促进法』vs PDF『信息通信基础保护法』，为两部不同法律 |
| JP-REG-003 | correct_metadata | 绑定正确（施行令→A02），但政令号陈旧（2021第311号 vs 平成15第507号） |
| KR-GUIDE-003 | correct_metadata | 主题正确（跨境转移→A03），但 PDF 为『规定/고시』非『指南』 |
| ORPHAN-JP-B01_1 | link_as_version | 网络安全基本法失效版，应绑定 B01_2 版本关系 |
| ORPHAN-KR-A04_1 | link_as_annex | 安全措施标准附表，应作为 A04_2 正文附件 |

`专家意见`、`审核人`、`审核日期` 三列由法律领域专家填写；重跑生成脚本不会覆盖这三列。

## 五、自动门禁（第五阶段）

`scripts/check_regional_source_identity.py` 只读检查：

- JP/KR source 与 PDF 一一绑定（无重复绑定）
- 孤立 PDF 必须在裁决表中声明，且处置为版本/附件/停用类
- 绑定 PDF 首页文本可抽取
- 隔离 source 的 registry 隔离标志一致，且 PDF 未被删除
- 裁决表处置枚举合法

```text
jp/kr sources          : 16
jp/kr PDFs bound       : 14
adjudication rows      : 14
anomalies              : 0
OK   JP/KR source identity checks pass (quarantine enforced, no new anomalies).
```

门禁只发现异常，不自动做法律裁决。

## 六、验证命令与结果

```bash
uv run --frozen python scripts/build_source_registry.py --write   # 120 entries, 0 drift
uv run --frozen python scripts/build_source_registry.py --check   # OK in sync
uv run --frozen python scripts/build_jp_kr_adjudication.py --write  # 14 rows
uv run --frozen python scripts/build_jp_kr_adjudication.py --check  # OK
uv run --frozen python scripts/build_jp_kr_pending_source_proposals.py --write  # 8 rows
uv run --frozen python scripts/build_jp_kr_pending_source_proposals.py --check  # OK
uv run --frozen python scripts/check_regional_source_identity.py    # EXIT=0
uv run --frozen pytest backend/common/knowledge/tests/test_regional_knowledge.py -q   # 7 passed
uv run --frozen pytest backend/common/knowledge/tests/test_registry.py -q             # 6 passed
uv run --frozen pytest backend/services/tests/test_knowledge_projection.py -q         # 2 passed
uv run --frozen pytest backend/common/ backend/services/ -q                          # 417 passed
```

## 七、待人工签署后执行（不阻断本报告，但未完成）

1. **第三阶段逐项裁决**：10 个隔离 source + 2 个元数据复核 + 2 个孤立 PDF 的最终处置需法律专家签署。
2. **JP-LAW-008 二选一**：确认原「电气通信事业法」PDF 是否放错；若放错则找真正 PDF 并保留 `JP-LAW-008`，否则改标题/语义并建立网络安全法新 source。
3. **KR-LAW-007 二选一**：确认「网络利用促进与信息保护法」正确 PDF，并为 `B01`『信息通信基础保护法』建立独立 source（两部不同法律，不可复用同一 source）。
4. **JP-GUIDE-006 / JP-GUIDE-007**：补齐『第三方提供记录编』『匿名加工信息编』正确 PDF；`A04`『基本方针』与 `A07`『欧盟/英国充分性』需另建独立 source。
5. **JP-LAW-009 / KR-GUIDE-006**：补官方 PDF 或登记 HTML 快照，或正式降级 metadata-only/停用。
6. **B01_1/B01_2 版本关系**、**A04_1/A04_2 附件关系**：需在 registry 增加 `version_group/valid_from/valid_to/supersedes` 与 `relation=annex` 字段后统一重建。
7. **第四阶段统一重建链**：签署后按 `裁决表 → sources.csv → source_registry.v1.json → regulation_articles.jsonl → legal_index_intl → Evidence Center → 历史引用兼容映射` 重建，并复验标题/条文/索引/前端一致。
8. **浏览器证据**：JP/KR 引用跳转与下载证据需在重建后补充。

未签署的 source 继续处于隔离态，不参与正式法律报告。

## 八、待建 source 提议表

`status/check/task065/jp_kr_pending_source_proposals.csv` 共 8 行，列出所有「真实存在但当前无正确 source 归属」的 PDF，供专家签署后直接用于第四阶段重建。

| proposal | relation | 建议 source_id | 建议 doc_type | PDF 首页身份 | 建议标题 |
|---|---|---|---|---|---|
| P-JP-01 | independent | JP-POLICY-001 | policy | 個人情報の保護に関する基本方針 | 日本个人信息保护基本方针 |
| P-JP-02 | independent | JP-GUIDE-009 | guideline | Supplementary Rules（EU/UK Adequacy） | 日本基于充分性决定接收欧盟/英国转移个人数据的补充规则 |
| P-JP-03 | independent | JP-LAW-010 | law | サイバーセキュリティ基本法（生效版） | 日本网络安全基本法（2026-10-01 施行版） |
| P-JP-04 | version | JP-LAW-010 | law | サイバーセキュリティ基本法（失效版） | 日本网络安全基本法（2026-10-01 失效版） |
| P-KR-01 | independent | KR-STD-007 | technical_standard | 개인정보의 안전성 확보조치 기준 | 韩国个人信息安全措施标准 |
| P-KR-02 | annex | KR-STD-007 | technical_standard | 【별표】보호조치 예시（附表） | 韩国个人信息安全措施标准附表 |
| P-KR-03 | independent | KR-GUIDE-008 | guideline | 표준 개인정보 보호지침 | 韩国标准个人信息保护指针 |
| P-KR-04 | independent | KR-LAW-008 | law | 정보통신기반 보호법 | 韩国信息通信基础保护法 |

生成命令：

```bash
uv run --frozen python scripts/build_jp_kr_pending_source_proposals.py --write  # 8 rows
uv run --frozen python scripts/build_jp_kr_pending_source_proposals.py --check  # OK
```

**枚举变更（已执行）**：经确认新增两个 `doc_type` 值——`policy`（政府方针）与 `technical_standard`（技术标准）。`backend/common/knowledge/registry.py::_source_kind_from_row` 已将它们映射到稳定的 `SourceKind` 词汇（`policy → official_guide`、`technical_standard → standard_clause`），避免扩 `SourceKind` Literal 牵连检索/引用策略与 Evidence Center 标签。`suggested_source_id` 前缀随之从 `GUIDE` 调整为 `POLICY`（P-JP-01）与 `STD`（P-KR-01/02），具体定名仍待专家确认。

**注意**：`suggested_source_id`、`suggested_title` 等仍为初稿建议；`P-JP-02`（欧盟/英国充分性补充规则）是否仍归 `guideline`、`JP-POLICY-001`/`KR-STD-007` 的前缀命名，同样待专家确认。
