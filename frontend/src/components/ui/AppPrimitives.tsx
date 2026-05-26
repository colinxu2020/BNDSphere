import type { ButtonHTMLAttributes, ReactNode } from "react";
import { AlertCircle, Inbox } from "lucide-react";
import { cn } from "../../lib/utils";
import { stringifyBackendValue } from "../../lib/format";

export const inputClassName =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900 placeholder:text-slate-400";

export const selectClassName =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900";

export const textareaClassName =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900 placeholder:text-slate-400 min-h-[120px] resize-none";

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
          <span className="text-xs font-bold tracking-wider uppercase text-primary-600">
            {eyebrow}
          </span>
        )}
        <h1 className="text-3xl md:text-4xl font-display font-bold text-slate-900 tracking-tight">
          {title}
        </h1>
        {description && (
          <p className="text-slate-500 text-lg max-w-2xl">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

export function Surface({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "bg-white rounded-[2rem] border border-slate-100 shadow-[0_8px_30px_-4px_rgba(0,0,0,0.04)] p-6 md:p-8",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function SectionTitle({
  icon,
  title,
  description,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex items-start gap-3 mb-6">
      {icon && (
        <div className="w-10 h-10 rounded-xl bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">
          {icon}
        </div>
      )}
      <div>
        <h2 className="text-xl font-display font-bold text-slate-900">
          {title}
        </h2>
        {description && (
          <p className="text-sm text-slate-500 mt-1">{description}</p>
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
    <label className="block">
      <span className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">
        {label}
      </span>
      {children}
      {hint && (
        <span className="block text-xs text-slate-400 mt-1.5 ml-1">{hint}</span>
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
        "inline-flex items-center justify-center gap-2 px-5 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-all shadow-md shadow-primary-500/20 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed",
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
        "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold rounded-xl transition-all active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed",
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
        "inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-red-50 hover:bg-red-100 border border-red-100 text-red-700 font-semibold rounded-xl transition-all active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed",
        className,
      )}
    >
      {children}
    </button>
  );
}

export function StatusMessage({
  value,
  tone = "error",
}: {
  value?: unknown;
  tone?: "error" | "success" | "info";
}) {
  const text = stringifyBackendValue(value);
  if (!text) return null;

  const toneClass = {
    error: "bg-red-50 text-red-700 border-red-100",
    success: "bg-emerald-50 text-emerald-700 border-emerald-100",
    info: "bg-slate-50 text-slate-600 border-slate-100",
  }[tone];

  return (
    <div
      className={cn(
        "rounded-xl border p-4 text-sm font-medium whitespace-pre-wrap",
        toneClass,
      )}
    >
      {text}
    </div>
  );
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
    <div className="flex flex-col items-center justify-center py-16 text-center bg-white border border-slate-100 border-dashed rounded-[2rem]">
      <div className="bg-slate-50 w-14 h-14 rounded-full flex items-center justify-center mb-4 text-slate-400">
        {icon || <Inbox size={24} />}
      </div>
      <h3 className="text-lg font-display font-semibold text-slate-800">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-slate-500 max-w-sm mt-2">{description}</p>
      )}
    </div>
  );
}

export function InlineError({ value }: { value?: unknown }) {
  const text = stringifyBackendValue(value);
  if (!text) return null;
  return (
    <div className="flex items-start gap-2 rounded-xl bg-red-50 border border-red-100 p-3 text-sm text-red-700 whitespace-pre-wrap">
      <AlertCircle size={16} className="mt-0.5 shrink-0" />
      <span>{text}</span>
    </div>
  );
}

export function Badge({
  children,
  tone = "slate",
}: {
  children: ReactNode;
  tone?: "slate" | "primary" | "yellow" | "green" | "red" | "blue";
}) {
  const toneClass = {
    slate: "bg-slate-50 text-slate-600 border-slate-100",
    primary: "bg-primary-50 text-primary-700 border-primary-100",
    yellow: "bg-yellow-50 text-yellow-700 border-yellow-100",
    green: "bg-emerald-50 text-emerald-700 border-emerald-100",
    red: "bg-red-50 text-red-700 border-red-100",
    blue: "bg-secondary-50 text-secondary-600 border-secondary-100",
  }[tone];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-lg border px-2.5 py-1 text-xs font-bold",
        toneClass,
      )}
    >
      {children}
    </span>
  );
}
