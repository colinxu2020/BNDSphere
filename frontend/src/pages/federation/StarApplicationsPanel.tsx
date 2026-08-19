import { useEffect, useMemo, useState } from "react";
import type React from "react";
import { Award, Clock, Save, X } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import {
  Badge,
  EmptyState,
  Field,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  Surface,
  inputClassName,
  selectClassName,
} from "../../components/ui/AppPrimitives";
import { AUDIT_STATUS_MAP, AUDIT_STATUS_OPTIONS, STAR_LEVEL_MAP } from "../../lib/labels";
import { AUDIT_TONE } from "../../lib/tones";
import { formatDateTime } from "../../lib/format";
import { cn } from "../../lib/utils";
import type { useActionFeedback } from "../../lib/useActionFeedback";
import { ExternalLink, LoadingRows, ReadOnlyValue } from "./shared";
import {
  booleanToSelectValue,
  buildStarReviewBody,
  getStarPreviewLevelText,
  getStarPreviewScoreText,
} from "./starReview";

type AuditStatus = components["schemas"]["AuditStatusEnum"];
type StarApplication = components["schemas"]["StarLevelApplicationPublicInfo"];
type StarReviewPreview = components["schemas"]["StarLevelApplicationReviewPreview"];

/**
 * 星级评价表审核 — the federation's star-application review.
 *
 * Extracted from Federation.tsx, which was a single ~1,000-line function serving
 * four unrelated concerns. Every piece of state here was already used only by this
 * concern, and the debounced preview effect only ever read star state, so nothing
 * about ownership was invented to make the split work: the panel keeps its own
 * form and selection state and takes the four genuinely shared values as props.
 */
