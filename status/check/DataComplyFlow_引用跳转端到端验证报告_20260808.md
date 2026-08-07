# DataComplyFlow 引用跳转端到端验证报告

- **日期**：2026-08-08
- **验证范围**：CN-REG-004 复验、路径 A（`[n]` 脚注）、路径 B（`【依据：】`）、P2 地区法规入库
- **配套档案**：`status/check/DataComplyFlow_引用跳转与知识库入库现状_20260808.md`（现状盘点，含 P0–P2 修复记录）

---

## 一、结论摘要

| 项目 | 结论 | 证据 |
|---|---|---|
| P0 CitationMap 字段名对齐 | ✅ 通过 | commit `979d714`，CN-REG-004 lookup FOUND |
| P1a `normalize_article_no` 中文数字 | ✅ 通过 | 第一条→1、第十三条→13、第二十条→20、第21条→21 |
| P1b `buildResolvedCitation` 异步化 | ✅ 通过 | 641 项测试全绿 |
| P2 地区法规字段名 | ✅ 已修复 | commit `57983e4` |
| P2 地区法规**覆盖率** | ⚠️ 部分缺失 | 51 个 source 中 18 个零条文（详见第四节） |
| 回归测试 | ✅ 641 passed / 0 failed | `uv run pytest -q`，83.68s |

**核心判断**：字段名层面的 bug 已全部关闭，跳转链路在**有条文数据的 source 上可用**。剩余的 NOT FOUND 属于**上游 PDF 解析缺口**，不是代码缺陷。

---

## 二、P2 字段名修复（本次会话）

### 2.1 问题根因

`scripts/ingest_regional_laws.py` 写入 JSONL 时使用 `article_no` / `article_text`，而 `backend/services/knowledge_index.py::get_article_detail` 读取 `article_ref` / `content`。两套字段名不兼容，导致所有地区法规 lookup 恒为 NOT FOUND。

### 2.2 修复内容

```python
# scripts/ingest_regional_laws.py — 写入侧
entry = {
    "source_id": s.source_id,
    "article_ref": article_no,       # was: article_no
    "law_name": s.law_name_for_articles,
    "content": article_text[:2000],  # was: article_text
    "jurisdiction": s.jurisdiction,
}

# existing_keys 去重侧（兼容旧数据）
keys.add((obj["source_id"], str(obj.get("article_ref") or obj.get("article_no", ""))))
```

### 2.3 数据迁移

1. 备份 `regulation_articles.jsonl.bak_fieldfix`
2. 删除 1347 条旧字段名条目（3030 → 1683 行）
3. 重新入库：`uv run python scripts/ingest_regional_laws.py`
   - Sources added: 0 / PDFs processed: 33 / Articles added: 1347 / PDFs skipped: 18
4. 最终 **3030 行**（1683 原有 + 1347 新入库）
5. 验证通过后删除备份

### 2.4 测试基线更新

`backend/services/tests/test_knowledge_index.py::test_article_detail_resolves_every_unique_registry_locator` 的硬编码计数随数据量变化：

| 断言 | 旧值 | 新值 |
|---|---|---|
| `len(unique_rows)` | 1613 | 2960 |
| unique `source_id` 数 | 69 | 102 |

`unique_rows` 2960 = 1613（原有）+ 1347（新入库，全部唯一）。差额 70 行为 CN-LAW-001 等**原始数据固有的重复键**（如 `第二十九条` 3 份），本次未引入新重复，该测试逻辑本就将其排除。

---

## 三、Lookup 抽查结果

### 3.1 CN-REG-004（数据出境安全评估办法）

| 引用 | 归一化 | 结果 |
|---|---|---|
| 第一条 | 1 | ✅ FOUND — 为了规范数据出境活动，保护个人信息权益… |
| 第十三条 | 13 | ✅ FOUND — 数据处理者对评估结果有异议的… |
| 第二十条 | 20 | ✅ FOUND — 本办法自2022年9月1日起施行… |
| 第二十一条 | 21 | ⭕ NOT FOUND（**预期**：该办法仅 20 条） |

### 3.2 地区法规抽查

| source | 引用 | 结果 | 说明 |
|---|---|---|---|
| JP-LAW-001 | 第1条 | ✅ FOUND | 字段名修复生效 |
| MY-LAW-001 | 第4条 | ✅ FOUND | 英文条文正常 |
| JP-LAW-002 | 第1条 | ❌ NOT FOUND | **该 source 零条文**（PDF 图片型） |
| SG-LAW-001 | 第11条 | ❌ NOT FOUND | 仅解析出第 3–9 条（附表段） |

---

## 四、遗留缺口：地区法规覆盖率

**51 个 SourceDef 中 33 个有条文、18 个零条文。** 零条文 source 上的任何引用都无法跳转。

### 4.1 零条文 source（18 个）

