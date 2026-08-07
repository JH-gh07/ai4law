# DataComplyFlow Schema-first 法律文档编译器架构方案

> 版本：v1.0
> 日期：2026-08-07
> 状态：阶段 A 已实现，阶段 B 适配层已落地（代表模块切换及 C–D 待实施）
> 前置分析：`DataComplyFlow_渲染错误定位_数据流追踪_20260807.md`
> 当前实现提交：`62e631e`、`0511ec8`、`870bd5c`、`d4ea7bf`

---

## 零、问题本质重定义

> 实施边界：本轮只落地阶段 A 的 IR/Compiler Gate、未注册 citation 可观测化和前端待核验展示；旧 Markdown 生成链路保持默认行为，阶段 B–D 不在本轮宣称完成。

### 0.1 当前架构诊断

当前链路：

```
结构化 JSON → LLM 自由生成 Markdown → 正则后处理 → 模板字符串 replace
→ 前端 normalize → ReactMarkdown → Citation 二次解析
```

**语义、结构、引用、展示四类职责混在一条字符串链路里反复修改同一份文本**。这才是 `**` 残留、标题倒挂、引用冲突、章节重复、前后端 normalize 打架等问题同时出现的根因。

### 0.2 核心设计原则

> **LLM 负责"写什么"，程序负责"它是什么、放哪里、引用谁、长什么样"。**

### 0.3 五条铁律

| # | 铁律 | 禁止 |
|---|------|------|
| 1 | **LLM 永远不负责文档语法** | 禁止输出 `#`、`**`、`[N]`、`{{CIT}}`、HTML |
| 2 | **DocumentIR 是唯一文档真值源** | Markdown/HTML/DOCX 都只是 artifact，不可作为数据的规范表示 |
| 3 | **Template 独占文档结构** | 模型不产生章号、标题等级、官方 section 编号 |
| 4 | **Citation ID 是身份，引用编号只是展示** | `citation_id ≠ [N]`，`[N]` 只能由 Renderer 在最后阶段分配 |
| 5 | **任何自动修复都必须可观测** | 不能出错→regex→静默消失，必须 Error→Diagnostic→Repair/Pending/Block |

### 0.4 正确的数据真值层级

```
L0  原始输入              附件 / 表单 / 法规原文
        ↓
L1  Evidence             EvidenceUnit (可验证的证据单元)
        ↓
L2  Semantic             Facts / Issues / Grounding (结构化的语义层)
        ↓
L3  DocumentIR            Sections / Blocks / Claims (文档中间表示)
        ↓
L4  Presentation AST     Pandoc AST / mdast (展示层抽象语法树)
        ↓
L5  Rendered Artifact    MD / HTML / DOCX / PDF (最终产物)
```

**原则：高层可以从低层生成，低层绝不能从高层字符串反推。**

---

## 一、目标架构总览

### 1.1 唯一主线（Compiler-oriented pipeline）

```
┌─────────────────────────────────────────────┐
│               SOURCE LAYER                  │
│ facts / issues / regulations / evidence     │
│        (Pydantic models, typed)             │
└──────────────────┬──────────────────────────┘
                   ↓
┌─────────────────────────────────────────────┐
│            GENERATION CONTEXT               │
│ SectionSpec + Facts Subset + Allowed Cites  │
│  + Expression Strategy + Tone Constraints   │
└──────────────────┬──────────────────────────┘
                   ↓
              LLM Structured Output
         (JSON via Pydantic schema constraint)
                   ↓
┌─────────────────────────────────────────────┐
│              SECTION IR                     │
│ Paragraph / Claim / List / Table / Warning  │
│ citation_refs = ["cit_export_assessment_art4"]│
│ fact_refs = ["FACT-request-company-name"]   │
│ verification_status = computed_by_program   │
└──────────────────┬──────────────────────────┘
                   ↓
           Schema Validator (Pydantic)
                   ↓
           Semantic Validator
                   ↓
          Citation Resolver
                   ↓
┌─────────────────────────────────────────────┐
│              DOCUMENT IR                    │
│ 文档的唯一 Canonical State                  │
│ sections[] / citation_registry / diagnostics│
└──────────────────┬──────────────────────────┘
                   ↓
          Document Compiler
          ├─ Template Assembly Pass
          ├─ Dedup Pass (reuse_policy check)
          ├─ Citation Numbering Pass
          ├─ CrossRef Pass
          ├─ Structure Validation Pass
          └─ Render Validation Pass
                   ↓
        ┌──────────┴──────────┐
        ↓                     ↓
  React Renderer        Export Renderer
  (Web Preview)         (Pandoc Adapter)
        ↓                     ↓
      DOM                  MD / DOCX / PDF
```


---

## 二、核心数据模型设计

### 2.1 Block 类型（Discriminated Union）

LLM 不再输出自由格式 Markdown，而是输出类型化语义块：

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional, Union, Annotated
from enum import Enum


class VerificationStatus(str, Enum):
    """验证状态枚举——由程序计算，不由 LLM 判断"""
    VERIFIED = "verified"                     # 有完整证据支撑
    PARTIALLY_VERIFIED = "partially_verified" # 部分证据支撑
    PENDING_REVIEW = "pending_review"         # 待人工复核
    MISSING_EVIDENCE = "missing_evidence"     # 缺少依据
    CONFLICTING_EVIDENCE = "conflicting"      # 证据冲突
    NOT_APPLICABLE = "not_applicable"         # 不适用


class ReusePolicy(str, Enum):
    """章节内容复用策略"""
    SINGLE_USE = "single_use"     # 不可重复使用（默认）
    SUMMARY = "summary"           # 后续使用仅可摘要引用
    REFERENCE = "reference"       # 后续使用仅可交叉引用
    VERBATIM = "verbatim"         # 允许全文复用（极少使用）


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"
```

### 2.2 Block 具体类型

```python
class ParagraphBlock(BaseModel):
    """普通叙述段落——不含法律断言"""
    type: Literal["paragraph"] = "paragraph"
    block_id: str
    text: str
    fact_refs: list[str] = Field(default_factory=list)
    issue_refs: list[str] = Field(default_factory=list)


class ClaimBlock(BaseModel):
    """带有法律依据的主张/断言——程序标注 verification_status"""
    type: Literal["claim"] = "claim"
    block_id: str
    text: str
    citation_refs: list[str] = Field(default_factory=list)
    fact_refs: list[str] = Field(default_factory=list)
    issue_refs: list[str] = Field(default_factory=list)
    verification: VerificationStatus = VerificationStatus.PENDING_REVIEW
    verification_reason: str = ""


class ListBlock(BaseModel):
    """有序/无序列表"""
    type: Literal["list"] = "list"
    block_id: str
    ordered: bool = False
    items: list[str] = Field(default_factory=list)


