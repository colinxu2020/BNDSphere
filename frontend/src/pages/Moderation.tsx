import { useCallback, useEffect, useState } from "react";
import { motion } from "motion/react";
import { Check, Clock, FilePenLine, RefreshCw, X } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { MODERATION_STATUS_MAP } from "../lib/labels";
import { formatDateTime } from "../lib/format";
import {
  Badge,
  EmptyState,
  PageHeader,
  PageTabs,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";
import { ForbiddenPage, isForbiddenResponse, PageLoading } from "../components/ui/PageStates";
import { InfiniteScrollTrigger } from "../components/ui/InfiniteScroll";
import { DEFAULT_PAGE_SIZE, getPageResult, useInfiniteList } from "../hooks/useInfiniteList";

type UserRequest = components["schemas"]["UserUpdateRequestInfo"];
type ActivityCreateRequest = components["schemas"]["ClubActivityCreateRequestInfo"];
type ActivityUpdateRequest = components["schemas"]["ClubActivityUpdateRequestInfo"];
type ClubUpdateRequest = components["schemas"]["ClubUpdateRequestInfo"];
type ModerationItem = UserRequest | ClubUpdateRequest;
type ModerationStatus = components["schemas"]["ModerationStatusEnum"];
type ActivityModerationKind = "create" | "update";
type QueueKey = "users" | "activities" | "clubUpdate";

const QUEUES: { key: QueueKey; label: string; description: string }[] = [
  { key: "users", label: "用户资料", description: "用户资料修改请求" },
  { key: "activities", label: "社团活动", description: "社团活动创建和修改请求" },
  { key: "clubUpdate", label: "社团资料", description: "社团资料修改请求" },
];

function getTargetLabel(item: ModerationItem) {
  if ("user_id" in item) return `用户 #${item.user_id}`;
  return `社团 #${item.club_id}`;
}

function renderRequestDetails(item: ModerationItem) {
  const rows: [string, unknown][] = [];
  if ("username" in item) {
    rows.push(["用户名", item.username]);
    rows.push(["头像", item.avatar_uri]);
    rows.push(["简介", item.description]);
  }
  if ("summary" in item) rows.push(["简介", item.summary]);
  if ("description" in item) rows.push(["描述", item.description]);
  if ("logo_uri" in item) rows.push(["Logo", item.logo_uri]);

  const visibleRows = rows.filter(([, value]) => value != null && value !== "");
  if (!visibleRows.length) {
    return <p className="text-sm text-slate-500">此请求没有可展示的变更字段。</p>;
  }
  return (
    <div className="grid gap-2">
      {visibleRows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[80px_1fr] gap-3 text-sm">
          <span className="font-semibold text-slate-500">{label}</span>
          <span className="whitespace-pre-wrap break-words text-slate-700">{String(value)}</span>
        </div>
      ))}
    </div>
  );
}

