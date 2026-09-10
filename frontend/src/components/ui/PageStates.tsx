import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { ArrowLeft, Compass, Shield } from "@/src/components/ui/Icons";
import { cn } from "../../lib/utils";

// eslint-disable-next-line react-refresh/only-export-components
export function isForbiddenResponse(response?: Response, error?: unknown) {
  if (response?.status === 403) return true;
  if (!error || typeof error !== "object") return false;

  const record = error as Record<string, unknown>;
  return (
    record.error_code === "ROLE_NOT_ALLOWED" ||
    record.error_code === "CLUB_ROLE_NOT_ALLOWED" ||
    record.message_key === "error.role.not_allowed" ||
    record.message_key === "error.club.role_not_allowed"
  );
}

export function PageLoading({
  title = "正在加载",
  description = "请稍候，正在加载页面内容。",
  compact = false,
  className,
}: {
  title?: string;
  description?: string;
  compact?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative isolate flex w-full items-center justify-center overflow-hidden rounded-md border border-slate-100 bg-white shadow-sm",
        compact ? "min-h-44 p-6" : "min-h-[360px] p-8",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_40%,rgba(20,184,166,0.08),transparent_42%)]" />

      <div className="relative flex max-w-sm flex-col items-center text-center">
        <div className="relative mb-5 flex h-16 w-16 items-center justify-center">
          <motion.div
            aria-hidden="true"
            className="absolute inset-0 rounded-[22px] bg-primary-100"
            animate={{ rotate: [0, 90, 180], borderRadius: ["22px", "32px", "22px"] }}
            transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            aria-hidden="true"
            className="absolute inset-2 rounded-2xl bg-primary-500 shadow-lg shadow-primary-500/25"
            animate={{ rotate: [0, -90, -180], scale: [0.9, 1, 0.9] }}
            transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            aria-hidden="true"
            className="relative h-2.5 w-2.5 rounded-full bg-white"
            animate={{ scale: [0.8, 1.35, 0.8], opacity: [0.75, 1, 0.75] }}
            transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
        <h2 className="font-display text-lg font-bold text-slate-900">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
        <div className="mt-5 flex items-center gap-1.5" aria-hidden="true">
          {[0, 1, 2].map((index) => (
            <motion.span
              key={index}
              className="h-1.5 w-1.5 rounded-full bg-primary-500"
              animate={{ y: [0, -5, 0], opacity: [0.35, 1, 0.35] }}
              transition={{ duration: 0.9, repeat: Infinity, delay: index * 0.14 }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export function ForbiddenPage({
  description = "当前账号没有访问此页面的权限。你可以返回上一页，或回到首页继续浏览。",
  backTo = "/",
  backLabel = "返回首页",
}: {
  description?: string;
  backTo?: string;
  backLabel?: string;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative isolate flex min-h-[480px] overflow-hidden rounded-md border border-slate-100 bg-white p-8 shadow-sm md:p-12"
    >
      <div className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full bg-primary-50 blur-2xl" />
      <div className="pointer-events-none absolute bottom-0 left-0 h-40 w-40 rounded-full bg-slate-100 blur-2xl" />

      <div className="relative m-auto flex max-w-xl flex-col items-center text-center">
        <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-[28px] border border-primary-100 bg-primary-50 text-primary-600 shadow-lg shadow-primary-500/10">
          <Shield size={38} />
        </div>
        <p className="text-sm font-bold uppercase tracking-[0.28em] text-primary-600">Forbidden</p>
        <h1 className="mt-2 font-display text-6xl font-bold tracking-tight text-slate-900">403</h1>
        <h2 className="mt-3 font-display text-2xl font-bold text-slate-900">无权访问此页面</h2>
        <p className="mt-3 max-w-md text-base leading-7 text-slate-500">{description}</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <button
            type="button"
            onClick={() => window.history.back()}
            className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-5 py-3 font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            <ArrowLeft size={17} /> 返回上一页
          </button>
          <Link
            to={backTo}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary-500 px-5 py-3 font-semibold text-white shadow-md shadow-primary-500/20 transition hover:bg-primary-600"
          >
            <Compass size={17} /> {backLabel}
          </Link>
        </div>
      </div>
    </motion.section>
  );
}
