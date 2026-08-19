import { useMemo, useState } from "react";
import type React from "react";
import {
  CalendarDays,
  Check,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  X,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import {
  Badge,
  DangerButton,
  EmptyState,
  Field,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  Surface,
  inputClassName,
  selectClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { ACTIVITY_LEVEL_MAP, ACTIVITY_LEVEL_OPTIONS } from "../../lib/labels";
import { formatDate, nullableText } from "../../lib/format";
import { cn } from "../../lib/utils";
import type { useActionFeedback } from "../../lib/useActionFeedback";
import { LoadingRows } from "./shared";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ActivityLevel = components["schemas"]["GeneralActivityLevelEnum"];

/**
 * 大型活动 — the federation's own general activities, and the editor that creates,
 * edits and deletes them.
 *
 * The last of Federation's four concerns to move out. Every piece of editor state
 * here was already local to it; the activity list, the loading flag, the feedback
 * hook and a refresh callback are the shared values, and they arrive as props.
 */
export function ActivityEditorPanel({
  activities,
  isLoading,
  feedback,
  onChanged,
}: {
  activities: GeneralActivity[];
  isLoading: boolean;
  feedback: ReturnType<typeof useActionFeedback>;
  onChanged: () => void;
}) {
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

  const selectedActivity = useMemo(
    () => activities.find((activity) => activity.id === selectedActivityId),
    [activities, selectedActivityId],
  );

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
        onChanged();
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
        onChanged();
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
        onChanged();
      }
    } catch (error) {
      feedback.report(error, "");
    }
  };

  return (
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
  );
}
