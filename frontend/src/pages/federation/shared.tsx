/**
 * Presentational helpers for the federation workbench — pure view components
 * with no state, moved out so the page file holds workflow, not markup.
 */
import React from "react";
import { Check, Clock, X } from "@/src/components/ui/Icons";
import type { components } from "../../api/schema";
import { MODERATION_STATUS_MAP } from "../../lib/labels";
import { formatDateTime } from "../../lib/format";
import {
  Badge,
  EmptyState,
  PrimaryButton,
  SecondaryButton,
} from "../../components/ui/AppPrimitives";

type ActivityCreateRequest = components["schemas"]["ClubActivityCreateRequestInfo"];
type ActivityUpdateRequest = components["schemas"]["ClubActivityUpdateRequestInfo"];
type ModerationStatus = components["schemas"]["ModerationStatusEnum"];
type ActivityModerationKind = "create" | "update";

/**
 * Presentational helpers for the federation workbench.
 *
 * Pure view components with no state of their own, moved out of Federation.tsx
 * so the page file holds workflow rather than markup fragments.
 */

export function LoadingRows() {
  return (
    <>
      {[...Array(3)].map((_, index) => (
        <div
          key={index}
          className="h-32 animate-pulse rounded-md border border-edge-subtle bg-surface-sunken"
        />
      ))}
    </>
  );
}

export function ReadOnlyValue({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[44px] rounded-md bg-surface-sunken px-3 py-2.5 text-sm font-semibold text-content ring-[1.5px] ring-edge">
      {children}
    </div>
  );
}

export function ActivityRequestList({
  title,
  kind,
  items,
  busyKey,
  onModerate,
}: {
  title: string;
  kind: ActivityModerationKind;
  items: Array<ActivityCreateRequest | ActivityUpdateRequest>;
  busyKey: string | null;
  onModerate: (
    kind: ActivityModerationKind,
    requestId: number,
    moderationStatus: ModerationStatus,
  ) => void;
}) {
  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-content">{title}</h3>
        <Badge tone={items.length ? "warning" : "neutral"}>{items.length} 条待处理</Badge>
      </div>
      {items.length ? (
        items.map((item) => {
          const itemBusyKey = `${kind}-${item.id}`;
          return (
            <div
              key={item.id}
              className="rounded-md border border-edge-subtle bg-surface-sunken p-4"
            >
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="warning">{MODERATION_STATUS_MAP[item.moderation_status]}</Badge>
                    <span className="text-xs font-medium text-content-subtle">
                      申请 #{item.id} · {getActivityRequestTarget(item)}
                    </span>
                  </div>
                  <h4 className="mt-2 font-semibold text-content">
                    {"name" in item && item.name ? item.name : "活动修改申请"}
                  </h4>
                  <p className="mt-1 text-xs font-medium text-content-subtle">
                    <Clock size={14} className="mr-1 inline" />
                    {formatDateTime(item.request_at)}
                  </p>
                </div>
                <div className="flex gap-2">
                  <PrimaryButton
                    type="button"
                    className="px-4 py-2.5"
                    loading={busyKey === itemBusyKey}
                    onClick={() => onModerate(kind, item.id, "approved")}
                  >
                    <Check size={16} /> 通过
                  </PrimaryButton>
                  <SecondaryButton
                    type="button"
                    disabled={busyKey === itemBusyKey}
                    onClick={() => onModerate(kind, item.id, "rejected")}
                    className="border-tone-danger-edge bg-tone-danger-bg text-tone-danger-fg hover:bg-tone-danger-bg-hover"
                  >
                    <X size={16} /> 驳回
                  </SecondaryButton>
                </div>
              </div>
              <div className="mt-4 rounded-md border border-edge-subtle bg-surface p-3">
                {renderActivityRequestDetails(item)}
              </div>
            </div>
          );
        })
      ) : (
        <EmptyState title="没有待处理申请" />
      )}
    </div>
  );
}

export function renderActivityRequestDetails(item: ActivityCreateRequest | ActivityUpdateRequest) {
  const rows: [string, unknown][] = [["申请人", `#${item.requestor_id}`]];

  if ("club_id" in item) {
    rows.push(["社团", `#${item.club_id}`]);
  }
  if ("club_activity_id" in item) {
    rows.push(["原活动", `#${item.club_activity_id}`]);
  }
  if ("name" in item) rows.push(["名称", item.name]);
  if ("description" in item) rows.push(["描述", item.description]);
  if ("start_time" in item) {
    rows.push(["开始时间", item.start_time ? formatDateTime(item.start_time) : null]);
  }
  if ("end_time" in item) {
    rows.push(["结束时间", item.end_time ? formatDateTime(item.end_time) : null]);
  }
  if ("location" in item) rows.push(["地点", item.location]);
  if ("picture_urls" in item) rows.push(["图片", item.picture_urls?.join("\n")]);

  const visibleRows = rows.filter(([, value]) => value != null && value !== "");
  return (
    <div className="grid gap-2">
      {visibleRows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[72px_1fr] gap-3 text-sm">
          <span className="font-semibold text-content-muted">{label}</span>
          <span className="whitespace-pre-wrap break-words text-content">{String(value)}</span>
        </div>
      ))}
    </div>
  );
}

export function getActivityRequestTarget(item: ActivityCreateRequest | ActivityUpdateRequest) {
  if ("club_id" in item) return `社团 #${item.club_id}`;
  return `原活动 #${item.club_activity_id}`;
}

export function ExternalLink({
  href,
  children,
}: {
  href?: string | null;
  children: React.ReactNode;
}) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="rounded-md border border-edge-subtle bg-surface px-2.5 py-1 text-xs font-semibold text-tone-brand-fg hover:text-tone-brand-fg"
    >
      {children}
    </a>
  );
}
