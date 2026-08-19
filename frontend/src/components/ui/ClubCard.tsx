import { Link } from "react-router-dom";
import { Hash, Users } from "@/src/components/ui/Icons";
import type { components } from "../../api/schema";
import { cn } from "../../lib/utils";
import { CategoryChip, categorySpine } from "./CategoryChip";
import { StarLevel } from "./StarLevel";

type ClubInfo = components["schemas"]["ClubInfo"];

/**
 * The one club card.
 *
 * Home and ExploreClubs each had their own version, which is why the same club
 * showed a coloured category chip and its star level in one place and grey
 * category text and nothing else in the other. One component, two densities.
 *
 * The card is a posted object: a drawn border, a hard offset, a category spine
 * down the left edge, and a lift toward the top-left on hover as if picked off a
 * board. The spine is an edge rather than a fill, so category colour stays an
 * accent.
 */
export function ClubCard({
  club,
  density = "comfortable",
  className,
}: {
  club: ClubInfo;
  /** `compact` is for side panels; `comfortable` for the directory. */
  density?: "comfortable" | "compact";
  className?: string;
}) {
  const isCompact = density === "compact";
  const memberCount = club.members?.length ?? 0;

  return (
    <Link
      to={`/club/${club.id}`}
      className={cn(
        "group flex h-full items-start border border-l-4 border-edge bg-surface shadow-sm transition-all duration-200",
        "hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-lg",
        "focus-visible:ring-brand-strong/40 outline-none focus-visible:ring-4",
        "motion-reduce:transform-none motion-reduce:transition-none",
        isCompact ? "gap-3 rounded-md p-3" : "gap-4 rounded-md p-5",
        categorySpine(club.category),
        className,
      )}
    >
      <div
        className={cn(
          "flex shrink-0 items-center justify-center overflow-hidden rounded-sm bg-surface-hover",
          isCompact ? "h-14 w-14" : "h-16 w-16",
        )}
      >
        {club.logo_uri ? (
          <img
            src={club.logo_uri}
            alt={club.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <Hash
            className="text-content-subtle stroke-[1.5]"
            size={isCompact ? 22 : 28}
          />
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <CategoryChip category={club.category} size="sm" />
          {club.star_level !== "none" && (
            <StarLevel level={club.star_level} size="sm" showLabel={false} />
          )}
        </div>

        <h3
          className={cn(
            "mt-1.5 truncate font-semibold text-content",
            isCompact ? "text-base" : "font-display text-lg",
          )}
        >
          {club.name}
        </h3>

        <p className="mt-1 line-clamp-2 text-sm text-content-muted">
          {club.summary}
        </p>

        {!isCompact && (
          <p className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-content-subtle">
            <Users size={14} />
            {memberCount} 名成员
          </p>
        )}
      </div>
    </Link>
  );
}
