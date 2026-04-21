import { useEffect, useMemo, useState } from "react";

type DocSubSection = {
  id: string;
  title: string;
  paragraphs: string[];
  bullets?: string[];
};

type DocSection = {
  id: string;
  title: string;
  intro?: string;
  paragraphs?: string[];
  bullets?: string[];
  children?: DocSubSection[];
};

const DOC_SECTIONS: DocSection[] = [
  {
    id: "positioning",
    title: "1. 页面定位",
    intro: "Docs 是 DataComply Flow 的使用手册与方法中枢，不承担营销转化和任务执行职责。",
    bullets: [
      "对外统一说明平台做什么、怎么用、边界是什么",
      "对内统一模块口径、输入输出标准、术语定义",
      "对执行提供从上手到交付复核的可操作说明"
    ]
  },
  {
    id: "relations",
    title: "2. 与其他页面关系",
    children: [
      {
        id: "relations-home",
        title: "2.1 与首页",
        paragraphs: [
          "首页负责价值表达与场景引导，Docs 负责方法说明与操作细则。",
          "建议首页将“了解更多”或“使用指南”统一导向 Docs。"
        ]
      },
      {
        id: "relations-tasks",
        title: "2.2 与任务空间",
        paragraphs: [
          "任务空间负责项目与任务管理，Docs 负责任务前准备与输入规范说明。",
          "用户应先在 Docs 明确输入要求，再进入任务空间执行。"
        ]
      },
      {
        id: "relations-workspace",
        title: "2.3 与工作台",
        paragraphs: [
          "工作台负责运行、审阅、导出；Docs 负责运行前指导与运行后复核标准。",
          "Docs 是执行的参照系，不替代执行本身。"
        ]
      },
      {
        id: "relations-evidence",
        title: "2.4 与知识库中心",
        paragraphs: [
          "知识库中心偏法规证据检索，Docs 偏产品使用与流程解释。",
          "两者互补：Docs 给方法路径，知识库给法规依据。"
        ]
      }
    ]
  },
  {
    id: "user-goals",
    title: "3. 用户进入页面后要解决的问题",
    bullets: [
      "平台是否适用于当前业务场景",
      "应先走哪个模块，完整流程如何推进",
      "每个模块需要哪些输入文件和字段",
      "输出结果如何阅读、复核和交付",
      "常见报错、权限问题如何排查"
    ]
  },
  {
    id: "content-scope",
    title: "4. 页面承载内容范围",
    bullets: [
      "平台概览与适用边界",
      "快速开始与典型路径",
      "模块说明与输入输出规范",
      "执行流程与交付复核规则",
      "FAQ 与术语表",
      "版本更新与变更影响"
    ]
  },
  {
    id: "structure",
    title: "5. 内容结构与分区组织",
    children: [
      {
        id: "structure-ia",
        title: "5.1 目录架构建议",
        bullets: [
          "平台概览",
          "快速开始",
          "核心模块说明",
          "输入与输出规范",
          "工作流说明",
          "常见问题",
          "术语表",
          "版本更新"
        ],
        paragraphs: [
          "目录采用一级/二级结构，避免过深层级。章节顺序遵循“先总后分、先路径后细节”。"
        ]
      },
      {
        id: "structure-template",
        title: "5.2 分区写作模板",
        bullets: [
          "本节目标",
          "你会得到",
          "关键说明",
          "操作步骤",
          "常见误区",
          "相关章节"
        ],
        paragraphs: [
          "每个章节按同一模板撰写，确保可读性和可执行性一致。"
        ]
      }
    ]
  },
  {
    id: "style",
    title: "6. 文案风格控制",
    bullets: [
      "专业：术语准确，边界明确",
      "可读：短句优先，结论先行",
      "指导：每节可落到动作，不停留概念层"
    ],
    paragraphs: [
      "避免过度营销、空泛叙述和术语混用。风险提示与免责声明应单独展示并语言克制。"
    ]
  },
  {
    id: "hero-copy",
    title: "7. 作为“帮助中心/文档中心”时的首屏文案建议",
    children: [
      {
        id: "hero-copy-main",
        title: "7.1 标题与副标题",
        paragraphs: [
          "标题：DataComply Flow 文档中心",
          "副标题：统一提供平台说明、模块指引与输入输出标准，帮助你从理解平台快速进入稳定执行。"
        ]
      },
      {
        id: "hero-copy-shortcuts",
        title: "7.2 首屏快捷入口",
        bullets: ["5 分钟快速开始", "模块说明总览", "输入输出规范", "常见问题与排查"],
        paragraphs: [
          "首屏建议附“推荐阅读路径”：先读快速开始，再进入模块说明与输入规范。"
        ]
      }
    ]
  }
];

const collectIds = (sections: DocSection[]): string[] =>
  sections.flatMap((section) => [section.id, ...(section.children ?? []).map((child) => child.id)]);

export function DocsPlaceholderPage() {
  const allIds = useMemo(() => collectIds(DOC_SECTIONS), []);
  const [activeId, setActiveId] = useState<string>(DOC_SECTIONS[0]?.id ?? "");
  const sectionTitleMap = useMemo(() => {
    const map = new Map<string, string>();
    DOC_SECTIONS.forEach((section) => {
      map.set(section.id, section.title);
      section.children?.forEach((child) => map.set(child.id, child.title));
    });
    return map;
  }, []);

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
          <h3>DataComply Flow 指南</h3>
          <p>当前章节：{sectionTitleMap.get(activeId) ?? "-"}</p>
        </div>
        <nav className="docs-toc-nav">
          {DOC_SECTIONS.map((section) => (
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
            <span className="docs-hero-kicker">项目文档中心</span>
            <h1>DataComply Flow 项目讲解与页面建设说明</h1>
            <p>
              本页用于统一平台定位、页面关系、模块说明、内容组织与写作规范，作为 Docs 页面后续设计与内容建设的执行基线。
            </p>
          </header>

          {DOC_SECTIONS.map((section) => (
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
                </section>
              ))}
            </section>
          ))}
        </article>
      </main>
    </section>
  );
}
