import { Link } from "react-router-dom";
import { ArrowUpRight, CalendarDays } from "@/src/components/ui/Icons";
import type { components } from "../../api/schema";
import { formatDate } from "../../lib/format";
import { ACTIVITY_LEVEL_MAP } from "../../lib/labels";
import { cn } from "../../lib/utils";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ActivityLevel = components["schemas"]["GeneralActivityLevelEnum"];

/**
 * Activity level identity — 校级 / 大型 / 社联.
 *
 * A level is what an activity IS, so it gets identity treatment like a club
 * category, not a status tone. Its own hues rather than borrowed category ones,
 * so a 校级 activity chip is never mistaken for a 科学 club chip.
 *
 * Written out per level: Tailwind scans source as text and never sees a
 * constructed class name.
 */
const LEVEL_CHIP: Record<ActivityLevel, string> = {
  school: "bg-level-school-bg text-level-school-fg border-level-school-edge",
  large: "bg-level-large-bg text-level-large-fg border-level-large-edge",
  club_federation: "bg-level-federation-bg text-level-federation-fg border-level-federation-edge",
};

const LEVEL_SPINE: Record<ActivityLevel, string> = {
  school: "border-l-level-school-fg",
  large: "border-l-level-large-fg",
  club_federation: "border-l-level-federation-fg",
};

export function ActivityLevelChip({
  level,
  className,
}: {
  level: ActivityLevel;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-bold",
        LEVEL_CHIP[level] ?? LEVEL_CHIP.school,
        className,
      )}
    >
      {ACTIVITY_LEVEL_MAP[level] ?? level}
    </span>
  );
}

/**
 * The one activity card — the same posted-object language as ClubCard, with the
 * level spine replacing the category spine and the date carrying the emphasis,
 * because what a student wants from an activity is when it is.
 */
export function ActivityCard({
  activity,
  className,
}: {
  activity: GeneralActivity;
  className?: string;
}) {
  const recordCount = activity.club_records?.length ?? 0;

  return (
    <Link
      to={`/activities/${activity.id}`}
      className={cn(
        "group flex h-full flex-col border border-l-4 border-edge bg-surface p-6 shadow-sm transition-all duration-200",
        "rounded-md hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-lg",
        "focus-visible:ring-brand-strong/40 outline-none focus-visible:ring-4",
        "motion-reduce:transform-none motion-reduce:transition-none",
        LEVEL_SPINE[activity.level] ?? LEVEL_SPINE.school,
        className,
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <ActivityLevelChip level={activity.level} />
        <ArrowUpRight
          size={18}
          className="shrink-0 text-content-subtle transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 motion-reduce:transform-none"
        />
      </div>

      <h3 className="mt-3 font-display text-lg font-semibold text-content">{activity.name}</h3>

      <p className="mt-2 line-clamp-2 text-sm text-content-muted">{activity.description}</p>

      <div className="mt-auto flex flex-wrap items-center gap-3 pt-5 text-xs font-semibold text-content-subtle">
        <span className="inline-flex items-center gap-1.5">
          <CalendarDays size={14} />
          {formatDate(activity.created_at)}
        </span>
        <span>{recordCount} 条社团记录</span>
      </div>
    </Link>
  );
}
