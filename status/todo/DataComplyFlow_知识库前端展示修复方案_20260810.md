# DataComplyFlow 知识库前端展示质量修复方案

> **版本**: v1.0
> **日期**: 2026-08-10
> **前置分析**: `status/todo/DataComplyFlow_知识库前端展示质量问题分析_20260810.md`
> **涉及范围**: 前端渲染 (LawViewerPage/EvidenceCenterPage) + 后端数据清洗 (`knowledge_index.py` `_clean_source_text`) + snapshot 文件治理
> **状态**: 待执行

---

## 一、修复目标

```
修复前问题数: 15 个 (4 P0 + 7 P1 + 4 P2)
修复后目标:   P0 清零，P1 ≤ 2 个可接受残余，P2 推迟到后续迭代

核心可度量指标:
┌─────────────────────────────────────┬──────────┬──────────┐
│ 指标                                │ 修复前   │ 目标     │
├─────────────────────────────────────┼──────────┼──────────┤
│ LawViewerPage 换行正确保留          │ ❌       │ ✅       │
│ metadata-only 数据源                │ 7 个     │ 0 个     │
│ PDF 页码/页眉混入正文的文件数       │ 16 个    │ 0 个     │
│ 省略号噪音行                        │ 全部 CELEX│ 0       │
│ 英文断字 (broken hyphenation)       │ CELEX+FR │ 0        │
│ 中文硬换行断句                      │ 7 个文件  │ 0        │
│ _clean_source_text 已知缺陷          │ 8 项     │ 0 项     │
│ snapshot 预览页展示 clean 内容       │ ❌       │ ✅       │
│ Markdown 渲染支持                   │ ❌       │ ✅       │
└─────────────────────────────────────┴──────────┴──────────┘
```

---

## 二、任务分解总表

```
回合 0: 无依赖的前置准备
  T0.1 _clean_source_text 全量重写（核心清洗引擎）
  T0.2 编写验证脚本框架（所有后续回合的验收基础）

回合 1: P0 阻断项（平行推进，3 项）
  T1.1 LawViewerPage white-space: pre-wrap
  T1.2 7 个元数据桩治理
  T1.3 CELEX PDF 页码/页眉清理策略（集成到 T0.1 清洗引擎）

回合 2: 数据清洗增强（依赖 T0.1，4 项平行）
  T2.1 省略号噪音行过滤
  T2.2 英文断字修复
  T2.3 中文硬换行合并
  T2.4 HTML 标签/entity 彻底清理

回合 3: 前端渲染增强（平行推进，2 项）
  T3.1 LawViewerPage Markdown 渲染
  T3.2 EvidenceCenterPage 与 LawViewerPage 渲染行为对齐

回合 4: 解析器扩展（依赖 T0.1，2 项）
  T4.1 _parse_articles_from_text 支持 EU/US 文章格式
  T4.2 snapshot 预览管道接入清洗引擎

回合 5: E2E 验证与收尾
  T5.1 全量回归——所有源 article_detail API 返回质量
  T5.2 报告归档到 check/
```

依赖图:
```
T0.1 ──┬── T1.3 ──┬── T2.1
T0.2    │          ├── T2.2
        │          ├── T2.3
        │          ├── T2.4
        │          ├── T4.1
        │          └── T4.2
        │
T1.1 ──────────────────────────────────── T3.1 ── T3.2
T1.2
        │
        └────────── T5.1 ── T5.2
```

---

## 三、T0：前置准备

### T0.1 _clean_source_text 全量重写

**文件**: `backend/services/knowledge_index.py`

**当前函数**: 7 行，8 项缺陷
**目标函数**: 单管线 5 阶段处理，每阶段独立可测试

#### 3.1.1 设计：5 阶段清洗管线

```
原始文本
  │
  ▼
Stage 1: NORMALIZE ─── 统一换行符、零宽字符、BOM 移除
  │
  ▼
Stage 2: DEARTIFACT ── PDF 页码/页眉过滤、省略号行移除、
  │                     换页符→段落分隔、vertical tab 处理
  ▼
Stage 3: DEHTML ─────── HTML 标签剥离、entity 解码 (&#xxx; &nbsp; &amp;)
  │
  ▼
Stage 4: REJOIN ────── 中文行合并、英文断字修复、多余空行折叠
  │
  ▼
Stage 5: NORMALIZE_FINAL ── 多余空格收敛、首尾 trim
  │
  ▼
清洁文本
```

#### 3.1.2 完整代码

