import { stringifyBackendValue } from "./format.ts";

export type WorkspaceLoadErrorEntry = {
  key: string;
  text: string;
};

const WORKSPACE_ERROR_LABELS: Record<string, string> = {
  club: "社团信息",
  user: "当前用户",
  membershipRequests: "加入申请",
  activities: "社团活动",
  generalActivities: "大型活动",
  records: "大型活动记录",
  starApplications: "星级申请",
  starRating: "星级评价",
  workspace: "工作台",
};

const INTERNAL_IDENTIFIER_PATTERN = /^(?:error\.[a-z0-9_.-]+|[A-Z][A-Z0-9_]+)$/;

export function formatWorkspaceLoadErrors(
  errors: Record<string, unknown>,
): WorkspaceLoadErrorEntry[] {
  return Object.entries(errors).flatMap(([key, value]) => {
    const formatted = stringifyBackendValue(value).trim();
    if (!formatted) return [];

    const message = INTERNAL_IDENTIFIER_PATTERN.test(formatted)
      ? "操作没有完成，请稍后重试"
      : formatted;
    const label = WORKSPACE_ERROR_LABELS[key] || "其他内容";
    return [{ key, text: `${label}：${message}` }];
  });
}