| 辖区 | source_id | 名称 |
|---|---|---|
| vn | VN-LAW-001 | 越南个人数据保护法（91/2025） |
| vn | VN-REG-002 | 越南个人数据保护法实施法令（356/2025） |
| vn | VN-LAW-003 | 越南数据法（60/2024） |
| vn | VN-REG-004 | 越南数据法实施法令（165/2025） |
| vn | VN-REG-005 | 越南重要数据和核心数据目录（20/2025） |
| vn | VN-LAW-006 | 越南网络安全法（116/2025） |
| sg | SG-REG-002 | 新加坡个人数据保护条例（PDPR 2021） |
| sg | SG-REG-004 | 新加坡个人数据保护执法条例 2021 |
| sg | SG-LAW-005 | 新加坡网络安全法（Cybersecurity Act 2018） |
| sg | SG-REG-006 | 新加坡第三方CII网络安全条例 2026 |
| jp | JP-GUIDE-007 | 日本个人信息保护匿名加工信息指南（2022） |
| jp | JP-LAW-009 | 日本重要经济安保信息保护法（2024） |
| kr | KR-GUIDE-006 | 韩国儿童个人信息保护指南（2024） |
| hk | HK-LAW-001 | 香港个人资料（私隐）条例（第486章） |
| hk | HK-GUIDE-004 | 香港资料泄露事故处理指引（2022） |
| mo | MO-GUIDE-002 | 澳门个人资料跨境转移指引（2024） |
| my | MY-REG-004 | 马来西亚个人数据保护注册条例（2013） |
| my | MY-REG-005 | 马来西亚个人数据保护豁免条例（2023） |

**越南 6 部法规全部零条文**，是覆盖缺口最集中的辖区。香港 `HK-LAW-001`（私隐条例第486章）作为主干法零条文，影响面较大。

### 4.2 解析可能不完整的 source（条文数异常偏少）

| source_id | 条文数 | 名称 |
|---|---|---|
| JP-GUIDE-005 | 2 | 日本个人信息保护境外提供指南（2022） |
| HK-GUIDE-005 | 2 | 香港AI处理个人资料实务守则（2024） |
| JP-GUIDE-006 | 3 | 日本个人信息保护第三方提供记录指南（2022） |
| MY-REG-007 | 3 | 马来西亚NCII条例（2024） |
| MY-REG-008 | 3 | 马来西亚网络安全服务提供者条例（2024） |
| JP-GUIDE-004 | 5 | 日本个人信息保护通则指南（2022） |
| HK-GUIDE-002 | 5 | 香港跨境资料转移指引 |
| HK-GUIDE-003 | 6 | 香港建议示范合同条款（2022） |
| SG-LAW-001 | 7 | 新加坡个人数据保护法（PDPA 2012） |
| HK-GUIDE-007 | 10 | 香港PCSO合规指引（2025） |

`SG-LAW-001` 是典型案例：PDPA 2012 实际有数十节，但只解析出 `article_ref` 3–9，且内容看起来来自 **FIRST SCHEDULE 附表**而非正文条款。说明条文切分正则未命中该 PDF 的正文编号格式。

---

## 五、未完成项

| 项目 | 状态 | 说明 |
|---|---|---|
| 路径 A / 路径 B 浏览器验证 | ⬜ 未执行 | 需启动前后端并人工点击取截图 |
| 图片型 PDF OCR 补全 | ⬜ 未排期 | 18 个零条文 source 的根本解法 |
| 条文切分正则加固 | ⬜ 未排期 | 针对 SG/HK/JP 的英文 `s. N` / 分节编号格式 |
| CN-LAW-001 重复键清理 | ⬜ 未排期 | 34 个重复键属原始数据问题，`get_article_detail` 命中多条时行为需确认 |

---

## 六、提交记录

| commit | 内容 |
|---|---|
| `979d714` | P0 CitationMap 字段名对齐 + CN-REG-004 正式条文替换 |
| `bc872c0` | P2 地区法规入库（首版，字段名有误） |
| `77333d2` | 现状文档 `status/view/` → `status/check/` |
| `57983e4` | P2 地区法规入库字段名对齐 `get_article_detail` + 测试基线更新 |

---

## 七、验证命令留档

```bash
# lookup 抽查
uv run python -c "
from backend.services.knowledge_index import get_article_detail
for src, art in [('CN-REG-004','1'),('CN-REG-004','13'),('JP-LAW-001','1'),('MY-LAW-001','4')]:
    r = get_article_detail(src, art)
    print(src, art, 'FOUND' if r else 'NOT FOUND')
"

# 回归
uv run pytest -q          # 641 passed

# 覆盖率盘点
uv run python -c "
import sys, json, collections; sys.path.insert(0,'scripts')
from ingest_regional_laws import SOURCES
c = collections.Counter()
for line in open('resources/legal/registry/regulation_articles.jsonl'):
    c[json.loads(line)['source_id']] += 1
print('零条文:', [s.source_id for s in SOURCES if c[s.source_id]==0])
"
```
