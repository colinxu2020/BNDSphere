import MarkdownPreview from "@uiw/react-markdown-preview/nohighlight";
import remarkBreaks from "remark-breaks";
import { rehypeSanitizeWithFragments } from "../../lib/markdown";
import "./Markdown.css";

export function MarkdownContent({ value }: { value: string }) {
  return (
    <MarkdownPreview
      className="markdown-content"
      source={value}
      skipHtml
      disableCopy
      remarkPlugins={[remarkBreaks]}
      rehypePlugins={[rehypeSanitizeWithFragments]}
    />
  );
}
