import MarkdownPreview from "@uiw/react-markdown-preview/nohighlight";
import rehypeSanitize from "rehype-sanitize";
import remarkBreaks from "remark-breaks";
import "./Markdown.css";

export function MarkdownContent({ value }: { value: string }) {
  return (
    <MarkdownPreview
      className="markdown-content"
      source={value}
      skipHtml
      disableCopy
      remarkPlugins={[remarkBreaks]}
      rehypePlugins={[rehypeSanitize]}
    />
  );
}