export function StarApplicationsPanel({
  applications,
  isLoading,
  feedback,
  onReviewed,
}: {
  applications: StarApplication[];
  isLoading: boolean;
  feedback: ReturnType<typeof useActionFeedback>;
  onReviewed: () => void;
}) {
  const [selectedStarId, setSelectedStarId] = useState<number | null>(null);
  const [starStatus, setStarStatus] = useState<AuditStatus>("pending");
  const [finalContestScore, setFinalContestScore] = useState("");
  const [uniquenessApproved, setUniquenessApproved] = useState("");
  const [growthStoryApproved, setGrowthStoryApproved] = useState("");
  const [starPreview, setStarPreview] = useState<StarReviewPreview | null>(null);
  const [isStarPreviewLoading, setIsStarPreviewLoading] = useState(false);
  const [isStarReviewing, setIsStarReviewing] = useState(false);

  const selectedStarApplication = useMemo(
    () => applications.find((application) => application.id === selectedStarId) || null,
    [selectedStarId, applications],
  );

  useEffect(() => {
    if (!selectedStarApplication) {
      setStarPreview(null);
      setIsStarPreviewLoading(false);
      return;
    }

    if (starStatus !== "approved") {
      setStarPreview({ approved_score: null, approved_level: null });
      setIsStarPreviewLoading(false);
      return;
    }

    let isCurrent = true;
    setIsStarPreviewLoading(true);
    const timer = window.setTimeout(async () => {
      try {
        const { data, error } = await client.POST(
          "/api/v1/club-federation/star-level/{star_level_id}/preview",
          {
            params: { path: { star_level_id: selectedStarApplication.id } },
            body: buildStarReviewBody(
              starStatus,
              finalContestScore,
              uniquenessApproved,
              growthStoryApproved,
            ),
          },
        );
        if (isCurrent) setStarPreview(error ? null : data || null);
      } catch {
        if (isCurrent) setStarPreview(null);
      } finally {
        if (isCurrent) setIsStarPreviewLoading(false);
      }
    }, 180);

    return () => {
      isCurrent = false;
      window.clearTimeout(timer);
    };
  }, [
    finalContestScore,
    growthStoryApproved,
    selectedStarApplication?.id,
    starStatus,
    uniquenessApproved,
  ]);

  const loadStarApplicationForReview = (application: StarApplication) => {
    setSelectedStarId(application.id);
    setStarStatus(application.audit_status || "pending");
    setFinalContestScore(
      application.final_contest_score == null
        ? application.requested_contest_score == null
          ? ""
          : String(application.requested_contest_score)
        : String(application.final_contest_score),
    );
    setUniquenessApproved(booleanToSelectValue(application.uniqueness_approved));
    setGrowthStoryApproved(booleanToSelectValue(application.growth_story_approved));
  };

  const reviewStarApplication = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedStarApplication) {
      feedback.report("请先选择一份星级评价表", "");
      return;
    }

    setIsStarReviewing(true);
    feedback.clear();
    try {
      const { error } = await client.PATCH("/api/v1/club-federation/star-level/{star_level_id}", {
        params: { path: { star_level_id: selectedStarApplication.id } },
        body: {
          ...buildStarReviewBody(
            starStatus,
            finalContestScore,
            uniquenessApproved,
            growthStoryApproved,
          ),
        },
      });
      feedback.report(error, "星级评价表已审核");
      if (!error) {
        setSelectedStarId(null);
        setStarPreview(null);
        onReviewed();
      }
    } catch (error) {
      feedback.report(error, "");
    } finally {
      setIsStarReviewing(false);
    }
  };

  return (
    <Surface density="compact">
      <SectionTitle density="compact" icon={<Award size={20} />} title="审核星级评价表" />
      <div className={cn("grid gap-6", selectedStarApplication && "lg:grid-cols-[1fr_380px]")}>
        <div className="grid gap-3">
          {isLoading ? (
            <LoadingRows />
          ) : applications.length ? (
            applications.map((application) => (
              <button
                key={application.id}
                type="button"
                onClick={() => loadStarApplicationForReview(application)}
                className={cn(
                  "rounded-md border border-edge-subtle bg-surface-sunken p-4 text-left transition hover:bg-surface",
                  selectedStarId === application.id && "border-tone-brand-edge bg-brand-subtle",
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={AUDIT_TONE[application.audit_status || "pending"]}>
                    {application.audit_status
                      ? AUDIT_STATUS_MAP[application.audit_status]
                      : "待审核"}
                  </Badge>
                  <Badge>
                    {application.approved_level
                      ? STAR_LEVEL_MAP[application.approved_level]
                      : "待计算"}
                  </Badge>
                  <span className="text-xs font-medium text-content-subtle">
                    申请 #{application.id}
                  </span>
                </div>
                <h3 className="mt-3 font-semibold text-content">{application.club.name}</h3>
                <p className="mt-1 text-sm text-content-muted">
                  申请竞赛分 {application.requested_contest_score ?? "未填"} ·{" "}
                  {application.academic_term.term_name}
                </p>
                <p className="mt-2 text-xs font-medium text-content-subtle">
                  <Clock size={14} className="mr-1 inline" />
                  {formatDateTime(application.created_at)}
                </p>
              </button>
            ))
          ) : (
            <EmptyState title="暂无星级评价表" />
          )}
        </div>

        {selectedStarApplication && (
          <form
            onSubmit={reviewStarApplication}
            className="h-fit rounded-md border border-edge-subtle bg-surface p-5"
          >
            <div className="grid gap-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wider text-content-subtle">
                    当前审核
                  </p>
                  <h3 className="mt-1 truncate font-bold text-content">
                    {selectedStarApplication.club.name}
                  </h3>
                  <p className="mt-1 text-sm text-content-muted">
                    申请 #{selectedStarApplication.id} ·{" "}
                    {selectedStarApplication.academic_term.term_name}
                  </p>
                </div>
                <SecondaryButton type="button" onClick={() => setSelectedStarId(null)}>
                  <X size={16} /> 收起
                </SecondaryButton>
              </div>
              <Field label="审核状态">
                <select
                  className={selectClassName}
                  value={starStatus}
                  onChange={(event) => setStarStatus(event.target.value as AuditStatus)}
                >
                  {AUDIT_STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="最终竞赛分">
                  <input
                    className={inputClassName}
                    type="number"
                    value={finalContestScore}
                    onChange={(event) => setFinalContestScore(event.target.value)}
                  />
                </Field>
                <Field label="审核总分">
                  <ReadOnlyValue>
                    {getStarPreviewScoreText(starStatus, isStarPreviewLoading, starPreview)}
                  </ReadOnlyValue>
                </Field>
              </div>
              <Field label="系统评定星级">
                <ReadOnlyValue>
                  {getStarPreviewLevelText(starStatus, isStarPreviewLoading, starPreview)}
                </ReadOnlyValue>
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="独特性审核">
                  <select
                    className={selectClassName}
                    value={uniquenessApproved}
                    onChange={(event) => setUniquenessApproved(event.target.value)}
                  >
                    <option value="">未定</option>
                    <option value="true">通过</option>
                    <option value="false">不通过</option>
                  </select>
                </Field>
                <Field label="成长故事">
                  <select
                    className={selectClassName}
                    value={growthStoryApproved}
                    onChange={(event) => setGrowthStoryApproved(event.target.value)}
                  >
                    <option value="">未定</option>
                    <option value="true">通过</option>
                    <option value="false">不通过</option>
                  </select>
                </Field>
              </div>
              <div className="rounded-md bg-surface-sunken p-3 text-sm text-content-muted">
                <p className="font-semibold text-content">申请内容</p>
                <p className="mt-2 whitespace-pre-wrap leading-6">
                  {selectedStarApplication.uniqueness_statement || "未填写特色说明。"}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <ExternalLink href={selectedStarApplication.contest_attachment}>
                    竞赛附件
                  </ExternalLink>
                  <ExternalLink href={selectedStarApplication.growth_story_url}>
                    成长故事
                  </ExternalLink>
                </div>
              </div>
              <PrimaryButton type="submit" loading={isStarReviewing}>
                <Save size={18} /> 提交审核
              </PrimaryButton>
            </div>
          </form>
        )}
      </div>
    </Surface>
  );
}
