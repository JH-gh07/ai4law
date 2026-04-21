import { useEffect, useMemo, useState } from "react";
import { useLang } from "../lib/language";

type DocExample = {
  title: string;
  input: string[];
  output: string[];
};

type DocMatrixRow = {
  topic: string;
  scenario: string;
  process: string;
  features: string;
  input: string;
  output: string;
  legal: string;
};

type DocSubSection = {
  id: string;
  title: string;
  paragraphs?: string[];
  bullets?: string[];
  examples?: DocExample[];
};

type DocSection = {
  id: string;
  title: string;
  intro?: string;
  paragraphs?: string[];
  bullets?: string[];
  examples?: DocExample[];
  matrix?: DocMatrixRow[];
  children?: DocSubSection[];
};

const IO_TOPIC_MATRIX: DocMatrixRow[] = [
  {
    topic: "合规路径诊断（总入口）",
    scenario: "用户尚不确定应走哪条路径",
    process: "选法域 → 填问卷 → 系统判断路径 → 生成结论/报告",
    features: "场景识别、路径判断、风险初筛、缺口提示",
    input: "企业类型、数据类型、数量规模、接收方、目的地、出境目的、CIIO/敏感个人信息等",
    output: "路径结论、判断依据、后续步骤、可选诊断报告",
    legal: "中国《个人信息保护法》《促进和规范数据跨境流动规定》；GDPR 第45-49条；CPRA/14117 框架"
  },
  {
    topic: "中国：安全评估路径",
    scenario: "中国向境外传输数据且触发安全评估",
    process: "判断适用 → 分步填报/批量上传 → 起草自评估报告 → 申报准备",
    features: "自评估报告生成、材料清单管理、申报辅助",
    input: "企业主体信息、法代/经办人、授权书、出境场景、合同/法律文件、安全措施信息",
    output: "《数据出境风险自评估报告》草案、申报材料包/清单",
    legal: "《个人信息保护法》《数据安全法》《网络安全法》《数据出境安全评估办法》《申报指南（第三版）》"
  },
  {
    topic: "中国：个人信息保护认证",
    scenario: "中国向境外提供个人信息且满足认证条件",
    process: "判断适用 → 认证前自检 → 影响评估 → 准备认证材料",
    features: "认证前自检、影响评估辅助、差距识别",
    input: "企业信息、出境场景、接收方信息、告知同意情况、安全与管理措施",
    output: "认证前自检结果、影响评估草案、材料清单",
    legal: "《个人信息出境认证办法》、GB/T 46068"
  },
  {
    topic: "中国：标准合同备案",
    scenario: "中国向境外提供个人信息且适用标准合同路径",
    process: "判断适用 → 填备案信息 → 生成/审查标准合同与PIPIA → 备案准备",
    features: "标准合同附件辅助、PIPIA生成、备案材料整理",
    input: "处理者基本信息、法代/经办人、承诺书、出境场景、标准合同文本",
    output: "《个人信息保护影响评估报告》草案、标准合同相关附件/材料包",
    legal: "《个人信息出境标准合同备案指南（第二版）》及标准合同/PIPIA模板"
  },
  {
    topic: "中国：文档智能审查",
    scenario: "已有隐私政策、合同、制度文件需合规检查",
    process: "上传文档 → 条款识别 → 法规比对 → 风险提示与修改建议",
    features: "合同审查、隐私政策审查、标准合同审查、差距分析",
    input: "隐私政策、数据处理协议、标准合同、内部制度等",
    output: "风险点、缺失条款、修改建议、整改清单",
    legal: "《个人信息出境标准合同办法》等现行规则与官方模板"
  },
  {
    topic: "欧盟：SCC",
    scenario: "欧盟向第三国传输个人数据并采用 SCC",
    process: "判断可用性 → 选择模块/附件 → 检查不当修改 → 补充措施",
    features: "SCC适用判断、模块匹配、附件辅助、文本审查",
    input: "出口方/进口方角色、传输场景、目的地国家、现有SCC文本",
    output: "SCC使用建议、附件内容、审查意见",
    legal: "GDPR 第46条；欧盟委员会 2021 SCC 文本及配套 Q&A"
  },
  {
    topic: "欧盟：BCR",
    scenario: "跨国集团内部长期、体系化跨境传输",
    process: "梳理集团与传输网络 → 起草规则框架 → 审查完整性 → 申请准备",
    features: "BCR框架搭建、集团规则核查、差距识别",
    input: "集团结构、实体清单、数据流、角色分工、培训/投诉/审计机制",
    output: "BCR框架草案、缺口清单、风险优先级清单",
    legal: "GDPR 第47条；EDPB/BCR 指南与建议文件"
  },
  {
    topic: "欧盟：DPIA",
    scenario: "高风险处理活动（新技术/大规模敏感数据）",
    process: "判断触发 → 描述处理活动 → 风险分析 → 输出评估草案",
    features: "DPIA触发判断、风险识别、措施建议、草案生成",
    input: "处理目的、数据类型、规模、数据主体类型、技术手段、现有措施",
    output: "DPIA 草案",
    legal: "GDPR 第35条；ISO/IEC 29134；ICO DPIA guidance/template"
  },
  {
    topic: "欧盟：TIA",
    scenario: "依赖 SCC/BCR 传输且需评估第三国法律环境",
    process: "确认工具 → 收集国家与接收方信息 → 评估法律与补充措施 → 输出评估",
    features: "第三国法律评估、补充措施分析、TIA草案生成",
    input: "传输场景、出口方/进口方信息、目的地国家法律环境、技术/合同/组织措施",
    output: "TIA 草案、补充措施建议",
    legal: "GDPR 第46.2/46.3；EDPB 05/2021、01/2020、02/2020；CNIL TIA 指南"
  },
  {
    topic: "美国（加州）：14117 行政令合规",
    scenario: "涉及受关注国家/被覆盖人/批量敏感数据传输或访问",
    process: "收集数据清单与实体清单 → 判断是否触发受管交易/限制 → 输出风险与建议",
    features: "数据分类、实体识别、风险筛查",
    input: "数据清单、实体清单、交易/访问关系",
    output: "风险识别结果、合规建议",
    legal: "EO 14117 及实施细则"
  },
  {
    topic: "美国（加州）：CPRA / 隐私政策与数据映射",
    scenario: "加州个人信息处理与跨境告知场景",
    process: "梳理数据流 → 检查隐私政策告知 → 输出映射报告与修改建议",
    features: "数据映射、隐私政策审查、告知完善",
    input: "数据清单、系统/流向信息、现有隐私政策",
    output: "数据映射报告、隐私政策修改建议",
    legal: "CCPA/CPRA"
  }
];

