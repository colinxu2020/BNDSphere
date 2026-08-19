import type { components } from "../../api/schema";
import { formatDateTime } from "../../lib/format";

type UserRequest = components["schemas"]["UserUpdateRequestInfo"];
type ActivityCreateRequest = components["schemas"]["ClubActivityCreateRequestInfo"];
type ActivityUpdateRequest = components["schemas"]["ClubActivityUpdateRequestInfo"];
type ClubUpdateRequest = components["schemas"]["ClubUpdateRequestInfo"];
export type ModerationItem =
  UserRequest | ActivityCreateRequest | ActivityUpdateRequest | ClubUpdateRequest;

export type QueueKey = "users" | "activityCreate" | "activityUpdate" | "clubUpdate";

export const QUEUES: { key: QueueKey; label: string; description: string }[] = [
  { key: "users", label: "用户资料", description: "用户资料修改请求" },
  { key: "activityCreate", label: "活动创建", description: "社团活动创建请求" },
  { key: "activityUpdate", label: "活动修改", description: "社团活动修改请求" },
  { key: "clubUpdate", label: "社团资料", description: "社团资料修改请求" },
];

/**
 * Presentation helpers for the moderation queues.
 *
 * A moderation item is one of four unrelated request shapes, so naming its target and
 * listing its changed fields is duck-typed on the keys present. That is view logic, and
 * it belongs beside the queue rather than inside the page.
 */
export function getTargetLabel(item: ModerationItem): string {
  if ("user_id" in item) return `用户 #${item.user_id}`;
  if ("club_id" in item) return `社团 #${item.club_id}`;
  if ("club_activity_id" in item) return `活动 #${item.club_activity_id}`;
  return `请求 #${(item as { id: number }).id}`;
}

export function renderRequestDetails(item: ModerationItem) {
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
    rows.push(["开始时间", item.start_time ? formatDateTime(item.start_time) : null]);
  if ("end_time" in item)
    rows.push(["结束时间", item.end_time ? formatDateTime(item.end_time) : null]);
  if ("location" in item) rows.push(["地点", item.location]);
  if ("logo_uri" in item) rows.push(["Logo", item.logo_uri]);
  if ("picture_urls" in item) rows.push(["图片", item.picture_urls?.join("\n")]);

  const visibleRows = rows.filter(([, value]) => value != null && value !== "");

  if (!visibleRows.length) {
    return <p className="text-sm text-content-muted">此请求没有可展示的变更字段。</p>;
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 grid gap-2">
      {visibleRows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[80px_1fr] gap-3 text-sm">
          <span className="font-semibold text-content-muted">{label}</span>
          <span className="text-content whitespace-pre-wrap break-words">{String(value)}</span>
        </div>
      ))}
    </div>
  );
}
