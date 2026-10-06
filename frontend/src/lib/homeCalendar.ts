import type { components } from "../api/schema";

type GeneralActivity = Pick<
  components["schemas"]["GeneralActivityInfo"],
  "id" | "name" | "description" | "starts_at" | "created_at"
>;
type ClubActivity = Pick<
  components["schemas"]["ClubActivityInfo"],
  "id" | "name" | "description" | "start_time"
> &
  Partial<Pick<components["schemas"]["ClubActivityInfo"], "cancelled_at">>;
type CalendarActivity = {
  key: string;
  id: number;
  name: string;
  description: string;
  startsAt: string;
};

export function buildMonthCalendar(
  generalActivities: GeneralActivity[],
  clubActivities: ClubActivity[],
  today = new Date(),
) {
  const items: CalendarActivity[] = [
    ...generalActivities.map((activity) => ({
      key: `general-${activity.id}`,
      id: activity.id,
      name: activity.name,
      description: activity.description,
      startsAt: activity.starts_at || activity.created_at,
    })),
    ...clubActivities
      .filter((activity) => !activity.cancelled_at)
      .map((activity) => ({
        key: `club-${activity.id}`,
        id: activity.id,
        name: activity.name,
        description: activity.description,
        startsAt: activity.start_time,
      })),
  ];
  const year = today.getFullYear();
  const month = today.getMonth();
  const firstDay = new Date(year, month, 1);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const leadingBlankCount = (firstDay.getDay() + 6) % 7;
  const monthItems = items.filter((item) => {
    const date = new Date(item.startsAt);
    return date.getFullYear() === year && date.getMonth() === month;
  });

  const days: Array<{ date: Date | null; activities: CalendarActivity[] }> = [];
  for (let index = 0; index < leadingBlankCount; index += 1) {
    days.push({ date: null, activities: [] });
  }
  for (let dateNumber = 1; dateNumber <= daysInMonth; dateNumber += 1) {
    const date = new Date(year, month, dateNumber);
    days.push({
      date,
      activities: monthItems.filter((item) => {
        const itemDate = new Date(item.startsAt);
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
