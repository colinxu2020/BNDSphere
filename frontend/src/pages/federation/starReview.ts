/**
 * Star-level review logic for the federation workbench.
 *
 * Pure functions: scoring payloads, select-value coercion, preview text and
 * ordering. Separate from the view helpers because this is the part that
 * decides things, and it moves with the star panel when that is extracted.
 */
import type { components } from "../../api/schema";
import { STAR_LEVEL_MAP } from "../../lib/labels";
import { nullableNumber } from "../../lib/format";

type AuditStatus = components["schemas"]["AuditStatusEnum"];
type StarApplication = components["schemas"]["StarLevelApplicationPublicInfo"];
type StarReviewPreview = components["schemas"]["StarLevelApplicationReviewPreview"];

export function buildStarReviewBody(
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

export function booleanToSelectValue(value?: boolean | null) {
  if (value == null) return "";
  return value ? "true" : "false";
}

export function selectValueToBoolean(value: string) {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

export function sortStarApplications(left: StarApplication, right: StarApplication) {
  if (left.audit_status !== right.audit_status) {
    if (!left.audit_status || left.audit_status === "pending") return -1;
    if (!right.audit_status || right.audit_status === "pending") return 1;
  }
  return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
}

export function getStarPreviewScoreText(
  auditStatus: AuditStatus,
  isLoading: boolean,
  preview: StarReviewPreview | null,
) {
  if (auditStatus !== "approved") return "审核通过后计算";
  if (isLoading) return "计算中";
  return preview?.approved_score == null ? "待计算" : `${preview.approved_score} 分`;
}

export function getStarPreviewLevelText(
  auditStatus: AuditStatus,
  isLoading: boolean,
  preview: StarReviewPreview | null,
) {
  if (auditStatus !== "approved") return "审核通过后计算";
  if (isLoading) return "计算中";
  return preview?.approved_level == null ? "待计算" : STAR_LEVEL_MAP[preview.approved_level];
}
