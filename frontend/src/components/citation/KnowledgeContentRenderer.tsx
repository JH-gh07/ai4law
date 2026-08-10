import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";

export type KnowledgeContentVariant = "default" | "compact" | "evidence";

interface KnowledgeContentRendererProps {
  content: string;
  variant?: KnowledgeContentVariant;
  className?: string;
}

/**
 * Unified, safe Markdown renderer for legal knowledge content.
 *
 * Used by LawViewerPage and EvidenceCenterPage to guarantee identical
 * rendering of titles, lists, tables, blockquotes, and inline code across
 * every surface that displays regulation text.
 *
 * Security: never enables ``rehypeRaw`` or ``dangerouslySetInnerHTML``.
 * Raw HTML strings in content are rendered as escaped text, not DOM nodes.
 */
export function KnowledgeContentRenderer({
  content,
  variant = "default",
  className,
}: KnowledgeContentRendererProps) {
  const variantClass = `kc-renderer-${variant}`;
  const combinedClass = ["kc-renderer", variantClass, className]
    .filter(Boolean)
    .join(" ");

  const components: Components = {
    a({ href, children, ...props }) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        >
          {children}
        </a>
      );
    },
    table({ children, ...props }) {
      return (
        <div className="kc-table-scroll">
          <table {...props}>{children}</table>
        </div>
      );
    },
  };

  return (
    <div className={combinedClass}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
