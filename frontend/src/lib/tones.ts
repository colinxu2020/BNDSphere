import type { components } from "../api/schema";

/**
 * The single tone vocabulary.
 *
 * Before this there were three overlapping ones: Badge took colour names
 * (slate/primary/yellow/green/red/blue), StatusMessage took semantic names
 * (error/success/info), and Federation kept a private getAuditTone mapping audit
 * status to Badge's colour names. Colour names in a component API mean a palette
 * change becomes a rename across every call site, and they say nothing about why
 * a thing is yellow.
 *
 * `brand` and `info` are deliberately separate concerns even though their hues
 * start out similar: `brand` is identity and emphasis (this product, this club,
 * this call to action), `info` is a system or informational state. They may
 * diverge later, and code that conflated them would have to be untangled then.
 */
export type Tone =
  | "neutral"
  | "brand"
  | "info"
  | "success"
  | "warning"
  | "danger";

type AuditStatus = components["schemas"]["AuditStatusEnum"];
type ModerationStatus = components["schemas"]["ModerationStatusEnum"];
type ClubStatus = components["schemas"]["ClubStatusEnum"];
type Membership = components["schemas"]["ClubMembershipEnum"];
type Role = components["schemas"]["RoleEnum"];

/**
 * Status-to-tone mapping, decided once here rather than per call site.
 *
 * The shape of the rule across every family: work that is not finished is
 * `warning`, a bad outcome is `danger`, a good outcome is `success`, a position
 * of responsibility is `brand`, and an inactive end state is `neutral`.
 */
export const AUDIT_TONE: Record<AuditStatus, Tone> = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
};

export const MODERATION_TONE: Record<ModerationStatus, Tone> = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
  superseded: "neutral",
};

export const CLUB_STATUS_TONE: Record<ClubStatus, Tone> = {
  unreviewed: "warning",
  normal: "success",
  archived: "neutral",
};

export const MEMBERSHIP_TONE: Record<Membership, Tone> = {
  pending: "warning",
  member: "neutral",
  president: "brand",
  vice_president: "brand",
  left: "neutral",
};

export const ROLE_TONE: Record<Role, Tone> = {
  ban: "danger",
  user: "neutral",
  moderator: "info",
  federation_staff: "info",
  admin: "brand",
  dev: "brand",
};

/** Tailwind class triples per tone. Written out rather than interpolated,
 *  because Tailwind scans source as text and never sees a built class name. */
export const TONE_CLASSES: Record<Tone, string> = {
  neutral: "bg-tone-neutral-bg text-tone-neutral-fg border-tone-neutral-edge",
  brand: "bg-tone-brand-bg text-tone-brand-fg border-tone-brand-edge",
  info: "bg-tone-info-bg text-tone-info-fg border-tone-info-edge",
  success: "bg-tone-success-bg text-tone-success-fg border-tone-success-edge",
  warning: "bg-tone-warning-bg text-tone-warning-fg border-tone-warning-edge",
  danger: "bg-tone-danger-bg text-tone-danger-fg border-tone-danger-edge",
};
