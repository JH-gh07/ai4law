import type { ArtifactPreview } from "../../api/artifacts";

type DocxArtifactPreviewProps = {
  preview: ArtifactPreview;
  lang: "zh" | "en";
  downloadBusy: boolean;
  onOpen: (path: string) => void;
  onDownload: (path: string) => void;
};

/**
 * DOCX artifact preview (task068 T08).
 *
 * A Word document is never rendered inline as Markdown. This component shows
 * the artifact metadata plus download/open actions, and keeps the server
 * extracted text collapsed and explicitly labelled as auxiliary — so the same
 * long text is never duplicated in the report body.
 */
export function DocxArtifactPreview({ preview, lang, downloadBusy, onOpen, onDownload }: DocxArtifactPreviewProps) {
  const content = preview.content ?? "";
  return (
    <article className="workspace-report-chapter workspace-report-preview-block">
      <div className="workspace-docx-meta">
        <strong>{preview.file_name || (lang === "zh" ? "Word 文档" : "Word Document")}</strong>
        <span className="workspace-docx-meta-kind">DOCX</span>
      </div>
      <p className="workspace-docx-meta-hint">
        {lang === "zh"
          ? "Word 文档不支持内嵌正文预览，请下载或打开原文件。"
          : "Word documents are not rendered inline; download or open the source file."}
      </p>
      <div className="workspace-docx-actions">
        <button type="button" onClick={() => onOpen(preview.path)}>
          {lang === "zh" ? "打开原文件" : "Open file"}
        </button>
        <button type="button" onClick={() => onDownload(preview.path)} disabled={downloadBusy}>
          {lang === "zh" ? "下载" : "Download"}
        </button>
      </div>
      {content.trim() ? (
        <details className="workspace-docx-extracted">
          <summary>{lang === "zh" ? "辅助抽取文本（点击展开）" : "Extracted text (auxiliary)"}</summary>
          <pre className="workspace-plain-preview">{content}</pre>
        </details>
      ) : null}
    </article>
  );
}
