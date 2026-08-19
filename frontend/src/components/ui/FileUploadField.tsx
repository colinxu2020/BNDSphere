import { useRef, useState } from "react";
import { FileUp, Loader2, X } from "@/src/components/ui/Icons";
import { uploadFile, type UploadScene } from "../../api/uploads";
import { stringifyBackendValue } from "../../lib/format";
import { cn } from "../../lib/utils";
import { SecondaryButton } from "./AppPrimitives";

type FileUploadFieldProps = {
  label: string;
  scene: UploadScene;
  value?: string;
  values?: string[];
  onChange?: (value: string) => void;
  onValuesChange?: (values: string[]) => void;
  multiple?: boolean;
  accept?: string;
  hint?: string;
  resizeImage?: boolean;
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
};

export function FileUploadField({
  label,
  scene,
  value,
  values,
  onChange,
  onValuesChange,
  multiple,
  accept,
  hint,
  resizeImage,
  maxWidth,
  maxHeight,
  quality,
}: FileUploadFieldProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState<unknown>(null);

  const urls = multiple ? values || [] : value ? [value] : [];

  const uploadSelectedFiles = async (files: FileList | null) => {
    if (!files?.length) return;
    setIsUploading(true);
    setMessage(null);

    try {
      const uploaded = [];
      for (const file of Array.from(files)) {
        uploaded.push(
          await uploadFile(file, scene, {
            resizeImage,
            maxWidth,
            maxHeight,
            quality,
          }),
        );
      }

      if (multiple) {
        onValuesChange?.([...(values || []), ...uploaded]);
      } else {
        onChange?.(uploaded[0]);
      }
    } catch (error) {
      setMessage(error);
    } finally {
      setIsUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const removeUrl = (url: string) => {
    if (multiple) {
      onValuesChange?.((values || []).filter((item) => item !== url));
    } else {
      onChange?.("");
    }
  };

  return (
    <div className="block min-w-0">
      <span className="block text-sm font-medium text-content mb-1.5 ml-1">{label}</span>
      <div className="min-w-0 rounded-md border border-edge bg-surface-sunken p-4">
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          className="hidden"
          onChange={(event) => uploadSelectedFiles(event.target.files)}
        />

        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-center">
          <SecondaryButton
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={isUploading}
            className="bg-surface"
          >
            {isUploading ? <Loader2 size={16} className="animate-spin" /> : <FileUp size={16} />}
            {isUploading ? "上传中..." : "选择文件"}
          </SecondaryButton>
          {hint && <p className="min-w-0 text-xs text-content-subtle">{hint}</p>}
        </div>

        {urls.length > 0 && (
          <div className="mt-4 flex min-w-0 flex-col gap-2">
            {urls.map((url) => (
              <div
                key={url}
                className="flex min-w-0 items-center justify-between gap-3 rounded-md border border-edge-subtle bg-surface px-3 py-2"
              >
                <a
                  href={url}
                  target="_blank"
                  rel="noreferrer"
                  className="min-w-0 truncate text-sm font-medium text-content-muted hover:text-tone-brand-fg"
                >
                  {url}
                </a>
                <button
                  type="button"
                  onClick={() => removeUrl(url)}
                  className={cn(
                    "shrink-0 w-8 h-8 rounded-lg bg-surface-sunken text-content-subtle hover:bg-tone-danger-bg hover:text-tone-danger-fg",
                    "inline-flex items-center justify-center transition-colors",
                  )}
                  aria-label="移除文件"
                >
                  <X size={15} />
                </button>
              </div>
            ))}
          </div>
        )}

        {message && (
          <div className="mt-3 rounded-md border border-tone-danger-edge bg-tone-danger-bg px-3 py-2 text-sm text-tone-danger-fg whitespace-pre-wrap">
            {stringifyBackendValue(message)}
          </div>
        )}
      </div>
    </div>
  );
}
