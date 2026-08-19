import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Check, Clock, FilePenLine, Inbox, RefreshCw, X } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  Badge,
  EmptyState,
  InlineError,
  PrimaryButton,
  SecondaryButton,
  StatusMessage,
} from "../components/ui/AppPrimitives";
import { formatDateTime } from "../lib/format";
import { MODERATION_STATUS_MAP } from "../lib/labels";
import { AUDIT_TONE } from "../lib/tones";
import { useActionFeedback } from "../lib/useActionFeedback";
import { cn } from "../lib/utils";
import {
  getTargetLabel,
  QUEUES,
  renderRequestDetails,
  type ModerationItem,
  type QueueKey,
} from "./moderation/requestView";

type ModerationStatus = components["schemas"]["ModerationStatusEnum"];

/**
 * 审核台 — master–detail.
 *
 * The queues were a vertical stack of fully expanded request cards: every item showed
 * all of its changed fields and its action buttons at once, so a queue of twenty meant
 * scrolling past twenty detail blocks to find the one you cared about.
 *
 * Now the queue is a scannable list and one request is open beside it. Acting on an item
 * leaves the list in place, which is the whole point of the shape for someone working
 * through a backlog.
 *
 * Selection lives in the query string, so a specific request is linkable — useful when
 * one gets escalated to a colleague. Below xl there is no room for two panes, so the
 * selected request appears below the list instead.
 */
