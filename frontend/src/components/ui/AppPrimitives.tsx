import type { ButtonHTMLAttributes, ReactNode } from "react";
import { AlertCircle, Inbox } from "@/src/components/ui/Icons";
import { cn } from "../../lib/utils";
import { stringifyBackendValue } from "../../lib/format";
import { TONE_CLASSES, type Tone } from "../../lib/tones";

export const inputClassName =
  "w-full min-w-0 px-4 py-3 bg-surface-sunken border border-edge rounded-md focus-visible:ring-2 focus-visible:ring-brand/30 focus-visible:border-brand outline-none transition-all font-medium text-content placeholder:text-content-subtle";

export const selectClassName =
  "w-full min-w-0 px-4 py-3 bg-surface-sunken border border-edge rounded-md focus-visible:ring-2 focus-visible:ring-brand/30 focus-visible:border-brand outline-none transition-all font-medium text-content";

export const textareaClassName =
  "w-full min-w-0 px-4 py-3 bg-surface-sunken border border-edge rounded-md focus-visible:ring-2 focus-visible:ring-brand/30 focus-visible:border-brand outline-none transition-all font-medium text-content placeholder:text-content-subtle min-h-[120px] resize-none";

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mt-4">
      <div className="flex flex-col gap-2">
        {eyebrow && (
          <span className="font-display text-xs font-bold tracking-[0.18em] uppercase text-tone-brand-fg">
            {eyebrow}
          </span>
        )}
        <h1 className="text-4xl md:text-5xl font-display font-bold text-content">
          {title}
        </h1>
        {description && (
          <p className="text-content-muted text-lg max-w-2xl">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

/**
 * A panel.
 *
 * `density="compact"` is for the operational workbenches. Public surfaces are
 * expressive and can afford air; a 社联 staffer working through 待审核 items wants
 * more on screen and less decoration, so the compact variant tightens padding and
 * drops the offset to the smallest step. Same component either way, so the two
 * never drift apart.
 */
export function Surface({
  children,
  className,
  density = "comfortable",
}: {
  children: ReactNode;
  className?: string;
  density?: "comfortable" | "compact";
}) {
  return (
    <section
      className={cn(
        "bg-surface rounded-md border border-edge shadow-sm",
        density === "compact" ? "p-4 md:p-5" : "p-6 md:p-8",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function SectionTitle({
  icon,
  className,
  iconClassName,
  title,
  description,
  density = "comfortable",
}: {
  icon?: ReactNode;
  className?: string;
  iconClassName?: string;
  title: string;
  description?: string;
  density?: "comfortable" | "compact";
}) {
  return (
    <div
      className={cn(
        "flex items-start gap-3",
        density === "compact" ? "mb-4" : "mb-6",
        className,
      )}
    >
      {icon && (
        <div
          className={cn(
            "rounded-md bg-brand-subtle text-tone-brand-fg flex items-center justify-center shrink-0",
            density === "compact" ? "w-8 h-8" : "w-10 h-10",
            iconClassName,
          )}
        >
          {icon}
        </div>
      )}
      <div>
        <h2
          className={cn(
            "font-display font-bold text-content",
            density === "compact" ? "text-lg" : "text-2xl",
          )}
        >
          {title}
        </h2>
        {description && (
          <p className="text-sm text-content-muted mt-1">{description}</p>
        )}
      </div>
    </div>
  );
}

export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label className="block min-w-0">
      <span className="block text-sm font-medium text-content mb-1.5 ml-1">
        {label}
      </span>
      {children}
      {hint && (
        <span className="block text-xs text-content-subtle mt-1.5 ml-1">{hint}</span>
      )}
    </label>
  );
}

export function PrimaryButton({
  children,
  className,
  loading,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean }) {
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={cn(
        "inline-flex items-center justify-center gap-2 px-5 py-3 bg-brand hover:bg-brand-hover text-brand-on font-semibold rounded-md transition-all shadow-md shadow-brand/20 active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100 disabled:opacity-70 disabled:cursor-not-allowed outline-none focus-visible:ring-4 focus-visible:ring-brand/40",
        className,
      )}
    >
      {loading ? "处理中..." : children}
    </button>
  );
}

export function SecondaryButton({
  children,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-surface-sunken hover:bg-surface-hover border border-edge text-content font-semibold rounded-md transition-all active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100 disabled:opacity-60 disabled:cursor-not-allowed outline-none focus-visible:ring-4 focus-visible:ring-brand/40",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function DangerButton({
  children,
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-tone-danger-bg hover:bg-tone-danger-bg-hover border border-tone-danger-edge text-tone-danger-fg font-semibold rounded-md transition-all active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100 disabled:opacity-60 disabled:cursor-not-allowed outline-none focus-visible:ring-4 focus-visible:ring-tone-danger-fg/40",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function StatusMessage({
  value,
  tone = "danger",
}: {
  value?: unknown;
  tone?: Tone;
}) {
  const text =
    tone === "success"
      ? stringifySuccessValue(value)
      : stringifyBackendValue(value);
  if (!text) return null;

  const toneClass = TONE_CLASSES[tone];

  return (
    <div
      className={cn(
        "rounded-md border p-4 text-sm font-medium whitespace-pre-wrap",
        toneClass,
      )}
    >
      {text}
    </div>
  );
}

function stringifySuccessValue(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return stringifyBackendValue(value);
  if (value instanceof Error) return value.message;
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    const detail = record.detail || record.message;
    if (typeof detail === "string") return stringifyBackendValue(detail);
    return "操作已完成";
  }
  return stringifyBackendValue(value);
}

export function EmptyState({
  title,
  description,
  icon,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center bg-surface border border-edge-subtle border-dashed rounded-md">
      <div className="bg-surface-sunken w-14 h-14 rounded-md flex items-center justify-center mb-4 text-content-subtle">
        {icon || <Inbox size={24} />}
      </div>
      <h3 className="text-lg font-display font-semibold text-content">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-content-muted max-w-sm mt-2">{description}</p>
      )}
    </div>
  );
}

export function InlineError({ value }: { value?: unknown }) {
  const text = stringifyBackendValue(value);
  if (!text) return null;
  return (
    <div className="flex items-start gap-2 rounded-md bg-tone-danger-bg border border-tone-danger-edge p-3 text-sm text-tone-danger-fg whitespace-pre-wrap">
      <AlertCircle size={16} className="mt-0.5 shrink-0" />
      <span>{text}</span>
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: Tone;
}) {
  const toneClass = TONE_CLASSES[tone];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2.5 py-1 text-xs font-bold",
        toneClass,
      )}
    >
      {children}
    </span>
  );
}