```python
import re
import html

# ── Stage 1: Normalize ──────────────────────────────────────

def _stage1_normalize(text: str) -> str:
    """统一换行符、移除零宽字符和 BOM，建立干净的基线。"""
    # BOM
    text = text.replace('﻿', '')
    # CRLF / CR → LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 零宽字符 (U+200B zero-width space, U+200C ZWNJ, U+200D ZWJ, U+FEFF)
    text = text.replace('​', '').replace('‌', '').replace('‍', '')
    return text


# ── Stage 2: Deartifact ─────────────────────────────────────

# EU Official Journal 页眉: "4.5.2016            EN                            Official Journal of the European Union                                                L 119/1"
_EU_OJ_HEADER_RE = re.compile(
    r'^\d{1,2}\.\d{1,2}\.\d{4}\s+EN\s+Official\s+Journal\s+of\s+the\s+European\s+Union\s+L\s+\d+/\d+\s*$',
    re.MULTILINE | re.IGNORECASE,
)

# 独立页码行: "L 199/31" (可能前后有空白行)
_EU_OJ_PAGE_RE = re.compile(
    r'^L\s+\d+/\d+\s*$',
    re.MULTILINE,
)

# 省略号噪音行: ". . . . . . . . . . . . . . . " (各种变体)
_ELLIPSIS_NOISE_RE = re.compile(
    r'^\s*(?:[.·]\s*){4,}\s*$',
    re.MULTILINE,
)

# 单独的数字行(大概率是页码残留): "31" 或 "   31   " 但需要谨慎，避免误删条款编号
# 只匹配纯数字+空白且周围有空行的情况
_STANDALONE_PAGE_NUM_RE = re.compile(
    r'^\s*\d{1,4}\s*$',
    re.MULTILINE,
)

def _stage2_deartifact(text: str) -> str:
    """移除 PDF/OCR 带来的结构噪音。"""
    # 1. 换页符 → 段落分隔
    text = text.replace('\f', '\n\n')
    # 2. Vertical tab → 换行
    text = text.replace('\v', '\n')
    # 3. EU Official Journal 完整页眉行
    text = _EU_OJ_HEADER_RE.sub('', text)
    # 4. 独立页码行
    text = _EU_OJ_PAGE_RE.sub('', text)
    # 5. 省略号噪音
    text = _ELLIPSIS_NOISE_RE.sub('', text)
    # 6. 3+ 连续空行 → 2 空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


# ── Stage 3: DeHTML ─────────────────────────────────────────

_HTML_TAG_RE = re.compile(r'(?is)<[^>]+>')
_HTML_ENTITY_RE = re.compile(r'&#?[a-zA-Z0-9]+;')

def _stage3_dehtml(text: str) -> str:
    """剥离 HTML 标签，解码 HTML entities。"""
    # 只在确实有 HTML 时生效
    if '<' in text and '>' in text:
        # 先处理 script/style/noscript（删除内容）
        text = re.sub(r'(?is)<script[^>]*>.*?</script>', ' ', text)
        text = re.sub(r'(?is)<style[^>]*>.*?</style>', ' ', text)
        text = re.sub(r'(?is)<noscript[^>]*>.*?</noscript>', ' ', text)
        # 将块级标签和列表标签替换为换行，保留段落边界
        block_tags = r'(?i)</?(?:p|div|section|article|li|ul|ol|tr|table|blockquote|h[1-6]|br)[^>]*/?>'
        text = re.sub(block_tags, '\n', text)
        # td/th → 空格
        text = re.sub(r'(?i)</?(?:td|th)[^>]*/?>', ' ', text)
        # 其余标签 → 空格
        text = _HTML_TAG_RE.sub(' ', text)
    # HTML entities
    text = html.unescape(text)
    return text


# ── Stage 4: Rejoin ─────────────────────────────────────────

# 中文行合并: 前一行以中文字符结尾, 后一行以中文字符开头, 中间只有 \n
_CN_REJOIN_RE = re.compile(r'([一-鿿])\n([一-鿿])')

# 英文断字修复: "process-\ning" → "processing"
# 条件: 前一行以 [a-z]{3,}- 结尾, 后一行以 [a-z]{3,} 开头
_EN_HYPHEN_RE = re.compile(r'([a-z]{3,})-\s*\n\s*([a-z]{3,})')

def _stage4_rejoin(text: str) -> str:
    """重建被 PDF/排版截断的语义连贯性。"""
    # 1. 中文行合并（去硬换行）："个人信息出境认证活\n动" → "个人信息出境认证活动"
    # 多轮合并直到稳定（最多5轮，实际1-2轮即收敛）
    for _ in range(5):
        new_text = _CN_REJOIN_RE.sub(r'\1\2', text)
        if new_text == text:
            break
        text = new_text
    # 2. 英文断字修复
    text = _EN_HYPHEN_RE.sub(r'\1\2', text)
    # 3. 多余空行 → 双空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


# ── Stage 5: Normalize Final ─────────────────────────────────

def _stage5_normalize_final(text: str) -> str:
    """最终标准化：空格收敛、首尾清理。"""
    # 多空格 → 单空格（保留换行）
    text = re.sub(r'[ \t]+', ' ', text)
    # 行首尾空格
    text = re.sub(r'^[ \t]+|[ \t]+$', '', text, flags=re.MULTILINE)
    # 全局首尾
    text = text.strip()
    return text


# ── 主入口 ──────────────────────────────────────────────────

def clean_source_text(text: str) -> str:
    """5 阶段清洗管线：标准化 → 去噪 → 除 HTML → 重连 → 终标准化。"""
    if not text:
        return ""
    stages = [
        _stage1_normalize,
        _stage2_deartifact,
        _stage3_dehtml,
        _stage4_rejoin,
        _stage5_normalize_final,
    ]
    result = text
    for stage in stages:
        result = stage(result)
    return result


# ── 兼容旧函数名 ─────────────────────────────────────────────

def _clean_source_text(text: str) -> str:
    """向后兼容 wrapper。"""
    return clean_source_text(text)
```

