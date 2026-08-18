import type { components } from "../../api/schema";
import { CATEGORY_MAP } from "../../lib/labels";
import { cn } from "../../lib/utils";

type ClubCategory = components["schemas"]["ClubCategoryEnum"];

/**
 * Club category identity.
 *
 * Every category has one fixed treatment so a category reads the same colour
 * everywhere it appears. Before this, all eight rendered as the same teal badge,
 * which made a directory of clubs uniformly grey-green and unscannable.
 *
 * Two constraints from the design spec are enforced here rather than left to
 * call sites:
 *
 *  - The hues differ in LIGHTNESS as well as hue, so they stay distinguishable
 *    without relying on hue perception and survive the dark scheme.
 *  - Category colour is for SMALL elements only — never a large surface. There is
 *    deliberately no "fill a panel with the category colour" variant; adding one
 *    would turn the browse page into visual noise. Other small treatments (a left
 *    border accent, an icon field) get added when something actually needs one.
 *
 * 其他 (other) is neutral on purpose: it is the absence of a category, so giving
 * it a colour would imply an identity it does not have.
 *
 * Class strings are written out per category rather than interpolated, because
 * Tailwind scans source as text and never sees a constructed class name.
 */
const CHIP: Record<ClubCategory, string> = {
  science: "bg-cat-science-bg text-cat-science-fg border-cat-science-edge",
  humanity: "bg-cat-humanity-bg text-cat-humanity-fg border-cat-humanity-edge",
  arts: "bg-cat-arts-bg text-cat-arts-fg border-cat-arts-edge",
  sports: "bg-cat-sports-bg text-cat-sports-fg border-cat-sports-edge",
  business: "bg-cat-business-bg text-cat-business-fg border-cat-business-edge",
  charity: "bg-cat-charity-bg text-cat-charity-fg border-cat-charity-edge",
  campus: "bg-cat-campus-bg text-cat-campus-fg border-cat-campus-edge",
  other: "bg-cat-other-bg text-cat-other-fg border-cat-other-edge",
};

/**
 * The category spine — a thick left edge in the category's own colour.
 *
 * This is the signature device: a club card reads as a posted, colour-tabbed
 * thing rather than a table row, and a directory becomes scannable by category
 * at a glance without any of them shouting. It stays within the small-element
 * rule because it is an edge, not a fill.
 */
const SPINE: Record<ClubCategory, string> = {
  science: "border-l-cat-science-fg",
  humanity: "border-l-cat-humanity-fg",
  arts: "border-l-cat-arts-fg",
  sports: "border-l-cat-sports-fg",
  business: "border-l-cat-business-fg",
  charity: "border-l-cat-charity-fg",
  campus: "border-l-cat-campus-fg",
  other: "border-l-cat-other-fg",
};

/** Pair with `border-l-4` on the element. */
export function categorySpine(category: ClubCategory): string {
  return SPINE[category] ?? SPINE.other;
}

const SIZES = {
  sm: "px-2 py-0.5 text-[10px]",
  md: "px-2.5 py-1 text-xs",
  lg: "px-3 py-1 text-sm",
} as const;

export function CategoryChip({
  category,
  size = "md",
  className,
}: {
  category: ClubCategory;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border font-bold",
        CHIP[category] ?? CHIP.other,
        SIZES[size],
        className,
      )}
    >
      {CATEGORY_MAP[category] ?? category}
    </span>
  );
}

