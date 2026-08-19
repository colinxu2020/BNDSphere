import { Hash, Sparkles } from "@/src/components/ui/Icons";
import type { components } from "../../api/schema";
import {
  Badge,
  EmptyState,
  InlineError,
  SectionTitle,
  Surface,
} from "../../components/ui/AppPrimitives";
import { CategoryChip } from "../../components/ui/CategoryChip";
import { StarLevel, StarLevelCompact } from "../../components/ui/StarLevel";
import { stringifyBackendValue } from "../../lib/format";

type ClubInfo = components["schemas"]["ClubInfo"];
type StarRating = components["schemas"]["StarRatingResponse"];

/**
 * ClubWorkspace's read-only sections.
 *
 * Three panels that render shared data and own nothing: the backend's load errors,
 * the club header that says which club you are managing, and the current star
 * rating. Grouped in one module because they are the same kind of thing — display —
 * and separating them from the four editors is most of what made the page hard to
 * read.
 */
export function LoadErrorsSection({ errors }: { errors: Record<string, unknown> }) {
  return (
            <Surface density="compact">
    <SectionTitle density="compact"
      title="加载反馈"
      description="以下内容直接来自后端响应。"
    />
    <div className="grid gap-3">
      {Object.entries(errors).map(([key, value]) => (
        <div key={key}>
          <InlineError
            value={`${key}: ${stringifyBackendValue(value)}`}
          />
        </div>
      ))}
    </div>
            </Surface>
  );
}

export function ClubHeaderSection({ club }: { club: ClubInfo }) {
  return (
            <Surface density="compact">
    <div className="flex flex-col md:flex-row md:items-center gap-5">
      <div className="w-20 h-20 rounded-md bg-surface-hover flex items-center justify-center shrink-0 overflow-hidden border border-edge">
        {club.logo_uri ? (
          <img
            src={club.logo_uri}
            alt={club.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <Hash className="text-content-subtle" size={30} />
        )}
      </div>
      <div className="flex-1">
        <div className="flex flex-wrap gap-2 mb-2">
          <CategoryChip category={club.category} />
          <StarLevel level={club.star_level} />
        </div>
        <h2 className="text-2xl font-display font-bold text-content">
          {club.name}
        </h2>
        <p className="text-content-muted mt-1">{club.summary}</p>
      </div>
    </div>
            </Surface>
  );
}

export function StarRatingSection({
  starRating,
}: {
  starRating: StarRating | null;
}) {
  return (
    <Surface density="compact">
      <SectionTitle density="compact" icon={<Sparkles size={20} />} title="星级评价" />
      {starRating ? (
        <div className="flex flex-col gap-5">
          <div className="rounded-md border border-edge-subtle bg-surface-sunken p-5">
            <p className="text-sm font-medium text-content-muted">当前总分</p>
            <p className="mt-2 text-4xl font-display font-bold text-content">
              {starRating.total_score}
            </p>
            <p className="mt-2">
              <StarLevelCompact level={starRating.star_level} />
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Badge tone="brand">
              会议出勤 {starRating.breakdown.meeting_attendance}
            </Badge>
            <Badge tone="brand">
              活动参与 {starRating.breakdown.activity_participation}
            </Badge>
            <Badge tone="brand">
              内部活动 {starRating.breakdown.internal_activities}
            </Badge>
            <Badge tone="brand">
              社团历史 {starRating.breakdown.club_history}
            </Badge>
          </div>
          <p className="text-sm text-content-muted">
            内部活动 {starRating.internal_activity_count} 次，社团年限{" "}
            {starRating.club_age_years} 年。
          </p>
        </div>
      ) : (
        <EmptyState title="暂无星级评价" />
      )}
    </Surface>
  );
}
