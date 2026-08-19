import React, { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  Award,
  CalendarDays,
  Check,
  Clock,
  FilePenLine,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Trash2,
  X,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import { useActionFeedback } from "../lib/useActionFeedback";
import { AUDIT_TONE } from "../lib/tones";
import type { components } from "../api/schema";
import {
  ACTIVITY_LEVEL_MAP,
  ACTIVITY_LEVEL_OPTIONS,
  AUDIT_STATUS_MAP,
  AUDIT_STATUS_OPTIONS,
  MODERATION_STATUS_MAP,
  PARTICIPATION_MAP,
  STAR_LEVEL_MAP,
} from "../lib/labels";
import {
  formatDate,
  formatDateTime,
  nullableNumber,
  nullableText,
} from "../lib/format";
import {
  Badge,
  DangerButton,
  EmptyState,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  selectClassName,
  textareaClassName,
} from "../components/ui/AppPrimitives";
import { cn } from "../lib/utils";
import {
  ActivityRequestList,
  ExternalLink,
  LoadingRows,
  ReadOnlyValue,
} from "./federation/shared";
import {
  booleanToSelectValue,
  buildStarReviewBody,
  getStarPreviewLevelText,
  getStarPreviewScoreText,
  sortStarApplications,
} from "./federation/starReview";
import { StarApplicationsPanel } from "./federation/StarApplicationsPanel";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type ActivityCreateRequest =
  components["schemas"]["ClubActivityCreateRequestInfo"];
type ActivityUpdateRequest =
  components["schemas"]["ClubActivityUpdateRequestInfo"];
type ActivityLevel = components["schemas"]["GeneralActivityLevelEnum"];
type AuditStatus = components["schemas"]["AuditStatusEnum"];
type ModerationStatus = components["schemas"]["ModerationStatusEnum"];
type StarApplication = components["schemas"]["StarLevelApplicationPublicInfo"];
type StarReviewPreview =
  components["schemas"]["StarLevelApplicationReviewPreview"];
type ActivityModerationKind = "create" | "update";
type ReviewRecord = ClubGeneralActivity & { activity: GeneralActivity };

export function Federation() {
  const [activities, setActivities] = useState<GeneralActivity[]>([]);
  const [activityCreateRequests, setActivityCreateRequests] = useState<
    ActivityCreateRequest[]
  >([]);
  const [activityUpdateRequests, setActivityUpdateRequests] = useState<
    ActivityUpdateRequest[]
  >([]);
  const [starApplications, setStarApplications] = useState<StarApplication[]>(
    [],
  );
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const feedback = useActionFeedback();

  const [activityName, setActivityName] = useState("");
  const [activityDescription, setActivityDescription] = useState("");
  const [activityLevel, setActivityLevel] =
    useState<ActivityLevel>("club_federation");
  const [isCreating, setIsCreating] = useState(false);
  const [activityEditorMode, setActivityEditorMode] = useState<
    "create" | "update" | null
  >(null);

  const [selectedActivityId, setSelectedActivityId] = useState<number | null>(
    null,
  );
  const [editActivityName, setEditActivityName] = useState("");
  const [editActivityDescription, setEditActivityDescription] = useState("");
  const [editActivityLevel, setEditActivityLevel] =
    useState<ActivityLevel>("club_federation");
  const [isEditing, setIsEditing] = useState(false);

  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [recordStatus, setRecordStatus] = useState<AuditStatus>("pending");
  const [recordScore, setRecordScore] = useState("");
  const [isRecordUpdating, setIsRecordUpdating] = useState(false);

  const [busyActivityRequest, setBusyActivityRequest] = useState<string | null>(
    null,
  );

  const selectedActivity = useMemo(
    () => activities.find((activity) => activity.id === selectedActivityId),
    [activities, selectedActivityId],
  );

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
          return (
            new Date(right.created_at).getTime() -
            new Date(left.created_at).getTime()
          );
        }),
    [activities],
  );

  const selectedRecord = useMemo(
    () => reviewRecords.find((record) => record.id === selectedRecordId),
    [reviewRecords, selectedRecordId],
  );

  const loadWorkspace = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [activityResponse, createResponse, updateResponse, starResponse] =
        await Promise.all([
          client.GET("/api/v1/general-activities/", {
            params: { query: { size: 50 } },
          }),
          client.GET("/api/v1/moderations/club-activities/create-requests", {
            params: { query: { size: 50 } },
          }),
          client.GET("/api/v1/moderations/club-activities/update-requests", {
            params: { query: { size: 50 } },
          }),
          client.GET("/api/v1/star-level/", {
            params: { query: { size: 50 } },
          }),
        ]);

      setActivities(
        activityResponse.error ? [] : activityResponse.data?.items || [],
      );
      setActivityCreateRequests(
        createResponse.error ? [] : createResponse.data?.items || [],
      );
      setActivityUpdateRequests(
        updateResponse.error ? [] : updateResponse.data?.items || [],
      );
      setStarApplications(
        starResponse.error
          ? []
          : (starResponse.data?.items || [])
              .filter(
                (application) =>
                  application.academic_term.is_current &&
                  application.audit_status !== "approved",
              )
              .sort(sortStarApplications),
      );

      const firstError =
        activityResponse.error ||
        createResponse.error ||
        updateResponse.error ||
        starResponse.error;
      if (firstError) setLoadError(firstError);
    } catch (error) {
      setLoadError(error);
      setActivities([]);
      setActivityCreateRequests([]);
      setActivityUpdateRequests([]);
      setStarApplications([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, []);

  const createActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsCreating(true);
    feedback.clear();
    try {
      const { data, error } = await client.POST(
        "/api/v1/club-federation/general-activity/",
        {
          body: {
            name: activityName,
            description: activityDescription,
            level: activityLevel,
          },
        },
      );
      feedback.report(error, "大型活动已创建");
      if (!error) {
        setActivityName("");
        setActivityDescription("");
        setSelectedActivityId(data?.id || null);
        if (data) loadActivityForEdit(data);
        loadWorkspace();
      }
    } catch (error) {
      feedback.report(error, "");
    } finally {
      setIsCreating(false);
    }
  };

  const loadActivityForEdit = (activity: GeneralActivity) => {
    setActivityEditorMode("update");
    setSelectedActivityId(activity.id);
    setEditActivityName(activity.name);
    setEditActivityDescription(activity.description);
    setEditActivityLevel(activity.level);
  };

  const openActivityCreate = () => {
    setActivityEditorMode("create");
    setSelectedActivityId(null);
    setActivityName("");
    setActivityDescription("");
    setActivityLevel("club_federation");
    feedback.clear();
  };

  const closeActivityEditor = () => {
    setActivityEditorMode(null);
    setSelectedActivityId(null);
  };

  const updateActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedActivityId) {
      feedback.report("请先从活动列表选择一个活动", "");
      return;
    }

    setIsEditing(true);
    feedback.clear();
    try {
      const { data, error } = await client.PATCH(
        "/api/v1/club-federation/general-activity/{activity_id}",
        {
          params: { path: { activity_id: selectedActivityId } },
          body: {
            name: nullableText(editActivityName),
            description: nullableText(editActivityDescription),
            level: editActivityLevel,
          },
        },
      );
      feedback.report(error, "大型活动已更新");
      if (!error) {
        if (data) loadActivityForEdit(data);
        loadWorkspace();
      }
    } catch (error) {
      feedback.report(error, "");
    } finally {
      setIsEditing(false);
    }
  };

  const deleteActivity = async (activity: GeneralActivity) => {
    if (!window.confirm(`确认删除 ${activity.name}？`)) return;
    feedback.clear();
    try {
      const { error } = await client.DELETE(
        "/api/v1/club-federation/general-activity/{activity_id}",
        { params: { path: { activity_id: activity.id } } },
      );
      feedback.report(error, "大型活动已删除");
      if (!error) {
        if (selectedActivityId === activity.id) {
          setActivityEditorMode(null);
          setSelectedActivityId(null);
          setEditActivityName("");
          setEditActivityDescription("");
        }
        loadWorkspace();
      }
    } catch (error) {
      feedback.report(error, "");
    }
  };

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
      if (!error) loadWorkspace();
    } catch (error) {
      feedback.report(error, "");
    } finally {
      setIsRecordUpdating(false);
    }
  };

  const moderateClubActivityRequest = async (
    kind: ActivityModerationKind,
    requestId: number,
    moderationStatus: ModerationStatus,
  ) => {
    const busyKey = `${kind}-${requestId}`;
    setBusyActivityRequest(busyKey);
    feedback.clear();
    const body = { moderation_status: moderationStatus };
    try {
      const result =
        kind === "create"
          ? await client.PATCH(
              "/api/v1/moderations/club-activities/create-requests/{request_id}",
              {
                params: { path: { request_id: requestId } },
                body,
              },
            )
          : await client.PATCH(
              "/api/v1/moderations/club-activities/update-requests/{request_id}",
              {
                params: { path: { request_id: requestId } },
                body,
              },
            );

      feedback.report(
        result.error,
        moderationStatus === "approved"
          ? "社团活动申请已通过"
          : "社团活动申请已驳回",
      );
      if (!result.error) loadWorkspace();
    } catch (error) {
      feedback.report(error, "");
    } finally {
      setBusyActivityRequest(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8"
    >
      <PageHeader
        eyebrow="Federation"
        title="社联工作台"
        action={
          <SecondaryButton
            type="button"
            onClick={loadWorkspace}
            disabled={isLoading}
          >
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {feedback.message && <StatusMessage value={feedback.message} tone={feedback.tone} />}
      {loadError && <StatusMessage value={loadError} />}

      <Surface density="compact">
        <SectionTitle density="compact"
          icon={<FilePenLine size={20} />}
          title="审核社团活动"
          description="处理社团提交的活动创建和修改申请。"
        />
        <div className="grid gap-6 lg:grid-cols-2">
          <ActivityRequestList
            title="活动创建申请"
            kind="create"
            items={activityCreateRequests}
            busyKey={busyActivityRequest}
            onModerate={moderateClubActivityRequest}
          />
          <ActivityRequestList
            title="活动修改申请"
            kind="update"
            items={activityUpdateRequests}
            busyKey={busyActivityRequest}
            onModerate={moderateClubActivityRequest}
          />
        </div>
      </Surface>

      <Surface density="compact">
        <SectionTitle density="compact"
          icon={<ShieldCheck size={20} />}
          title="审核社团综评记录"
        />
        <div
          className={cn(
            "grid gap-6",
            selectedRecord && "lg:grid-cols-[1fr_360px]",
          )}
        >
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
                    selectedRecordId === record.id &&
                      "border-tone-brand-edge bg-brand-subtle",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={AUDIT_TONE[record.audit_status]}>
                      {AUDIT_STATUS_MAP[record.audit_status]}
                    </Badge>
                    <Badge>
                      {PARTICIPATION_MAP[record.participation_type]}
                    </Badge>
                    <span className="text-xs font-medium text-content-subtle">
                      记录 #{record.id}
                    </span>
                  </div>
                  <h3 className="mt-3 font-semibold text-content">
                    {record.activity.name}
                  </h3>
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
                  <SecondaryButton
                    type="button"
                    onClick={() => setSelectedRecordId(null)}
                  >
                    <X size={16} /> 收起
                  </SecondaryButton>
                </div>
                <Field label="审核状态">
                  <select
                    className={selectClassName}
                    value={recordStatus}
                    onChange={(event) =>
                      setRecordStatus(event.target.value as AuditStatus)
                    }
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
                    <p className="mb-2 text-sm font-semibold text-content">
                      证明材料
                    </p>
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

      <StarApplicationsPanel
        applications={starApplications}
        isLoading={isLoading}
        feedback={feedback}
        onReviewed={loadWorkspace}
      />
      <Surface density="compact">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <SectionTitle density="compact"
            className="mb-0"
            icon={<CalendarDays size={20} />}
            title="管理大型活动"
          />
          <SecondaryButton
            type="button"
            onClick={openActivityCreate}
            className="w-full whitespace-nowrap sm:w-auto"
          >
            <Plus size={16} /> 新建大型活动
          </SecondaryButton>
        </div>
        <div
          className={cn(
            "grid gap-6",
            activityEditorMode && "lg:grid-cols-[0.95fr_1.05fr]",
          )}
        >
          <div className="grid gap-3">
            {isLoading ? (
              <LoadingRows />
            ) : activities.length ? (
              activities.map((activity) => (
                <button
                  key={activity.id}
                  type="button"
                  onClick={() => loadActivityForEdit(activity)}
                  className={cn(
                    "rounded-md border border-edge-subtle bg-surface-sunken p-4 text-left transition hover:bg-surface",
                    selectedActivityId === activity.id &&
                      "border-tone-brand-edge bg-brand-subtle",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="brand">
                      {ACTIVITY_LEVEL_MAP[activity.level]}
                    </Badge>
                    <Badge>{activity.club_records?.length || 0} 条记录</Badge>
                  </div>
                  <h3 className="mt-3 font-semibold text-content">
                    {activity.name}
                  </h3>
                  <p className="mt-1 line-clamp-2 text-sm text-content-muted">
                    {activity.description}
                  </p>
                  <p className="mt-2 text-xs font-medium text-content-subtle">
                    #{activity.id} ·{" "}
                    {formatDate(activity.starts_at || activity.created_at)}
                  </p>
                </button>
              ))
            ) : (
              <EmptyState title="暂无大型活动" />
            )}
          </div>

          {activityEditorMode && (
            <div className="h-fit rounded-md border border-edge-subtle bg-surface p-5">
              {activityEditorMode === "create" ? (
                <form onSubmit={createActivity} className="grid gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
                        新建活动
                      </p>
                      <h3 className="mt-1 font-bold text-content">
                        创建大型活动
                      </h3>
                    </div>
                    <SecondaryButton
                      type="button"
                      onClick={closeActivityEditor}
                    >
                      <X size={16} /> 收起
                    </SecondaryButton>
                  </div>
                  <Field label="活动名称">
                    <input
                      className={inputClassName}
                      value={activityName}
                      onChange={(event) => setActivityName(event.target.value)}
                      required
                    />
                  </Field>
                  <Field label="活动层级">
                    <select
                      className={selectClassName}
                      value={activityLevel}
                      onChange={(event) =>
                        setActivityLevel(event.target.value as ActivityLevel)
                      }
                    >
                      {ACTIVITY_LEVEL_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="活动描述">
                    <textarea
                      className={textareaClassName}
                      value={activityDescription}
                      onChange={(event) =>
                        setActivityDescription(event.target.value)
                      }
                      required
                    />
                  </Field>
                  <PrimaryButton type="submit" loading={isCreating}>
                    <Save size={18} /> 创建大型活动
                  </PrimaryButton>
                </form>
              ) : selectedActivity ? (
                <form onSubmit={updateActivity} className="grid gap-4">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
                        当前编辑
                      </p>
                      <h3 className="mt-1 truncate text-lg font-bold text-content">
                        {selectedActivity.name}
                      </h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <SecondaryButton
                        type="button"
                        onClick={closeActivityEditor}
                      >
                        <X size={16} /> 收起
                      </SecondaryButton>
                      <Link
                        to={`/activities/${selectedActivity.id}`}
                        className="inline-flex items-center justify-center rounded-md border border-edge bg-surface-sunken px-4 py-2.5 text-sm font-semibold text-content transition hover:bg-surface-hover"
                      >
                        详情
                      </Link>
                      <DangerButton
                        type="button"
                        onClick={() => deleteActivity(selectedActivity)}
                      >
                        <Trash2 size={16} /> 删除
                      </DangerButton>
                    </div>
                  </div>
                  <Field label="活动名称">
                    <input
                      className={inputClassName}
                      value={editActivityName}
                      onChange={(event) =>
                        setEditActivityName(event.target.value)
                      }
                      required
                    />
                  </Field>
                  <Field label="活动层级">
                    <select
                      className={selectClassName}
                      value={editActivityLevel}
                      onChange={(event) =>
                        setEditActivityLevel(
                          event.target.value as ActivityLevel,
                        )
                      }
                    >
                      {ACTIVITY_LEVEL_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="活动描述">
                    <textarea
                      className={textareaClassName}
                      value={editActivityDescription}
                      onChange={(event) =>
                        setEditActivityDescription(event.target.value)
                      }
                    />
                  </Field>
                  <PrimaryButton type="submit" loading={isEditing}>
                    更新活动
                  </PrimaryButton>
                </form>
              ) : (
                <EmptyState title="请选择大型活动" />
              )}
            </div>
          )}
        </div>
      </Surface>
    </motion.div>
  );
}