const DOC_SECTIONS_ZH: DocSection[] = [
  {
    id: "product-intro",
    title: "1. 产品简介",
    intro:
      "DataComply Flow（数规通）是面向企业法务、合规与数据保护岗位的 AI 辅助合规平台，覆盖“路径诊断 → 文书生成 → 文件审查”闭环。",
    paragraphs: [
      "平台当前优先覆盖中国大陆数据出境合规链路，并扩展支持欧盟 GDPR 与美国加州 CPRA 相关任务。",
      "系统输出均为草案或辅助结论，不构成正式法律意见；正式申报或对外交付前必须由专业人员复核。"
    ]
  },
  {
    id: "target-users",
    title: "2. 适用对象",
    bullets: [
      "企业法务与合规团队",
      "律所合规服务团队",
      "数据保护官（DPO）",
      "数据跨境教学与实训场景中的教师与学习者"
    ],
    paragraphs: [
      "如果核心问题是“该走哪条路径、材料如何准备、现有文本是否合规”，建议优先使用本平台。"
    ]
  },
  {
    id: "platform-structure",
    title: "3. 平台整体结构",
    children: [
      {
        id: "platform-home",
        title: "3.1 首页",
        paragraphs: ["首页用于解释平台能力边界，并提供进入任务空间与模块的入口。"]
      },
      {
        id: "platform-taskspace",
        title: "3.2 任务空间",
        paragraphs: ["任务空间用于创建和管理任务，可按法域、任务类型和案例场景进入不同模块。"]
      },
      {
        id: "platform-workspace",
        title: "3.3 工作台",
        paragraphs: [
          "工作台是核心执行区，由资源目录、运行面板与 Copilot 辅助区组成，用于输入管理、模块执行、结果审阅和导出。"
        ]
      },
      {
        id: "platform-knowledge",
        title: "3.4 知识库中心",
        paragraphs: ["知识库中心用于查看法规依据、方法说明和案例知识，支撑结果可解释性。"]
      },
      {
        id: "platform-docs",
        title: "3.5 Docs / 文档中心",
        paragraphs: ["Docs 提供使用说明、输入输出要求、FAQ 与术语解释，作为统一的阅读与培训入口。"]
      }
    ]
  },
  {
    id: "main-modules",
    title: "4. 主要功能模块",
    bullets: [
      "diagnosis：合规路径诊断",
      "assessment：数据出境安全评估",
      "scc：标准合同合规审查",
      "pipia：个人信息保护影响评估",
      "bcr / dpia / tia：欧盟相关评估和审查",
      "cpra：美国加州隐私合规分析",
      "review：文件智能审查"
    ],
    paragraphs: [
      "模块共享统一模型调用、法规检索和文档渲染能力，并支持上下文在模块间传递。",
      "从能力视角可归纳为四类：诊断、起草、审查、整改。"
    ]
  },
  {
    id: "typical-flow",
    title: "5. 典型使用流程",
    children: [
      {
        id: "flow-route-a",
        title: "5.1 路线一：先诊断，再进入目标模块",
        paragraphs: [
          "适用于尚不确定应走哪条路径的场景。",
          "建议流程：进入合规路径诊断 → 完成结构化问答 → 查看推荐路径和依据 → 跳转后续模块生成报告或继续审查。",
          "该路线可以先做路径判断，再做材料与文书工作，减少进入错误流程的风险。"
        ]
      },
      {
        id: "flow-route-b",
        title: "5.2 路线二：直接进入独立模块",
        paragraphs: [
          "适用于已明确任务类型的场景，例如已确认要生成安全评估报告、开展 PIPIA，或直接做合同/隐私政策审查。",
          "该路线可跳过路径诊断，直接进入对应模块独立运行。"
        ]
      }
    ]
  },
  {
    id: "module-howto",
    title: "6. 核心模块使用方法",
    children: [
      {
        id: "module-diagnosis",
        title: "6.1 合规路径诊断",
        paragraphs: [
          "目标：判断当前业务场景应走哪条数据出境合规路径（如安全评估、标准合同备案、个人信息出境认证）。",
          "步骤：进入模块 → 回答结构化问题 → 系统判断路径 → 查看结论与法律依据 → 下载报告或跳转下游模块。"
        ],
        bullets: [
          "输出：路径结论",
          "输出：结论依据",
          "输出：注意事项与后续动作",
          "输出：诊断报告（PDF / DOCX / HTML）"
        ],
        examples: [
          {
            title: "输入输出示例：跨境电商用户数据出境",
            input: [
              "输入字段：是否处理个人信息=是，是否跨境传输=是，敏感信息=身份证号，出境规模=10-100万",
              "输入材料：业务说明（文本）、数据清单（Excel）"
            ],
            output: [
              "输出结论：建议优先进入安全评估路径",
              "输出附件：路径诊断报告（含依据条款与后续动作）"
            ]
          }
        ]
      },
      {
        id: "module-drafting",
        title: "6.2 安全评估 / PIPIA / SCC 等报告生成模块",
        paragraphs: [
          "目标：基于结构化输入与上传材料生成合规报告草案。",
          "步骤：进入目标模块 → 填写企业与业务字段 → 上传材料 → 生成报告 → 在线预览 → 下载文档包。"
        ],
        bullets: [
          "输出：报告草案",
          "输出：章节化预览结果",
          "输出：引用链与风险标记",
          "输出：ZIP 打包交付物"
        ],
        examples: [
          {
            title: "输入输出示例：PIPIA 生成",
            input: [
              "输入字段：处理目的、处理方式、接收方信息、数据类型、保留期限",
              "输入材料：隐私政策草稿（DOCX）、数据流转表（XLSX）"
            ],
            output: [
              "输出结果：PIPIA 报告草案（按章节生成）",
              "输出清单：风险点列表 + 需人工复核项"
            ]
          }
        ]
      },
      {
        id: "module-review",
        title: "6.3 文件智能审查",
        paragraphs: [
          "目标：对已有法律文件进行条款级审查，识别风险点、缺失项与整改建议。",
          "支持对象：标准合同、隐私政策、数据处理协议、云服务协议等 Word/PDF 文件。",
          "步骤：上传文件 → 选择审查类型和适用法律 → 查看风险分级与依据 → 下载报告与问题清单。"
        ],
        bullets: [
          "支持 HIGH / MEDIUM / LOW 风险筛选",
          "支持修改后再次上传进行迭代复审"
        ],
        examples: [
          {
            title: "输入输出示例：标准合同审查",
            input: [
              "输入材料：标准合同文本（DOCX）",
              "输入配置：适用法域=中国大陆，审查类型=跨境传输条款审查"
            ],
            output: [
              "输出报告：逐条问题、风险等级、法规依据、建议修订",
              "输出文件：问题清单 Excel + 审查报告 DOCX/PDF"
            ]
          }
        ]
      }
    ]
  },
  {
    id: "processing-principle",
    title: "7. 平台内部处理原理（用户理解版）",
    children: [
      {
        id: "processing-rule",
        title: "7.1 规则层",
        paragraphs: ["负责路径判断、阈值判断与结构化约束；路径诊断优先采用规则引擎以保证一致性和可追溯性。"]
      },
      {
        id: "processing-ai",
        title: "7.2 AI 层",
        paragraphs: ["负责摘要生成、文书草拟、条款审查与建议生成，但在结构化约束下运行。"]
      },
      {
        id: "processing-platform",
        title: "7.3 平台层",
        paragraphs: ["负责任务管理、文件上传、进度追踪、结果预览、导出下载与记录保存。"]
      }
    ],
    paragraphs: ["整体采用前后端分离架构：前端 React + TypeScript + Vite，后端 FastAPI。"]
  },
  {
    id: "io-spec",
    title: "8. 专题适用场景与输入输出矩阵",
    paragraphs: [
      "以下矩阵替代通用输入/输出清单，按专题直接展示适用场景、流程、核心功能、输入输出与关键法律依据，便于用户快速定位任务入口。"
    ],
    matrix: IO_TOPIC_MATRIX
  },
  {
    id: "risk-reading",
    title: "9. 结果阅读与风险标记",
    bullets: [
      "HIGH 风险：需优先处理",
      "MEDIUM 风险：需关注和修正",
      "LOW 风险：相对可接受",
      "需人工复核：系统不确定或高风险节点"
    ],
    paragraphs: ["高风险与低置信度内容会被程序化标记，避免草案被误用为正式申报文件。"]
  },
  {
    id: "delivery",
    title: "10. 下载与交付",
    bullets: ["docx", "PDF", "HTML", "ZIP", "Excel"],
    paragraphs: [
      "所有生成文件通常包含“草案”属性，仅供内部辅助和复核使用。",
      "对外申报、备案或正式提交前，必须由专业人员复核并确认。"
    ]
  },
  {
    id: "boundaries",
    title: "11. 系统使用边界与注意事项",
    children: [
      {
        id: "boundaries-legal",
        title: "11.1 不替代律师意见",
        paragraphs: ["平台是合规辅助工具，不提供具有法律效力的最终法律意见。"]
      },
      {
        id: "boundaries-scope",
        title: "11.2 不覆盖的场景",
        bullets: ["监管执法趋势预测", "诉讼策略建议", "合同谈判策略", "法规解释争议仲裁", "数据跨境合规之外的其他法律领域"],
        paragraphs: []
      },
      {
        id: "boundaries-security",
        title: "11.3 数据与文件安全",
        paragraphs: ["平台采用本地向量索引与本地文件存储策略；原始上传文件保存在本地目录，解析后文本再进入模型处理链路。"]
      }
    ]
  },
  {
    id: "faq",
    title: "12. 常见问题",
    children: [
      {
        id: "faq-1",
        title: "Q1：不知道该走哪条路径怎么办？",
        paragraphs: ["先进入“合规路径诊断”，完成判断后再进入下游模块。"]
      },
      {
        id: "faq-2",
        title: "Q2：已经有材料，还需要先诊断吗？",
        paragraphs: ["不一定。若已明确任务，可直接进入相应模块独立运行。"]
      },
      {
        id: "faq-3",
        title: "Q3：结果能直接提交监管机构吗？",
        paragraphs: ["不能。系统输出均为草案，需专业人员复核。"]
      },
      {
        id: "faq-4",
        title: "Q4：文档审查后还能继续改吗？",
        paragraphs: ["可以。修改后可再次上传并进行迭代复审。"]
      }
    ]
  },
  {
    id: "quickstart",
    title: "13. 快速上手建议",
    children: [
      {
        id: "quickstart-a",
        title: "路线 A：新用户推荐",
        paragraphs: ["首页 → 任务空间 → 合规路径诊断 → 目标模块 → 上传材料/生成报告 → 查看结果 → 文档审查"]
      },
      {
        id: "quickstart-b",
        title: "路线 B：已有明确任务",
        paragraphs: ["首页/任务空间 → 直接进入目标模块 → 填写并上传 → 生成结果 → 下载复核"]
      },
      {
        id: "quickstart-c",
        title: "路线 C：已有文档待审查",
        paragraphs: ["首页/任务空间 → 文件审查 → 上传文档 → 查看问题 → 下载问题清单 → 修改后复审"]
      }
    ]
  }
];

