import { useState } from "react";
import { CalendarDays, Plus } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import {
  EmptyState,
  Field,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { FileUploadField } from "../../components/ui/FileUploadField";
import {
  formatDateTime,
  fromDateTimeLocalValue,
  nullableText,
  toDateTimeLocalValue,
} from "../../lib/format";
import { useActionFeedback } from "../../lib/useActionFeedback";
import { EditorHeader, sameStringArray } from "./helpers";

type ClubActivity = components["schemas"]["ClubActivityInfo"];

/**
 * 社团活动申请 — a club's own activities, and the editor that requests creating or
 * amending one. Both go through moderation, which is why this is a request form rather
 * than a direct edit.
 *
 * The last concern to leave ClubWorkspace. It has one derived value — which activity is
 * selected for amendment — and it moves with the state group and the three handlers,
 * per the rule the earlier back-out established. Two feedback hooks, because create and
 * amend report separately.
 */
export function ClubActivitiesSection({
  clubId,
  activities,
  onChanged,
}: {
  clubId: number;
  activities: ClubActivity[];
  onChanged: () => void;
}) {
  const [activityName, setActivityName] = useState("");
  const [activityDescription, setActivityDescription] = useState("");
  const [activityStart, setActivityStart] = useState("");
  const [activityEnd, setActivityEnd] = useState("");
  const [activityLocation, setActivityLocation] = useState("");
  const activityCreateFeedback = useActionFeedback();
  const [isActivityCreating, setIsActivityCreating] = useState(false);
  const [activityEditorMode, setActivityEditorMode] = useState<
    "create" | "update" | null
  >(null);

  const [updateActivityId, setUpdateActivityId] = useState("");
  const [updateActivityName, setUpdateActivityName] = useState("");
  const [updateActivityDescription, setUpdateActivityDescription] =
    useState("");
  const [updateActivityStart, setUpdateActivityStart] = useState("");
  const [updateActivityEnd, setUpdateActivityEnd] = useState("");
  const [updateActivityLocation, setUpdateActivityLocation] = useState("");
  const [updateActivityPictureUrls, setUpdateActivityPictureUrls] = useState<
    string[]
  >([]);
  const activityUpdateFeedback = useActionFeedback();
  const [isActivityUpdating, setIsActivityUpdating] = useState(false);

  const selectedUpdateActivity = activities.find(
    (activityItem) => String(activityItem.id) === updateActivityId,
  );

  const selectActivityForUpdate = (activityItem: ClubActivity) => {
    setActivityEditorMode("update");
    setUpdateActivityId(String(activityItem.id));
    setUpdateActivityName(activityItem.name);
    setUpdateActivityDescription(activityItem.description);
    setUpdateActivityStart(toDateTimeLocalValue(activityItem.start_time));
    setUpdateActivityEnd(toDateTimeLocalValue(activityItem.end_time));
    setUpdateActivityLocation(activityItem.location);
    setUpdateActivityPictureUrls(activityItem.picture_urls || []);
    activityUpdateFeedback.clear();
  };

  const openActivityCreate = () => {
    setActivityEditorMode("create");
    setUpdateActivityId("");
    setActivityName("");
    setActivityDescription("");
    setActivityStart("");
    setActivityEnd("");
    setActivityLocation("");
    activityCreateFeedback.clear();
  };

  const closeActivityEditor = () => {
    setActivityEditorMode(null);
    setUpdateActivityId("");
  };

  const submitActivityCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsActivityCreating(true);
    activityCreateFeedback.clear();
    try {
      const { error } = await client.POST(
        "/api/v1/clubs/{club_id}/activities/create-requests",
        {
          params: { path: { club_id: clubId } },
          body: {
            name: activityName,
            description: activityDescription,
            start_time: fromDateTimeLocalValue(activityStart),
            end_time: fromDateTimeLocalValue(activityEnd),
            location: activityLocation,
          },
        },
      );
      if (error) {
        activityCreateFeedback.fail(error);
      } else {
        activityCreateFeedback.succeed("活动创建申请已提交");
        onChanged();
      }
    } catch (error) {
      activityCreateFeedback.fail(error);
    } finally {
      setIsActivityCreating(false);
    }
  };

  const submitActivityUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedUpdateActivity) {
      activityUpdateFeedback.fail("请先选择一个社团活动");
      return;
    }

    setIsActivityUpdating(true);
    activityUpdateFeedback.clear();
    const originalStart = toDateTimeLocalValue(
      selectedUpdateActivity.start_time,
    );
    const originalEnd = toDateTimeLocalValue(selectedUpdateActivity.end_time);
    const originalPictures = selectedUpdateActivity.picture_urls || [];
    const body: components["schemas"]["ClubActivityUpdateRequestCreatePublic"] =
      {};

    if (updateActivityName.trim() !== selectedUpdateActivity.name) {
      body.name = nullableText(updateActivityName);
    }
    if (
      updateActivityDescription.trim() !== selectedUpdateActivity.description
    ) {
      body.description = nullableText(updateActivityDescription);
    }
    if (updateActivityStart && updateActivityStart !== originalStart) {
      body.start_time = fromDateTimeLocalValue(updateActivityStart);
    }
    if (updateActivityEnd && updateActivityEnd !== originalEnd) {
      body.end_time = fromDateTimeLocalValue(updateActivityEnd);
    }
    if (updateActivityLocation.trim() !== selectedUpdateActivity.location) {
      body.location = nullableText(updateActivityLocation);
    }
    if (!sameStringArray(updateActivityPictureUrls, originalPictures)) {
      body.picture_urls = updateActivityPictureUrls;
    }

    try {
      const { error } = await client.POST(
        "/api/v1/clubs/{club_id}/activities/update-requests/{activity_id}",
        {
          params: {
            path: { club_id: clubId, activity_id: selectedUpdateActivity.id },
          },
          body,
        },
      );
      if (error) {
        activityUpdateFeedback.fail(error);
      } else {
        activityUpdateFeedback.succeed("活动修改申请已提交");
      }
    } catch (error) {
      activityUpdateFeedback.fail(error);
    } finally {
      setIsActivityUpdating(false);
    }
  };

  return (
    <Surface density="compact">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle density="compact"
          className="mb-0"
          icon={<CalendarDays size={20} />}
          title="社团活动申请"
        />
        <SecondaryButton
          type="button"
          onClick={openActivityCreate}
          className="w-full whitespace-nowrap sm:w-auto"
        >
          <Plus size={16} /> 新建社团活动申请
        </SecondaryButton>
      </div>
      <div
        className={`grid gap-6 ${
          activityEditorMode
            ? "lg:grid-cols-[0.95fr_1.05fr]"
            : "grid-cols-1"
        }`}
      >
        <div className="grid gap-3">
          {activities.length ? (
            activities.map((activityItem) => (
              <button
                key={activityItem.id}
                type="button"
                onClick={() => selectActivityForUpdate(activityItem)}
                className={`rounded-md border p-4 text-left transition hover:bg-surface ${
                  updateActivityId === String(activityItem.id)
                    ? "border-tone-brand-edge bg-brand-subtle"
                    : "border-edge-subtle bg-surface-sunken"
                }`}
              >
                <h3 className="font-semibold text-content">
                  {activityItem.name}
                </h3>
                <p className="mt-1 line-clamp-2 text-sm text-content-muted">
                  {activityItem.description}
                </p>
                <p className="mt-2 text-xs font-medium text-content-subtle">
                  #{activityItem.id} ·{" "}
                  {formatDateTime(activityItem.start_time)} ·{" "}
                  {activityItem.location}
                </p>
              </button>
            ))
          ) : (
            <EmptyState title="暂无社团活动" />
          )}
        </div>

        {activityEditorMode && (
          <div className="rounded-md border border-edge-subtle bg-surface p-5">
            {activityEditorMode === "create" ? (
              <form
                onSubmit={submitActivityCreate}
                className="flex flex-col gap-4"
              >
                <EditorHeader
                  eyebrow="新建申请"
                  title="创建社团活动"
                  onClose={closeActivityEditor}
                />
                <Field label="活动名称">
                  <input
                    className={inputClassName}
                    value={activityName}
                    onChange={(event) =>
                      setActivityName(event.target.value)
                    }
                    required
                  />
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
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <Field label="开始时间">
                    <input
                      className={inputClassName}
                      type="datetime-local"
                      value={activityStart}
                      onChange={(event) =>
                        setActivityStart(event.target.value)
                      }
                      required
                    />
                  </Field>
                  <Field label="结束时间">
                    <input
                      className={inputClassName}
                      type="datetime-local"
                      value={activityEnd}
                      onChange={(event) =>
                        setActivityEnd(event.target.value)
                      }
                      required
                    />
                  </Field>
                </div>
                <Field label="地点">
                  <input
                    className={inputClassName}
                    value={activityLocation}
                    onChange={(event) =>
                      setActivityLocation(event.target.value)
                    }
                    required
                  />
                </Field>
                <StatusMessage
                  value={activityCreateFeedback.message}
                  tone={activityCreateFeedback.tone}
                />
                <PrimaryButton type="submit" loading={isActivityCreating}>
                  提交活动申请
                </PrimaryButton>
              </form>
            ) : selectedUpdateActivity ? (
              <form
                onSubmit={submitActivityUpdate}
                className="flex flex-col gap-4"
              >
                <EditorHeader
                  eyebrow="当前编辑"
                  title={selectedUpdateActivity.name}
                  onClose={closeActivityEditor}
                />
                <Field label="新名称">
                  <input
                    className={inputClassName}
                    value={updateActivityName}
                    onChange={(event) =>
                      setUpdateActivityName(event.target.value)
                    }
                  />
                </Field>
                <Field label="新描述">
                  <textarea
                    className={textareaClassName}
                    value={updateActivityDescription}
                    onChange={(event) =>
                      setUpdateActivityDescription(event.target.value)
                    }
                  />
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="新开始时间">
                    <input
                      className={inputClassName}
                      type="datetime-local"
                      value={updateActivityStart}
                      onChange={(event) =>
                        setUpdateActivityStart(event.target.value)
                      }
                    />
                  </Field>
                  <Field label="新结束时间">
                    <input
                      className={inputClassName}
                      type="datetime-local"
                      value={updateActivityEnd}
                      onChange={(event) =>
                        setUpdateActivityEnd(event.target.value)
                      }
                    />
                  </Field>
                </div>
                <Field label="新地点">
                  <input
                    className={inputClassName}
                    value={updateActivityLocation}
                    onChange={(event) =>
                      setUpdateActivityLocation(event.target.value)
                    }
                  />
                </Field>
                <FileUploadField
                  label="活动图片"
                  scene="activity_poster"
                  values={updateActivityPictureUrls}
                  onValuesChange={setUpdateActivityPictureUrls}
                  multiple
                  accept="image/*"
                />
                <StatusMessage
                  value={activityUpdateFeedback.message}
                  tone={activityUpdateFeedback.tone}
                />
                <PrimaryButton type="submit" loading={isActivityUpdating}>
                  提交修改申请
                </PrimaryButton>
              </form>
            ) : (
              <EmptyState title="请选择社团活动" />
            )}
          </div>
        )}
      </div>
    </Surface>
  );
}