#### 3.1.3 修改点

文件 `backend/services/knowledge_index.py`：
- 新增 `Stage 1-5` 五个静态函数 + `clean_source_text()` 主入口
- 保留 `_clean_source_text()` 作为 wrapper 调用 `clean_source_text()`
- 删除旧 `_clean_source_text` 函数体

#### 3.1.4 验证命令

```bash
# 1. 单元级测试：各 Stage 独立验证
python3 << 'EOF'
import sys; sys.path.insert(0, '.')
from backend.services.knowledge_index import clean_source_text

# Stage 2: PDF page header removal
text = "7.6.2021            EN                            Official Journal of the European Union                                                L 199/31\n\nSome content"
result = clean_source_text(text)
assert "Official Journal" not in result, f"FAIL: page header not removed: {result[:100]}"
assert "L 199/31" not in result, f"FAIL: page number not removed"
assert "Some content" in result, f"FAIL: real content removed"
print("PASS: PDF page header removal")

# Stage 2: Ellipsis noise
text = ". . . . . . . . . . . . . . . . . . . .\n\nreal text"
result = clean_source_text(text)
assert ". . ." not in result, f"FAIL: ellipsis noise not removed"
assert "real text" in result
print("PASS: Ellipsis noise removal")

# Stage 4: Chinese line rejoining
text = "个人信息出境认证活\n动，促进个人信息高效安全跨境流动"
result = clean_source_text(text)
assert "活动" in result, f"FAIL: CN line not rejoined: {result[:80]}"
assert "个人信息出境认证活动" in result
print("PASS: Chinese line rejoining")

# Stage 4: English hyphenation fix
text = "The controller shall implement appro-\npriate technical measures."
result = clean_source_text(text)
assert "appro-\npriate" not in result, f"FAIL: hyphenation not fixed"
assert "appropriate" in result, f"FAIL: hyphenated word not merged: {result[:80]}"
print("PASS: English hyphenation fix")

# Stage 3: HTML tag removal
text = "<strong>Article 1</strong> Text here &amp; more"
result = clean_source_text(text)
assert "<strong>" not in result, f"FAIL: HTML tags not removed"
assert "&amp;" not in result, f"FAIL: HTML entities not decoded"
assert "Article 1" in result
assert "& more" in result
print("PASS: HTML tag/entity removal")

# Stage 1: BOM + zero-width
text = "﻿Hello​ world\r\nLine2"
result = clean_source_text(text)
assert "﻿" not in result
assert "​" not in result
assert "\r" not in result
print("PASS: BOM + zero-width + CRLF normalization")

print("\nALL UNIT TESTS PASSED")
EOF

# 2. 集成测试：用真实 CELEX 文件验证
python3 << 'EOF'
import sys; sys.path.insert(0, '.')
from backend.services.knowledge_index import clean_source_text

test_file = "resources/legal/sources/eu/snapshots/eu-sup-013_celex_32021d0914_en_txt_a7400d96.md"
with open(test_file, 'r', encoding='utf-8', errors='ignore') as f:
    raw = f.read()

clean = clean_source_text(raw)

checks = [
    ("L 199/31", "page number"),
    ("Official Journal of the European Union", "OJ header"),
    ("7.6.2021", "OJ date line"),
    (". . . .", "ellipsis noise"),
]
for pattern, desc in checks:
    if pattern in clean:
        print(f"FAIL: {desc} still present in output")

# Count preserved meaningful content
lines = [l for l in clean.split('\n') if l.strip()]
print(f"Clean output: {len(lines)} non-empty lines ({len(clean)} chars)")
print(f"Original: {len(raw)} chars")
print("INTEGRATION TEST COMPLETE")
EOF
```

---

### T0.2 验证脚本框架

**文件**: `status/todo/verify_knowledge_frontend_quality.py`

