import { Seal, Star, StarFilled } from "@/src/components/ui/Icons";
import type { components } from "../../api/schema";
import { STAR_LEVEL_MAP } from "../../lib/labels";
import { cn } from "../../lib/utils";

type StarLevelEnum = components["schemas"]["ClubStarLevelEnum"];

/**
 * The club honours system, drawn.
 *
 * The canonical progression is a single ranked scale:
 *
 *   无星级 → 一星 → 二星 → 三星 → 四星 → 五星 → 荣誉社团
 *
 * 荣誉社团 is the HIGHEST LEVEL of that scale, not a parallel honour. It is
 * rendered as an elevated treatment on top of the five-star state — five filled
 * stars plus a seal — rather than a sixth star. The distinction is visual only;
 * semantically it is still the top rank, which is why RANK gives it 5 stars and
 * a separate flag instead of 6.
 *
 * Accessibility rule, binding on every variant: the textual level is always
 * present. When it is not shown visually it is rendered sr-only, so the stars
 * and the seal are never the only carrier of meaning.
 */
const RANK: Record<StarLevelEnum, number> = {
  none: 0,
  one_star: 1,
  two_star: 2,
  three_star: 3,
  four_star: 4,
  five_star: 5,
  honorary: 5,
};

const TOTAL_STARS = 5;

const SIZES = {
  sm: { icon: 12, text: "text-[11px]", gap: "gap-0.5" },
  md: { icon: 14, text: "text-xs", gap: "gap-1" },
  lg: { icon: 20, text: "text-sm", gap: "gap-1.5" },
} as const;

export function StarLevel({
  level,
  size = "md",
  showLabel = true,
  className,
}: {
  level: StarLevelEnum;
  size?: keyof typeof SIZES;
  /** When false the label is still rendered, sr-only. */
  showLabel?: boolean;
  className?: string;
}) {
  const label = STAR_LEVEL_MAP[level] ?? level;
  const { icon, text, gap } = SIZES[size];
  const rank = RANK[level];
  const isHonorary = level === "honorary";

  // 无星级 has nothing to draw; the text is the whole representation.
  if (level === "none") {
    return (
      <span
        className={cn(
          "bg-tone-neutral-bg text-tone-neutral-fg border-tone-neutral-edge inline-flex items-center rounded-md border px-2 py-0.5 font-semibold",
          text,
          className,
        )}
      >
        {label}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 font-bold",
        isHonorary
          ? "bg-tone-brand-bg text-tone-brand-fg border-tone-brand-edge"
          : "bg-brand-subtle text-tone-brand-fg border-tone-brand-edge",
        text,
        gap,
        className,
      )}
    >
      {isHonorary && <Seal size={icon} aria-hidden="true" />}
      <span className={cn("inline-flex items-center", gap)} aria-hidden="true">
        {Array.from({ length: TOTAL_STARS }, (_, i) =>
          i < rank ? (
            <StarFilled key={i} size={icon} className="text-brand" />
          ) : (
            <Star key={i} size={icon} className="text-content-subtle" />
          ),
        )}
      </span>
      <span className={showLabel ? undefined : "sr-only"}>{label}</span>
    </span>
  );
}

/**
 * Dense variant for workbench tables and moderation queues, where five glyphs
 * per row is too much. The number carries the rank and the text carries the
 * meaning; a single star is decoration only.
 */
export function StarLevelCompact({
  level,
  className,
}: {
  level: StarLevelEnum;
  className?: string;
}) {
  const label = STAR_LEVEL_MAP[level] ?? level;

  if (level === "none") {
    return (
      <span className={cn("text-content-subtle text-xs", className)}>
        {label}
      </span>
    );
  }

  return (
    <span
      className={cn(
        "text-tone-brand-fg inline-flex items-center gap-1 text-xs font-bold",
        className,
      )}
    >
      {level === "honorary" ? (
        <Seal size={12} aria-hidden="true" />
      ) : (
        <StarFilled size={12} aria-hidden="true" />
      )}
      {label}
    </span>
  );
}