const IO_TOPIC_MATRIX_EN: DocMatrixRow[] = [
  {
    topic: "Compliance Route Diagnosis (Entry)",
    scenario: "Users are unsure which route to take",
    process: "Choose jurisdiction → Fill questionnaire → System determines route → Generate conclusion/report",
    features: "Scenario recognition, route decision, risk screening, gap hints",
    input: "Entity type, data type, volume, recipient, destination, transfer purpose, CIIO/sensitive PI status",
    output: "Route conclusion, reasoning basis, next steps, optional diagnosis report",
    legal: "PIPL + PRC cross-border rules; GDPR Art.45-49; CPRA/EO 14117 framework"
  },
  {
    topic: "China: Security Assessment Path",
    scenario: "Cross-border transfer from China triggers security assessment",
    process: "Applicability check → Step-by-step filing/upload → Self-assessment draft → Submission prep",
    features: "Self-assessment drafting, material checklist, submission support",
    input: "Entity profile, legal rep/operator, authorization, transfer scenario, contracts/legal docs, security measures",
    output: "Data Export Risk Self-Assessment draft, submission package/checklist",
    legal: "PIPL, DSL, CSL, Security Assessment Measures, Filing Guide (v3)"
  },
  {
    topic: "China: Personal Information Certification",
    scenario: "Cross-border PI transfer under certification conditions",
    process: "Applicability check → Pre-cert self-check → Impact assessment → Certification materials",
    features: "Pre-cert gap scan, impact-assessment support",
    input: "Entity info, transfer scenario, recipient info, notice/consent details, governance controls",
    output: "Pre-cert self-check result, impact-assessment draft, checklist",
    legal: "PI Cross-border Certification Measures, GB/T 46068"
  },
  {
    topic: "China: Standard Contract Filing",
    scenario: "Cross-border PI transfer under SCC filing route",
    process: "Applicability check → Filing info → SCC + PIPIA drafting/review → Filing prep",
    features: "SCC attachment support, PIPIA drafting, filing package assembly",
    input: "PI processor profile, legal rep/operator, commitment letter, transfer scenario, SCC text",
    output: "PIPIA draft, SCC filing attachments/package",
    legal: "SCC Filing Guide (v2), SCC template, PIPIA template"
  },
  {
    topic: "China: Intelligent Document Review",
    scenario: "Review existing policy/contract/internal docs",
    process: "Upload doc → Clause parsing → Regulation comparison → Risk and edits",
    features: "Contract/policy review, SCC review, gap analysis",
    input: "Privacy policy, DPA, SCC, internal policies",
    output: "Risk points, missing clauses, revision suggestions, remediation list",
    legal: "Current PRC rules and official templates"
  },
  {
    topic: "EU: SCC",
    scenario: "EU-to-third-country transfer with SCC",
    process: "SCC applicability → Module/annex selection → Text integrity check → Supplementary measures",
    features: "Applicability, module match, annex support, text review",
    input: "Exporter/importer roles, transfer scenario, destination country, SCC text",
    output: "SCC usage suggestion, annex content, review comments",
    legal: "GDPR Art.46; EU 2021 SCC and Q&A"
  },
  {
    topic: "EU: BCR",
    scenario: "Intra-group long-term structured transfers",
    process: "Group/data-flow mapping → Rule framework draft → Completeness check → Approval prep",
    features: "BCR framework support, gap identification",
    input: "Group structure, entities, data flows, role assignment, training/complaint/audit process",
    output: "BCR framework draft, gap list, risk-priority list",
    legal: "GDPR Art.47; EDPB/BCR guidance"
  },
  {
    topic: "EU: DPIA",
    scenario: "High-risk processing activities",
    process: "Trigger check → Activity description → Risk analysis → Draft output",
    features: "DPIA trigger check, risk analysis, mitigation suggestions",
    input: "Purpose, data categories, scale, data subject groups, technical means, existing controls",
    output: "DPIA draft",
    legal: "GDPR Art.35; ISO/IEC 29134; ICO DPIA guidance"
  },
  {
    topic: "EU: TIA",
    scenario: "SCC/BCR transfer requiring third-country law assessment",
    process: "Tool confirmation → Country/recipient data collection → Law + supplementary measures assessment",
    features: "Third-country law assessment, supplementary measures analysis",
    input: "Transfer scenario, exporter/importer info, destination law context, technical/contractual/organizational controls",
    output: "TIA draft, supplementary-measure recommendations",
    legal: "GDPR Art.46.2/46.3; EDPB 05/2021, 01/2020, 02/2020"
  },
  {
    topic: "US (CA): EO 14117",
    scenario: "Sensitive bulk data transfer/access involving covered persons or countries",
    process: "Data/entity inventory → Restricted transaction screening → Risk/advice output",
    features: "Data classification, entity screening, risk triage",
    input: "Data inventory, entity inventory, transfer/access relationship",
    output: "Risk findings, compliance recommendations",
    legal: "EO 14117 and implementing rules"
  },
  {
    topic: "US (CA): CPRA / Privacy Policy & Data Mapping",
    scenario: "California PI processing and cross-border notice obligations",
    process: "Data-flow mapping → Privacy notice check → Mapping report and revision advice",
    features: "Data mapping, privacy policy review, notice optimization",
    input: "Data inventory, systems/flows, current privacy policy",
    output: "Data mapping report, privacy-policy revision suggestions",
    legal: "CCPA/CPRA"
  }
];

