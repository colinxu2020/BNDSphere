import MDEditor from "@uiw/react-md-editor/nohighlight";
import * as commands from "@uiw/react-md-editor/commands-cn";
import { MarkdownContent } from "./MarkdownContent";
import { markdownLengthError } from "../../lib/markdown";

export function MarkdownEditor({
  id,
  value,
  onChange,
  label,
  maxLength,
  required = false,
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  label: string;
  maxLength: number;
  required?: boolean;
}) {
  const lengthError = markdownLengthError(value, maxLength);
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
        textareaProps={{
          id,
          "aria-label": label,
          "aria-invalid": Boolean(lengthError),
          "aria-describedby": lengthError ? `${id}-error` : undefined,
          maxLength,
          required,
        }}
        components={{ preview: (source) => <MarkdownContent value={source} /> }}
      />
      {lengthError && (
        <p id={`${id}-error`} role="alert" className="mt-1.5 text-xs text-red-600">
          {lengthError}
        </p>
      )}
      <p className="mt-1.5 text-xs text-slate-500">
        支持 Markdown，可切换预览。
        <a
          href="https://sspai.com/post/36610"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 underline underline-offset-2 hover:text-primary-700"
        >
          了解更多
        </a>{" "}
        {value.length}/{maxLength}
      </p>
    </div>
  );
}