```python
#!/usr/bin/env python3
"""知识库前端展示质量验证脚本。
用法: python3 verify_knowledge_frontend_quality.py [--all]
"""
import sys, os, re, json, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.knowledge_index import (
    clean_source_text,
    get_article_detail,
    _parse_articles_from_text,
)

PASS = 0
FAIL = 0

def check(name: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        print(f"  ✅ {name}" + (f": {detail}" if detail else ""))
        PASS += 1
    else:
        print(f"  ❌ {name}" + (f": {detail}" if detail else ""))
        FAIL += 1

# ── 1. 清洗引擎单元测试 ──
def verify_clean_engine():
    print("\n📋 clean_source_text 清洗引擎")

    # PDF header
    result = clean_source_text("7.6.2021   EN   Official Journal of the European Union   L 199/31\n\ncontent")
    check("PDF 页眉过滤", "Official Journal" not in result and "L 199" not in result)
    check("正文保留", "content" in result)

    # Ellipsis
    result = clean_source_text(". . . . . . . . . . .\nreal")
    check("省略号行过滤", ". . ." not in result)

    # CN rejoining
    result = clean_source_text("个人信息保护认\n证办法，由\n专业认证机构")
    check("中文合并(1)", "个人信息保护认证办法" in result)
    check("中文合并(2)", "专业认证机构" in result)

    # EN hyphenation
    result = clean_source_text("appro-\npriate technical")
    check("英文断字修复", "appropriate" in result)

    # HTML
    result = clean_source_text("<strong>Title</strong> &amp; text &#169;")
    check("HTML 标签", "<strong>" not in result)
    check("HTML entity (&amp;)", "&amp;" not in result and "&" in result)

    # BOM
    result = clean_source_text("﻿Hello​")
    check("BOM + 零宽", "﻿" not in result and "​" not in result)

# ── 2. CELEX 集成测试 ──
def verify_celex_files():
    print("\n📋 CELEX 文件清洗集成测试")
    import glob
    celex_files = glob.glob("resources/legal/sources/eu/snapshots/eu-sup-*_celex_*_en_txt_*.md")
    for fp in celex_files:
        fname = os.path.basename(fp)[:60]
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()
        clean = clean_source_text(raw)
        has_oj = "Official Journal" in clean
        has_page = re.search(r'^L\s+\d+/\d+\s*$', clean, re.MULTILINE)
        has_ellipsis = re.search(r'^\s*(?:[.·]\s*){4,}\s*$', clean, re.MULTILINE)
        ok = not has_oj and not has_page and not has_ellipsis
        check(f"CELEX: {fname}", ok,
              f"OJ={has_oj} page={bool(has_page)} ellipsis={has_ellipsis}" if not ok else "clean")

# ── 3. 前端渲染一致性 ──
def verify_frontend_consistency():
    print("\n📋 前端渲染一致性")
    # 检查 CSS 是否含 white-space: pre-wrap
    css_path = "frontend/src/styles/app/pages.css"
    with open(css_path, 'r') as f:
        css = f.read()
    check(".law-viewer-article p 含 white-space",
          "white-space" in css and "pre-wrap" in css or "pre-line" in css)

    # 检查两个页面组件渲染方式
    lvp = open("frontend/src/pages/LawViewerPage.tsx").read()
    evp = open("frontend/src/pages/EvidenceCenterPage.tsx").read()
    check("LawViewerPage article 渲染", "article_content" in lvp)
    check("EvidenceCenterPage article 渲染", "pre-wrap" in evp or "pre-line" in evp)

# ── 4. 元数据桩治理 ──
def verify_metadata_stubs():
    print("\n📋 元数据桩治理")
    stub_files = [
        "resources/legal/sources/cn/snapshots/cn-sup-005_汽车数据安全管理若干规定_试行_中央网络安全和信息化委员会办公室_69b8dec0.md",
        "resources/legal/sources/cn/snapshots/cn-tpl-022_隐私政策样例_510dc5fc.md",
        "resources/legal/sources/us/snapshots/us_cpra_reference.md",
        "resources/legal/sources/us/snapshots/us_eo_14117_reference.md",
        "resources/legal/sources/eu/snapshots/eu_gdpr_art35_reference.md",
        "resources/legal/sources/eu/snapshots/eu_gdpr_art47_bcr_reference.md",
        "resources/legal/sources/eu/snapshots/eu_edpb_012020_tia_reference.md",
    ]
    for fp in stub_files:
        fname = os.path.basename(fp)[:50]
        if not os.path.exists(fp):
            check(f"移除: {fname}", True, "file removed")
            continue
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        # Must have real body content (not just metadata)
        lines = [l for l in content.split('\n') if l.strip() and not l.strip().startswith('#')]
        has_body = len(lines) >= 3 and sum(len(l) for l in lines) >= 200
        check(f"内容: {fname}", has_body,
              f"only {len(lines)} lines, {sum(len(l) for l in lines)} chars" if not has_body else "has body")

# ── 5. API 返回质量 ──
def verify_api_quality():
    print("\n📋 API article_detail 返回质量")
    # 抽样关键源
    test_cases = [
        ("CN-LAW-001", "1", 50, "cn law"),
        ("EU-LAW-001", "5", 100, "gdpr"),
        ("US-CA-001", "1798.100", 100, "cpra"),
        ("CN-REG-006", "1", 50, "cn regulation"),
    ]
    for sid, ano, min_len, desc in test_cases:
        detail = get_article_detail(sid, ano)
        ok = detail is not None and len(detail.get('article_content', '')) >= min_len
        content_len = len(detail.get('article_content', '')) if detail else 0
        check(f"{desc} ({sid}/{ano})", ok, f"{content_len} chars" if ok else "NOT FOUND")

# ── 6. Markdown 渲染支持 ──
def verify_markdown_support():
    print("\n📋 Markdown 渲染支持")
    lvp = open("frontend/src/pages/LawViewerPage.tsx").read()
    # 检查是否使用了 markdown 渲染组件或库
    has_md = "react-markdown" in lvp or "MarkdownRenderer" in lvp or "marked" in lvp or "remark" in lvp
    check("LawViewerPage Markdown 渲染", has_md, "no markdown renderer found" if not has_md else "found")

# ── sum
def main():
    global PASS, FAIL
    verify_clean_engine()
    verify_celex_files()
    verify_frontend_consistency()
    verify_metadata_stubs()
    verify_api_quality()
    verify_markdown_support()
    print(f"\n{'='*60}")
    print(f"  总计: {PASS} 通过 / {FAIL} 失败")
    print(f"{'='*60}")
    return 0 if FAIL == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 四、T1：P0 阻断项修复

### T1.1 LawViewerPage white-space 修复

**文件**: `frontend/src/styles/app/pages.css`

**修改**: 在 `.law-viewer-article p` 规则中添加 `white-space: pre-line`

```css
.law-viewer-article p {
  margin: 0.25rem 0;
  line-height: 1.65;
  color: #2e3a4d;
  white-space: pre-line;   /* ← 新增：保留换行，折叠多余空格 */
}
```

**选择 `pre-line` 而非 `pre-wrap` 的原因**:
- `pre-wrap`: 保留所有空格和换行 → CELEX 文件中大量不规则空格会被保留
- `pre-line`: 保留换行但折叠多余空格 → 比 `pre-wrap` 更适合 PDF 提取的文本

**验证**:
```bash
# 检查 CSS 文件中是否添加了 white-space
grep -n "white-space" frontend/src/styles/app/pages.css
# 期望: 在 .law-viewer-article p 块内包含 white-space: pre-line
```

---

### T1.2 7 个元数据桩治理

#### 治理策略

按源的实际情况分 3 类处理：

```
类型 A: 有替代数据源 — 更新 snapshot_path 指向正确文件
  ├── eu_gdpr_art35_reference.md   → 已通过 regulation_articles.jsonl 覆盖(GDPR Art 35)
  ├── eu_gdpr_art47_bcr_reference.md → 已通过 regulation_articles.jsonl 覆盖(GDPR Art 47)
  ├── us_cpra_reference.md          → 已通过 regulation_articles.jsonl 覆盖(CPRA)
  └── us_eo_14117_reference.md      → 已有 fr_2025_01_08_eo14117_excerpts.md