const DOC_SECTIONS_EN: DocSection[] = [
  { id: "product-intro", title: "1. Product Overview", paragraphs: ["DataComply Flow is an AI-assisted platform for cross-border data compliance workflows.", "Outputs are drafts and must be reviewed by qualified legal/compliance professionals before external submission."] },
  { id: "target-users", title: "2. Target Users", bullets: ["Corporate legal/compliance teams", "Law-firm compliance teams", "DPO and data governance roles", "Training and education users"] },
  {
    id: "platform-structure",
    title: "3. Platform Structure",
    children: [
      { id: "platform-home", title: "3.1 Home", paragraphs: ["Explains value and routes users into tasks."] },
      { id: "platform-taskspace", title: "3.2 Task Space", paragraphs: ["Creates and manages tasks by jurisdiction and module."] },
      { id: "platform-workspace", title: "3.3 Workspace", paragraphs: ["Main execution area for input, run, review, and export."] },
      { id: "platform-knowledge", title: "3.4 Knowledge Center", paragraphs: ["Supports decisions with regulation and evidence context."] },
      { id: "platform-docs", title: "3.5 Docs Center", paragraphs: ["Unified user guide, I/O requirements, and FAQs."] }
    ]
  },
  { id: "main-modules", title: "4. Core Modules", bullets: ["Diagnosis", "Assessment", "SCC", "PIPIA", "BCR/DPIA/TIA", "CPRA", "Document Review"] },
  {
    id: "typical-flow",
    title: "5. Typical Workflows",
    children: [
      { id: "flow-route-a", title: "5.1 Route A: Diagnose First", paragraphs: ["Use diagnosis first when route is unclear, then jump to downstream modules."] },
      { id: "flow-route-b", title: "5.2 Route B: Direct Module", paragraphs: ["If the target task is clear, enter the module directly."] }
    ]
  },
  {
    id: "module-howto",
    title: "6. How to Use Key Modules",
    children: [
      { id: "module-diagnosis", title: "6.1 Compliance Route Diagnosis", paragraphs: ["Complete structured questions to obtain a route recommendation and legal basis."] },
      { id: "module-drafting", title: "6.2 Drafting Modules", paragraphs: ["Fill structured fields and upload materials to generate report drafts."] },
      { id: "module-review", title: "6.3 Intelligent Document Review", paragraphs: ["Upload contract/policy files for clause-level risk analysis and revision suggestions."] }
    ]
  },
  {
    id: "processing-principle",
    title: "7. Processing Logic (User View)",
    children: [
      { id: "processing-rule", title: "7.1 Rules Layer", paragraphs: ["Deterministic routing and threshold checks."] },
      { id: "processing-ai", title: "7.2 AI Layer", paragraphs: ["Drafting, summarization, and recommendation under structured constraints."] },
      { id: "processing-platform", title: "7.3 Platform Layer", paragraphs: ["Task, file, progress, preview, and export management."] }
    ]
  },
  {
    id: "io-spec",
    title: "8. Scenario & Input/Output Matrix",
    paragraphs: ["This matrix provides module-by-module applicability, workflow, I/O, and legal references."],
    matrix: IO_TOPIC_MATRIX_EN
  },
  { id: "risk-reading", title: "9. Risk Labels in Results", bullets: ["HIGH: prioritize", "MEDIUM: fix soon", "LOW: monitor", "Manual Review Required: uncertain/high-impact nodes"] },
  { id: "delivery", title: "10. Export & Delivery", bullets: ["DOCX", "PDF", "HTML", "ZIP", "Excel"], paragraphs: ["All generated files are draft materials for internal review before official use."] },
  {
    id: "boundaries",
    title: "11. Boundaries and Notes",
    children: [
      { id: "boundaries-legal", title: "11.1 Not Legal Advice", paragraphs: ["The platform is an assistant and does not replace formal legal opinion."] },
      { id: "boundaries-scope", title: "11.2 Out-of-Scope", bullets: ["Litigation strategy", "Negotiation strategy", "Regulatory trend prediction", "Non-cross-border legal domains"] },
      { id: "boundaries-security", title: "11.3 Data & File Handling", paragraphs: ["Local storage/indexing is used for files and processing artifacts in the current architecture."] }
    ]
  },
  {
    id: "faq",
    title: "12. FAQ",
    children: [
      { id: "faq-1", title: "Q1: I don't know which route to choose.", paragraphs: ["Start with Compliance Route Diagnosis."] },
      { id: "faq-2", title: "Q2: I already have materials. Do I still need diagnosis?", paragraphs: ["Not always. If route is clear, go directly to the target module."] },
      { id: "faq-3", title: "Q3: Can I submit generated outputs directly?", paragraphs: ["No. Outputs are drafts and must be professionally reviewed."] },
      { id: "faq-4", title: "Q4: Can I re-run review after document updates?", paragraphs: ["Yes. Upload revised files and run another review cycle."] }
    ]
  },
  {
    id: "quickstart",
    title: "13. Quick Start",
    children: [
      { id: "quickstart-a", title: "Route A (Recommended)", paragraphs: ["Home → Task Space → Diagnosis → Target Module → Generate → Review"] },
      { id: "quickstart-b", title: "Route B (Known Task)", paragraphs: ["Home/Task Space → Target Module → Fill & Upload → Generate → Export"] },
      { id: "quickstart-c", title: "Route C (Review First)", paragraphs: ["Home/Task Space → Document Review → Upload → Analyze → Fix → Re-review"] }
    ]
  }
];

