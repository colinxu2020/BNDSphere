import React, { useEffect, useState } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Award,
  CalendarDays,
  Check,
  FileCheck2,
  Hash,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
  X,
} from "@/src/components/ui/Icons";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  AUDIT_STATUS_MAP,
  CATEGORY_MAP,
  MEMBERSHIP_MAP,
  PARTICIPATION_MAP,
  PARTICIPATION_OPTIONS,
  STAR_LEVEL_MAP,
} from "../lib/labels";
import {
  formatDateTime,
  fromDateTimeLocalValue,
  nullableNumber,
  nullableText,
  stringifyBackendValue,
  toDateTimeLocalValue,
  toNumberOrZero,
} from "../lib/format";
import {
  Badge,
  DangerButton,
  EmptyState,
  Field,
  InlineError,
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
import { FileUploadField } from "../components/ui/FileUploadField";

type Club = components["schemas"]["ClubInfo"];
type ClubMember = components["schemas"]["ClubMemberInfo"];
type ClubMemberAssignableRole = components["schemas"]["ClubMemberAssignableRoleEnum"];
type ClubMembershipRequest = components["schemas"]["ClubMembershipRequestInfo"];
type ClubActivity = components["schemas"]["ClubActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type StarApplication = components["schemas"]["StarLevelApplicationInfo"];
type StarRating = components["schemas"]["StarRatingResponse"];
type ParticipationType = components["schemas"]["ParticipationTypeEnum"];
type UserInfo = components["schemas"]["UserInfo"];

export function ClubWorkspace() {
  const { id } = useParams<{ id: string }>();
  const clubId = Number(id);

  const [club, setClub] = useState<Club | null>(null);
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);
  const [membershipRequests, setMembershipRequests] = useState<ClubMembershipRequest[]>([]);
  const [membershipApplicants, setMembershipApplicants] = useState<Record<number, UserInfo>>({});
  const [activities, setActivities] = useState<ClubActivity[]>([]);
  const [generalActivities, setGeneralActivities] = useState<GeneralActivity[]>([]);
  const [records, setRecords] = useState<ClubGeneralActivity[]>([]);
  const [starApplications, setStarApplications] = useState<StarApplication[]>([]);
  const [starRating, setStarRating] = useState<StarRating | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadErrors, setLoadErrors] = useState<Record<string, unknown>>({});

  const [memberMessage, setMemberMessage] = useState<unknown>(null);
  const [memberTone, setMemberTone] = useState<"error" | "success">("error");
  const [memberSubmittingId, setMemberSubmittingId] = useState<number | null>(null);
  const [pendingTransfer, setPendingTransfer] = useState<ClubMember | null>(null);
  const [transferCountdown, setTransferCountdown] = useState(5);
  const [membershipRequestMessage, setMembershipRequestMessage] = useState<unknown>(null);
  const [membershipRequestTone, setMembershipRequestTone] = useState<"error" | "success">("error");
  const [membershipRequestSubmittingId, setMembershipRequestSubmittingId] = useState<number | null>(
    null,
  );

  const [clubSummary, setClubSummary] = useState("");
  const [clubDescription, setClubDescription] = useState("");
  const [clubLogo, setClubLogo] = useState("");
  const [clubMessage, setClubMessage] = useState<unknown>(null);
  const [clubTone, setClubTone] = useState<"error" | "success">("error");
  const [isClubSubmitting, setIsClubSubmitting] = useState(false);

  const [activityName, setActivityName] = useState("");
  const [activityDescription, setActivityDescription] = useState("");
  const [activityStart, setActivityStart] = useState("");
  const [activityEnd, setActivityEnd] = useState("");
  const [activityLocation, setActivityLocation] = useState("");
  const [activityCreateMessage, setActivityCreateMessage] = useState<unknown>(null);
  const [activityCreateTone, setActivityCreateTone] = useState<"error" | "success">("error");
  const [isActivityCreating, setIsActivityCreating] = useState(false);
  const [activityEditorMode, setActivityEditorMode] = useState<"create" | "update" | null>(null);

  const [updateActivityId, setUpdateActivityId] = useState("");
  const [updateActivityName, setUpdateActivityName] = useState("");
  const [updateActivityDescription, setUpdateActivityDescription] = useState("");
  const [updateActivityStart, setUpdateActivityStart] = useState("");
  const [updateActivityEnd, setUpdateActivityEnd] = useState("");
  const [updateActivityLocation, setUpdateActivityLocation] = useState("");
  const [updateActivityPictureUrls, setUpdateActivityPictureUrls] = useState<string[]>([]);
  const [activityUpdateMessage, setActivityUpdateMessage] = useState<unknown>(null);
  const [activityUpdateTone, setActivityUpdateTone] = useState<"error" | "success">("error");
  const [isActivityUpdating, setIsActivityUpdating] = useState(false);

  const [generalActivityId, setGeneralActivityId] = useState("");
  const [participationType, setParticipationType] = useState<ParticipationType>("participate_only");
  const [requestedScore, setRequestedScore] = useState("");
  const [proofFileUrls, setProofFileUrls] = useState<string[]>([]);
  const [recordMessage, setRecordMessage] = useState<unknown>(null);
  const [recordTone, setRecordTone] = useState<"error" | "success">("error");
  const [isRecordSubmitting, setIsRecordSubmitting] = useState(false);

  const [starAttachment, setStarAttachment] = useState("");
  const [starScore, setStarScore] = useState("");
  const [starStatement, setStarStatement] = useState("");
  const [starCreateMessage, setStarCreateMessage] = useState<unknown>(null);
  const [starCreateTone, setStarCreateTone] = useState<"error" | "success">("error");
  const [isStarCreating, setIsStarCreating] = useState(false);
  const [starEditorMode, setStarEditorMode] = useState<"create" | "update" | null>(null);

  const [starUpdateId, setStarUpdateId] = useState("");
  const [starUpdateAttachment, setStarUpdateAttachment] = useState("");
  const [starUpdateScore, setStarUpdateScore] = useState("");
  const [starUpdateStatement, setStarUpdateStatement] = useState("");
  const [starUpdateMessage, setStarUpdateMessage] = useState<unknown>(null);
  const [starUpdateTone, setStarUpdateTone] = useState<"error" | "success">("error");
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
      if (nextClub) {
        setClubSummary(nextClub.summary || "");
        setClubDescription(nextClub.description || "");
        setClubLogo(nextClub.logo_uri || "");
      }
    }

    const userResponse = await client.GET("/api/v1/users/me");
    if (userResponse.error) {
      errors.user = userResponse.error;
      setCurrentUser(null);
    } else {
      setCurrentUser(userResponse.data || null);
    }

    const membershipRequestsResponse = await client.GET(
      "/api/v1/clubs/{club_id}/membership-requests",
      { params: { path: { club_id: clubId }, query: { size: 100 } } },
    );
    if (membershipRequestsResponse.error) {
      errors.membershipRequests = membershipRequestsResponse.error;
      setMembershipRequests([]);
      setMembershipApplicants({});
    } else {
      const nextRequests = membershipRequestsResponse.data?.items || [];
      setMembershipRequests(nextRequests);
      const applicantResults = await Promise.all(
        nextRequests.map(async (request) => {
          const response = await client.GET("/api/v1/users/{user_id}", {
            params: { path: { user_id: request.applicant_id } },
          });
          return response.data ? ([request.applicant_id, response.data] as const) : null;
        }),
      );
      setMembershipApplicants(
        Object.fromEntries(applicantResults.filter((result) => result !== null)),
      );
    }

    const activitiesResponse = await client.GET("/api/v1/clubs/{club_id}/activities/", {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (activitiesResponse.error) {
      errors.activities = activitiesResponse.error;
      setActivities([]);
    } else {
      setActivities(activitiesResponse.data?.items || []);
    }

    const generalActivitiesResponse = await client.GET("/api/v1/general-activities/", {
      params: { query: { size: 100 } },
    });
    if (generalActivitiesResponse.error) {
      errors.generalActivities = generalActivitiesResponse.error;
      setGeneralActivities([]);
    } else {
      setGeneralActivities(generalActivitiesResponse.data?.items || []);
    }

    const recordsResponse = await client.GET("/api/v1/clubs/{club_id}/general-activities/", {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (recordsResponse.error) {
      errors.records = recordsResponse.error;
      setRecords([]);
    } else {
      setRecords(recordsResponse.data?.items || []);
    }

    const applicationsResponse = await client.GET("/api/v1/clubs/{club_id}/star-level/", {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (applicationsResponse.error) {
      errors.starApplications = applicationsResponse.error;
      setStarApplications([]);
    } else {
      setStarApplications(applicationsResponse.data?.items || []);
    }

    const ratingResponse = await client.GET("/api/v1/clubs/{club_id}/star-rating/", {
      params: { path: { club_id: clubId } },
    });
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
    // Refresh when the routed club changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clubId]);

  useEffect(() => {
    if (!pendingTransfer) return;

    const startedAt = Date.now();
    setTransferCountdown(5);
    const timer = window.setInterval(() => {
      const remaining = Math.max(0, Math.ceil((5000 - (Date.now() - startedAt)) / 1000));
      setTransferCountdown(remaining);
      if (remaining === 0) window.clearInterval(timer);
    }, 200);

    return () => window.clearInterval(timer);
  }, [pendingTransfer]);

  const selectedUpdateActivity = activities.find(
    (activityItem) => String(activityItem.id) === updateActivityId,
  );
  const selectedGeneralActivity = generalActivities.find(
    (activityItem) => String(activityItem.id) === generalActivityId,
  );
  const selectedGeneralRecord =
    records.find((record) => String(record.activity_id) === generalActivityId) || null;
  const currentMembership = club?.members.find(
    (member) => member.user_id === currentUser?.id,
  )?.membership;
  const isPresident = currentMembership === "president";
  const canVerifyMemberships =
    currentMembership === "president" || currentMembership === "vice_president";
  const activeMembers = (club?.members || [])
    .filter((member) => ["member", "president", "vice_president"].includes(member.membership))
    .sort((left, right) => membershipOrder(left.membership) - membershipOrder(right.membership));

  const selectActivityForUpdate = (activityItem: ClubActivity) => {
    setActivityEditorMode("update");
    setUpdateActivityId(String(activityItem.id));
    setUpdateActivityName(activityItem.name);
    setUpdateActivityDescription(activityItem.description);
    setUpdateActivityStart(toDateTimeLocalValue(activityItem.start_time));
    setUpdateActivityEnd(toDateTimeLocalValue(activityItem.end_time));
    setUpdateActivityLocation(activityItem.location);
    setUpdateActivityPictureUrls(activityItem.picture_urls || []);
    setActivityUpdateMessage(null);
  };

  const openActivityCreate = () => {
    setActivityEditorMode("create");
    setUpdateActivityId("");
    setActivityName("");
    setActivityDescription("");
    setActivityStart("");
    setActivityEnd("");
    setActivityLocation("");
    setActivityCreateMessage(null);
  };

  const closeActivityEditor = () => {
    setActivityEditorMode(null);
    setUpdateActivityId("");
  };

  const selectGeneralActivityForRecord = (activityItem: GeneralActivity) => {
    const existingRecord = records.find((record) => record.activity_id === activityItem.id);
    setGeneralActivityId(String(activityItem.id));
    if (existingRecord) {
      setParticipationType(existingRecord.participation_type);
      setRequestedScore(String(existingRecord.requested_score));
      setProofFileUrls(existingRecord.proof_files || []);
    } else {
      setParticipationType("participate_only");
      setRequestedScore("");
      setProofFileUrls([]);
    }
    setRecordMessage(null);
  };

  const submitClubUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsClubSubmitting(true);
    setClubMessage(null);
    try {
      const { data, error } = await client.POST("/api/v1/clubs/{club_id}/update-requests", {
        params: { path: { club_id: clubId } },
        body: {
          summary: nullableText(clubSummary),
          description: nullableText(clubDescription),
          logo_uri: nullableText(clubLogo),
        },
      });
      if (error) {
        setClubTone("error");
        setClubMessage(error);
      } else {
        setClubTone("success");
        setClubMessage(data);
      }
    } catch (error) {
      setClubTone("error");
      setClubMessage(error);
    } finally {
      setIsClubSubmitting(false);
    }
  };

  const submitActivityCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsActivityCreating(true);
    setActivityCreateMessage(null);
    try {
      const { error } = await client.POST("/api/v1/clubs/{club_id}/activities/create-requests", {
        params: { path: { club_id: clubId } },
        body: {
          name: activityName,
          description: activityDescription,
          start_time: fromDateTimeLocalValue(activityStart),
          end_time: fromDateTimeLocalValue(activityEnd),
          location: activityLocation,
        },
      });
      if (error) {
        setActivityCreateTone("error");
        setActivityCreateMessage(error);
      } else {
        setActivityCreateTone("success");
        setActivityCreateMessage("活动创建申请已提交");
        refresh();
      }
    } catch (error) {
      setActivityCreateTone("error");
      setActivityCreateMessage(error);
    } finally {
      setIsActivityCreating(false);
    }
  };

  const submitActivityUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedUpdateActivity) {
      setActivityUpdateTone("error");
      setActivityUpdateMessage("请先选择一个社团活动");
      return;
    }

    setIsActivityUpdating(true);
    setActivityUpdateMessage(null);
    const originalStart = toDateTimeLocalValue(selectedUpdateActivity.start_time);
    const originalEnd = toDateTimeLocalValue(selectedUpdateActivity.end_time);
    const originalPictures = selectedUpdateActivity.picture_urls || [];
    const body: components["schemas"]["ClubActivityUpdateRequestCreatePublic"] = {};

    if (updateActivityName.trim() !== selectedUpdateActivity.name) {
      body.name = nullableText(updateActivityName);
    }
    if (updateActivityDescription.trim() !== selectedUpdateActivity.description) {
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
        setActivityUpdateTone("error");
        setActivityUpdateMessage(error);
      } else {
        setActivityUpdateTone("success");
        setActivityUpdateMessage("活动修改申请已提交");
      }
    } catch (error) {
      setActivityUpdateTone("error");
      setActivityUpdateMessage(error);
    } finally {
      setIsActivityUpdating(false);
    }
  };

  const submitRecord = async (mode: "create" | "update") => {
    setIsRecordSubmitting(true);
    setRecordMessage(null);
    const payload = {
      activity_id: toNumberOrZero(generalActivityId),
      participation_type: participationType,
      proof_files: proofFileUrls,
      requested_score: toNumberOrZero(requestedScore),
    };

    try {
      const request =
        mode === "create"
          ? client.POST("/api/v1/clubs/{club_id}/general-activities/", {
              params: { path: { club_id: clubId } },
              body: payload,
            })
          : client.PATCH("/api/v1/clubs/{club_id}/general-activities/", {
              params: { path: { club_id: clubId } },
              body: payload,
            });

      const { data, error } = await request;
      if (error) {
        setRecordTone("error");
        setRecordMessage(error);
      } else {
        setRecordTone("success");
        setRecordMessage(data);
        refresh();
      }
    } catch (error) {
      setRecordTone("error");
      setRecordMessage(error);
    } finally {
      setIsRecordSubmitting(false);
    }
  };

  const submitStarCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarCreating(true);
    setStarCreateMessage(null);
    try {
      const { data, error } = await client.POST("/api/v1/clubs/{club_id}/star-level/", {
        params: { path: { club_id: clubId } },
        body: {
          contest_attachment: nullableText(starAttachment),
          requested_contest_score: nullableNumber(starScore),
          uniqueness_statement: nullableText(starStatement),
        },
      });
      if (error) {
        setStarCreateTone("error");
        setStarCreateMessage(error);
      } else {
        setStarCreateTone("success");
        setStarCreateMessage(data);
        refresh();
      }
    } catch (error) {
      setStarCreateTone("error");
      setStarCreateMessage(error);
    } finally {
      setIsStarCreating(false);
    }
  };

  const selectStarApplication = (application: StarApplication) => {
    setStarEditorMode("update");
    setStarUpdateTone("success");
    setStarUpdateMessage(null);
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
    setStarCreateMessage(null);
  };

  const closeStarEditor = () => {
    setStarEditorMode(null);
    setStarUpdateId("");
  };

  const submitStarUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarUpdating(true);
    setStarUpdateMessage(null);
    try {
      const { data, error } = await client.PATCH("/api/v1/star-level/{star_level_id}", {
        params: { path: { star_level_id: Number(starUpdateId) } },
        body: {
          contest_attachment: nullableText(starUpdateAttachment),
          requested_contest_score: nullableNumber(starUpdateScore),
          uniqueness_statement: nullableText(starUpdateStatement),
        },
      });
      if (error) {
        setStarUpdateTone("error");
        setStarUpdateMessage(error);
      } else {
        setStarUpdateTone("success");
        setStarUpdateMessage(data);
        refresh();
      }
    } catch (error) {
      setStarUpdateTone("error");
      setStarUpdateMessage(error);
    } finally {
      setIsStarUpdating(false);
    }
  };

  const verifyMembershipRequest = async (
    request: ClubMembershipRequest,
    verificationStatus: "approved" | "rejected",
  ) => {
    setMembershipRequestSubmittingId(request.id);
    setMembershipRequestMessage(null);
    try {
      const { error } = await client.PATCH(
        "/api/v1/clubs/{club_id}/membership-requests/{request_id}",
        {
          params: { path: { club_id: clubId, request_id: request.id } },
          body: { verification_status: verificationStatus },
        },
      );
      if (error) {
        setMembershipRequestTone("error");
        setMembershipRequestMessage(error);
      } else {
        const applicantName =
          membershipApplicants[request.applicant_id]?.username || `用户 #${request.applicant_id}`;
        setMembershipRequestTone("success");
        setMembershipRequestMessage(
          verificationStatus === "approved"
            ? `已批准 ${applicantName} 加入社团`
            : `已驳回 ${applicantName} 的入社申请`,
        );
        await refresh();
      }
    } catch (error) {
      setMembershipRequestTone("error");
      setMembershipRequestMessage(error);
    } finally {
      setMembershipRequestSubmittingId(null);
    }
  };

  const changeMemberRole = async (member: ClubMember, membership: ClubMemberAssignableRole) => {
    setMemberSubmittingId(member.user_id);
    setMemberMessage(null);
    try {
      const { error } = await client.PATCH("/api/v1/clubs/{club_id}/members/{user_id}", {
        params: { path: { club_id: clubId, user_id: member.user_id } },
        body: { membership },
      });
      if (error) {
        setMemberTone("error");
        setMemberMessage(error);
        return false;
      }

      setMemberTone("success");
      setMemberMessage(
        membership === "president"
          ? `已将社团交接给 ${member.user.username}`
          : membership === "vice_president"
            ? `已将 ${member.user.username} 设置为副社长`
            : `已将 ${member.user.username} 调整为普通成员`,
      );
      await refresh();
      return true;
    } catch (error) {
      setMemberTone("error");
      setMemberMessage(error);
      return false;
    } finally {
      setMemberSubmittingId(null);
    }
  };

  const confirmTransfer = async () => {
    if (!pendingTransfer || transferCountdown > 0) return;
    if (await changeMemberRole(pendingTransfer, "president")) {
      setPendingTransfer(null);
    }
  };

  const removeMember = async (member: ClubMember) => {
    if (!window.confirm(`确定要将 ${member.user.username} 移出社团吗？`)) return;

    setMemberSubmittingId(member.user_id);
    setMemberMessage(null);
    try {
      const { error } = await client.DELETE("/api/v1/clubs/{club_id}/members/{user_id}", {
        params: { path: { club_id: clubId, user_id: member.user_id } },
      });
      if (error) {
        setMemberTone("error");
        setMemberMessage(error);
      } else {
        setMemberTone("success");
        setMemberMessage(`已将 ${member.user.username} 移出社团`);
        await refresh();
      }
    } catch (error) {
      setMemberTone("error");
      setMemberMessage(error);
    } finally {
      setMemberSubmittingId(null);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <Link
        to={`/club/${clubId}`}
        className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 font-medium w-fit transition-colors"
      >
        <ArrowLeft size={18} /> 返回社团
      </Link>

      <PageHeader
        eyebrow="Workspace"
        title={club?.name || `社团 #${clubId} 工作台`}
        action={
          <div className="flex flex-wrap gap-2">
            <Link
              to={`/club/${clubId}/joint-activities/manage`}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-primary-100 bg-primary-50 px-4 py-2.5 font-semibold text-primary-700 hover:bg-primary-100"
            >
              <CalendarDays size={16} /> 联合活动
            </Link>
            <SecondaryButton onClick={() => refresh()} disabled={isLoading}>
              <RefreshCw size={16} /> 刷新
            </SecondaryButton>
          </div>
        }
      />

      {isLoading ? (
        <div className="animate-pulse bg-white rounded-md h-72 border border-slate-100" />
      ) : (
        <>
          {Object.keys(loadErrors).length > 0 && (
            <Surface>
              <SectionTitle title="加载反馈" description="以下内容直接来自后端响应。" />
              <div className="grid gap-3">
                {Object.entries(loadErrors).map(([key, value]) => (
                  <div key={key}>
                    <InlineError value={`${key}: ${stringifyBackendValue(value)}`} />
                  </div>
                ))}
              </div>
            </Surface>
          )}

          {club && (
            <Surface>
              <div className="flex flex-col md:flex-row md:items-center gap-5">
                <div className="w-20 h-20 rounded-md bg-slate-100 flex items-center justify-center shrink-0 overflow-hidden border border-slate-200">
                  {club.logo_uri ? (
                    <img
                      src={club.logo_uri}
                      alt={club.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <Hash className="text-slate-400" size={30} />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap gap-2 mb-2">
                    <Badge tone="primary">{CATEGORY_MAP[club.category]}</Badge>
                    <Badge tone="yellow">{STAR_LEVEL_MAP[club.star_level]}</Badge>
                  </div>
                  <h2 className="text-2xl font-display font-bold text-slate-900">{club.name}</h2>
                  <p className="text-slate-500 mt-1">{club.summary}</p>
                </div>
              </div>
            </Surface>
          )}

          {club && canVerifyMemberships && (
            <Surface>
              <SectionTitle icon={<Users size={20} />} title="成员管理" />
              <div className="grid gap-7">
                <section>
                  <div className="mb-3 flex items-center justify-between gap-3">
                    <h3 className="font-semibold text-slate-900">待审批申请</h3>
                    <Badge tone={membershipRequests.length ? "yellow" : "slate"}>
                      {membershipRequests.length} 条
                    </Badge>
                  </div>
                  <StatusMessage value={membershipRequestMessage} tone={membershipRequestTone} />
                  <div className="mt-4 grid gap-3">
                    {membershipRequests.length ? (
                      membershipRequests.map((request) => {
                        const applicant = membershipApplicants[request.applicant_id];
                        const isSubmitting = membershipRequestSubmittingId === request.id;
                        return (
                          <div
                            key={request.id}
                            className="flex flex-col gap-4 rounded-md border border-slate-100 bg-slate-50 p-4 md:flex-row md:items-center"
                          >
                            <div className="min-w-0 flex-1">
                              <Link
                                to={`/users/${request.applicant_id}`}
                                className="font-semibold text-slate-900 hover:text-primary-600"
                              >
                                {applicant?.username || `用户 #${request.applicant_id}`}
                              </Link>
                              <p className="mt-1 text-sm text-slate-500">
                                {request.message.trim() || "申请人没有填写留言"}
                              </p>
                            </div>
                            <div className="flex flex-wrap gap-2 md:justify-end">
                              <PrimaryButton
                                type="button"
                                loading={isSubmitting}
                                disabled={membershipRequestSubmittingId !== null}
                                onClick={() => verifyMembershipRequest(request, "approved")}
                                className="px-4 py-2.5"
                              >
                                <Check size={16} /> 通过
                              </PrimaryButton>
                              <DangerButton
                                type="button"
                                disabled={membershipRequestSubmittingId !== null}
                                onClick={() => verifyMembershipRequest(request, "rejected")}
                              >
                                <X size={16} /> 驳回
                              </DangerButton>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <EmptyState title="暂无待审批的入社申请" />
                    )}
                  </div>
                </section>

                {isPresident && (
                  <section className="border-t border-slate-100 pt-7">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <h3 className="font-semibold text-slate-900">社团成员</h3>
                      <Badge>{activeMembers.length} 人</Badge>
                    </div>
                    <StatusMessage value={memberMessage} tone={memberTone} />
                    <div className="mt-4 grid gap-3">
                      {activeMembers.map((member) => {
                        const isCurrentPresident = member.membership === "president";
                        const isSubmitting = memberSubmittingId === member.user_id;
                        return (
                          <div
                            key={member.id}
                            className="flex flex-col gap-4 rounded-md border border-slate-100 bg-slate-50 p-4 md:flex-row md:items-center"
                          >
                            <div className="flex min-w-0 flex-1 items-center gap-3">
                              <div className="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-md border border-slate-200 bg-white font-semibold text-slate-500">
                                {member.user.avatar_uri ? (
                                  <img
                                    src={member.user.avatar_uri}
                                    alt=""
                                    className="h-full w-full object-cover"
                                  />
                                ) : (
                                  member.user.username.slice(0, 1).toUpperCase()
                                )}
                              </div>
                              <div className="min-w-0">
                                <Link
                                  to={`/users/${member.user_id}`}
                                  className="truncate font-semibold text-slate-900 hover:text-primary-600"
                                >
                                  {member.user.username}
                                </Link>
                                <div className="mt-1">
                                  <Badge tone={isCurrentPresident ? "primary" : "slate"}>
                                    {MEMBERSHIP_MAP[member.membership]}
                                  </Badge>
                                </div>
                              </div>
                            </div>

                            {!isCurrentPresident && (
                              <div className="flex flex-wrap gap-2 md:justify-end">
                                <SecondaryButton
                                  type="button"
                                  disabled={memberSubmittingId !== null}
                                  onClick={() =>
                                    changeMemberRole(
                                      member,
                                      member.membership === "vice_president"
                                        ? "member"
                                        : "vice_president",
                                    )
                                  }
                                >
                                  <ShieldCheck size={16} />
                                  {isSubmitting
                                    ? "处理中..."
                                    : member.membership === "vice_president"
                                      ? "取消副社长"
                                      : "设为副社长"}
                                </SecondaryButton>
                                <DangerButton
                                  type="button"
                                  disabled={memberSubmittingId !== null}
                                  onClick={() => setPendingTransfer(member)}
                                >
                                  交接社团
                                </DangerButton>
                                <DangerButton
                                  type="button"
                                  disabled={memberSubmittingId !== null}
                                  onClick={() => removeMember(member)}
                                >
                                  <Trash2 size={16} /> 移除
                                </DangerButton>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </section>
                )}
              </div>
            </Surface>
          )}

          {pendingTransfer && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/55 p-4"
              role="dialog"
              aria-modal="true"
              aria-labelledby="transfer-club-title"
            >
              <div className="w-full max-w-lg rounded-md border border-red-200 bg-white p-6 shadow-2xl">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-bold text-red-600">危险操作</p>
                    <h2
                      id="transfer-club-title"
                      className="mt-1 text-2xl font-display font-bold text-slate-900"
                    >
                      确认交接社团？
                    </h2>
                  </div>
                  <button
                    type="button"
                    onClick={() => setPendingTransfer(null)}
                    className="rounded-md p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                    aria-label="取消交接"
                  >
                    <X size={20} />
                  </button>
                </div>
                <div className="mt-5 rounded-md border border-red-100 bg-red-50 p-4 text-sm leading-6 text-red-800">
                  你将把 <strong>{club.name}</strong> 交接给{" "}
                  <strong>{pendingTransfer.user.username}</strong>。提交后，对方会立即成为社长，
                  你会降为普通成员，并失去仅限社长的成员管理权限。
                </div>
                <p className="mt-4 text-sm text-slate-500">
                  请确认接任人无误。为防止误操作，确认按钮将在 5 秒后启用。
                </p>
                <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                  <SecondaryButton type="button" onClick={() => setPendingTransfer(null)}>
                    取消
                  </SecondaryButton>
                  <DangerButton
                    type="button"
                    disabled={transferCountdown > 0 || memberSubmittingId !== null}
                    onClick={confirmTransfer}
                    className="bg-red-600 text-white hover:bg-red-700"
                  >
                    {memberSubmittingId === pendingTransfer.user_id
                      ? "正在交接..."
                      : transferCountdown > 0
                        ? `请等待 ${transferCountdown} 秒`
                        : "再次确认并交接"}
                  </DangerButton>
                </div>
              </div>
            </div>
          )}

          <Surface>
            <SectionTitle icon={<Sparkles size={20} />} title="星级评价" />
            {starRating ? (
              <div className="flex flex-col gap-5">
                <div className="rounded-md border border-slate-100 bg-slate-50 p-5">
                  <p className="text-sm font-medium text-slate-500">当前总分</p>
                  <p className="mt-2 text-4xl font-display font-bold text-slate-900">
                    {starRating.total_score}
                  </p>
                  <p className="mt-2 text-sm font-semibold text-primary-600">
                    {STAR_LEVEL_MAP[starRating.star_level]}
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                  <Badge tone="primary">会议出勤 {starRating.breakdown.meeting_attendance}</Badge>
                  <Badge tone="primary">
                    活动参与 {starRating.breakdown.activity_participation}
                  </Badge>
                  <Badge tone="primary">内部活动 {starRating.breakdown.internal_activities}</Badge>
                  <Badge tone="primary">社团历史 {starRating.breakdown.club_history}</Badge>
                </div>
                <p className="text-sm text-slate-500">
                  内部活动 {starRating.internal_activity_count} 次，社团年限{" "}
                  {starRating.club_age_years} 年。
                </p>
              </div>
            ) : (
              <EmptyState title="暂无星级评价" />
            )}
          </Surface>

          <Surface>
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <SectionTitle
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
                activityEditorMode ? "lg:grid-cols-[0.95fr_1.05fr]" : "grid-cols-1"
              }`}
            >
              <div className="grid gap-3">
                {activities.length ? (
                  activities.map((activityItem) => (
                    <button
                      key={activityItem.id}
                      type="button"
                      onClick={() => selectActivityForUpdate(activityItem)}
                      className={`rounded-md border p-4 text-left transition hover:bg-white ${
                        updateActivityId === String(activityItem.id)
                          ? "border-primary-200 bg-primary-50"
                          : "border-slate-100 bg-slate-50"
                      }`}
                    >
                      <h3 className="font-semibold text-slate-900">{activityItem.name}</h3>
                      <p className="mt-1 line-clamp-2 text-sm text-slate-500">
                        {activityItem.description}
                      </p>
                      <p className="mt-2 text-xs font-medium text-slate-400">
                        #{activityItem.id} · {formatDateTime(activityItem.start_time)} ·{" "}
                        {activityItem.location}
                      </p>
                    </button>
                  ))
                ) : (
                  <EmptyState title="暂无社团活动" />
                )}
              </div>

              {activityEditorMode && (
                <div className="rounded-md border border-slate-100 bg-white p-5">
                  {activityEditorMode === "create" ? (
                    <form onSubmit={submitActivityCreate} className="flex flex-col gap-4">
                      <EditorHeader
                        eyebrow="新建申请"
                        title="创建社团活动"
                        onClose={closeActivityEditor}
                      />
                      <Field label="活动名称">
                        <input
                          className={inputClassName}
                          value={activityName}
                          onChange={(event) => setActivityName(event.target.value)}
                          required
                        />
                      </Field>
                      <Field label="活动描述">
                        <textarea
                          className={textareaClassName}
                          value={activityDescription}
                          onChange={(event) => setActivityDescription(event.target.value)}
                          required
                        />
                      </Field>
                      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <Field label="开始时间">
                          <input
                            className={inputClassName}
                            type="datetime-local"
                            value={activityStart}
                            onChange={(event) => setActivityStart(event.target.value)}
                            required
                          />
                        </Field>
                        <Field label="结束时间">
                          <input
                            className={inputClassName}
                            type="datetime-local"
                            value={activityEnd}
                            onChange={(event) => setActivityEnd(event.target.value)}
                            required
                          />
                        </Field>
                      </div>
                      <Field label="地点">
                        <input
                          className={inputClassName}
                          value={activityLocation}
                          onChange={(event) => setActivityLocation(event.target.value)}
                          required
                        />
                      </Field>
                      <StatusMessage value={activityCreateMessage} tone={activityCreateTone} />
                      <PrimaryButton type="submit" loading={isActivityCreating}>
                        提交活动申请
                      </PrimaryButton>
                    </form>
                  ) : selectedUpdateActivity ? (
                    <form onSubmit={submitActivityUpdate} className="flex flex-col gap-4">
                      <EditorHeader
                        eyebrow="当前编辑"
                        title={selectedUpdateActivity.name}
                        onClose={closeActivityEditor}
                      />
                      <Field label="新名称">
                        <input
                          className={inputClassName}
                          value={updateActivityName}
                          onChange={(event) => setUpdateActivityName(event.target.value)}
                        />
                      </Field>
                      <Field label="新描述">
                        <textarea
                          className={textareaClassName}
                          value={updateActivityDescription}
                          onChange={(event) => setUpdateActivityDescription(event.target.value)}
                        />
                      </Field>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <Field label="新开始时间">
                          <input
                            className={inputClassName}
                            type="datetime-local"
                            value={updateActivityStart}
                            onChange={(event) => setUpdateActivityStart(event.target.value)}
                          />
                        </Field>
                        <Field label="新结束时间">
                          <input
                            className={inputClassName}
                            type="datetime-local"
                            value={updateActivityEnd}
                            onChange={(event) => setUpdateActivityEnd(event.target.value)}
                          />
                        </Field>
                      </div>
                      <Field label="新地点">
                        <input
                          className={inputClassName}
                          value={updateActivityLocation}
                          onChange={(event) => setUpdateActivityLocation(event.target.value)}
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
                      <StatusMessage value={activityUpdateMessage} tone={activityUpdateTone} />
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

          <Surface>
            <SectionTitle
              icon={<FileCheck2 size={20} />}
              title="综评活动记录"
              description="点击“未提交”的大型活动可新建记录；点击已提交的活动可查看或修改记录。"
            />
            <div
              className={`grid gap-6 ${
                selectedGeneralActivity ? "lg:grid-cols-[0.95fr_1.05fr]" : "grid-cols-1"
              }`}
            >
              <div className="grid gap-3">
                {generalActivities.length ? (
                  generalActivities.map((activityItem) => {
                    const record = records.find((item) => item.activity_id === activityItem.id);
                    const isSelected = generalActivityId === String(activityItem.id);
                    return (
                      <button
                        key={activityItem.id}
                        type="button"
                        onClick={() => selectGeneralActivityForRecord(activityItem)}
                        className={`rounded-md p-4 text-left transition hover:bg-white ${
                          isSelected
                            ? "bg-primary-50 shadow-[inset_0_0_0_1.5px_rgba(14,165,233,0.35)]"
                            : "bg-slate-50 shadow-[inset_0_0_0_1.5px_rgba(148,163,184,0.18)]"
                        }`}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          {record ? (
                            <>
                              <Badge tone={getAuditTone(record.audit_status)}>
                                {AUDIT_STATUS_MAP[record.audit_status]}
                              </Badge>
                              <Badge>{PARTICIPATION_MAP[record.participation_type]}</Badge>
                            </>
                          ) : (
                            <Badge tone="slate">未提交</Badge>
                          )}
                        </div>
                        <h3 className="mt-3 font-semibold text-slate-900">{activityItem.name}</h3>
                        <p className="mt-1 line-clamp-2 text-sm text-slate-500">
                          {activityItem.description}
                        </p>
                        <p className="mt-2 text-xs font-medium text-slate-400">
                          #{activityItem.id} ·{" "}
                          {formatDateTime(activityItem.starts_at || activityItem.created_at)}
                          {record ? ` · 申请 ${record.requested_score} 分` : ""}
                        </p>
                      </button>
                    );
                  })
                ) : (
                  <EmptyState title="暂无综评活动" />
                )}
              </div>

              {selectedGeneralActivity && (
                <div className="rounded-md bg-white p-5 shadow-[inset_0_0_0_1.5px_rgba(148,163,184,0.18)]">
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      submitRecord(selectedGeneralRecord ? "update" : "create");
                    }}
                    className="flex flex-col gap-4"
                  >
                    <div>
                      <EditorHeader
                        eyebrow={selectedGeneralRecord ? "当前记录" : "新建记录"}
                        title={selectedGeneralActivity.name}
                        onClose={() => setGeneralActivityId("")}
                      />
                      {selectedGeneralRecord && (
                        <p className="mt-1 text-sm text-slate-500">
                          记录 #{selectedGeneralRecord.id}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <Field label="参与类型">
                        <select
                          className={selectClassName}
                          value={participationType}
                          onChange={(event) =>
                            setParticipationType(event.target.value as ParticipationType)
                          }
                        >
                          {PARTICIPATION_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </Field>
                      <Field label="申请分值">
                        <input
                          className={inputClassName}
                          type="number"
                          value={requestedScore}
                          onChange={(event) => setRequestedScore(event.target.value)}
                          required
                        />
                      </Field>
                    </div>
                    <FileUploadField
                      label="证明材料"
                      scene="application_file"
                      values={proofFileUrls}
                      onValuesChange={setProofFileUrls}
                      multiple
                    />
                    {selectedGeneralRecord?.audit_status !== "pending" && selectedGeneralRecord && (
                      <StatusMessage value="已审核的综评记录不能在这里更新。" tone="info" />
                    )}
                    <StatusMessage value={recordMessage} tone={recordTone} />
                    <PrimaryButton
                      type="submit"
                      loading={isRecordSubmitting}
                      disabled={
                        selectedGeneralRecord?.audit_status !== "pending" &&
                        Boolean(selectedGeneralRecord)
                      }
                    >
                      {selectedGeneralRecord ? "更新记录" : "创建记录"}
                    </PrimaryButton>
                  </form>
                </div>
              )}
            </div>
          </Surface>

          <Surface>
            <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <SectionTitle className="mb-0" icon={<Award size={20} />} title="星级申请" />
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
                      className={`rounded-md border p-5 text-left transition hover:bg-white ${
                        starUpdateId === String(application.id)
                          ? "border-primary-200 bg-primary-50"
                          : "border-slate-100 bg-slate-50"
                      }`}
                    >
                      <div className="flex flex-wrap gap-2">
                        <Badge
                          tone={
                            application.audit_status === "approved"
                              ? "green"
                              : application.audit_status === "rejected"
                                ? "red"
                                : "yellow"
                          }
                        >
                          {application.audit_status
                            ? AUDIT_STATUS_MAP[application.audit_status]
                            : "未审核"}
                        </Badge>
                        {application.approved_level && (
                          <Badge tone="primary">{STAR_LEVEL_MAP[application.approved_level]}</Badge>
                        )}
                      </div>
                      <h3 className="mt-3 font-semibold text-slate-900">申请 #{application.id}</h3>
                      <p className="mt-1 text-sm text-slate-500">
                        申请竞赛分 {application.requested_contest_score ?? "未填"}
                        ，核定分 {application.approved_score ?? "未定"}
                      </p>
                    </button>
                  ))
                ) : (
                  <EmptyState title="暂无星级申请" />
                )}
              </div>

              {starEditorMode && (
                <div className="rounded-md border border-slate-100 bg-white p-5">
                  {starEditorMode === "create" ? (
                    <form onSubmit={submitStarCreate} className="flex flex-col gap-4">
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
                          onChange={(event) => setStarStatement(event.target.value)}
                        />
                      </Field>
                      <StatusMessage value={starCreateMessage} tone={starCreateTone} />
                      <PrimaryButton type="submit" loading={isStarCreating}>
                        提交星级申请
                      </PrimaryButton>
                    </form>
                  ) : starUpdateId ? (
                    <form onSubmit={submitStarUpdate} className="flex flex-col gap-4">
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
                          onChange={(event) => setStarUpdateScore(event.target.value)}
                        />
                      </Field>
                      <Field label="独特性说明">
                        <textarea
                          className={textareaClassName}
                          value={starUpdateStatement}
                          onChange={(event) => setStarUpdateStatement(event.target.value)}
                        />
                      </Field>
                      <PrimaryButton type="submit" loading={isStarUpdating}>
                        更新申请
                      </PrimaryButton>
                      <StatusMessage value={starUpdateMessage} tone={starUpdateTone} />
                    </form>
                  ) : (
                    <EmptyState title="请选择星级申请" />
                  )}
                </div>
              )}
            </div>
          </Surface>

          <Surface>
            <SectionTitle icon={<Save size={20} />} title="社团资料变更申请" />
            <form onSubmit={submitClubUpdate} className="flex flex-col gap-4">
              <Field label="简介">
                <input
                  className={inputClassName}
                  value={clubSummary}
                  onChange={(event) => setClubSummary(event.target.value)}
                />
              </Field>
              <Field label="详细介绍">
                <textarea
                  className={textareaClassName}
                  value={clubDescription}
                  onChange={(event) => setClubDescription(event.target.value)}
                />
              </Field>
              <FileUploadField
                label="Logo"
                scene="club_logo"
                value={clubLogo}
                onChange={setClubLogo}
                accept="image/*"
                hint="上传后作为社团资料变更申请的 Logo。"
              />
              <StatusMessage value={clubMessage} tone={clubTone} />
              <PrimaryButton type="submit" loading={isClubSubmitting}>
                提交变更申请
              </PrimaryButton>
            </form>
          </Surface>
        </>
      )}
    </motion.div>
  );
}

function EditorHeader({
  eyebrow,
  title,
  onClose,
}: {
  eyebrow: string;
  title: string;
  onClose: () => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{eyebrow}</p>
        <h3 className="mt-1 truncate font-bold text-slate-900">{title}</h3>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-sm font-semibold text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
        aria-label="收起编辑区域"
      >
        <X size={16} /> 收起
      </button>
    </div>
  );
}

function sameStringArray(left: string[], right: string[]) {
  if (left.length !== right.length) return false;
  return left.every((item, index) => item === right[index]);
}

function membershipOrder(membership: components["schemas"]["ClubMembershipEnum"]) {
  return {
    president: 0,
    vice_president: 1,
    member: 2,
    pending: 3,
    left: 4,
  }[membership];
}

function getAuditTone(status: components["schemas"]["AuditStatusEnum"]) {
  if (status === "approved") return "green";
  if (status === "rejected") return "red";
  return "yellow";
}