类型 B: 有对应的真实 excerpts 文件
  └── eu_edpb_012020_tia_reference.md → 已有 edpb_recommendations_01_2020_excerpts.md

类型 C: 无替代源 — 标记为 reference-only
  ├── cn-sup-005 (汽车数据安全管理若干规定) → 标记 path=reference
  └── cn-tpl-022 (隐私政策样例)             → 标记 path=reference
```

#### 具体操作

**Step 1**: 对类型 A/B，在 `sources.csv` 中更新 `snapshot_path`

```csv
# 修改前 → 修改后 (sources.csv)

# EU-GUIDE-002 (EDPB 01/2020) — 已有真实 excerpts
snapshot_path: resources/legal/sources/eu/snapshots/eu_edpb_012020_tia_reference.md
→ 不变（source 本身 snapshot 已指向 excerpts 文件 edpb_recommendations_01_2020_excerpts.md）

# US-FED-001 — 更新为真实文件
snapshot_path: resources/legal/sources/us/snapshots/us_eo_14117_reference.md
→ snapshot_path: resources/legal/sources/us/snapshots/fr_2025_01_08_eo14117_excerpts.md
```

**Step 2**: 对类型 C，在 `sources.csv` 中标记 `path=reference`

```csv
# CN-SUP-005 路径: path=reference (原 path 可能是 all 或空)
# CN-TPL-022 路径: path=reference
```

**Step 3**: 对类型 A 中已有 regulation_articles 覆盖的，可以保留 reference.md 文件（作为开发笔记），但确保不通过 snapshot_path 被前端引用。

**验证**:
```bash
python3 << 'EOF'
import csv
stub_ids = {'CN-SUP-005', 'CN-TPL-022'}
reference_ids = {'US-FED-001'}  # 已知已更新
with open('resources/legal/catalog/sources.csv') as f:
    for row in csv.DictReader(f):
        sid = row.get('source_id', '').strip()
        if sid in stub_ids:
            assert row.get('path', '').strip() == 'reference', f"{sid} must be path=reference"
        if sid in reference_ids:
            sp = row.get('snapshot_path', '')
            assert 'reference.md' not in sp, f"{sid} snapshot must not be reference.md"
print("Metadata stubs fix verified")
EOF
```

---

### T1.3 PDF 页码/页眉清理

**文件**: `backend/services/knowledge_index.py`

**方案**: 此项已集成到 **T0.1 的 `_stage2_deartifact()`** 中，不需要额外的代码修改。

`_stage2_deartifact()` 中已经实现了：
- EU Official Journal 完整页眉行匹配和删除
- 独立页码行 `L XXX/YY` 的匹配和删除
- 换页符 `\f` 替换为段落分隔

**验证**: 见 T0.1 验证命令中的 CELEX 集成测试部分。
直接对 16 个 CELEX 文件运行清洗 → 验证无页码残留。

---

## 五、T2：数据清洗增强

### T2.1 省略号噪音行过滤

**文件**: 已集成到 T0.1 `_stage2_deartifact()`

**_ELLIPSIS_NOISE_RE** 正则覆盖以下模式：
```
. . . . . . . . . . . . . . . . . . . .
     2. . . . . . . . . . . . . . . . .
