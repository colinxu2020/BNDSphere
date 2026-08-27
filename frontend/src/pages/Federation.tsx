import React, { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  Award,
  CalendarDays,
  Clock,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Trash2,
  X,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  ACTIVITY_LEVEL_MAP,
  ACTIVITY_LEVEL_OPTIONS,
  AUDIT_STATUS_MAP,
  AUDIT_STATUS_OPTIONS,
  PARTICIPATION_MAP,
  STAR_LEVEL_MAP,
} from "../lib/labels";
import { formatDate, formatDateTime, nullableNumber, nullableText } from "../lib/format";
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

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type ActivityLevel = components["schemas"]["GeneralActivityLevelEnum"];
type AuditStatus = components["schemas"]["AuditStatusEnum"];
type StarApplication = components["schemas"]["StarLevelApplicationPublicInfo"];
type StarReviewPreview = components["schemas"]["StarLevelApplicationReviewPreview"];
type ReviewRecord = ClubGeneralActivity & { activity: GeneralActivity };

export function Federation() {
  const [activities, setActivities] = useState<GeneralActivity[]>([]);
  const [starApplications, setStarApplications] = useState<StarApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [message, setMessage] = useState<unknown>(null);
  const [messageTone, setMessageTone] = useState<"error" | "success">("error");

  const [activityName, setActivityName] = useState("");
  const [activityDescription, setActivityDescription] = useState("");
  const [activityLevel, setActivityLevel] = useState<ActivityLevel>("club_federation");
  const [isCreating, setIsCreating] = useState(false);
  const [activityEditorMode, setActivityEditorMode] = useState<"create" | "update" | null>(null);

  const [selectedActivityId, setSelectedActivityId] = useState<number | null>(null);
  const [editActivityName, setEditActivityName] = useState("");
  const [editActivityDescription, setEditActivityDescription] = useState("");
  const [editActivityLevel, setEditActivityLevel] = useState<ActivityLevel>("club_federation");
  const [isEditing, setIsEditing] = useState(false);

  const [selectedRecordId, setSelectedRecordId] = useState<number | null>(null);
  const [recordStatus, setRecordStatus] = useState<AuditStatus>("pending");
  const [recordScore, setRecordScore] = useState("");
  const [isRecordUpdating, setIsRecordUpdating] = useState(false);

  const [selectedStarId, setSelectedStarId] = useState<number | null>(null);
  const [starStatus, setStarStatus] = useState<AuditStatus>("pending");
  const [finalContestScore, setFinalContestScore] = useState("");
  const [uniquenessApproved, setUniquenessApproved] = useState("");
  const [growthStoryApproved, setGrowthStoryApproved] = useState("");
  const [starPreview, setStarPreview] = useState<StarReviewPreview | null>(null);
  const [isStarPreviewLoading, setIsStarPreviewLoading] = useState(false);
  const [isStarReviewing, setIsStarReviewing] = useState(false);

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
          return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
        }),
    [activities],
  );

  const selectedRecord = useMemo(
    () => reviewRecords.find((record) => record.id === selectedRecordId),
    [reviewRecords, selectedRecordId],
  );
  const selectedStarApplication = useMemo(
    () => starApplications.find((application) => application.id === selectedStarId) || null,
    [selectedStarId, starApplications],
  );

  const loadWorkspace = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const [activityResponse, starResponse] = await Promise.all([
        client.GET("/api/v1/general-activities/", {
          params: { query: { size: 50 } },
        }),
        client.GET("/api/v1/star-level/", {
          params: { query: { size: 50 } },
        }),
      ]);

      setActivities(activityResponse.error ? [] : activityResponse.data?.items || []);
      setStarApplications(
        starResponse.error
          ? []
          : (starResponse.data?.items || [])
              .filter(
                (application) =>
                  application.academic_term.is_current && application.audit_status !== "approved",
              )
              .sort(sortStarApplications),
      );

      const firstError = activityResponse.error || starResponse.error;
      if (firstError) setLoadError(firstError);
    } catch (error) {
      setLoadError(error);
      setActivities([]);
      setStarApplications([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspace();
  }, []);

  useEffect(() => {
    if (!selectedStarApplication) {
      setStarPreview(null);
      setIsStarPreviewLoading(false);
      return;
    }

    if (starStatus !== "approved") {
      setStarPreview({ approved_score: null, approved_level: null });
      setIsStarPreviewLoading(false);
      return;
    }

    let isCurrent = true;
    setIsStarPreviewLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        const { data, error } = await client.POST(
          "/api/v1/club-federation/star-level/{star_level_id}/preview",
          {
            params: { path: { star_level_id: selectedStarApplication.id } },
            body: buildStarReviewBody(
              starStatus,
              finalContestScore,
              uniquenessApproved,
              growthStoryApproved,
            ),
          },
        );
        if (isCurrent) setStarPreview(error ? null : data || null);
      } catch {
        if (isCurrent) setStarPreview(null);
      } finally {
        if (isCurrent) setIsStarPreviewLoading(false);
      }
    }, 180);

    return () => {
      isCurrent = false;
      window.clearTimeout(timer);
    };
    // The selected object is intentionally represented by its stable ID.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    finalContestScore,
    growthStoryApproved,
    selectedStarApplication?.id,
    starStatus,
    uniquenessApproved,
  ]);

  const setResult = (error: unknown, successMessage: string) => {
    if (error) {
      setMessageTone("error");
      setMessage(error);
      return;
    }
    setMessageTone("success");
    setMessage(successMessage);
  };

  const createActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsCreating(true);
    setMessage(null);
    try {
      const { data, error } = await client.POST("/api/v1/club-federation/general-activity/", {
        body: {
          name: activityName,
          description: activityDescription,
          level: activityLevel,
        },
      });
      setResult(error, "大型活动已创建");
      if (!error) {
        setActivityName("");
        setActivityDescription("");
        setSelectedActivityId(data?.id || null);
        if (data) loadActivityForEdit(data);
        loadWorkspace();
      }
    } catch (error) {
      setResult(error, "");
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
    setMessage(null);
  };

  const closeActivityEditor = () => {
    setActivityEditorMode(null);
    setSelectedActivityId(null);
  };

  const updateActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedActivityId) {
      setResult("请先从活动列表选择一个活动", "");
      return;
    }

    setIsEditing(true);
    setMessage(null);
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
      setResult(error, "大型活动已更新");
      if (!error) {
        if (data) loadActivityForEdit(data);
        loadWorkspace();
      }
    } catch (error) {
      setResult(error, "");
    } finally {
      setIsEditing(false);
    }
  };

  const deleteActivity = async (activity: GeneralActivity) => {
    if (!window.confirm(`确认删除 ${activity.name}？`)) return;
    setMessage(null);
    try {
      const { error } = await client.DELETE(
        "/api/v1/club-federation/general-activity/{activity_id}",
        { params: { path: { activity_id: activity.id } } },
      );
      setResult(error, "大型活动已删除");
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
      setResult(error, "");
    }
  };

  const loadRecordForReview = (record: ReviewRecord) => {
    setSelectedRecordId(record.id);
    setRecordStatus(record.audit_status);
    setRecordScore(String(record.requested_score));
  };

  const loadStarApplicationForReview = (application: StarApplication) => {
    setSelectedStarId(application.id);
    setStarStatus(application.audit_status || "pending");
    setFinalContestScore(
      application.final_contest_score == null
        ? application.requested_contest_score == null
          ? ""
          : String(application.requested_contest_score)
        : String(application.final_contest_score),
    );
    setUniquenessApproved(booleanToSelectValue(application.uniqueness_approved));
    setGrowthStoryApproved(booleanToSelectValue(application.growth_story_approved));
  };

  const updateRecord = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedRecordId) {
      setResult("请先选择一条社团记录", "");
      return;
    }

    setIsRecordUpdating(true);
    setMessage(null);
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
      setResult(error, "社团活动记录已更新");
      if (!error) loadWorkspace();
    } catch (error) {
      setResult(error, "");
    } finally {
      setIsRecordUpdating(false);
    }
  };

  const reviewStarApplication = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedStarApplication) {
      setResult("请先选择一份星级评价表", "");
      return;
    }

    setIsStarReviewing(true);
    setMessage(null);
    try {
      const { error } = await client.PATCH("/api/v1/club-federation/star-level/{star_level_id}", {
        params: { path: { star_level_id: selectedStarApplication.id } },
        body: {
          ...buildStarReviewBody(
            starStatus,
            finalContestScore,
            uniquenessApproved,
            growthStoryApproved,
          ),
        },
      });
      setResult(error, "星级评价表已审核");
      if (!error) {
        setSelectedStarId(null);
        setStarPreview(null);
        loadWorkspace();
      }
    } catch (error) {
      setResult(error, "");
    } finally {
      setIsStarReviewing(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <PageHeader
        eyebrow="Federation"
        title="社联工作台"
        action={
          <div className="flex flex-wrap justify-between gap-2">
            <Link
              to="/federation/joint-activities"
              className="inline-flex items-center justify-center gap-2 rounded-md border border-primary-100 bg-primary-50 px-4 py-2.5 font-semibold text-primary-700 hover:bg-primary-100"
            >
              <CalendarDays size={16} /> 联合活动审核
            </Link>
            <SecondaryButton type="button" onClick={loadWorkspace} disabled={isLoading}>
              <RefreshCw size={16} /> 刷新
            </SecondaryButton>
          </div>
        }
      />

      {message && <StatusMessage value={message} tone={messageTone} />}
      {loadError && <StatusMessage value={loadError} />}

      <Surface>
        <SectionTitle icon={<ShieldCheck size={20} />} title="审核社团综评记录" />
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
                    "rounded-md border border-slate-100 bg-slate-50 p-4 text-left transition hover:bg-white",
                    selectedRecordId === record.id && "border-primary-200 bg-primary-50",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={getAuditTone(record.audit_status)}>
                      {AUDIT_STATUS_MAP[record.audit_status]}
                    </Badge>
                    <Badge>{PARTICIPATION_MAP[record.participation_type]}</Badge>
                    <span className="text-xs font-medium text-slate-400">记录 #{record.id}</span>
                  </div>
                  <h3 className="mt-3 font-semibold text-slate-900">{record.activity.name}</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    社团 #{record.club_id} · 申请 {record.requested_score} 分
                  </p>
                  <p className="mt-2 text-xs font-medium text-slate-400">
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
              className="h-fit rounded-md border border-slate-100 bg-white p-5"
            >
              <div className="grid gap-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      当前审核
                    </p>
                    <h3 className="mt-1 truncate font-bold text-slate-900">
                      {selectedRecord.activity.name}
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">
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
                  <div className="rounded-md bg-slate-50 p-3">
                    <p className="mb-2 text-sm font-semibold text-slate-700">证明材料</p>
                    <div className="grid gap-1">
                      {selectedRecord.proof_files.map((file, index) => (
                        <a
                          key={file}
                          href={file}
                          target="_blank"
                          rel="noreferrer"
                          className="truncate text-sm font-medium text-primary-600 hover:text-primary-700"
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

      <Surface>
        <SectionTitle icon={<Award size={20} />} title="审核星级评价表" />
        <div className={cn("grid gap-6", selectedStarApplication && "lg:grid-cols-[1fr_380px]")}>
          <div className="grid gap-3">
            {isLoading ? (
              <LoadingRows />
            ) : starApplications.length ? (
              starApplications.map((application) => (
                <button
                  key={application.id}
                  type="button"
                  onClick={() => loadStarApplicationForReview(application)}
                  className={cn(
                    "rounded-md border border-slate-100 bg-slate-50 p-4 text-left transition hover:bg-white",
                    selectedStarId === application.id && "border-primary-200 bg-primary-50",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone={getAuditTone(application.audit_status || "pending")}>
                      {application.audit_status
                        ? AUDIT_STATUS_MAP[application.audit_status]
                        : "待审核"}
                    </Badge>
                    <Badge>
                      {application.approved_level
                        ? STAR_LEVEL_MAP[application.approved_level]
                        : "待计算"}
                    </Badge>
                    <span className="text-xs font-medium text-slate-400">
                      申请 #{application.id}
                    </span>
                  </div>
                  <h3 className="mt-3 font-semibold text-slate-900">{application.club.name}</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    申请竞赛分 {application.requested_contest_score ?? "未填"} ·{" "}
                    {application.academic_term.term_name}
                  </p>
                  <p className="mt-2 text-xs font-medium text-slate-400">
                    <Clock size={14} className="mr-1 inline" />
                    {formatDateTime(application.created_at)}
                  </p>
                </button>
              ))
            ) : (
              <EmptyState title="暂无星级评价表" />
            )}
          </div>

          {selectedStarApplication && (
            <form
              onSubmit={reviewStarApplication}
              className="h-fit rounded-md border border-slate-100 bg-white p-5"
            >
              <div className="grid gap-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                      当前审核
                    </p>
                    <h3 className="mt-1 truncate font-bold text-slate-900">
                      {selectedStarApplication.club.name}
                    </h3>
                    <p className="mt-1 text-sm text-slate-500">
                      申请 #{selectedStarApplication.id} ·{" "}
                      {selectedStarApplication.academic_term.term_name}
                    </p>
                  </div>
                  <SecondaryButton type="button" onClick={() => setSelectedStarId(null)}>
                    <X size={16} /> 收起
                  </SecondaryButton>
                </div>
                <Field label="审核状态">
                  <select
                    className={selectClassName}
                    value={starStatus}
                    onChange={(event) => setStarStatus(event.target.value as AuditStatus)}
                  >
                    {AUDIT_STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="最终竞赛分">
                    <input
                      className={inputClassName}
                      type="number"
                      value={finalContestScore}
                      onChange={(event) => setFinalContestScore(event.target.value)}
                    />
                  </Field>
                  <Field label="审核总分">
                    <ReadOnlyValue>
                      {getStarPreviewScoreText(starStatus, isStarPreviewLoading, starPreview)}
                    </ReadOnlyValue>
                  </Field>
                </div>
                <Field label="系统评定星级">
                  <ReadOnlyValue>
                    {getStarPreviewLevelText(starStatus, isStarPreviewLoading, starPreview)}
                  </ReadOnlyValue>
                </Field>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Field label="独特性审核">
                    <select
                      className={selectClassName}
                      value={uniquenessApproved}
                      onChange={(event) => setUniquenessApproved(event.target.value)}
                    >
                      <option value="">未定</option>
                      <option value="true">通过</option>
                      <option value="false">不通过</option>
                    </select>
                  </Field>
                  <Field label="成长故事">
                    <select
                      className={selectClassName}
                      value={growthStoryApproved}
                      onChange={(event) => setGrowthStoryApproved(event.target.value)}
                    >
                      <option value="">未定</option>
                      <option value="true">通过</option>
                      <option value="false">不通过</option>
                    </select>
                  </Field>
                </div>
                <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-600">
                  <p className="font-semibold text-slate-800">申请内容</p>
                  <p className="mt-2 whitespace-pre-wrap leading-6">
                    {selectedStarApplication.uniqueness_statement || "未填写特色说明。"}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <ExternalLink href={selectedStarApplication.contest_attachment}>
                      竞赛附件
                    </ExternalLink>
                    <ExternalLink href={selectedStarApplication.growth_story_url}>
                      成长故事
                    </ExternalLink>
                  </div>
                </div>
                <PrimaryButton type="submit" loading={isStarReviewing}>
                  <Save size={18} /> 提交审核
                </PrimaryButton>
              </div>
            </form>
          )}
        </div>
      </Surface>

      <Surface>
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <SectionTitle className="mb-0" icon={<CalendarDays size={20} />} title="管理大型活动" />
          <SecondaryButton
            type="button"
            onClick={openActivityCreate}
            className="w-full whitespace-nowrap sm:w-auto"
          >
            <Plus size={16} /> 新建大型活动
          </SecondaryButton>
        </div>
        <div className={cn("grid gap-6", activityEditorMode && "lg:grid-cols-[0.95fr_1.05fr]")}>
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
                    "rounded-md border border-slate-100 bg-slate-50 p-4 text-left transition hover:bg-white",
                    selectedActivityId === activity.id && "border-primary-200 bg-primary-50",
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="primary">{ACTIVITY_LEVEL_MAP[activity.level]}</Badge>
                    <Badge>{activity.club_records?.length || 0} 条记录</Badge>
                  </div>
                  <h3 className="mt-3 font-semibold text-slate-900">{activity.name}</h3>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500">{activity.description}</p>
                  <p className="mt-2 text-xs font-medium text-slate-400">
                    #{activity.id} · {formatDate(activity.starts_at || activity.created_at)}
                  </p>
                </button>
              ))
            ) : (
              <EmptyState title="暂无大型活动" />
            )}
          </div>

          {activityEditorMode && (
            <div className="h-fit rounded-md border border-slate-100 bg-white p-5">
              {activityEditorMode === "create" ? (
                <form onSubmit={createActivity} className="grid gap-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        新建活动
                      </p>
                      <h3 className="mt-1 font-bold text-slate-900">创建大型活动</h3>
                    </div>
                    <SecondaryButton type="button" onClick={closeActivityEditor}>
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
                      onChange={(event) => setActivityLevel(event.target.value as ActivityLevel)}
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
                      onChange={(event) => setActivityDescription(event.target.value)}
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
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        当前编辑
                      </p>
                      <h3 className="mt-1 truncate text-lg font-bold text-slate-900">
                        {selectedActivity.name}
                      </h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <SecondaryButton type="button" onClick={closeActivityEditor}>
                        <X size={16} /> 收起
                      </SecondaryButton>
                      <Link
                        to={`/activities/${selectedActivity.id}`}
                        className="inline-flex items-center justify-center rounded-md border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                      >
                        详情
                      </Link>
                      <DangerButton type="button" onClick={() => deleteActivity(selectedActivity)}>
                        <Trash2 size={16} /> 删除
                      </DangerButton>
                    </div>
                  </div>
                  <Field label="活动名称">
                    <input
                      className={inputClassName}
                      value={editActivityName}
                      onChange={(event) => setEditActivityName(event.target.value)}
                      required
                    />
                  </Field>
                  <Field label="活动层级">
                    <select
                      className={selectClassName}
                      value={editActivityLevel}
                      onChange={(event) =>
                        setEditActivityLevel(event.target.value as ActivityLevel)
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
                      onChange={(event) => setEditActivityDescription(event.target.value)}
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

function LoadingRows() {
  return (
    <>
      {[...Array(3)].map((_, index) => (
        <div
          key={index}
          className="h-32 animate-pulse rounded-md border border-slate-100 bg-slate-50"
        />
      ))}
    </>
  );
}

function ReadOnlyValue({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[44px] rounded-md bg-slate-50 px-3 py-2.5 text-sm font-semibold text-slate-700 shadow-[inset_0_0_0_1.5px_rgba(148,163,184,0.22)]">
      {children}
    </div>
  );
}

function ExternalLink({ href, children }: { href?: string | null; children: React.ReactNode }) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="rounded-md border border-slate-100 bg-white px-2.5 py-1 text-xs font-semibold text-primary-600 hover:text-primary-700"
    >
      {children}
    </a>
  );
}

function buildStarReviewBody(
  auditStatus: AuditStatus,
  finalContestScore: string,
  uniquenessApproved: string,
  growthStoryApproved: string,
): components["schemas"]["StarLevelApplicationReview"] {
  return {
    audit_status: auditStatus,
    final_contest_score: nullableNumber(finalContestScore),
    uniqueness_approved: selectValueToBoolean(uniquenessApproved),
    growth_story_approved: selectValueToBoolean(growthStoryApproved),
  };
}

function booleanToSelectValue(value?: boolean | null) {
  if (value == null) return "";
  return value ? "true" : "false";
}

function selectValueToBoolean(value: string) {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

function sortStarApplications(left: StarApplication, right: StarApplication) {
  if (left.audit_status !== right.audit_status) {
    if (!left.audit_status || left.audit_status === "pending") return -1;
    if (!right.audit_status || right.audit_status === "pending") return 1;
  }
  return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
}

function getStarPreviewScoreText(
  auditStatus: AuditStatus,
  isLoading: boolean,
  preview: StarReviewPreview | null,
) {
  if (auditStatus !== "approved") return "审核通过后计算";
  if (isLoading) return "计算中";
  return preview?.approved_score == null ? "待计算" : `${preview.approved_score} 分`;
}

function getStarPreviewLevelText(
  auditStatus: AuditStatus,
  isLoading: boolean,
  preview: StarReviewPreview | null,
) {
  if (auditStatus !== "approved") return "审核通过后计算";
  if (isLoading) return "计算中";
  return preview?.approved_level == null ? "待计算" : STAR_LEVEL_MAP[preview.approved_level];
}

function getAuditTone(status: AuditStatus) {
  if (status === "approved") return "green";
  if (status === "rejected") return "red";
  return "yellow";
}
