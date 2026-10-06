export function canCancelClubActivity(activity: { cancelled_at: string | null }): boolean {
  // The server owns the time boundary; device clock skew must not hide it.
  return activity.cancelled_at === null;
}

export function countCurrentTermActivities(
  activities: Array<{ cancelled_at: string | null; academic_term: { is_current: boolean } }>,
): number {
  return activities.filter(
    (activity) => !activity.cancelled_at && activity.academic_term.is_current,
  ).length;
}