· · · · · · · · · · · · · · · · · ·
 .  .  .  .  .  .  .  .  .
```

**验证**:
```bash
# 直接测试
python3 -c "
import sys; sys.path.insert(0, '.')
from backend.services.knowledge_index import clean_source_text
for test in ['. . . . . . . . .', '  .  .  .  .  .  .  .', '· · · · ·']:
    r = clean_source_text(test + '\n\nreal')
    assert 'real' in r and '. . .' not in r, f'Failed: {test}'
print('Ellipsis filter PASS')
"
```

---

### T2.2 英文断字修复

**文件**: 已集成到 T0.1 `_stage4_rejoin()`

**_EN_HYPHEN_RE** 正则：
```python
r'([a-z]{3,})-\s*\n\s*([a-z]{3,})'
```

匹配条件：
- 行末：至少 3 个小写字母 + `-`
- 换行
- 行首：至少 3 个小写字母
- 替换为：直接拼接（不含连字符）

**安全边界**：
- 只匹配 `[a-z]` 小写字母 → 避免误匹配专有名词断行（"US-\nChina"）
- `{3,}` 最小长度 → 避免对短词（"a-\nb"）的错误合并

**验证**:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from backend.services.knowledge_index import clean_source_text
tests = [
    ('appro-\npriate', 'appropriate'),
    ('process-\ning', 'processing'),
    ('trans-\nfer', 'transfer'),
    ('imple-\nment', 'implement'),
    # 不应合并的边界情况
    ('US-\nChina relations', 'US-\nChina relations'),
]
for inp, expected in tests:
    result = clean_source_text(inp)
    assert expected in result, f'Expected {expected!r} in {result!r}'
print('Hyphenation fix PASS')
"
```

---

### T2.3 中文硬换行合并

**文件**: 已集成到 T0.1 `_stage4_rejoin()`

**_CN_REJOIN_RE** 正则：
```python
r'([一-鿿])\n([一-鿿])'
```

多轮迭代合并（最多 5 轮）直到文本稳定。

**安全边界**：
- 仅当换行符两侧都是中文字符时才合并
- 保留中文和其他字符（英文、数字）间的换行

**验证**:
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from backend.services.knowledge_index import clean_source_text
tests = [
    ('个人信息出境认证活\n动，促进', '个人信息出境认证活动，促进'),
    ('根据《中华人民共和国个\n人信息保护法》', '根据《中华人民共和国个人信息保护法》'),
    # 不应合并：中英混排
    ('符合GDPR第\n一条规定', '符合GDPR第\n一条规定'),  # GDP 是英文，第一条是中文
]
for inp, expected in tests:
    result = clean_source_text(inp)
    # 比较时忽略多余空格
    assert expected.replace(' ', '') in result.replace(' ', ''), f'Expected {expected!r} in {result!r}'
print('CN rejoining PASS')
"
```

---

### T2.4 HTML 标签/entity 彻底清理

**文件**: 已集成到 T0.1 `_stage3_dehtml()`

增强点：
1. 新增 `script`/`style`/`noscript` 内容删除
2. 保留块级标签的换行语义 → 用 `\n` 替代
3. `&nbsp;` `&amp;` `&#169;` 等全部解码

**验证**: 见 T0.1 验证。

---

## 六、T3：前端渲染增强

### T3.1 LawViewerPage Markdown 渲染

**文件**: `frontend/src/pages/LawViewerPage.tsx`

**现状**: `<p>{article.article_content}</p>` — 纯文本渲染
**目标**: 对含 Markdown 标记的内容做 basic Markdown → HTML 转换

**方案 A（轻量，推荐）**: 手写一个 minimal 的 Markdown 转 HTML 函数，仅支持 Heading (`##`/`###`) 和粗体 (`**`)

```tsx
// 在 LawViewerPage.tsx 中添加
function renderArticleContent(content: string): React.ReactNode {
  if (!content) return null;
  
  // 检查是否包含 Markdown 标记
  const hasMarkdown = /^#{1,3}\s|^\*\*|^\-\s|^>\s/m.test(content);
  if (!hasMarkdown) {
    // 纯文本，直接渲染
    return content.split('\n').map((line, i) => (
      <React.Fragment key={i}>
        {i > 0 && <br />}
        {line}
      </React.Fragment>
    ));
  }
  
  // Markdown 渲染：按行处理
  return content.split('\n').map((line, i) => {
    // Heading
    const hMatch = line.match(/^(#{1,3})\s+(.+)/);
    if (hMatch) {
      const level = hMatch[1].length;
      const text = hMatch[2].replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      const Tag = `h${level + 3}` as keyof JSX.IntrinsicElements; // h4-h6
      return <Tag key={i} dangerouslySetInnerHTML={{ __html: text }} />;
    }
    // Bold
    const boldLine = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    return (
      <React.Fragment key={i}>
        {i > 0 && <br />}
        <span dangerouslySetInnerHTML={{ __html: boldLine }} />
      </React.Fragment>
    );
  });
}

// 使用处: 将 <p>{article.article_content}</p> 替换为
<div style={{ whiteSpace: 'pre-line' }}>{renderArticleContent(article.article_content)}</div>
```