class TableBlock(BaseModel):
    """结构化表格——由 Template 提供 headers，LLM 填充 rows"""
    type: Literal["table"] = "table"
    block_id: str
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)


class WarningBlock(BaseModel):
    """警告/待核验/风险提示——不应与 Claim 混淆"""
    type: Literal["warning"] = "warning"
    block_id: str
    text: str
    severity: DiagnosticSeverity = DiagnosticSeverity.WARNING


Block = Annotated[
    Union[ParagraphBlock, ClaimBlock, ListBlock, TableBlock, WarningBlock],
    Field(discriminator="type"),
]
```

### 2.3 SectionIR — 由 Template 提供结构，LLM 填充 blocks

```python
class SectionIR(BaseModel):
    section_id: str
    title: str          # ← 由 Template 提供，LLM 不输出
    level: int          # ← 由 Template 提供
    ordinal: Optional[str] = None  # ← 由 Template 提供（如"第一章"）
    blocks: list[Block] = Field(default_factory=list)

    generated_by: Optional[GenerationMeta] = None


class GenerationMeta(BaseModel):
    stage: str              # "chapter_generation"
    model: str
    prompt_version: str
    prompt_hash: Optional[str] = None
    tokens_used: Optional[int] = None
```

### 2.4 CitationRecord — 引用身份，而非 `[N]`

```python
class CitationLocator(BaseModel):
    article: Optional[str] = None     # "第三十八条"
    paragraph: Optional[str] = None
    item: Optional[str] = None


class CitationRecord(BaseModel):
    """引用记录——citation_id 是身份，[N] 只是 Renderer 分配的展示编号"""
    citation_id: str                      # "cit_pipl_art38"
    source_id: str                        # "reg_pipl"
    source_type: Literal["regulation", "standard", "policy_qa", "case", "guide"]
    title: str                            # "中华人民共和国个人信息保护法"
    locator: Optional[CitationLocator] = None
    knowledge_id: Optional[str] = None
    evidence_unit_id: Optional[str] = None
    status: VerificationStatus = VerificationStatus.PENDING_REVIEW
    confidence_score: float = 0.0
    authority_level: Literal["high", "medium", "low"] = "medium"
    binding_force: Literal["mandatory", "recommended", "reference"] = "reference"
    can_enter_external_report: bool = False
```

### 2.5 DocumentIR — 文档唯一真值源

```python
class ReportMetadata(BaseModel):
    title: str
    company_name: str
    report_date: str
    report_id: str
    risk_level: Optional[str] = None
    recommended_path: Optional[str] = None


class Provenance(BaseModel):
    generated_at: datetime
    facts_version: Optional[str] = None
    issues_version: Optional[str] = None
    evidence_version: Optional[str] = None


class DocumentIR(BaseModel):
    """文档的唯一规范表示——任何格式（MD/HTML/DOCX/PDF）都从此生成"""
    schema_version: str = "3.0"
    compiler_version: str
    prompt_version: str
    template_version: str
    model: str

    document_id: str
    report_type: str
    metadata: ReportMetadata

    sections: list[SectionIR]
    citation_registry: dict[str, CitationRecord] = Field(default_factory=dict)
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    provenance: Provenance

    input_hash: Optional[str] = None
    document_ir_hash: Optional[str] = None


class Diagnostic(BaseModel):
    code: str
    severity: DiagnosticSeverity
    message: str
    location: Optional[DiagnosticLocation] = None
    suggestion: Optional[str] = None


class DiagnosticLocation(BaseModel):
    section_id: Optional[str] = None
    block_id: Optional[str] = None
    field: Optional[str] = None
    citation_id: Optional[str] = None
```

### 2.6 SourceMap — 每段文字可追溯到证据

```python
class SourceMapEntry(BaseModel):
    block_id: str
    section_id: str
    generated_by: GenerationMeta
    fact_refs: list[str] = Field(default_factory=list)
    issue_refs: list[str] = Field(default_factory=list)
    citation_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class DocumentSourceMap(BaseModel):
    document_id: str
    entries: dict[str, SourceMapEntry] = Field(default_factory=dict)
```

### 2.7 关键设计决策：为什么自建 DocumentIR 而非直接使用 Markdown AST

Markdown AST（mdast）只有：
```
paragraph / heading / list / table / emphasis / link
```

但法律文档需要：
```
claim（法律主张）/ citation（法规引用）/ pending_verification（待核验）
/ risk（风险判断）/ legal_basis（合法性基础）/ fact（事实）/ evidence（证据）
```

因此 **业务 IR > Markdown AST**。

---

## 三、结构化生成改造——LLM 从 Markdown 协议迁移到 SectionIR 协议

### 3.1 LLM 输出契约变更

**当前（字符串协议）**：
```python
raw = str(response.get("content"))        # 自由格式 Markdown
raw = strip_markdown_inline(raw)          # 去 **
raw = convert_citation_markers(raw, reg)  # {{CIT}} → [N]
raw = normalize_legal_markdown_structure(raw)  # 中文层级归一化
# → str
```

**改造后（类型协议）**：
```python
response = llm.chat_with_metadata(
    system=STRUCTURED_SYSTEM_PROMPT,
    user=build_prompt(section_spec, context),
    response_format={"type": "json_object"},
)
output = SectionOutput.model_validate_json(response["content"])
section_ir = enrich_section(output, context)
# → SectionIR (Pydantic model)
```


### 3.2 LLM Output Schema Definition

```python
class SectionOutput(BaseModel):
    """LLM 的结构化输出契约——这是模型与程序之间的 API Contract"""
    section_id: str = Field(
        description="此章节的 ID，必须与生成请求中传入的 section_id 一致"
    )
    blocks: list[Block] = Field(
        description="章节内容块序列。严禁在任何 text 字段中包含 Markdown 语法。"
    )
