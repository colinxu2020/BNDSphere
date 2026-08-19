import { useMemo, useState } from "react";
import type React from "react";
import { Clock, Save, ShieldCheck, X } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import {
  Badge,
  EmptyState,
  Field,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  Surface,
  inputClassName,
  selectClassName,
} from "../../components/ui/AppPrimitives";
import { AUDIT_STATUS_MAP, AUDIT_STATUS_OPTIONS, PARTICIPATION_MAP } from "../../lib/labels";
import { AUDIT_TONE } from "../../lib/tones";
import { formatDateTime, nullableNumber } from "../../lib/format";
import { cn } from "../../lib/utils";
import type { components } from "../../api/schema";
import type { useActionFeedback } from "../../lib/useActionFeedback";
import { LoadingRows } from "./shared";

type AuditStatus = components["schemas"]["AuditStatusEnum"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type ReviewRecord = ClubGeneralActivity & { activity: GeneralActivity };

/**
 * 社团活动记录审核 — the federation's review of club participation records.
 *
 * `reviewRecords` is derived from the shared activity list rather than fetched, so
 * the derivation moves here with its only consumer: the panel takes `activities`
 * as a prop and flattens/sorts it itself. Selection and form state were already
 * local to this concern.
 */
export function ClubRecordsPanel({
  activities,
  isLoading,
  feedback,
  onUpdated,
}: {
  activities: GeneralActivity[];
  isLoading: boolean;
  feedback: ReturnType<typeof useActionFeedback>;
  onUpdated: () => void;
}) {
  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [recordStatus, setRecordStatus] = useState<AuditStatus>("pending");
  const [recordScore, setRecordScore] = useState("");
  const [isRecordUpdating, setIsRecordUpdating] = useState(false);

  const reviewRecords = useMemo(
    () =>
      activities
        .flatMap((activity) =>
          (activity.club_records || []).map((record) => ({
            ...record,
            activity,
          })),
        )
        .sort((left, right) => {
          if (left.audit_status !== right.audit_status) {
            if (left.audit_status === "pending") return -1;
            if (right.audit_status === "pending") return 1;
          }
          return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
        }),
    [activities],
  );

  const selectedRecord = useMemo(
    () => reviewRecords.find((record) => record.id === selectedRecordId),
    [reviewRecords, selectedRecordId],
  );

  const loadRecordForReview = (record: ReviewRecord) => {
    setSelectedRecordId(record.id);
    setRecordStatus(record.audit_status);
    setRecordScore(String(record.requested_score));
  };

  const updateRecord = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedRecordId) {
      feedback.report("请先选择一条社团记录", "");
      return;
    }

    setIsRecordUpdating(true);
    feedback.clear();
    try {
      const { error } = await client.PATCH(
        "/api/v1/club-federation/general-activity/club-records/{record_id}",
        {
          params: { path: { record_id: selectedRecordId } },
          body: {
            audit_status: recordStatus,
            final_score: nullableNumber(recordScore),
          },
        },
      );
      feedback.report(error, "社团活动记录已更新");
      if (!error) onUpdated();
    } catch (error) {
      feedback.report(error, "");
    } finally {
      setIsRecordUpdating(false);
    }
  };

  return (
    <Surface density="compact">
      <SectionTitle density="compact" icon={<ShieldCheck size={20} />} title="审核社团综评记录" />
      <div className={cn("grid gap-6", selectedRecord && "lg:grid-cols-[1fr_360px]")}>
        <div className="grid gap-3">
          {isLoading ? (
            <LoadingRows />
          ) : reviewRecords.length ? (
            reviewRecords.map((record) => (
              <button
                key={record.id}
                type="button"
                onClick={() => loadRecordForReview(record)}
                className={cn(
                  "rounded-md border border-edge-subtle bg-surface-sunken p-4 text-left transition hover:bg-surface",
                  selectedRecordId === record.id && "border-tone-brand-edge bg-brand-subtle",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={AUDIT_TONE[record.audit_status]}>
                    {AUDIT_STATUS_MAP[record.audit_status]}
                  </Badge>
                  <Badge>{PARTICIPATION_MAP[record.participation_type]}</Badge>
                  <span className="text-xs font-medium text-content-subtle">记录 #{record.id}</span>
                </div>
                <h3 className="mt-3 font-semibold text-content">{record.activity.name}</h3>
                <p className="mt-1 text-sm text-content-muted">
                  社团 #{record.club_id} · 申请 {record.requested_score} 分
                </p>
                <p className="mt-2 text-xs font-medium text-content-subtle">
                  <Clock size={14} className="mr-1 inline" />
                  {formatDateTime(record.created_at)}
                </p>
              </button>
            ))
          ) : (
            <EmptyState title="暂无社团综评记录" />
          )}
        </div>

        {selectedRecord && (
          <form
            onSubmit={updateRecord}
            className="h-fit rounded-md border border-edge-subtle bg-surface p-5"
          >
            <div className="grid gap-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
                    当前审核
                  </p>
                  <h3 className="mt-1 truncate font-bold text-content">
                    {selectedRecord.activity.name}
                  </h3>
                  <p className="mt-1 text-sm text-content-muted">
                    社团 #{selectedRecord.club_id} · 记录 #{selectedRecord.id}
                  </p>
                </div>
                <SecondaryButton type="button" onClick={() => setSelectedRecordId(null)}>
                  <X size={16} /> 收起
                </SecondaryButton>
              </div>
              <Field label="审核状态">
                <select
                  className={selectClassName}
                  value={recordStatus}
                  onChange={(event) => setRecordStatus(event.target.value as AuditStatus)}
                >
                  {AUDIT_STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="最终分值">
                <input
                  className={inputClassName}
                  type="number"
                  value={recordScore}
                  onChange={(event) => setRecordScore(event.target.value)}
                />
              </Field>
              {selectedRecord.proof_files.length > 0 && (
                <div className="rounded-md bg-surface-sunken p-3">
                  <p className="mb-2 text-sm font-semibold text-content">证明材料</p>
                  <div className="grid gap-1">
                    {selectedRecord.proof_files.map((file, index) => (
                      <a
                        key={file}
                        href={file}
                        target="_blank"
                        rel="noreferrer"
                        className="truncate text-sm font-medium text-tone-brand-fg hover:text-tone-brand-fg"
                      >
                        材料 {index + 1}
                      </a>
                    ))}
                  </div>
                </div>
              )}
              <PrimaryButton type="submit" loading={isRecordUpdating}>
                <Save size={18} /> 更新记录
              </PrimaryButton>
            </div>
          </form>
        )}
      </div>
    </Surface>
  );
}