**方案 B（完整，需要安装依赖）**: 安装 `react-markdown` + `remark-gfm`

但考虑到当前 Markdown 使用场景有限（仅 GDPR excerpts 文件的 `##` 标题），方案 A 足够。

**验证**:
```bash
# 检查 LawViewerPage.tsx 中是否引入了 renderArticleContent 或类似函数
grep -n "renderArticleContent\|marked\|markdown\|## Article\|heading" frontend/src/pages/LawViewerPage.tsx
```

---

### T3.2 EvidenceCenterPage 与 LawViewerPage 渲染对齐

**文件**: `frontend/src/pages/LawViewerPage.tsx` + `frontend/src/styles/app/pages.css`

**目标**: 两个页面的法条渲染行为一致

| 特性 | 对齐后 |
|------|:---:|
| `white-space: pre-line` | ✅ 两处统一 |
| Markdown heading 渲染 | ✅ 提取为共享函数 |
| 前后条文上下文 | LawViewerPage 保留此能力 |
| 高亮当前条文 | LawViewerPage 保留此能力 |

**具体修改**:

1. 将 Markdown 渲染函数提取到 `frontend/src/lib/markdown-article.ts`（共享模块）
2. LawViewerPage 引用共享模块
3. EvidenceCenterPage（如果需要）也在 article 展示处引用

```tsx
// frontend/src/lib/markdown-article.ts
export function renderArticleContent(content: string): React.ReactNode {
  // 同 T3.1 的实现
}
```

**验证**:
```bash
# 检查两个文件是否使用相同的渲染函数
grep -n "renderArticleContent" frontend/src/pages/LawViewerPage.tsx frontend/src/pages/EvidenceCenterPage.tsx
# 或检查共享模块引用
grep -rn "from.*markdown-article" frontend/src/pages/LawViewerPage.tsx frontend/src/pages/EvidenceCenterPage.tsx
```

---

## 七、T4：解析器扩展

### T4.1 _parse_articles_from_text 支持 EU/US

**文件**: `backend/services/knowledge_index.py`

**修改**: 扩展 `_parse_articles_from_text()` 使其能识别三种法系的文章标记

```python
def _parse_articles_from_text(full_text: str) -> dict[str, str]:
    """Parse legal text into {article_no: article_text}.

    Supports three jurisdiction patterns:
      - CN: 第X条, 第X条之一, 第X条之二
      - EU: Article X, Article Xa, Article X-Y
      - US: §1798.XXX, Section X
    """
    # ── Pass 1: Find all article header positions ──
    patterns = [
        # CN: 第X条 or 第X条之Y
        re.compile(
            r'第([一二两三四五六七八九十百千万零〇\d]+)条'
            r'(?:之[一二两三四五六七八九十百千万零〇\d]+)?'
        ),
        # EU: Article X (possibly followed by letter or range)
        re.compile(
            r'^\s*Article\s+(\d+[A-Za-z]?(?:\s*[-–—]\s*\d+[A-Za-z]?)?)\b',
            re.MULTILINE
        ),
        # EU: CHAPTER X / Chapter X (section-level, less granular)
        re.compile(
            r'^\s*CHAPTER\s+([IVXLCDM]+|\d+)\b',
            re.MULTILINE | re.IGNORECASE
        ),
        # US: § 1798.100 or Section 1798.100
        re.compile(
            r'^§\s*(\d+\.\d+(?:\.\d+)?)\b',
            re.MULTILINE
        ),
    ]

    headers: list[tuple[int, int, str]] = []  # (start, end, normalized_article_no)
    for pattern in patterns:
        for m in pattern.finditer(full_text):
            start = m.start()
            # Boundary check: the char before should be a non-alnum boundary
            if start > 0 and full_text[start - 1].isalnum():
                continue
            # Normalize article number
            raw_num = m.group(1)
            if re.match(r'^[一二两三四五六七八九十百千万零〇]+$', raw_num):
                # Chinese numeral → Arabic
                num = str(_chinese_to_int(raw_num))
            else:
                num = raw_num.strip()
            headers.append((start, m.end(), num))

    if not headers:
        return {}

    # ── Pass 2: Split at header boundaries, deduplicate ──
    headers.sort(key=lambda x: x[0])
    result: dict[str, str] = {}
    for i, (hdr_start, hdr_end, num) in enumerate(headers):
        content_start = hdr_end
        content_end = headers[i + 1][0] if i + 1 < len(headers) else len(full_text)
        content = full_text[content_start:content_end].strip()
        # Deduplicate: only keep first occurrence of each article_no
        if num not in result:
            result[num] = content

    return result
```

**注意**: EU US 解析器当前是防御性设计——因为 GDPR/CPRA 已全部在 `regulation_articles.jsonl` 中，此解析器是 fallback 路径。实际的 fallback 触发概率低（仅当新 EU/US source 加入且无 JSONL 条目时才触发）。

