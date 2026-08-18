import React, { useEffect, useMemo, useState } from "react";
import {
  Bell,
  CalendarDays,
  RefreshCw,
  Save,
  Shield,
  Trash2,
  Users,
} from "@/src/components/ui/Icons";
import type { Tone } from "../../lib/tones";
import {
  Badge,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  StatusMessage,
  inputClassName,
  selectClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { cn } from "../../lib/utils";

export function AdminGrid({
  title,
  list,
  children,
  refreshing,
  onRefresh,
}: {
  title: string;
  list: React.ReactNode;
  children: React.ReactNode;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="grid min-w-0 gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div className="grid min-w-0 content-start gap-3 self-start">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-lg font-bold">{title}</h2>
          <button
            type="button"
            onClick={onRefresh}
            disabled={refreshing}
            className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-edge text-content-muted hover:bg-surface-sunken disabled:opacity-50"
            aria-label="刷新"
          >
            <RefreshCw size={15} className={cn(refreshing && "animate-spin")} />
          </button>
        </div>
        {list}
      </div>
      <div className="min-h-[420px] min-w-0 rounded-md border border-edge bg-surface-sunken p-4">
        {children}
      </div>
    </div>
  );
}

export function ItemList({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-h-[620px] space-y-2 overflow-y-auto overflow-x-hidden pr-1">
      {children}
    </div>
  );
}

export function ListButton({
  title,
  meta,
  badge,
  active,
  onClick,
}: {
  key?: React.Key;
  title: string;
  meta?: string;
  badge?: string;
  active?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full min-w-0 rounded-md border p-3 text-left transition",
        active
          ? "border-content bg-surface"
          : "border-edge bg-surface hover:border-edge-strong",
      )}
    >
      <div className="flex min-w-0 items-center justify-between gap-2">
        <p className="min-w-0 truncate text-sm font-semibold text-content">
          {title}
        </p>
        {badge && <Badge tone="brand">{badge}</Badge>}
      </div>
      {meta && <p className="mt-1 truncate text-xs text-content-muted">{meta}</p>}
    </button>
  );
}

export function FormHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="min-w-0 border-b border-edge pb-3">
      <h3 className="break-words font-display text-xl font-bold text-content">
        {title}
      </h3>
      <p className="break-words text-sm text-content-muted">{subtitle}</p>
    </div>
  );
}

export function PickPlaceholder({ label }: { label: string }) {
  return (
    <div className="flex min-h-[360px] items-center justify-center rounded-md border border-dashed border-edge bg-surface text-sm font-semibold text-content-muted">
      {label}
    </div>
  );
}
