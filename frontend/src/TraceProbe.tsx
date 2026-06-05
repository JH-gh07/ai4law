import type { Language } from "./lib/i18n";
import type { TraceNode } from "./lib/domain";
import { TraceRunHeader } from "./components/workspace/TraceRunHeader";
import { TraceNodeView } from "./components/workspace/TraceNodeView";

type Props = {
  lang: Language;
};

const SAMPLE_NODES: Record<Language, TraceNode[]> = {
  zh: [
    {
      id: "trace-zh-1",
      stage: "RAG",
      action: "检索法规与依据",
      description: "围绕 GDPR 第 46 条补充检索传输依据。",
      detail: "调用对象：rag_search\n调用摘要：gdpr transfer 等 4 项\n结果摘要：4 项",
      status: "success",
      timestamp: "2026-06-05T10:00:00.000Z",
      durationMs: 1800,
      badge: "RAG",
      input: {
        label: "QUERY",
        content: "gdpr transfer safeguards\nscc bcr third-country access",
        preview: "gdpr transfer safeguards\nscc bcr third-country access",
      },
      output: {
        label: "RESULT",
        content: "命中 4 条法规依据",
        preview: "命中 4 条法规依据",
        summary: "4 项",
      },
    },
    {
      id: "trace-zh-2",
      stage: "LLM",
      action: "请求模型生成",
      description: "生成 BCR 条款责任与救济分析。",
      detail: "调用对象：llm_chat\n调用摘要：provider=siliconflow · model=deepseek-ai/DeepSeek-V3.2\n结果摘要：生成专项分析结果",
      status: "success",
      timestamp: "2026-06-05T10:00:02.000Z",
      badge: "LLM",
      output: {
        label: "OUTPUT",
        content: "模型输出正文……\n第二段内容……\n第三段内容……\n第四段内容……\n第五段内容……\n第六段内容……\n第七段内容……\n第八段内容……\n第九段内容……",
        preview: "模型输出正文……\n第二段内容……\n第三段内容……\n第四段内容……\n第五段内容……\n第六段内容……\n第七段内容……\n第八段内容……\n...",
        isTruncated: true,
        summary: "生成专项分析结果",
      },
    },
  ],
  en: [
    {
      id: "trace-en-1",
      stage: "RAG",
      action: "Search legal references",
      description: "Retrieve GDPR Article 46 references for transfer safeguards.",
      detail: "Call target: rag_search\nCall summary: gdpr transfer; scc safeguards 4 more items\nResult summary: 4 items",
      status: "success",
      timestamp: "2026-06-05T10:00:00.000Z",
      durationMs: 1800,
      badge: "RAG",
      input: {
        label: "QUERY",
        content: "gdpr transfer safeguards\nscc bcr third-country access",
        preview: "gdpr transfer safeguards\nscc bcr third-country access",
      },
      output: {
        label: "RESULT",
        content: "Retrieved 4 legal references",
        preview: "Retrieved 4 legal references",
        summary: "4 items",
      },
    },
    {
      id: "trace-en-2",
      stage: "LLM",
      action: "Request model generation",
      description: "Generate the BCR liability and remedies analysis.",
      detail: "Call target: llm_chat\nCall summary: provider=siliconflow · model=deepseek-ai/DeepSeek-V3.2\nResult summary: Generate specialized analysis",
      status: "success",
      timestamp: "2026-06-05T10:00:02.000Z",
      badge: "LLM",
      output: {
        label: "OUTPUT",
        content: "Model output paragraph 1...\nParagraph 2...\nParagraph 3...\nParagraph 4...\nParagraph 5...\nParagraph 6...\nParagraph 7...\nParagraph 8...\nParagraph 9...",
        preview: "Model output paragraph 1...\nParagraph 2...\nParagraph 3...\nParagraph 4...\nParagraph 5...\nParagraph 6...\nParagraph 7...\nParagraph 8...\n...",
        isTruncated: true,
        summary: "Generate specialized analysis",
      },
    },
  ],
};

export function TraceProbe({ lang }: Props) {
  const nodes = SAMPLE_NODES[lang];
  return (
    <main style={{ padding: 24, background: "#f5f7fb", minHeight: "100vh" }}>
      <div style={{ maxWidth: 1200, margin: "0 auto" }}>
        <TraceRunHeader
          lang={lang}
          moduleLabel={lang === "zh" ? "BCR 审查" : "BCR Review"}
          status="completed"
          taskId="trace-probe-task-001"
          startedAt="2026-06-05T10:00:00.000Z"
          completedAt="2026-06-05T10:00:18.000Z"
          nodeCount={nodes.length}
          eventCount={6}
          workflowPromptTokens={1200}
          workflowCompletionTokens={560}
          workflowTotalTokens={1760}
          copilotPromptTokens={220}
          copilotCompletionTokens={90}
          copilotTotalTokens={310}
          totalPromptTokens={1420}
          totalCompletionTokens={650}
          totalTokens={2070}
        />
        <section className="execution-timeline" style={{ marginTop: 24 }}>
          <div className="trace-timeline-line">
            {nodes.map((node) => (
              <TraceNodeView key={node.id} node={node} lang={lang} />
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