**验证**:
```bash
python3 << 'EOF'
import sys; sys.path.insert(0, '.')
from backend.services.knowledge_index import _parse_articles_from_text

# CN test
text_cn = "第一条 内容A\n\n第二条 内容B"
result = _parse_articles_from_text(text_cn)
assert '1' in result, f"CN Art 1 not parsed: {result}"
assert '内容A' in result['1']
print("CN parsing PASS")

# EU test
text_eu = "Article 5 Content of Article 5\n\nArticle 6 Content of Article 6"
result = _parse_articles_from_text(text_eu)
assert '5' in result, f"EU Art 5 not parsed: {result}"
assert 'Content of Article 5' in result['5']
print("EU parsing PASS")

# US test
text_us = "§1798.100 General duties\n\n§1798.105 Right to delete"
result = _parse_articles_from_text(text_us)
assert '1798.100' in result, f"US §1798.100 not parsed: {result}"
print("US parsing PASS")

print("\nAll article parsing tests PASSED")
EOF
```

---

### T4.2 snapshot 预览管道接入清洗引擎

**文件**: `backend/services/knowledge_index.py`

**当前**: `read_text_preview()` → 读文件 → `_build_preview_text()` → `_clean_source_text()` → 返回预览

**问题**: `_clean_source_text()` 已经是新版本（T0.1 重写后的版本），预览内容应自动变干净。

**需要确认**: `_build_preview_text()` 调用了 `_clean_source_text()`，确认新函数被正确调用。

**验证**:
```bash
python3 << 'EOF'
import sys; sys.path.insert(0, '.')
from backend.services.knowledge_index import read_text_preview, _clean_source_text

# 验证预览管线使用新清洗引擎
import inspect
src = inspect.getsource(_clean_source_text)
assert 'clean_source_text' in src or '_stage1_normalize' in src, \
    "ERROR: _clean_source_text is still the old version"
print("Preview pipeline uses new clean engine: PASS")

# 实际预览质量测试
preview = read_text_preview(
    "resources/legal/sources/eu/snapshots/eu-sup-013_celex_32021d0914_en_txt_a7400d96.md",
    limit=600
)
assert "Official Journal" not in preview, f"OJ header still in preview: {preview[:100]}"
assert "L 199" not in preview, f"Page number still in preview"
print(f"Preview quality: OK ({len(preview)} chars, clean)")
EOF
```

---

## 八、T5：E2E 验证与收尾

### T5.1 全量回归——所有源 article_detail API 质量

执行 T0.2 编写的 `verify_knowledge_frontend_quality.py` 脚本。

```bash
cd /Users/oujiazhan/Desktop/实验室/社团/代码/ai4law
python3 status/todo/verify_knowledge_frontend_quality.py --all
```

**验收标准**:
- `clean_source_text` 清洗引擎: 全部单元测试通过
- CELEX 文件集成测试: 16 个文件全部通过
- 前端渲染一致性: CSS+组件检查通过
- 元数据桩治理: 全部 7 个文件不再暴露空内容
- API 质量: 所有抽样源返回 ≥ 最低字符数
- Markdown 渲染: 检测到渲染函数

---

### T5.2 报告归档

将修复方案和验证结果写入 `status/check/`。

```bash
cp status/todo/DataComplyFlow_知识库前端展示质量分析_20260810.md \
   status/check/DataComplyFlow_知识库前端展示修复验收_20260810.md
```

---

## 九、执行计划

```
Phase 1 (2h) ─ T0.1 + T1 全系列
  ├── T0.1: _clean_source_text 全量重写 (90 min)
  ├── T1.1: CSS 加 white-space: pre-line (5 min)
  ├── T1.2: 7 个元数据桩治理 (15 min)
  └── T1.3: 自动完成（已集成到 T0.1）

Phase 2 (2h) ─ T2 全系列（依赖 T0.1）
  ├── T2.1-T2.4: 全部已集成到 T0.1，运行验证即可

Phase 3 (1.5h) ─ T3 + T4（可与 Phase 2 平行）
  ├── T3.1: Markdown 渲染函数 (45 min)
  ├── T3.2: 渲染对齐 (30 min, 依赖 T3.1)
  ├── T4.1: EU/US 解析器扩展 (30 min)
  └── T4.2: snapshot 预览验证 (15 min)

Phase 4 (30min) ─ T5 验证归档
  ├── T5.1: 全量回归脚本运行
  └── T5.2: 报告归档

总计: 6 hours
```

## 十、风险与边界

| 风险 | 缓解 |
|------|------|
| `_stage4_rejoin` 中文合并误伤中英混排 | 正则 `([一-鿿])\n([一-鿿])` 仅合并两侧都是中文的 |
| 英文断字修复误伤正常连字符行 | `[a-z]{3,}` → 仅小写字母，不匹配专有名词、数字 |
| `_stage2_deartifact` 误删正文中的 `L 123/45` 样式文本 | 使用 `^...$` 锚定：只匹配独立成行的页码 |
| EU/US 解析器覆盖不完整 | 已标注为防御性 fallback，核心数据走 JSONL |
| Markdown 渲染 XSS 风险 | 使用 `dangerouslySetInnerHTML` 但输入来自后端本地文件 |
