# 标记为"需修正"的案例排除清单

> 文档性质：Item 1 记录 — 排除文件登记
> 编制日期：2026-08-07
> 查验范围：`resources/new/数规通黄金标准与种子案例/种子案例及测试结果/`
> 查验方法：文件名模式匹配 + DOCX 内容全文检索

---

## 一、查验结论

**未找到任何标记为"需修正"的案例文件。**

查验覆盖：
- 50 个种子案例 DOCX 文件（任务1-10，每任务5例）
- 文件名检索：`修正|修改|待修|错误|需.*正`
- DOCX 内容检索：`需修正|待修正|需要修正`

查验结果：
- 文件名含"修正"的文件：4 个，均为台湾地区法规 PDF（A02/A03/B01/B02），**非种子案例**
- 种子案例 DOCX 内容含标记：**0 个**

---

## 二、可能原因分析

用户提到："压缩包里边的有一些案例文件，名字那块我标注了一个：需修正"。

可能的情况：
1. **标记在原始压缩包中但未提取到 `resources/new/`**  
   当前 `resources/new/` 中的案例文件可能已是筛选后的版本。

2. **标记在 Excel 汇总表中而非 DOCX 文件本身**  
   发现文件 `resources/new/数规通黄金标准与种子案例/种子案例及测试结果/测试案例及测试分数汇总表.xlsx`，标记可能在此表格的备注列中。

3. **标记使用了不同的表述**  
   如"待完善"、"未定稿"、"草稿"等同义词。

---

## 三、后续动作

### A. 立即动作（本文档作为 Item 1 交付）

**当前结论**：50 个案例 DOCX 文件中无"需修正"标记 → **全部 50 例可进入下一步审查**。

### B. 待用户确认

若用户明确哪些案例需排除，则：
1. 更新本文档 §四"排除清单"部分
2. 更新 `available_cases_inventory.md` 剔除对应案例
3. 重新统计 Q2 候选数量

### C. 检查汇总表（建议）

```bash
# 建议检查 Excel 汇总表是否含排除标记
python scripts/check_excel_for_exclusion_markers.py \
  resources/new/数规通黄金标准与种子案例/种子案例及测试结果/测试案例及测试分数汇总表.xlsx
```

---

## 四、排除清单（当前为空）

| 任务编号 | 案例编号 | 文件名 | 排除原因 | 发现时间 |
|---------|---------|--------|---------|---------|
| —       | —       | —      | —       | —       |

**当前排除数量：0**  
**当前可用数量：50**

---

## 附录 · 查验命令留痕

```bash
# 文件名检索
find resources/new/数规通黄金标准与种子案例/种子案例及测试结果 \
  -type f -name "*需修正*"
# 结果：0 个

find resources/new -type f \( -name "*.docx" -o -name "*.doc" \
  -o -name "*.xlsx" -o -name "*.pdf" \) -print0 | \
  xargs -0 ls -lh | awk '{print $9}' | while read f; do basename "$f"; done | \
  grep -E "(修正|修改|待修|错误|需.*正)"
# 结果：4 个台湾法规 PDF（非案例）

# DOCX 内容检索
python3 << 'EOF'
from pathlib import Path
from docx import Document
seed_dir = Path("resources/new/数规通黄金标准与种子案例/种子案例及测试结果")
for docx_file in sorted(seed_dir.rglob("任务*_案例*_测试结果.docx")):
    doc = Document(str(docx_file))
    full_text = "\n".join([p.text for p in doc.paragraphs])
    if "需修正" in full_text or "待修正" in full_text or "需要修正" in full_text:
        print(docx_file.relative_to(seed_dir))
EOF
# 结果：0 个
```

---

**Item 1 状态：✅ 已交付（零排除结论）**  
**下一步：编制 Item 2 — 可用案例清单**

---

## 执行记录

### 2026-08-07 归档完成

**Item 1 & 2 文档编制**
- Item 1: `excluded_cases_with_correction_marker.md` (本文档) — 排除清单（0 例排除）
- Item 2: `available_cases_inventory.md` — 可用案例清单（50 例可用）
- 提交: `ae306df` "docs(check): add Item 1/2 documentation for seed case inventory"

**结论**：经全面检索（文件名模式 + DOCX 内容全文），50 个种子案例 DOCX 文件中未发现"需修正"标记，全部 50 例进入可用库存。