export function Moderation() {
  const [activeQueue, setActiveQueue] = useState<QueueKey>("users");
  const [isForbidden, setIsForbidden] = useState(false);
  const [message, setMessage] = useState<unknown>(null);
  const [messageTone, setMessageTone] = useState<"error" | "success">("error");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [busyActivityRequest, setBusyActivityRequest] = useState<string | null>(null);

  const checkForbidden = (response?: Response, error?: unknown) => {
    if (isForbiddenResponse(response, error)) setIsForbidden(true);
  };
  const loadUserRequestsPage = useCallback(async (page: number, signal: AbortSignal) => {
    const response = await client.GET("/api/v1/moderations/users/update-requests", {
      params: { query: { page, size: DEFAULT_PAGE_SIZE } },
      signal,
    });
    checkForbidden(response.response, response.error);
    return getPageResult(response.data, response.error, page);
  }, []);
  const loadClubRequestsPage = useCallback(async (page: number, signal: AbortSignal) => {
    const response = await client.GET("/api/v1/moderations/clubs/update-requests", {
      params: { query: { page, size: DEFAULT_PAGE_SIZE } },
      signal,
    });
    checkForbidden(response.response, response.error);
    return getPageResult(response.data, response.error, page);
  }, []);
  const loadActivityCreateRequestsPage = useCallback(async (page: number, signal: AbortSignal) => {
    const response = await client.GET("/api/v1/moderations/club-activities/create-requests", {
      params: { query: { page, size: DEFAULT_PAGE_SIZE } },
      signal,
    });
    checkForbidden(response.response, response.error);
    return getPageResult(response.data, response.error, page);
  }, []);
  const loadActivityUpdateRequestsPage = useCallback(async (page: number, signal: AbortSignal) => {
    const response = await client.GET("/api/v1/moderations/club-activities/update-requests", {
      params: { query: { page, size: DEFAULT_PAGE_SIZE } },
      signal,
    });
    checkForbidden(response.response, response.error);
    return getPageResult(response.data, response.error, page);
  }, []);

  const userRequests = useInfiniteList<UserRequest>(loadUserRequestsPage, activeQueue === "users");
  const clubRequests = useInfiniteList<ClubUpdateRequest>(
    loadClubRequestsPage,
    activeQueue === "clubUpdate",
  );
  const activityCreateRequests = useInfiniteList<ActivityCreateRequest>(
    loadActivityCreateRequestsPage,
    activeQueue === "activities",
  );
  const activityUpdateRequests = useInfiniteList<ActivityUpdateRequest>(
    loadActivityUpdateRequestsPage,
    activeQueue === "activities",
  );
  const activeList = activeQueue === "users" ? userRequests : clubRequests;
  const items: ModerationItem[] = activeList.items;
  const isLoading =
    activeQueue === "activities"
      ? activityCreateRequests.isInitialLoading || activityUpdateRequests.isInitialLoading
      : activeList.isInitialLoading;
  const loadError =
    activeQueue === "activities"
      ? activityCreateRequests.error || activityUpdateRequests.error
      : activeList.error;

  const loadRequests = async () => {
    setIsForbidden(false);
    if (activeQueue === "activities") {
      await Promise.all([activityCreateRequests.reload(), activityUpdateRequests.reload()]);
    } else {
      await activeList.reload();
    }
  };

  useEffect(() => {
    setMessage(null);
  }, [activeQueue]);

  const setResult = (error: unknown, successMessage: string) => {
    if (error) {
      setMessageTone("error");
      setMessage(error);
      return;
    }
    setMessageTone("success");
    setMessage(successMessage);
  };

  const moderateRequest = async (requestId: number, moderationStatus: ModerationStatus) => {
    setBusyId(requestId);
    setMessage(null);
    const body = { moderation_status: moderationStatus };
    try {
      const result =
        activeQueue === "users"
          ? await client.PATCH("/api/v1/moderations/users/update-requests/{request_id}", {
              params: { path: { request_id: requestId } },
              body,
            })
          : await client.PATCH("/api/v1/moderations/clubs/update-requests/{request_id}", {
              params: { path: { request_id: requestId } },
              body,
            });

      setResult(result.error, moderationStatus === "approved" ? "审核已通过" : "审核已驳回");
      if (!result.error) loadRequests();
    } catch (error) {
      setResult(error, "");
    } finally {
      setBusyId(null);
    }
  };

  const moderateClubActivityRequest = async (
    kind: ActivityModerationKind,
    requestId: number,
    moderationStatus: ModerationStatus,
  ) => {
    const busyKey = `${kind}-${requestId}`;
    setBusyActivityRequest(busyKey);
    setMessage(null);
    const body = { moderation_status: moderationStatus };
    try {
      const result =
        kind === "create"
          ? await client.PATCH("/api/v1/moderations/club-activities/create-requests/{request_id}", {
              params: { path: { request_id: requestId } },
              body,
            })
          : await client.PATCH("/api/v1/moderations/club-activities/update-requests/{request_id}", {
              params: { path: { request_id: requestId } },
              body,
            });

      setResult(
        result.error,
        moderationStatus === "approved" ? "社团活动申请已通过" : "社团活动申请已驳回",
      );
      if (!result.error) loadRequests();
    } catch (error) {
      setResult(error, "");
    } finally {
      setBusyActivityRequest(null);
    }
  };

  if (isForbidden) {
    return <ForbiddenPage description="只有审核员及获授权的管理角色可以进入审核台。" />;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <PageHeader
        eyebrow="Moderation"
        title="审核台"
        action={
          <SecondaryButton type="button" onClick={loadRequests} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {message && <StatusMessage value={message} tone={messageTone} />}
      {loadError && <StatusMessage value={loadError} />}

      <PageTabs<QueueKey>
        tabs={QUEUES}
        activeTab={activeQueue}
        onChange={setActiveQueue}
        ariaLabel="审核类型"
      />

      {activeQueue === "activities" ? (
        <Surface>
          <SectionTitle icon={<FilePenLine size={20} />} title="审核社团活动" />
          {isLoading ? (
            <PageLoading compact />
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              <ActivityRequestList
                title="活动创建申请"
                kind="create"
                items={activityCreateRequests.items}
                busyKey={busyActivityRequest}
                onModerate={moderateClubActivityRequest}
                pagination={activityCreateRequests}
              />
              <ActivityRequestList
                title="活动修改申请"
                kind="update"
                items={activityUpdateRequests.items}
                busyKey={busyActivityRequest}
                onModerate={moderateClubActivityRequest}
                pagination={activityUpdateRequests}
              />
            </div>
          )}
        </Surface>
      ) : (
        <ModerationRequestList
          title={activeQueue === "users" ? "用户资料修改请求" : "社团资料修改请求"}
          items={items}
          isLoading={isLoading}
          busyId={busyId}
          onModerate={moderateRequest}
          pagination={activeList}
        />
      )}
    </motion.div>
  );
}

function ModerationRequestList({
  title,
  items,
  isLoading,
  busyId,
  onModerate,
  pagination,
}: {
  title: string;
  items: ModerationItem[];
  isLoading: boolean;
  busyId: number | null;
  onModerate: (requestId: number, moderationStatus: ModerationStatus) => void;
  pagination: Pick<
    ReturnType<typeof useInfiniteList<ModerationItem>>,
    "hasMore" | "isLoadingMore" | "error" | "loadMore"
  >;
}) {
  return (
    <Surface>
      <SectionTitle icon={<FilePenLine size={20} />} title={title} />
      {isLoading ? (
        <PageLoading compact />
      ) : items.length ? (
        <div className="grid gap-4">
          {items.map((item) => (
            <div key={item.id} className="rounded-md border border-slate-100 bg-slate-50 p-5">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="yellow">{MODERATION_STATUS_MAP[item.moderation_status]}</Badge>
                    <span className="text-xs font-medium text-slate-400">
                      #{item.id} · {getTargetLabel(item)}
                    </span>
                  </div>
                  <p className="mt-2 flex items-center gap-1 text-xs font-medium text-slate-400">
                    <Clock size={14} /> {formatDateTime(item.request_at)}
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <PrimaryButton
                    type="button"
                    className="px-4 py-2.5"
                    loading={busyId === item.id}
                    onClick={() => onModerate(item.id, "approved")}
                  >
                    <Check size={16} /> 通过
                  </PrimaryButton>
                  <SecondaryButton
                    type="button"
                    disabled={busyId === item.id}
                    onClick={() => onModerate(item.id, "rejected")}
                    className="border-red-100 bg-red-50 text-red-700 hover:bg-red-100"
                  >
                    <X size={16} /> 驳回
                  </SecondaryButton>
                </div>
              </div>
              <div className="mt-5 rounded-md border border-slate-100 bg-white p-4">
                {renderRequestDetails(item)}
              </div>
            </div>
          ))}
          <InfiniteScrollTrigger
            hasMore={pagination.hasMore}
            isLoading={pagination.isLoadingMore}
            error={pagination.error}
            onLoadMore={pagination.loadMore}
          />
        </div>
      ) : (
        <EmptyState title="没有待处理请求" />
      )}
    </Surface>
  );
}

function ActivityRequestList({
  title,
  kind,
  items,
  busyKey,
  onModerate,
  pagination,
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
  pagination: Pick<
    ReturnType<typeof useInfiniteList<ActivityCreateRequest | ActivityUpdateRequest>>,
    "hasMore" | "isLoadingMore" | "error" | "loadMore"
  >;
}) {
  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-slate-900">{title}</h3>
        <Badge tone={items.length ? "yellow" : "slate"}>{items.length} 条待处理</Badge>
      </div>
      {items.length ? (
        <>
          {items.map((item) => {
            const itemBusyKey = `${kind}-${item.id}`;
            return (
              <div key={item.id} className="rounded-md border border-slate-100 bg-slate-50 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone="yellow">{MODERATION_STATUS_MAP[item.moderation_status]}</Badge>
                      <span className="text-xs font-medium text-slate-400">
                        申请 #{item.id} · {getActivityRequestTarget(item)}
                      </span>
                    </div>
                    <h4 className="mt-2 font-semibold text-slate-900">
                      {"name" in item && item.name ? item.name : "活动修改申请"}
                    </h4>
                    <p className="mt-1 text-xs font-medium text-slate-400">
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
                      className="border-red-100 bg-red-50 text-red-700 hover:bg-red-100"
                    >
                      <X size={16} /> 驳回
                    </SecondaryButton>
                  </div>
                </div>
                <div className="mt-4 rounded-md border border-slate-100 bg-white p-3">
                  {renderActivityRequestDetails(item)}
                </div>
              </div>
            );
          })}
          <InfiniteScrollTrigger
            hasMore={pagination.hasMore}
            isLoading={pagination.isLoadingMore}
            error={pagination.error}
            onLoadMore={pagination.loadMore}
          />
        </>
      ) : (
        <EmptyState title="没有待处理申请" />
      )}
    </div>
  );
}

function renderActivityRequestDetails(item: ActivityCreateRequest | ActivityUpdateRequest) {
  const rows: [string, unknown][] = [["申请人", `#${item.requestor_id}`]];

  if ("club_id" in item) rows.push(["社团", `#${item.club_id}`]);
  if ("club_activity_id" in item) rows.push(["原活动", `#${item.club_activity_id}`]);
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
          <span className="font-semibold text-slate-500">{label}</span>
          <span className="whitespace-pre-wrap break-words text-slate-700">{String(value)}</span>
        </div>
      ))}
    </div>
  );
}

function getActivityRequestTarget(item: ActivityCreateRequest | ActivityUpdateRequest) {
  if ("club_id" in item) return `社团 #${item.club_id}`;
  return `原活动 #${item.club_activity_id}`;
}
