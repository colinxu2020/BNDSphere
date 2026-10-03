export function canCancelClubActivity(
  activity: { start_time: string; cancelled_at: string | null },
  now: Date = new Date(),
): boolean {
  return activity.cancelled_at === null && Date.parse(activity.start_time) > now.getTime();
}