export function Moderation() {
  const [activeQueue, setActiveQueue] = useState<QueueKey>("users");
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const action = useActionFeedback();
  const [busyId, setBusyId] = useState<number | null>(null);
  const [params, setParams] = useSearchParams();
  const selectedId = Number(params.get("request")) || null;

  const fetchQueue = async () => {
    setIsLoading(true);
    setError(null);
    // Deliberately does NOT clear the action feedback: moderate() calls this on
    // success, so clearing here wiped the confirmation the moment it was earned.
    // Switching queues clears it instead, which is when it actually goes stale.

    try {
      if (activeQueue === "users") {
        const { data, error } = await client.GET("/api/v1/moderations/users/update-requests", {
          params: { query: { size: 50 } },
        });
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
        const { data, error } = await client.GET("/api/v1/moderations/clubs/update-requests", {
          params: { query: { size: 50 } },
        });
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

  const moderate = async (requestId: number, moderationStatus: ModerationStatus) => {
    setBusyId(requestId);
    action.clear();
    const body = { moderation_status: moderationStatus };

    try {
      let result: { data?: unknown; error?: unknown } = {};

      if (activeQueue === "users") {
        result = await client.PATCH("/api/v1/moderations/users/update-requests/{request_id}", {
          params: { path: { request_id: requestId } },
          body,
        });
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
        result = await client.PATCH("/api/v1/moderations/clubs/update-requests/{request_id}", {
          params: { path: { request_id: requestId } },
          body,
        });
      }

      if (result.error) {
        action.fail(result.error);
      } else {
        action.succeed(result.data);
        fetchQueue();
      }
    } catch (requestError) {
      action.fail(requestError);
    } finally {
      setBusyId(null);
    }
  };

  const activeMeta = QUEUES.find((queue) => queue.key === activeQueue);
  const selected = items.find((item) => item.id === selectedId) ?? null;

  const selectRequest = (id: number) => {
    const next = new URLSearchParams(params);
    next.set("request", String(id));
    setParams(next, { replace: true });
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
      {/* Queue */}
      <div className="flex min-w-0 flex-col border-edge xl:w-[24rem] xl:shrink-0 xl:border-r">
        <div className="border-b border-edge bg-surface px-4 py-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-display text-[11px] font-bold tracking-[0.18em] text-tone-brand-fg uppercase">
                Moderation
              </p>
              <h1 className="font-display text-2xl font-bold text-content">审核台</h1>
            </div>
            <SecondaryButton onClick={fetchQueue} disabled={isLoading}>
              <RefreshCw size={15} /> 刷新
            </SecondaryButton>
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {QUEUES.map((queue) => (
              <button
                key={queue.key}
                type="button"
                onClick={() => {
                  action.clear();
                  setActiveQueue(queue.key);
                }}
                aria-pressed={activeQueue === queue.key}
                className={cn(
                  "rounded-md border px-2.5 py-1 text-xs font-bold outline-none focus-visible:ring-4 focus-visible:ring-brand-strong/40",
                  activeQueue === queue.key
                    ? "border-content bg-surface-inverted text-content-on-inverted"
                    : "border-edge bg-surface text-content-muted hover:bg-surface-hover hover:text-content",
                )}
              >
                {queue.label}
              </button>
            ))}
          </div>
          <p className="mt-2 text-xs text-content-muted">{activeMeta?.description}</p>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {/* Action feedback belongs to the queue, not the request. Approving an item
              removes it from the list, which unmounts the detail pane — so a message
              rendered there vanished the instant it became relevant. */}
          {action.message != null && (
            <div className="mb-3">
              <StatusMessage value={action.message} tone={action.tone} />
            </div>
          )}

          {error != null && (
            <div className="mb-3">
              <InlineError value={error} />
            </div>
          )}

          {isLoading ? (
            <ul className="flex flex-col gap-2">
              {[0, 1, 2, 3, 4].map((index) => (
                <li
                  key={index}
                  className="h-20 animate-pulse rounded-md border border-edge bg-surface-skeleton motion-reduce:animate-none"
                />
              ))}
            </ul>
          ) : items.length ? (
            <ul className="flex flex-col gap-2">
              {items.map((item) => {
                const isSelected = item.id === selectedId;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => selectRequest(item.id)}
                      aria-current={isSelected ? "true" : undefined}
                      className={cn(
                        "w-full rounded-md border p-3 text-left outline-none transition-colors focus-visible:ring-4 focus-visible:ring-brand-strong/40",
                        isSelected
                          ? "border-edge bg-brand-subtle"
                          : "border-edge bg-surface hover:bg-surface-hover",
                      )}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={AUDIT_TONE[item.moderation_status ?? "pending"]}>
                          {MODERATION_STATUS_MAP[item.moderation_status]}
                        </Badge>
                        <span className="text-xs font-semibold text-content">
                          {getTargetLabel(item)}
                        </span>
                      </div>
                      <p className="mt-1.5 inline-flex items-center gap-1.5 text-[11px] font-medium text-content-subtle">
                        <Clock size={12} /> {formatDateTime(item.request_at)} · #{item.id}
                      </p>
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : (
            <EmptyState title="没有待处理请求" />
          )}
        </div>
      </div>

      {/* Request */}
      <div className="min-w-0 flex-1 overflow-y-auto">
        {selected ? (
          <article className="p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={AUDIT_TONE[selected.moderation_status ?? "pending"]}>
                    {MODERATION_STATUS_MAP[selected.moderation_status]}
                  </Badge>
                  <span className="text-xs font-semibold text-content-subtle">#{selected.id}</span>
                </div>
                <h2 className="font-display mt-2 text-2xl font-bold text-content">
                  {getTargetLabel(selected)}
                </h2>
                <p className="mt-1 inline-flex items-center gap-1.5 text-xs font-medium text-content-subtle">
                  <Clock size={13} /> {formatDateTime(selected.request_at)}
                </p>
              </div>
              <div className="flex shrink-0 gap-2">
                <PrimaryButton
                  type="button"
                  loading={busyId === selected.id}
                  onClick={() => moderate(selected.id, "approved")}
                >
                  <Check size={16} /> 通过
                </PrimaryButton>
                <SecondaryButton
                  type="button"
                  onClick={() => moderate(selected.id, "rejected")}
                  disabled={busyId === selected.id}
                  className="border-tone-danger-edge bg-tone-danger-bg text-tone-danger-fg hover:bg-tone-danger-bg-hover"
                >
                  <X size={16} /> 驳回
                </SecondaryButton>
              </div>
            </div>

            <div className="mt-5 rounded-md border border-edge bg-surface p-4 shadow-sm">
              <h3 className="font-display mb-3 flex items-center gap-2 text-sm font-bold text-content">
                <FilePenLine size={15} className="text-content-subtle" />
                申请内容
              </h3>
              {renderRequestDetails(selected)}
            </div>
          </article>
        ) : (
          <div className="flex h-full min-h-64 flex-col items-center justify-center p-10 text-center">
            <Inbox size={28} className="mb-3 text-content-subtle" />
            <p className="font-display text-lg font-bold text-content">从左侧选择一条请求</p>
            <p className="mt-1 max-w-sm text-sm text-content-muted">
              申请内容与审核操作会显示在这里，处理后列表不会跳走。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