```

### 3.3 系统 Prompt 改造

**改造前**（自由文本）：
```
"你是一名专注于中国数据跨境合规的资深律师…请撰写报告章节内容。"
```

**改造后**（结构化输出约束）：
```python
_STRUCTURED_SYSTEM_PROMPT = """
你是一名专注于中国数据跨境合规的资深律师。
你的任务是根据给定的事实/问题/法规，生成《数据出境风险自评估报告》特定章节的
**语义内容块**，而非最终文档格式。

严格输出 JSON，遵循以下 Schema:

{
  "section_id": "接收到的 section_id",
  "blocks": [
    {
      "type": "paragraph | claim | list | table | warning",
      ...各类型字段见下方说明
    }
  ]
}

## Block 类型说明

### paragraph — 普通叙述段落（无法律断言）
{"type": "paragraph", "block_id": "唯一ID", "text": "..."}

### claim — 带法律依据的主张
{"type": "claim", "block_id": "唯一ID", "text": "...",
 "citation_refs": ["cit_export_assessment_art4"],
 "fact_refs": ["FACT-request-company-name"]}

当 citation_refs 为空且 allowed_citations 列表中确实没有直接支持的法规时，
不要编造引用，使用空数组即可。程序会自动标注 missing_evidence 状态。

### list — 有序/无序列表
{"type": "list", "block_id": "唯一ID", "ordered": true,
 "items": ["保障全球服务连续性...", "满足跨国风控需求..."]}

### table — 表格
{"type": "table", "block_id": "唯一ID",
 "headers": ["项目", "内容"],
 "rows": [["企业名称", "测试公司"], ...]}

### warning — 待核验/风险提示（不含法律断言）
{"type": "warning", "block_id": "唯一ID",
 "text": "当前材料未提供具体清单。", "severity": "warning"}

## 铁律（违反将导致输出被拒绝并重试）
1. 严禁在任何 text 字段中包含 Markdown 语法：#  **  *  `  [N]  {{CIT}}
2. 引用只能通过 citation_refs 字段使用给定的 citation_id
3. 不得自行编号章节——section_id 和编号由系统管理
4. 禁止输出"【依据：未检索到】"——使用 claim 类型 + 空 citation_refs
5. 不得在 text 中硬编码脚注编号 [N]
6. block_id 必须全局唯一，格式为 {section_id}_b{序号}
"""
```

### 3.4 生成函数改造

```python
MAX_RETRIES = 2

