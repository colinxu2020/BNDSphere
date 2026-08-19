import React, { useEffect, useState } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Award,
  CalendarDays,
  Plus,
  RefreshCw,
} from "@/src/components/ui/Icons";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import { ClubProfileRequestSection } from "./clubWorkspace/ClubProfileRequestSection";
import { ClubRecordsSection } from "./clubWorkspace/ClubRecordsSection";
import { ClubHeaderSection, LoadErrorsSection, StarRatingSection } from "./clubWorkspace/displaySections";
import { EditorHeader, sameStringArray } from "./clubWorkspace/helpers";
import { useActionFeedback } from "../lib/useActionFeedback";
import { StarLevelCompact } from "../components/ui/StarLevel";
import { AUDIT_TONE } from "../lib/tones";
import type { components } from "../api/schema";
import { AUDIT_STATUS_MAP } from "../lib/labels";
import {
  formatDateTime,
  fromDateTimeLocalValue,
  nullableNumber,
  nullableText,
  toDateTimeLocalValue,
} from "../lib/format";
import {
  Badge,
  EmptyState,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  textareaClassName,
} from "../components/ui/AppPrimitives";
import { FileUploadField } from "../components/ui/FileUploadField";

type Club = components["schemas"]["ClubInfo"];
type ClubActivity = components["schemas"]["ClubActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type StarApplication = components["schemas"]["StarLevelApplicationInfo"];
type StarRating = components["schemas"]["StarRatingResponse"];

export function ClubWorkspace() {
  const { id } = useParams<{ id: string }>();
  const clubId = Number(id);

  const [club, setClub] = useState<Club | null>(null);
  const [activities, setActivities] = useState<ClubActivity[]>([]);
  const [generalActivities, setGeneralActivities] = useState<GeneralActivity[]>(
    [],
  );
  const [records, setRecords] = useState<ClubGeneralActivity[]>([]);
  const [starApplications, setStarApplications] = useState<StarApplication[]>(
    [],
  );
  const [starRating, setStarRating] = useState<StarRating | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadErrors, setLoadErrors] = useState<Record<string, unknown>>({});

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

  const [starAttachment, setStarAttachment] = useState("");
  const [starScore, setStarScore] = useState("");
  const [starStatement, setStarStatement] = useState("");
  const starCreateFeedback = useActionFeedback();
  const [isStarCreating, setIsStarCreating] = useState(false);
  const [starEditorMode, setStarEditorMode] = useState<
    "create" | "update" | null
  >(null);

  const [starUpdateId, setStarUpdateId] = useState("");
  const [starUpdateAttachment, setStarUpdateAttachment] = useState("");
  const [starUpdateScore, setStarUpdateScore] = useState("");
  const [starUpdateStatement, setStarUpdateStatement] = useState("");
  const starUpdateFeedback = useActionFeedback();
  const [isStarUpdating, setIsStarUpdating] = useState(false);

  const refresh = async () => {
    setIsLoading(true);
    const errors: Record<string, unknown> = {};

    const clubResponse = await client.GET("/api/v1/clubs/{club_id}", {
      params: { path: { club_id: clubId } },
    });
    if (clubResponse.error) {
      errors.club = clubResponse.error;
      setClub(null);
    } else {
      const nextClub = clubResponse.data || null;
      setClub(nextClub);
    }

    const activitiesResponse = await client.GET(
      "/api/v1/clubs/{club_id}/activities/",
      {
        params: { path: { club_id: clubId }, query: { size: 50 } },
      },
    );
    if (activitiesResponse.error) {
      errors.activities = activitiesResponse.error;
      setActivities([]);
    } else {
      setActivities(activitiesResponse.data?.items || []);
    }

    const generalActivitiesResponse = await client.GET(
      "/api/v1/general-activities/",
      {
        params: { query: { size: 100 } },
      },
    );
    if (generalActivitiesResponse.error) {
      errors.generalActivities = generalActivitiesResponse.error;
      setGeneralActivities([]);
    } else {
      setGeneralActivities(generalActivitiesResponse.data?.items || []);
    }

    const recordsResponse = await client.GET(
      "/api/v1/clubs/{club_id}/general-activities/",
      {
        params: { path: { club_id: clubId }, query: { size: 50 } },
      },
    );
    if (recordsResponse.error) {
      errors.records = recordsResponse.error;
      setRecords([]);
    } else {
      setRecords(recordsResponse.data?.items || []);
    }

    const applicationsResponse = await client.GET(
      "/api/v1/clubs/{club_id}/star-level/",
      {
        params: { path: { club_id: clubId }, query: { size: 50 } },
      },
    );
    if (applicationsResponse.error) {
      errors.starApplications = applicationsResponse.error;
      setStarApplications([]);
    } else {
      setStarApplications(applicationsResponse.data?.items || []);
    }

    const ratingResponse = await client.GET(
      "/api/v1/clubs/{club_id}/star-rating/",
      {
        params: { path: { club_id: clubId } },
      },
    );
    if (ratingResponse.error) {
      errors.starRating = ratingResponse.error;
      setStarRating(null);
    } else {
      setStarRating(ratingResponse.data || null);
    }

    setLoadErrors(errors);
    setIsLoading(false);
  };

  useEffect(() => {
    refresh().catch((error) => {
      setLoadErrors({ workspace: error });
      setIsLoading(false);
    });
  }, [clubId]);

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
      const { data, error } = await client.POST(
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
        refresh();
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
      const { data, error } = await client.POST(
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

  const submitStarCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarCreating(true);
    starCreateFeedback.clear();
    try {
      const { data, error } = await client.POST(
        "/api/v1/clubs/{club_id}/star-level/",
        {
          params: { path: { club_id: clubId } },
          body: {
            contest_attachment: nullableText(starAttachment),
            requested_contest_score: nullableNumber(starScore),
            uniqueness_statement: nullableText(starStatement),
          },
        },
      );
      if (error) {
        starCreateFeedback.fail(error);
      } else {
        starCreateFeedback.succeed(data);
        refresh();
      }
    } catch (error) {
      starCreateFeedback.fail(error);
    } finally {
      setIsStarCreating(false);
    }
  };

  const selectStarApplication = (application: StarApplication) => {
    setStarEditorMode("update");
    starUpdateFeedback.succeed(null);
    setStarUpdateId(String(application.id));
    setStarUpdateAttachment(application.contest_attachment || "");
    setStarUpdateScore(
      application.requested_contest_score == null
        ? ""
        : String(application.requested_contest_score),
    );
    setStarUpdateStatement(application.uniqueness_statement || "");
  };

  const openStarCreate = () => {
    setStarEditorMode("create");
    setStarUpdateId("");
    setStarAttachment("");
    setStarScore("");
    setStarStatement("");
    starCreateFeedback.clear();
  };

  const closeStarEditor = () => {
    setStarEditorMode(null);
    setStarUpdateId("");
  };

  const submitStarUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarUpdating(true);
    starUpdateFeedback.clear();
    try {
      const { data, error } = await client.PATCH(
        "/api/v1/star-level/{star_level_id}",
        {
          params: { path: { star_level_id: Number(starUpdateId) } },
          body: {
            contest_attachment: nullableText(starUpdateAttachment),
            requested_contest_score: nullableNumber(starUpdateScore),
            uniqueness_statement: nullableText(starUpdateStatement),
          },
        },
      );
      if (error) {
        starUpdateFeedback.fail(error);
      } else {
        starUpdateFeedback.succeed(data);
        refresh();
      }
    } catch (error) {
      starUpdateFeedback.fail(error);
    } finally {
      setIsStarUpdating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex flex-col gap-8"
    >
      <Link
        to={`/club/${clubId}`}
        className="inline-flex items-center gap-2 text-content-muted hover:text-content font-medium w-fit transition-colors"
      >
        <ArrowLeft size={18} /> 返回社团
      </Link>

      <PageHeader density="compact"
        eyebrow="Workspace"
        title={club?.name || `社团 #${clubId} 工作台`}
        action={
          <SecondaryButton onClick={() => refresh()} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {isLoading ? (
        <div className="animate-pulse bg-surface rounded-md h-72 border border-edge-subtle" />
      ) : (
        <>
            {Object.keys(loadErrors).length > 0 && (
              <LoadErrorsSection errors={loadErrors} />
            )}

            {club && <ClubHeaderSection club={club} />}

            <StarRatingSection starRating={starRating} />

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

          <ClubRecordsSection
            clubId={clubId}
            generalActivities={generalActivities}
            records={records}
            onSubmitted={refresh}
          />

          <Surface density="compact">
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <SectionTitle density="compact"
                className="mb-0"
                icon={<Award size={20} />}
                title="星级申请"
              />
              <SecondaryButton
                type="button"
                onClick={openStarCreate}
                className="w-full whitespace-nowrap sm:w-auto"
              >
                <Plus size={16} /> 新建星级申请
              </SecondaryButton>
            </div>
            <div
              className={`grid gap-6 ${
                starEditorMode ? "lg:grid-cols-[0.95fr_1.05fr]" : "grid-cols-1"
              }`}
            >
              <div className="grid gap-3">
                {starApplications.length ? (
                  starApplications.map((application) => (
                    <button
                      type="button"
                      key={application.id}
                      onClick={() => selectStarApplication(application)}
                      className={`rounded-md border p-5 text-left transition hover:bg-surface ${
                        starUpdateId === String(application.id)
                          ? "border-tone-brand-edge bg-brand-subtle"
                          : "border-edge-subtle bg-surface-sunken"
                      }`}
                    >
                      <div className="flex flex-wrap gap-2">
                        <Badge
                          tone={AUDIT_TONE[application.audit_status ?? "pending"]}
                        >
                          {application.audit_status
                            ? AUDIT_STATUS_MAP[application.audit_status]
                            : "未审核"}
                        </Badge>
                        {application.approved_level && (
                          <StarLevelCompact level={application.approved_level} />
                        )}
                      </div>
                      <h3 className="mt-3 font-semibold text-content">
                        申请 #{application.id}
                      </h3>
                      <p className="mt-1 text-sm text-content-muted">
                        申请竞赛分{" "}
                        {application.requested_contest_score ?? "未填"}
                        ，核定分 {application.approved_score ?? "未定"}
                      </p>
                    </button>
                  ))
                ) : (
                  <EmptyState title="暂无星级申请" />
                )}
              </div>

              {starEditorMode && (
                <div className="rounded-md border border-edge-subtle bg-surface p-5">
                  {starEditorMode === "create" ? (
                    <form
                      onSubmit={submitStarCreate}
                      className="flex flex-col gap-4"
                    >
                      <EditorHeader
                        eyebrow="新建申请"
                        title="创建星级申请"
                        onClose={closeStarEditor}
                      />
                      <FileUploadField
                        label="竞赛附件"
                        scene="application_file"
                        value={starAttachment}
                        onChange={setStarAttachment}
                        hint="上传后作为星级申请附件。"
                      />
                      <Field label="申请竞赛分">
                        <input
                          className={inputClassName}
                          type="number"
                          value={starScore}
                          onChange={(event) => setStarScore(event.target.value)}
                        />
                      </Field>
                      <Field label="独特性说明">
                        <textarea
                          className={textareaClassName}
                          value={starStatement}
                          onChange={(event) =>
                            setStarStatement(event.target.value)
                          }
                        />
                      </Field>
                      <StatusMessage
                        value={starCreateFeedback.message}
                        tone={starCreateFeedback.tone}
                      />
                      <PrimaryButton type="submit" loading={isStarCreating}>
                        提交星级申请
                      </PrimaryButton>
                    </form>
                  ) : starUpdateId ? (
                    <form
                      onSubmit={submitStarUpdate}
                      className="flex flex-col gap-4"
                    >
                      <EditorHeader
                        eyebrow="当前编辑"
                        title={`星级申请 #${starUpdateId}`}
                        onClose={closeStarEditor}
                      />
                      <FileUploadField
                        label="竞赛附件"
                        scene="application_file"
                        value={starUpdateAttachment}
                        onChange={setStarUpdateAttachment}
                        hint="上传后替换星级申请附件。"
                      />
                      <Field label="申请竞赛分">
                        <input
                          className={inputClassName}
                          type="number"
                          value={starUpdateScore}
                          onChange={(event) =>
                            setStarUpdateScore(event.target.value)
                          }
                        />
                      </Field>
                      <Field label="独特性说明">
                        <textarea
                          className={textareaClassName}
                          value={starUpdateStatement}
                          onChange={(event) =>
                            setStarUpdateStatement(event.target.value)
                          }
                        />
                      </Field>
                      <PrimaryButton type="submit" loading={isStarUpdating}>
                        更新申请
                      </PrimaryButton>
                      <StatusMessage
                        value={starUpdateFeedback.message}
                        tone={starUpdateFeedback.tone}
                      />
                    </form>
                  ) : (
                    <EmptyState title="请选择星级申请" />
                  )}
                </div>
              )}
            </div>
          </Surface>

          <ClubProfileRequestSection
            clubId={clubId}
            initialSummary={club?.summary || ""}
            initialDescription={club?.description || ""}
            initialLogo={club?.logo_uri || ""}
          />
        </>
      )}
    </motion.div>
  );
}