const collectIds = (sections: DocSection[]): string[] =>
  sections.flatMap((section) => [section.id, ...(section.children ?? []).map((child) => child.id)]);

export function DocsPlaceholderPage() {
  const { lang } = useLang();
  const docsSections = lang === "zh" ? DOC_SECTIONS_ZH : DOC_SECTIONS_EN;
  const allIds = useMemo(() => collectIds(docsSections), [docsSections]);
  const [activeId, setActiveId] = useState<string>(docsSections[0]?.id ?? "");
  const sectionTitleMap = useMemo(() => {
    const map = new Map<string, string>();
    docsSections.forEach((section) => {
      map.set(section.id, section.title);
      section.children?.forEach((child) => map.set(child.id, child.title));
    });
    return map;
  }, [docsSections]);

  useEffect(() => {
    setActiveId(docsSections[0]?.id ?? "");
  }, [docsSections]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible.length === 0) return;
        const id = visible[0].target.getAttribute("id");
        if (id) setActiveId(id);
      },
      {
        root: document.querySelector(".docs-center-scroll"),
        rootMargin: "0px 0px -55% 0px",
        threshold: [0.2, 0.45, 0.7]
      }
    );

    allIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [allIds]);

  const scrollToId = (id: string) => {
    const container = document.querySelector(".docs-center-scroll");
    const target = document.getElementById(id);
    if (!container || !target) return;
    const top = target.offsetTop - 18;
    container.scrollTo({ top, behavior: "smooth" });
    setActiveId(id);
  };

  return (
    <section className="docs-center-shell">
      <aside className="docs-toc-pane" aria-label="docs table of contents">
        <div className="docs-toc-head">
          <span className="docs-toc-kicker">Documentation</span>
          <h3>{lang === "zh" ? "DataComply Flow 指南" : "DataComply Flow Guide"}</h3>
          <p>{lang === "zh" ? "当前章节：" : "Current section: "}{sectionTitleMap.get(activeId) ?? "-"}</p>
        </div>
        <nav className="docs-toc-nav">
          {docsSections.map((section) => (
            <div key={section.id} className="docs-toc-group">
              <button
                type="button"
                className={`docs-toc-item level-1 ${activeId === section.id ? "active" : ""}`}
                onClick={() => scrollToId(section.id)}
                aria-current={activeId === section.id ? "true" : undefined}
              >
                {section.title}
              </button>
              {section.children?.map((child) => (
                <button
                  type="button"
                  key={child.id}
                  className={`docs-toc-item level-2 ${activeId === child.id ? "active" : ""}`}
                  onClick={() => scrollToId(child.id)}
                  aria-current={activeId === child.id ? "true" : undefined}
                >
                  {child.title}
                </button>
              ))}
            </div>
          ))}
        </nav>
      </aside>

      <main className="docs-center-scroll" aria-label="docs content">
        <article className="docs-article">
          <header className="docs-hero">
            <span className="docs-hero-kicker">{lang === "zh" ? "使用说明书" : "User Manual"}</span>
            <h1>{lang === "zh" ? "DataComply Flow（数规通）网站使用说明书" : "DataComply Flow Website User Guide"}</h1>
            <p>
              {lang === "zh"
                ? "本说明书面向平台实际使用者，用于指导“路径诊断、文书生成、文件审查”等核心任务的规范使用与结果复核。"
                : "This guide helps end users run diagnosis, drafting, and document-review workflows in a consistent and reviewable way."}
            </p>
          </header>

          {docsSections.map((section) => (
            <section key={section.id} id={section.id} className="docs-section">
              <h2>{section.title}</h2>
              {section.intro ? <p>{section.intro}</p> : null}
              {section.paragraphs?.map((paragraph, idx) => (
                <p key={`${section.id}-p-${idx}`}>{paragraph}</p>
              ))}
              {section.bullets ? (
                <ul>
                  {section.bullets.map((item) => (
                    <li key={`${section.id}-${item}`}>{item}</li>
                  ))}
                </ul>
              ) : null}
              {section.matrix ? (
                <div className="docs-matrix-wrap">
                  <table className="docs-matrix-table">
                    <thead>
                      <tr>
                        <th>{lang === "zh" ? "专题" : "Topic"}</th>
                        <th>{lang === "zh" ? "适用场景" : "Scenario"}</th>
                        <th>{lang === "zh" ? "典型流程" : "Workflow"}</th>
                        <th>{lang === "zh" ? "核心功能" : "Core Features"}</th>
                        <th>{lang === "zh" ? "主要输入" : "Main Inputs"}</th>
                        <th>{lang === "zh" ? "主要输出" : "Main Outputs"}</th>
                        <th>{lang === "zh" ? "关键法律/模板文件" : "Legal / Template Basis"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {section.matrix.map((row) => (
                        <tr key={`${section.id}-${row.topic}`}>
                          <td>{row.topic}</td>
                          <td>{row.scenario}</td>
                          <td>{row.process}</td>
                          <td>{row.features}</td>
                          <td>{row.input}</td>
                          <td>{row.output}</td>
                          <td>{row.legal}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
              {section.examples?.map((example) => (
                <div className="docs-example" key={`${section.id}-${example.title}`}>
                  <h4>{example.title}</h4>
                  <div className="docs-example-grid">
                    <div>
                      <strong>{lang === "zh" ? "输入示例" : "Input Example"}</strong>
                      <ul>
                        {example.input.map((item) => (
                          <li key={`${section.id}-${example.title}-in-${item}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <strong>{lang === "zh" ? "输出示例" : "Output Example"}</strong>
                      <ul>
                        {example.output.map((item) => (
                          <li key={`${section.id}-${example.title}-out-${item}`}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}

              {section.children?.map((child) => (
                <section key={child.id} id={child.id} className="docs-subsection">
                  <h3>{child.title}</h3>
                  {child.paragraphs?.map((paragraph, idx) => (
                    <p key={`${child.id}-p-${idx}`}>{paragraph}</p>
                  ))}
                  {child.bullets ? (
                    <ul>
                      {child.bullets.map((item) => (
                        <li key={`${child.id}-${item}`}>{item}</li>
                      ))}
                    </ul>
                  ) : null}
                  {child.examples?.map((example) => (
                    <div className="docs-example" key={`${child.id}-${example.title}`}>
                      <h4>{example.title}</h4>
                      <div className="docs-example-grid">
                        <div>
                          <strong>{lang === "zh" ? "输入示例" : "Input Example"}</strong>
                          <ul>
                            {example.input.map((item) => (
                              <li key={`${child.id}-${example.title}-in-${item}`}>{item}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <strong>{lang === "zh" ? "输出示例" : "Output Example"}</strong>
                          <ul>
                            {example.output.map((item) => (
                              <li key={`${child.id}-${example.title}-out-${item}`}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  ))}
                </section>
              ))}
            </section>
          ))}
        </article>
      </main>
    </section>
  );
}