def generate_section(self, section_spec: SectionSpec, context: GenerationContext) -> SectionIR:
    """生成结构化章节内容，返回 SectionIR"""
    prompt = self._build_generation_prompt(section_spec, context)

    for attempt in range(MAX_RETRIES + 1):
        response = self.llm.chat_with_metadata(
            system=_STRUCTURED_SYSTEM_PROMPT,
            user=prompt,
            temperature=0.2 if attempt == 0 else 0.1,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        try:
            raw_output = SectionOutput.model_validate_json(
                response.get("content", "{}")
            )
            # 后处理：程序标注 verification_status
            return self._enrich_section(raw_output, context)

        except ValidationError as e:
            if attempt < MAX_RETRIES:
                prompt = self._build_retry_prompt(section_spec, context, str(e))
                continue
            # 全部重试失败 → fallback
            return self._build_fallback_section(section_spec, context, str(e))

    # unreachable, but type-safe
    return self._build_fallback_section(section_spec, context, "max retries exceeded")


def _enrich_section(self, output: SectionOutput, context: GenerationContext) -> SectionIR:
    """程序负责标注 verification_status——不由 LLM 判断"""
    blocks = []
    for block in output.blocks:
        if isinstance(block, ClaimBlock):
            resolved = [cid for cid in block.citation_refs if cid in context.allowed_citations]
            unresolved = [cid for cid in block.citation_refs if cid not in context.allowed_citations]

            if not resolved and not unresolved:
                block.verification = VerificationStatus.MISSING_EVIDENCE
                block.verification_reason = "该主张未提供法规依据"
            elif unresolved:
                block.verification = VerificationStatus.PARTIALLY_VERIFIED
                block.verification_reason = f"部分引用无法解析: {unresolved}"
            else:
                block.verification = VerificationStatus.VERIFIED
            block.citation_refs = resolved
        blocks.append(block)

    return SectionIR(section_id=output.section_id, blocks=blocks)


def _build_fallback_section(self, spec, context, error_detail) -> SectionIR:
    """生成失败时的降级方案——返回 WarningBlock 而非静默输出"""
    return SectionIR(
        section_id=spec.section_id,
        blocks=[WarningBlock(
            block_id=f"{spec.section_id}_fallback",
            text=f"本章节生成失败（{error_detail}）。请人工补充。",
            severity=DiagnosticSeverity.ERROR,
        )],
    )
```

---

## 四、Template 架构改造——结构由 Template 独占

### 4.1 Template Schema（YAML 驱动）

当前：`official_risk_self_assessment_template.md`（纯 Markdown + `{{placeholder}}`）
改造后：YAML Schema 定义章节结构、映射关系、复用策略

```yaml
# templates/cn_security_assessment.yaml
report_type: security_assessment
template_version: "3.0"

sections:
  - section_id: work_summary
    number: "一"
    title: "自评估工作情况"
    level: 2
    required: true
    intent: "描述本次自评估的组织过程、时间范围、评估方法和参与人员"
    reuse_policy: single_use
    empty_behavior: none_to_report

  - section_id: activity_overview
    number: "二"
    title: "出境活动整体情况"
    level: 2
    required: true
    subsections:
      - section_id: processor_profile
        number: "（一）"
        title: "数据处理者基本情况"
        level: 3
        required: true
        intent: "描述数据处理者主体身份、行业归属、经营情况和监管属性"
        reuse_policy: single_use
        prefab_table:
          headers: ["项目", "内容"]
          rows:
            - ["企业名称", "{{company_name}}"]
            - ["所属行业", "{{industry}}"]
            - ["是否关键信息基础设施运营者", "{{is_ciio}}"]
            - ["数据处理角色", "数据出境方（境内数据处理者）"]

      - section_id: data_scope
        number: "（二）"
        title: "拟出境数据情况"
        level: 3
        required: true
        reuse_policy: single_use

      - section_id: security_measures
        number: "（三）"
        title: "数据处理者数据安全保障能力情况"
        level: 3
        reuse_policy: single_use

      - section_id: receiver_profile
        number: "（四）"
        title: "境外接收方情况"
        level: 3
        reuse_policy: single_use

      - section_id: legal_documents
        number: "（五）"
        title: "法律文件约定数据安全保护责任义务的情况"
        level: 3
        reuse_policy: single_use

      - section_id: other_conditions
        number: "（六）"
        title: "其他情况"
        level: 3
        required: false
        reuse_policy: reference
        empty_behavior: none_to_report

  - section_id: risk_assessment
    number: "三"
    title: "出境活动风险自评估情况及结论"
    level: 2
    required: true
    reuse_policy: single_use
```

### 4.2 关键原则：Template 独占结构，LLM 独占正文

| 职责 | Owner | 说明 |
|------|-------|------|
| 章节编号（一、二、三） | Template | LLM 不输出章节号 |
| 标题等级（H2/H3） | Template | LLM 返回的 SectionIR 中 level 由 Template 注入 |
| 章节标题文字 | Template | LLM 不生成标题 |
| 预制表格结构 | Template | headers 固定，LLM 只填 rows 或留空 |
| 段落正文 | LLM | SectionIR.blocks |
| 引用语义 | LLM + 程序 | LLM 输出 citation_refs，程序计算 verification_status |


---

## 五、Citation 单一真值源改造

### 5.1 核心原则

```
citation_id  →  引用身份（唯一、稳定、可追溯到知识库）
     ↓
CitationRegistry  →  系统内唯一真值源
     ↓
CitationNumberingPass  →  按首次出现顺序分配 [N]
     ↓
Renderer  →  仅负责展示 [N]
```

**`[1]` 不是 citation identity，`citation_id` 才是。**

### 5.2 CitationRegistry 设计

```python
class CitationRegistry:
    """全局引用注册表——系统内 citation 的唯一真值源"""

    def __init__(self):
        self._records: dict[str, CitationRecord] = {}
        self._footnote_map: dict[str, int] = {}
        self._next_number: int = 1

    def register(self, record: CitationRecord) -> str:
        """注册引用来源，返回 citation_id"""
        self._records[record.citation_id] = record
        return record.citation_id

    def resolve(self, citation_id: str) -> Optional[CitationRecord]:
        """O(1) 查找引用详情"""
        return self._records.get(citation_id)

    def assign_footnote_number(self, citation_id: str) -> Optional[int]:
        """分配脚注编号——仅在 Compiler CitationNumberingPass 中调用"""
        if citation_id not in self._footnote_map:
            if citation_id not in self._records:
                return None  # 未注册的引用
            self._footnote_map[citation_id] = self._next_number
            self._next_number += 1
        return self._footnote_map[citation_id]

    def get_footnote_map(self) -> dict[int, CitationRecord]:
        """{脚注编号 → CitationRecord}——供前端 citationMap 使用"""
        return {
            num: self._records[cid]
            for cid, num in self._footnote_map.items()
        }

    def build_citation_index_section(self) -> str:
        """生成报告末尾的"引用依据索引"章节"""
        if not self._footnote_map:
            return "（本报告未引用法规依据索引）"
        entries = []
        for cid, num in sorted(self._footnote_map.items(), key=lambda x: x[1]):
            record = self._records[cid]
            loc = f" {record.locator.article}" if record.locator and record.locator.article else ""
            entries.append(
                f"[{num}] **{record.title}**{loc} "
                f"（{record.source_type}，权威等级：{record.authority_level}）"
            )
        return "\n\n".join(entries)
```

### 5.3 CitationValidationPass

```python
class CitationValidationPass:
    """验证所有引用是否在 Registry 中存在"""

    def run(self, state: CompilerState) -> PassResult:
        diagnostics = []
        all_used_ids = set()

        for section in state.sections:
            for block in section.blocks:
                if hasattr(block, "citation_refs"):
                    for cid in block.citation_refs:
                        all_used_ids.add(cid)
                        if cid not in state.citation_registry._records:
                            diagnostics.append(Diagnostic(
                                code="CITATION_NOT_REGISTERED",
                                severity=DiagnosticSeverity.ERROR,
                                message=f"引用 ID 未注册: {cid}",
                                location=DiagnosticLocation(
                                    section_id=section.section_id,
                                    block_id=getattr(block, "block_id", None),
                                    citation_id=cid,
                                ),
                                suggestion="检查该 citation_id 是否在 allowed_citations 列表中",
                            ))

        return PassResult(
            status="error" if any(d.severity == "error" for d in diagnostics) else "success",
            diagnostics=diagnostics,
        )
```

### 5.4 彻底消除 `【依据：未检索到】`

**当前**：LLM 输出 `【依据：未检索到】` → `CitationMarkdownRenderer.renderInlineCitationText` 正则 `/【依据：[^】]+】/` 匹配 → 渲染为蓝色可交互标记但无数据。

**改造后**：
- LLM 不再输出 `【依据：未检索到】`（结构化 prompt 明确禁止）
- 前端 `ClaimBlockView` 根据 `verification` 字段渲染不同样式：

```typescript
const VERIFICATION_STYLES: Record<VerificationStatus, { icon: string; className: string }> = {
  verified:          { icon: "✅", className: "claim-verified" },
  partially_verified:{ icon: "⚠️", className: "claim-partial" },
  pending_review:    { icon: "⏳", className: "claim-pending" },
  missing_evidence:  { icon: "🔴", className: "claim-missing" },
  conflicting:       { icon: "⚡", className: "claim-conflict" },
  not_applicable:    { icon: "—",  className: "claim-na" },
};
```

---

## 六、Document Compiler（文档编译器）

### 6.1 Compiler 核心设计

```python
@dataclass
class CompilerState:
    sections: list[SectionIR]
    citation_registry: CitationRegistry
    source_map: DocumentSourceMap
    diagnostics: list[Diagnostic]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PassResult:
    status: Literal["success", "warning", "error", "fatal"]
    output: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


class CompilerPass(ABC):
    """每个 Pass 只做一件事"""
    @abstractmethod
    def run(self, state: CompilerState) -> PassResult: ...


class DocumentCompiler:
    """将 SectionIR[] 编译为 DocumentIR"""

    def __init__(self, template: ReportTemplate):
        self.template = template
        self.passes: list[CompilerPass] = []

    def compile(self, sections: list[SectionIR], registry: CitationRegistry,
                source_map: DocumentSourceMap) -> CompileResult:
        state = CompilerState(
            sections=sections, citation_registry=registry,
            source_map=source_map, diagnostics=[],
        )
        for p in self.passes:
            result = p.run(state)
            state.diagnostics.extend(result.diagnostics)
            if result.status == "fatal":
                return CompileResult(status="fatal", diagnostics=state.diagnostics)

        document = self._assemble_document(state)
        document.diagnostics = state.diagnostics
        return CompileResult(status=self._worst_severity(state.diagnostics),
                            document=document, diagnostics=state.diagnostics)
```

### 6.2 完整 Pass 序列（9 Passes）

```python
def build_assessment_compiler(template: ReportTemplate) -> DocumentCompiler:
    compiler = DocumentCompiler(template)
    compiler.passes = [
        InputValidationPass(),       # P0: 输入格式校验
        SchemaValidationPass(),      # P1: Pydantic 校验
        SemanticValidationPass(),    # P2: 语义一致性
        CitationValidationPass(),    # P3: 引用存在性
        TemplateAssemblyPass(),      # P4: 模板组装
        DedupValidationPass(),       # P5: 去重检查
        CitationNumberingPass(),     # P6: 引用编号
        StructureValidationPass(),   # P7: 文档结构
        RenderValidationPass(),      # P8: 渲染前最终防线
    ]
    return compiler
```

### 6.3 各 Gate 检查项总表

| Pass | 检查项 | 违反 Severity |
|------|--------|--------------|
| **P0 Input** | SectionIR 无 Markdown 语法残留 | ERROR |
| | 无 `{{CIT-xxx}}` 残留 | ERROR |
| | 无裸 `[N]` 硬编码脚注 | ERROR |
| **P1 Schema** | 所有 Block 通过 Pydantic 校验 | FATAL |
| | block_id 全局唯一 | ERROR |
| **P2 Semantic** | Claim 的 fact_refs 指向存在的 Fact | ERROR |
| | 不存在自相矛盾的 Claim（如同一段既说"合规"又说"不合规"） | WARNING |
| **P3 Citation** | citation_id 全部在 Registry 中存在 | ERROR |
| | verified 状态但无 evidence_unit | WARNING |
| **P4 Template** | 所有 required section 已填充 | FATAL |
| | section 层级关系符合 Template | ERROR |
| **P5 Dedup** | SINGLE_USE block 不重复 | ERROR |
| **P6 Numbering** | citation_id → 脚注编号唯一映射 | ERROR |
| | 脚注编号连续 | ERROR |
| **P7 Structure** | heading 层级不跳跃（H2→H4） | ERROR |
| | 无孤立空白 section | WARNING |
| **P8 Render** | 无 `{{` 残留 | FATAL |
| | 无孤立 `**` | ERROR |
| | 脚注编号连续且唯一 | ERROR |


---

## 七、前端 Renderer 改造——从 Markdown Renderer 到 Document Renderer

### 7.1 架构对比

**当前**：
```
API → Markdown 字符串
  → normalizeMarkdownForRender()
  → CitationMarkdownRenderer (ReactMarkdown + remarkGfm)
    → renderInlineCitationText() (正则扫描 [N] / 【依据】)
    → findCitationFromMap() (模糊匹配)
    → CitationPopover / CitationArticleDrawer
```

**改造后**：
```
API → DocumentIR JSON
  → DocumentRenderer
    → SectionRenderer
      → BlockRenderer (type dispatch)
        → ClaimBlockView (直接读取 citation_refs + citationRegistry)
        → CitationMarker (data-citation-id)
        → CitationPopover / CitationArticleDrawer (使用 citation_id)
```

### 7.2 TypeScript 类型定义

```typescript
// frontend/src/lib/document/types.ts

export type VerificationStatus =
  | "verified"
  | "partially_verified"
  | "pending_review"
  | "missing_evidence"
  | "conflicting"
  | "not_applicable";

export interface ParagraphBlock {
  type: "paragraph";
  block_id: string;
  text: string;
  fact_refs: string[];
  issue_refs: string[];
}

export interface ClaimBlock {
  type: "claim";
  block_id: string;
  text: string;
  citation_refs: string[];
  fact_refs: string[];
  issue_refs: string[];
  verification: VerificationStatus;
  verification_reason: string;
}

export interface ListBlock {
  type: "list";
  block_id: string;
  ordered: boolean;
  items: string[];
}

export interface TableBlock {
  type: "table";
  block_id: string;
  headers: string[];
  rows: string[][];
}

export interface WarningBlock {
  type: "warning";
  block_id: string;
  text: string;
  severity: "info" | "warning" | "error" | "fatal";
}

export type Block = ParagraphBlock | ClaimBlock | ListBlock | TableBlock | WarningBlock;

export interface SectionIR {
  section_id: string;
  title: string;
  level: number;
  ordinal?: string;
  blocks: Block[];
}

export interface DocumentIR {
  schema_version: string;
  document_id: string;
  report_type: string;
  metadata: ReportMetadata;
  sections: SectionIR[];
  citation_registry: Record<string, CitationRecord>;
  diagnostics: Diagnostic[];
  document_ir_hash?: string;
}
```

### 7.3 DocumentRenderer 组件

```typescript
// frontend/src/components/document/DocumentRenderer.tsx

interface DocumentViewProps {
  document: DocumentIR;
  footnoteMap: Record<string, number>;  // citation_id → [N]
  sourceMap?: DocumentSourceMap;
  onBlockClick?: (blockId: string) => void;
  onCitationClick?: (citationId: string) => void;
}

export const DocumentRenderer: React.FC<DocumentViewProps> = ({
  document, footnoteMap, sourceMap, onBlockClick, onCitationClick,
}) => (
  <article className="legal-document">
    <DocumentHeader metadata={document.metadata} />
    {document.sections.map(section => (
      <SectionRenderer
        key={section.section_id}
        section={section}
        document={document}
        footnoteMap={footnoteMap}
        sourceMap={sourceMap}
        onBlockClick={onBlockClick}
        onCitationClick={onCitationClick}
      />
    ))}
    <CitationIndexSection
      registry={document.citation_registry}
      footnoteMap={footnoteMap}
    />
    {document.diagnostics.length > 0 && (
      <DiagnosticsPanel diagnostics={document.diagnostics} />
    )}
  </article>
);
```

### 7.4 BlockRenderer — 类型分发

```typescript
const BlockRenderer: React.FC<BlockRendererProps> = ({ block, ...props }) => {
  switch (block.type) {
    case "paragraph":
      return <ParagraphBlockView block={block} {...props} />;
    case "claim":
      return <ClaimBlockView block={block} {...props} />;
    case "list":
      return <ListBlockView block={block} {...props} />;
    case "table":
      return <TableBlockView block={block} {...props} />;
    case "warning":
      return <WarningBlockView block={block} {...props} />;
    default:
      return null;
  }
};
```

### 7.5 ClaimBlockView — 替代 renderInlineCitationText

```typescript
const VERIFICATION_CONFIG: Record<VerificationStatus, VerificationStyle> = {
  verified:          { label: "已核验", icon: "✅", className: "claim-verified" },
  partially_verified:{ label: "部分核验", icon: "⚠️", className: "claim-partial" },
  pending_review:    { label: "待核验", icon: "⏳", className: "claim-pending" },
  missing_evidence:  { label: "缺少依据", icon: "🔴", className: "claim-missing" },
  conflicting:       { label: "证据冲突", icon: "⚡", className: "claim-conflict" },
  not_applicable:    { label: "不适用", icon: "—",  className: "claim-na" },
};

const ClaimBlockView: React.FC<Props> = ({
  block, citationRegistry, footnoteMap,
  sourceMapEntry, onCitationClick,
}) => {
  const config = VERIFICATION_CONFIG[block.verification];

  return (
    <p
      className={`legal-claim ${config.className}`}
      data-block-id={block.block_id}
      data-verification={block.verification}
    >
      {/* 验证状态标记——替代"【待核验：缺少法规依据】"纯文本 */}
      <span className="verification-badge" title={block.verification_reason}>
        {config.icon} {config.label}
      </span>

      <span className="claim-text">{block.text}</span>

      {/* 引用角标——使用 citation_id 而非硬编码 [N] */}
      {block.citation_refs.map(citationId => {
        const fn = footnoteMap[citationId];
        const citation = citationRegistry[citationId];
        if (!citation || !fn) return null;
        return (
          <CitationMarker
            key={citationId}
            citationId={citationId}
            footnoteNumber={fn}
            citation={citation}
            onClick={() => onCitationClick?.(citationId)}
          />
        );
      })}

      {/* 溯源面板（开发/调试模式） */}
      {sourceMapEntry && <BlockProvenanceTooltip entry={sourceMapEntry} />}
    </p>
  );
};
```

### 7.6 CitationMarker — DOM Hook 化

```html
<!-- 改造前：从 [N] 反查 citationMap["1"] -->
<span class="citation-marker-inline" data-footnote="1">[1]</span>

<!-- 改造后：稳定的 data-citation-id -->
<span
  class="citation-marker-inline"
  data-citation-id="cit_export_assessment_art4"
  data-source-id="reg_export_assessment"
  data-footnote="1"
>
  [1]
</span>
```

点击后：
```
citation_id = "cit_export_assessment_art4"
  ↓ CitationRegistry.resolve()
  ↓ knowledge_id → 知识库原文
  ↓ evidence_unit_id → 附件证据
```

不再需要通过 `citationMap["1"]` 模糊查找。

### 7.7 逐步废弃清单

| 废弃函数 | 说明 |
|---------|------|
| `normalizeMarkdownForRender()` | 前端不再接收 Markdown 字符串 |
| `normalizeFallbackMarkdownForRender()` | 同上 |
| `renderInlineCitationText()` | 由 `ClaimBlockView` 替代——不再正则扫描字符串 |
| `extractBasisItems()` | 由 `block.citation_refs` 替代——直接从结构化字段读取 |
| `findCitationFromMap()` (模糊匹配) | 由 `citationRegistry[citationId]` O(1) 查找替代 |
| `isBasisOnlyParagraph()` | 由 `block.type === "claim"` 替代 |
| `isHighlightParagraph()` | 由 `WarningBlock` 类型 + CSS class 替代 |
| `resolveAll()` (批量远程解析) | 由 Compiler `CitationValidationPass` 在生成阶段完成 |


---

## 八、多格式导出层（Pandoc Adapter）

### 8.1 设计

```
DocumentIR
    │
    ▼
PandocASTAdapter.convert()
    │
    ▼
Pandoc AST (native Python objects)
    │
    ├──→ pandoc.write(markdown) → .md
    ├──→ pandoc.write(html)     → .html
    ├──→ pandoc.write(docx)     → .docx
    └──→ pandoc.write(pdf)      → .pdf
```

利用 Pandoc 成熟的 reader→AST→filter→writer 体系，而非自建所有格式渲染器。

### 8.2 核心适配逻辑

```python
class PandocASTAdapter:
    def convert(self, document: DocumentIR) -> pandoc.types.Pandoc:
        blocks = []
        for section in document.sections:
            blocks.append(Header(section.level, ("", [], []), [Str(section.title)]))
            for block in section.blocks:
                pandoc_blocks = self._convert_block(block, document)
                blocks.extend(pandoc_blocks)
        return Pandoc(Meta({}), blocks)

    def _convert_block(self, block: Block, doc: DocumentIR) -> list:
        if isinstance(block, ParagraphBlock):
            return [Para([Str(block.text)])]

        if isinstance(block, ClaimBlock):
            inlines = [Str(block.text)]
            for cid in block.citation_refs:
                fn = doc._footnote_map.get(cid)
                if fn:
                    inlines.append(Space())
                    inlines.append(Str(f"[{fn}]"))
            return [Para(inlines)]

        if isinstance(block, ListBlock):
            items = [[Plain([Str(item)])] for item in block.items]
            return [OrderedList((1, 1, 1), items) if block.ordered else BulletList(items)]

        if isinstance(block, TableBlock):
            # 转换为 Pandoc Table
            ...

        if isinstance(block, WarningBlock):
            return [Para([Str(f"⚠️ {block.text}")])]

        return []
```

---

## 九、Source Map 溯源体系

### 9.1 溯源链路

```
最终文字
   ↑
Block (block_id)
   ↑
LLM Generation (prompt_version, model, tokens)
   ↑
Fact / Issue / Evidence (fact_refs, issue_refs, evidence_refs)
   ↑
原始附件 / 法规知识库 (knowledge_id, source_url)
```

### 9.2 DOM Hook

```html
<p
  data-block-id="block_processor_b003"
  data-section-id="processor_profile"
  data-verification="missing_evidence"
  data-has-citations="cit_export_assessment_art4,cit_pipl_art38"
  data-fact-refs="FACT-request-ciio,FACT-request-important-data"
>
  应当通过国家网信部门组织的数据出境安全评估。[1][2]
</p>
```

用户点击任一段落：
```
block_processor_b003
  ↓ SourceMap 查询
  ├── 生成信息: model=gpt-4o, prompt_version=chapter-v8
  ├── 关联事实: FACT-request-ciio, FACT-request-important-data
  ├── 关联问题: ISSUE-ciio-security-assessment
  ├── 引用法规: cit_export_assessment_art4 → 数据出境安全评估办法 第四条
  └── 证据单元: EU-1923 → attachment/review_case_scc_contract.docx
```

---

## 十、运行过程 Checkpoint 化

### 10.1 目录结构

```
run/{run_id}/
├── 00_inputs.json              # 原始输入
├── 01_facts.json               # 事实提取
├── 02_diagnosis.json           # 路径诊断
├── 03_issues.json              # 问题清单
├── 04_legal_grounding.json     # 法规检索
├── 05_evidence.json            # 证据链
├── 06_compliance_reasoning.json
├── 07_writing_strategy.json
├── 08_generation_context.json  # 传入 LLM 的完整上下文
├── 09_sections_raw.json        # LLM 结构化输出
├── 10_sections_validated.json  # Schema 校验后
├── 11_document_ir.json         # 组装后的 DocumentIR
├── 12_citation_registry.json   # Registry 快照
├── 13_compiled_document.json   # Compiler 输出（含 diagnostics）
├── 14_source_map.json          # DocumentSourceMap
├── 15_rendered.md
├── 16_rendered.docx
├── 17_rendered.pdf
├── diagnostics.json            # 全链路诊断汇总
├── trace.jsonl                 # 时间线
└── manifest.json               # 版本/哈希/状态
```

### 10.2 Manifest

```json
{
  "run_id": "c42ba73e-...",
  "status": "success_with_warnings",
  "schema_version": "3.0",
  "compiler_version": "1.0.0",
  "prompt_version": "chapter-v8",
  "template_version": "cn-sa-v3",
  "model": "gpt-4o-2024-08-06",
  "citation_registry_version": "2026Q3",
  "renderer_version": "2.0.1",
  "input_hash": "a1b2c3d4...",
  "document_ir_hash": "e5f6g7h8...",
  "artifact_md5": "i9j0k1l2...",
  "diagnostics_summary": {
    "total": 5, "fatal": 0, "error": 0, "warning": 3, "info": 2
  },
  "duration_ms": 28450,
  "total_tokens": 45678
}
```

**每个阶段可重放、可 Diff、可定位。**

---

## 十一、测试体系设计

### 11.1 五层测试金字塔

```
        ┌──────────────────┐
        │  E2E Legal (5)   │  完整场景：用户输入→最终文档
        ├──────────────────┤
        │  Property (20+)  │  不变性/幂等性/确定性/跨格式一致性
        ├──────────────────┤
        │  Golden Snapshot │  固定 DocumentIR → 固定渲染输出
        ├──────────────────┤
        │  Compiler Gates  │  每个 Pass 的 Invariant 检查
        ├──────────────────┤
        │  Schema (100%)   │  Pydantic validation
        └──────────────────┘
```

### 11.2 核心测试用例

```python
# Schema Test
def test_llm_output_rejects_markdown_syntax():
    """包含 ** 的 text 必须被拒绝"""
    with pytest.raises(ValidationError):
        SectionOutput.model_validate({
            "section_id": "test",
            "blocks": [{"type": "claim", "block_id": "b1",
                        "text": "**应当申报安全评估。**"}]
        })

# Compiler Invariant Test
def test_single_use_block_not_duplicated():
    """SINGLE_USE block 在不同 section 中出现两次 → ERROR"""

def test_heading_level_no_skip():
    """H2 → H4 跳跃 → ERROR"""

def test_citation_not_registered_error():
    """引用未注册的 citation_id → ERROR"""

def test_footnote_numbering_continuous():
    """[1,2,3] 非 [1,3,5]"""

def test_no_residual_cit_markers():
    """渲染产物不得含 {{CIT-xxx}}"""

# Property Test
def test_citation_id_invariant_under_reorder():
    """章节重排序后 citation_id 不变，但 [N] 可以变"""

def test_cross_format_citation_consistency():
    """MD/HTML 产物中引用语义一致"""

# E2E Test
def test_e2e_ciio_claim_evidence_coverage():
    """每个 legal_rule claim 必须有 citation 覆盖"""
```

---

## 十二、质量指标体系

| 指标 | 定义 | 目标 |
|------|------|------|
| Schema Valid Rate | LLM 首次通过 Pydantic 校验的比例 | ≥ 95% |
| Citation Resolution Rate | citation_refs 成功解析比例 | ≥ 99% |
| Evidence Coverage | 有依据的 claim / 总 claim | ≥ 90% |
| Unsupported Claim Rate | 无依据法律主张比例 | ≤ 5% |
| Pending Verification Rate | 待核验比例 | ≤ 15% |
| Duplicate Block Rate | 重复内容比例 | 0% |
| Structural Violation Rate | 文档结构错误 | 0% |
| LLM Repair Rate | 需要重试修复的比例 | ≤ 5% |
| Render Determinism | 同 IR 多次渲染 hash 一致率 | 100% |
| Trace Completeness | 可追溯到 Fact/Evidence 的比例 | ≥ 95% |


---

## 十三、分四阶段实施路线图

### 阶段 A：止血（1-2 周）

**目标**：不改生成流程，新增 Compiler Gates 作为安全网。

| # | 任务 | 产出 |
|---|------|------|
| A1 | 实现 `RenderValidationPass` | 检测 `{{CIT-}}`、`**`、裸 `[N]` 残留 |
| A2 | 实现 `StructureValidationPass` | 检测标题层级倒挂（MD001） |
| A3 | 实现 `DedupValidationPass` | 检测章节内容重复 |
| A4 | 实现 `CitationValidationPass` | 检测未注册引用 |
| A5 | 前端过滤 `【依据：未检索到】` | 不再渲染为 CitationPopover |
| A6 | 前端 `【待核验】` 黄色警告样式 | CSS 区分 |
| A7 | `convert_citation_markers` 未注册 ID 改为 `【未注册引用：xxx】` | 不再静默丢弃 |

**不做的**：不改 LLM prompt、不改模板拼装、不改前端整体架构。

### 阶段 B：Citation 重构（2-3 周）

**目标**：Citation 语义与编号分离，消除双轨脚注。

| # | 任务 | 产出 |
|---|------|------|
| B1 | `CitationRecord` / `CitationRegistry` Pydantic 模型 | `backend/common/citation/models.py` |
| B2 | `CitationRegistry` 实现 | `registry.py` |
| B3 | `CitationValidationPass` | Compiler Pass |
| B4 | `CitationNumberingPass` | 按首次出现分配 |
| B5 | 修改 `convert_citation_markers` 适配新 Registry | 过渡期兼容 |
| B6 | 前端 `CitationMarker` 改用 `data-citation-id` | DOM Hook |
| B7 | 测试：citation_id 不变性、编号唯一性 | 自动化 |

### 阶段 C：结构化生成（3-4 周）

**目标**：LLM 从 Markdown 协议迁移到 SectionIR 类型协议。

| # | 任务 | 产出 |
|---|------|------|
| C1 | `SectionOutput` / `Block` / `SectionIR` 模型 | `backend/common/reporting/schema/` |
| C2 | `_generate_chapter` → `_generate_section` | 结构化输出 |
| C3 | LLM prompt 改造：JSON Schema 约束 | 新 prompt |
| C4 | `_enrich_section`（程序计算 verification_status） | 状态由程序标注 |
| C5 | 有限重试机制 | 容错 |
| C6 | `TemplateAssemblyPass` | Compiler Pass |
| C7 | 渐进废弃 chapter 链路中的 `strip_markdown_inline` / `normalize_legal_markdown_structure` | 清理 |
| C8 | 测试：Schema Valid Rate、Golden Snapshot | 回归 |

### 阶段 D：前端 IR Renderer + Pandoc 导出（2-3 周）

**目标**：前端从 Markdown Renderer 迁移到 Document Renderer。

| # | 任务 | 产出 |
|---|------|------|
| D1 | TypeScript `DocumentIR` 类型定义 | `frontend/src/lib/document/types.ts` |
| D2 | `DocumentRenderer` / `SectionRenderer` | React 组件 |
| D3 | `ClaimBlockView` / `VerificationBadge` | 引用+状态渲染 |
| D4 | `BlockProvenanceTooltip` | 溯源交互 |
| D5 | 前端 `DocumentSourceMap` 查询 | `sourceMap.ts` |
| D6 | `PandocASTAdapter` | Pandoc 导出 |
| D7 | MD/DOCX/PDF 通过 Pandoc 生成 | 多格式导出 |
| D8 | 渐进废弃前端 `normalizeMarkdownForRender` 等 | 清理 |
| D9 | 保持 `CitationMarkdownRenderer` 作为兼容层 | 向后兼容 |

---

## 十四、10 个现存问题的解决映射

| # | 问题 | 解决阶段 | 根除机制 |
|---|------|---------|---------|
| 1 | LLM 输出格式不受控 | C | LLM 输出 JSON 而非 Markdown；Schema Gate 拒绝非法输出 |
| 2 | 孤立 `**` 残留 | C+A | A: RenderValidationPass 检测；C: LLM 不再生成 `**` |
| 3 | `{{CIT}}` 双轨脚注 | B | citation_id 与 `[N]` 分离；CitationNumberingPass 唯一分配 |
| 4 | `【依据：未检索到】` 无效引用 | A+C | A: 前端过滤；C: verification=missing_evidence 替代 |
| 5 | 层级倒挂 | A+D | A: StructureValidationPass 检测；D: Template 独占 heading |
| 6 | 章节内容重复 | C | TemplateAssemblyPass + DedupValidationPass + reuse_policy |
| 7 | 模板拼装不归一化 | C | DocumentIR 编译替代字符串拼装 |
| 8 | 前后端归一化冲突 | D | 前端不再 normalize——接收结构化 IR |
| 9 | `【待核验】` 无视觉区分 | A+D | A: 前端样式；D: VerificationBadge 组件 |
| 10 | `{{CIT}}` 字面残留 | A+B | A: 改为 `【未注册引用：xxx】`；B: CitationValidationPass 阻止产生 |

---

## 十五、目录结构最终形态

```
backend/
├── common/
│   ├── citation/
│   │   ├── models.py              # CitationRecord, CitationRegistry
│   │   └── registry.py            # Registry 实现
│   │
│   ├── reporting/
│   │   ├── schema/
│   │   │   ├── document.py        # DocumentIR, ReportMetadata
│   │   │   ├── section.py         # SectionIR, SectionSpec
│   │   │   ├── block.py           # Block (discriminated union)
│   │   │   ├── citation.py        # CitationRecord, CitationLocator
│   │   │   └── diagnostic.py      # Diagnostic, DiagnosticSeverity
│   │   │
│   │   ├── generation/
│   │   │   ├── context.py         # GenerationContext
│   │   │   ├── generator.py       # 结构化生成器
│   │   │   └── repair.py          # 局部修复
│   │   │
│   │   ├── compiler/
│   │   │   ├── compiler.py        # DocumentCompiler
│   │   │   ├── state.py           # CompilerState, PassResult
│   │   │   └── passes/
│   │   │       ├── validate_input.py
│   │   │       ├── validate_schema.py
│   │   │       ├── validate_semantics.py
│   │   │       ├── validate_citation.py
│   │   │       ├── assemble_template.py
│   │   │       ├── validate_dedup.py
│   │   │       ├── assign_numbers.py
│   │   │       ├── validate_structure.py
│   │   │       └── validate_render.py
│   │   │
│   │   ├── templates/
│   │   │   └── cn_security_assessment.yaml
│   │   │
│   │   ├── renderers/
│   │   │   ├── markdown.py
│   │   │   ├── html.py
│   │   │   ├── pandoc_adapter.py
│   │   │   └── json_renderer.py
│   │   │
│   │   └── tracing/
│   │       ├── source_map.py
│   │       └── run_trace.py
│   │
│   └── llm/
│       └── postprocess.py         # 保留但逐步缩减职责

frontend/src/
├── lib/document/
│   ├── types.ts                   # TypeScript 类型
│   ├── sourceMap.ts               # 前端 SourceMap 查询
│   └── compiler.ts                # 前端轻量 Compiler
│
└── components/document/
    ├── DocumentRenderer.tsx
    ├── SectionRenderer.tsx
    ├── BlockRenderer.tsx
    ├── blocks/
    │   ├── ParagraphBlock.tsx
    │   ├── ClaimBlockView.tsx
    │   ├── ListBlockView.tsx
    │   ├── TableBlockView.tsx
    │   └── WarningBlockView.tsx
    ├── citation/
    │   ├── CitationMarker.tsx
    │   ├── CitationPopover.tsx
    │   └── CitationArticleDrawer.tsx
    ├── diagnostics/
    │   ├── VerificationBadge.tsx
    │   └── DiagnosticsPanel.tsx
    └── provenance/
        └── BlockProvenanceTooltip.tsx
```

---

## 十六、兼容策略

### 16.1 Feature Flag 控制双轨切换

```python
USE_STRUCTURED_GENERATION = os.getenv("USE_STRUCTURED_GENERATION", "false") == "true"
```

### 16.2 渐进废弃清单

| 阶段 | 废弃项 | 替代 |
|------|--------|------|
| B 完成 | `convert_citation_markers` 正则 replace | CitationRegistry.footnote_assignments |
| C 完成 | `strip_markdown_inline` | 结构不需要 inline 格式 |
| C 完成 | `normalize_legal_markdown_structure` (chapter 链路) | Compiler Passes |
| D 完成 | 前端 `normalizeMarkdownForRender` | DocumentRenderer 渲染 IR |
| D 完成 | 前端 `renderInlineCitationText` | ClaimBlockView 结构化渲染 |
| D 完成 | 前端 `findCitationFromMap` (模糊匹配) | citationRegistry O(1) 查找 |

---

## 附录 A：关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| IR 格式 | 自建 Pydantic DocumentIR | mdast 只有 paragraph/heading/list，缺少 claim/verification/citation_refs 等法律语义 |
| 结构化生成 | JSON Schema（非 function calling） | 跨模型兼容，provider-independent |
| 导出层 | Pandoc AST Adapter | 利用 Pandoc 成熟的 reader→AST→writer 体系，减少维护负担 |
| 引用引擎 | 自建 CitationRegistry（非 CSL/citeproc-js） | 中国法规特殊语义（条/款/项），不适用标准 CSL |
| 前端渲染 | React 组件树（非 react-markdown） | 从 Block 类型直接渲染，不需要 Markdown 中间层 |
| 错误处理 | 显式 Diagnostic + 不静默修复 | 合规系统需要可审计的错误链 |
| 过渡策略 | Feature flag + 双轨并行 | 避免一次性重写导致线上中断 |

## 附录 B：外部参考

| 项目 | 借鉴点 | 采用方式 |
|------|--------|---------|
| [Pandoc](https://pandoc.org/filters.html) | reader→AST→filter→writer 编译架构 | 导出层直接使用；架构思想全局采用 |
| [Instructor](https://github.com/567-labs/instructor) | Pydantic + validate + 有限重试 | 可直接采用或借模式 |
| [Outlines](https://github.com/dottxt-ai/outlines) | 结构化生成、token masking 约束 | 借思想，暂不依赖 |
| [remark](https://github.com/remarkjs/remark) | AST 操作替代字符串正则 | 过渡期 Markdown 处理可考虑 |
| [markdownlint](https://github.com/DavidAnson/markdownlint/blob/main/doc/Rules.md) | 规则集（MD001 标题层级） | 借规则思想用于 StructureValidationPass |
| [Citum](https://citum.org) | citation_id / semantic hook / source mapping | 借思想（pre-1.0 不直接依赖） |
| [citeproc-js](https://citeproc-js.readthedocs.io/en/draft/setting-up.html) | 引用数据与显示格式分离 | 借思想 |
| [Guardrails](https://github.com/guardrails-ai/guardrails-internal) | validate→corrective action→reask | 借思想 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | checkpoint / state / replay | 借思想用于运行过程可观测性 |
