/**
 * Home's derivations, moved out of the page.
 *
 * These decide things — which of a viewer's clubs have activities worth surfacing,
 * how the month grid is laid out — and the page is now a layout of tiles, so the
 * two belong apart.
 */
import type { components } from "../../api/schema";
import type { Tone } from "../../lib/tones";

type ClubInfo = components["schemas"]["ClubInfo"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ClubActivity = components["schemas"]["ClubActivityInfo"];
export type MyClubActivityStatus = "ended" | "ongoing" | "upcoming";
export type MyClubActivity = {
  activity: ClubActivity;
  club: ClubInfo;
  status: MyClubActivityStatus;
  distanceMs: number;
};

export const MY_CLUB_ACTIVITY_STATUS_TEXT: Record<MyClubActivityStatus, string> = {
  ended: "已结束",
  ongoing: "进行中",
  upcoming: "即将开始",
};

export function getMyClubActivityTone(status: MyClubActivityStatus): Tone {
  if (status === "ongoing") return "success";
  if (status === "ended") return "neutral";
  return "info";
}

export function getJoinedClubIds(clubs: ClubInfo[], userId?: number | null) {
  if (!userId) return new Set<number>();
  return new Set(
    clubs
      .filter((club) =>
        club.members.some(
          (member) =>
            member.user_id === userId &&
            ["member", "president", "vice_president"].includes(
              member.membership,
            ),
        ),
      )
      .map((club) => club.id),
  );
}

export function getMyClubActivities(clubs: ClubInfo[], userId?: number | null) {
  const joinedClubIds = getJoinedClubIds(clubs, userId);
  if (!joinedClubIds.size) return [];
  const now = new Date();
  const upcomingWindowMs = 14 * 24 * 60 * 60 * 1000;
  const endedWindowMs = 3 * 24 * 60 * 60 * 1000;

  return clubs
    .filter((club) => joinedClubIds.has(club.id))
    .flatMap((club) =>
      (club.club_activities || [])
        .map((activity) => {
          const start = new Date(activity.start_time);
          const end = new Date(activity.end_time);
          const startsInMs = start.getTime() - now.getTime();
          const endedAgoMs = now.getTime() - end.getTime();

          if (startsInMs > upcomingWindowMs) return null;
          if (endedAgoMs > endedWindowMs) return null;

          const status: MyClubActivityStatus =
            start <= now && end >= now
              ? "ongoing"
              : end < now
                ? "ended"
                : "upcoming";
          const distanceMs =
            status === "ended"
              ? endedAgoMs
              : Math.abs(start.getTime() - now.getTime());
          return { activity, club, status, distanceMs };
        })
        .filter((item): item is MyClubActivity => Boolean(item)),
    )
    .sort((left, right) => left.distanceMs - right.distanceMs);
}

export function buildMonthCalendar(items: GeneralActivity[]) {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const leadingBlankCount = (firstDay.getDay() + 6) % 7;
  const monthItems = items.filter((item) => {
    const date = new Date(item.starts_at || item.created_at);
    return date.getFullYear() === year && date.getMonth() === month;
  });

  const days: Array<{ date: Date | null; activities: GeneralActivity[] }> = [];
  for (let index = 0; index < leadingBlankCount; index += 1) {
    days.push({ date: null, activities: [] });
  }
  for (let dateNumber = 1; dateNumber <= daysInMonth; dateNumber += 1) {
    const date = new Date(year, month, dateNumber);
    days.push({
      date,
      activities: monthItems.filter((item) => {
        const itemDate = new Date(item.starts_at || item.created_at);
        return itemDate.getDate() === dateNumber;
      }),
    });
  }
  while (days.length % 7 !== 0) {
    days.push({ date: null, activities: [] });
  }

  return {
    days,
    monthLabel: `${year} 年 ${month + 1} 月`,
  };
}
