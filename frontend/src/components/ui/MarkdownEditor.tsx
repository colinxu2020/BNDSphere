import MDEditor from "@uiw/react-md-editor/nohighlight";
import * as commands from "@uiw/react-md-editor/commands-cn";
import { MarkdownContent } from "./MarkdownContent";

export function MarkdownEditor({
  value,
  onChange,
  label,
  maxLength,
  required = false,
}: {
  value: string;
  onChange: (value: string) => void;
  label: string;
  maxLength: number;
  required?: boolean;
}) {
  return (
    <div className="markdown-editor min-w-0">
      <MDEditor
        value={value}
        onChange={(nextValue) => onChange(nextValue ?? "")}
        preview="edit"
        height={240}
        visibleDragbar={false}
        defaultTabEnable
        commands={[
          commands.bold,
          commands.italic,
          { ...commands.title, buttonProps: { "aria-label": "插入标题", title: "插入标题" } },
          commands.divider,
          commands.link,
          commands.image,
          { ...commands.quote, buttonProps: { "aria-label": "插入引用", title: "插入引用" } },
          commands.unorderedListCommand,
          commands.orderedListCommand,
          commands.code,
        ]}
        extraCommands={[
          { ...commands.codeEdit, buttonProps: { "aria-label": "编辑", title: "编辑" } },
          { ...commands.codePreview, buttonProps: { "aria-label": "预览", title: "预览" } },
        ]}
        textareaProps={{ "aria-label": label, maxLength, required }}
        components={{ preview: (source) => <MarkdownContent value={source} /> }}
      />
      <p className="mt-1.5 text-xs text-slate-500">
        支持 Markdown，可切换预览。{value.length}/{maxLength}
      </p>
    </div>
  );
}
