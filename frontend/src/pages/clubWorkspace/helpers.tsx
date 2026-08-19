/**
 * Helpers for the club workspace.
 *
 * EditorHeader is a pure view component; sameStringArray is a pure comparison
 * used to decide whether a multi-select actually changed. Both moved out as the
 * safe first step of decomposing a 1,225-line page.
 */
import { X } from "@/src/components/ui/Icons";

export function EditorHeader({
  eyebrow,
  title,
  onClose,
}: {
  eyebrow: string;
  title: string;
  onClose: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
          {eyebrow}
        </p>
        <h3 className="mt-1 truncate font-bold text-content">{title}</h3>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-sm font-semibold text-content-muted transition hover:bg-surface-hover hover:text-content"
        aria-label="收起编辑区域"
      >
        <X size={16} /> 收起
      </button>
    </div>
  );
}

export function sameStringArray(left: string[], right: string[]) {
  if (left.length !== right.length) return false;
  return left.every((item, index) => item === right[index]);
}
