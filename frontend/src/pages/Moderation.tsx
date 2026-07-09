import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Check, Clock, FilePenLine, RefreshCw, X } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { MODERATION_STATUS_MAP } from "../lib/labels";
import { formatDateTime, stringifyBackendValue } from "../lib/format";
import {
  Badge,
  EmptyState,
  InlineError,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";
import { cn } from "../lib/utils";

type UserRequest = components["schemas"]["UserUpdateRequestInfo"];
type ActivityCreateRequest =
  components["schemas"]["ClubActivityCreateRequestInfo"];
type ActivityUpdateRequest =
  components["schemas"]["ClubActivityUpdateRequestInfo"];
type ClubUpdateRequest = components["schemas"]["ClubUpdateRequestInfo"];
type ModerationItem =
  | UserRequest
  | ActivityCreateRequest
  | ActivityUpdateRequest
  | ClubUpdateRequest;
type ModerationStatus = components["schemas"]["ModerationStatusEnum"];
type QueueKey = "users" | "activityCreate" | "activityUpdate" | "clubUpdate";

const QUEUES: { key: QueueKey; label: string; description: string }[] = [
  { key: "users", label: "用户资料", description: "用户资料修改请求" },
  { key: "activityCreate", label: "活动创建", description: "社团活动创建请求" },
  { key: "activityUpdate", label: "活动修改", description: "社团活动修改请求" },
  { key: "clubUpdate", label: "社团资料", description: "社团资料修改请求" },
];

function getTargetLabel(item: ModerationItem): string {
  if ("user_id" in item) return `用户 #${item.user_id}`;
  if ("club_id" in item) return `社团 #${item.club_id}`;
  if ("club_activity_id" in item) return `活动 #${item.club_activity_id}`;
  return `请求 #${(item as { id: number }).id}`;
}

function renderRequestDetails(item: ModerationItem) {
  const rows: [string, unknown][] = [];

  if ("username" in item) {
    rows.push(["用户名", item.username]);
    rows.push(["头像", item.avatar_uri]);
    rows.push(["简介", item.description]);
  }

  if ("name" in item) rows.push(["名称", item.name]);
  if ("summary" in item) rows.push(["简介", item.summary]);
  if ("description" in item) rows.push(["描述", item.description]);
  if ("start_time" in item)
    rows.push([
      "开始时间",
      item.start_time ? formatDateTime(item.start_time) : null,
    ]);
  if ("end_time" in item)
    rows.push([
      "结束时间",
      item.end_time ? formatDateTime(item.end_time) : null,
    ]);
  if ("location" in item) rows.push(["地点", item.location]);
  if ("logo_uri" in item) rows.push(["Logo", item.logo_uri]);
  if ("picture_urls" in item)
    rows.push(["图片", item.picture_urls?.join("\n")]);

  const visibleRows = rows.filter(([, value]) => value != null && value !== "");

  if (!visibleRows.length) {
    return (
      <p className="text-sm text-slate-500">此请求没有可展示的变更字段。</p>
    );
  }

  return (
    <div className="grid gap-2">
      {visibleRows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[80px_1fr] gap-3 text-sm">
          <span className="font-semibold text-slate-500">{label}</span>
          <span className="text-slate-700 whitespace-pre-wrap break-words">
            {String(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function Moderation() {
  const [activeQueue, setActiveQueue] = useState<QueueKey>("users");
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [actionMessage, setActionMessage] = useState<unknown>(null);
  const [actionTone, setActionTone] = useState<"error" | "success">("error");
  const [busyId, setBusyId] = useState<number | null>(null);

  const fetchQueue = async () => {
    setIsLoading(true);
    setError(null);
    setActionMessage(null);

    try {
      if (activeQueue === "users") {
        const { data, error } = await client.GET(
          "/api/v1/moderations/users/update-requests",
          {
            params: { query: { size: 50 } },
          },
        );
        if (error) setError(error);
        setItems(data?.items || []);
      }

      if (activeQueue === "activityCreate") {
        const { data, error } = await client.GET(
          "/api/v1/moderations/club-activities/create-requests",
          {
            params: { query: { size: 50 } },
          },
        );
        if (error) setError(error);
        setItems(data?.items || []);
      }

      if (activeQueue === "activityUpdate") {
        const { data, error } = await client.GET(
          "/api/v1/moderations/club-activities/update-requests",
          {
            params: { query: { size: 50 } },
          },
        );
        if (error) setError(error);
        setItems(data?.items || []);
      }

      if (activeQueue === "clubUpdate") {
        const { data, error } = await client.GET(
          "/api/v1/moderations/clubs/update-requests",
          {
            params: { query: { size: 50 } },
          },
        );
        if (error) setError(error);
        setItems(data?.items || []);
      }
    } catch (requestError) {
      setError(requestError);
      setItems([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [activeQueue]);

  const moderate = async (
    requestId: number,
    moderationStatus: ModerationStatus,
  ) => {
    setBusyId(requestId);
    setActionMessage(null);
    const body = { moderation_status: moderationStatus };

    try {
      let result: { data?: unknown; error?: unknown } = {};

      if (activeQueue === "users") {
        result = await client.PATCH(
          "/api/v1/moderations/users/update-requests/{request_id}",
          {
            params: { path: { request_id: requestId } },
            body,
          },
        );
      }

      if (activeQueue === "activityCreate") {
        result = await client.PATCH(
          "/api/v1/moderations/club-activities/create-requests/{request_id}",
          {
            params: { path: { request_id: requestId } },
            body,
          },
        );
      }

      if (activeQueue === "activityUpdate") {
        result = await client.PATCH(
          "/api/v1/moderations/club-activities/update-requests/{request_id}",
          {
            params: { path: { request_id: requestId } },
            body,
          },
        );
      }

      if (activeQueue === "clubUpdate") {
        result = await client.PATCH(
          "/api/v1/moderations/clubs/update-requests/{request_id}",
          {
            params: { path: { request_id: requestId } },
            body,
          },
        );
      }

      if (result.error) {
        setActionTone("error");
        setActionMessage(result.error);
      } else {
        setActionTone("success");
        setActionMessage(result.data);
        fetchQueue();
      }
    } catch (requestError) {
      setActionTone("error");
      setActionMessage(requestError);
    } finally {
      setBusyId(null);
    }
  };

  const activeMeta = QUEUES.find((queue) => queue.key === activeQueue);

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
        description="处理用户资料、社团资料和社团活动请求。错误与返回值会直接显示后端响应。"
        action={
          <SecondaryButton onClick={fetchQueue} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      <div className="w-full overflow-x-auto hide-scrollbar">
        <div className="flex gap-2 min-w-max pb-2">
          {QUEUES.map((queue) => (
            <button
              key={queue.key}
              onClick={() => setActiveQueue(queue.key)}
              className={cn(
                "px-4 py-2 rounded-md text-sm font-semibold transition-all shadow-sm whitespace-nowrap",
                activeQueue === queue.key
                  ? "bg-slate-900 text-white shadow-slate-900/10"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50",
              )}
            >
              {queue.label}
            </button>
          ))}
        </div>
      </div>

      <Surface>
        <div className="flex items-start gap-3 mb-6">
          <div className="w-10 h-10 rounded-md bg-primary-50 text-primary-600 flex items-center justify-center">
            <FilePenLine size={20} />
          </div>
          <div>
            <h2 className="text-xl font-display font-bold text-slate-900">
              {activeMeta?.label}
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              {activeMeta?.description}
            </p>
          </div>
        </div>

        {actionMessage && (
          <div className="mb-5">
            <StatusMessage value={actionMessage} tone={actionTone} />
          </div>
        )}
        {error && (
          <div className="mb-5">
            <InlineError value={error} />
          </div>
        )}

        {isLoading ? (
          <div className="grid gap-4">
            {[...Array(3)].map((_, index) => (
              <div
                key={index}
                className="animate-pulse bg-slate-50 h-40 rounded-md border border-slate-100"
              />
            ))}
          </div>
        ) : items.length ? (
          <div className="grid gap-4">
            {items.map((item) => (
              <div
                key={item.id}
                className="rounded-md border border-slate-100 bg-slate-50 p-5"
              >
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge
                        tone={
                          item.moderation_status === "approved"
                            ? "green"
                            : item.moderation_status === "rejected"
                              ? "red"
                              : "yellow"
                        }
                      >
                        {MODERATION_STATUS_MAP[item.moderation_status]}
                      </Badge>
                      <span className="text-xs font-medium text-slate-400">
                        #{item.id} · {getTargetLabel(item)}
                      </span>
                    </div>
                    <p className="mt-2 text-xs font-medium text-slate-400 flex items-center gap-1">
                      <Clock size={14} /> {formatDateTime(item.request_at)}
                    </p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <PrimaryButton
                      type="button"
                      className="px-4 py-2.5"
                      loading={busyId === item.id}
                      onClick={() => moderate(item.id, "approved")}
                    >
                      <Check size={16} /> 通过
                    </PrimaryButton>
                    <SecondaryButton
                      type="button"
                      onClick={() => moderate(item.id, "rejected")}
                      disabled={busyId === item.id}
                      className="text-red-700 bg-red-50 hover:bg-red-100 border-red-100"
                    >
                      <X size={16} /> 驳回
                    </SecondaryButton>
                  </div>
                </div>
                <div className="mt-5 rounded-md bg-white border border-slate-100 p-4">
                  {renderRequestDetails(item)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            title="没有待处理请求"
            description={error ? stringifyBackendValue(error) : undefined}
          />
        )}
      </Surface>
    </motion.div>
  );
}

