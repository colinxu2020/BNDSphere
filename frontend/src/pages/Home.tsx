import { useEffect, useMemo, useState, type ReactNode } from "react";
import { motion } from "motion/react";
import {
  ArrowUpRight,
  Bell,
  CalendarDays,
  Image,
  Megaphone,
  Users,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { CATEGORY_MAP } from "../lib/labels";
import { formatDate } from "../lib/format";
import { Badge, StatusMessage } from "../components/ui/AppPrimitives";
import { cn } from "../lib/utils";

type ClubInfo = components["schemas"]["ClubInfo"];
type ClubActivity = components["schemas"]["ClubActivityInfo"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type Announcement = components["schemas"]["AnnouncementInfo"];
type UserInfo = components["schemas"]["UserInfo"];
type MyClubActivityStatus = "ended" | "ongoing" | "upcoming";
type MyClubActivity = {
  activity: ClubActivity;
  club: ClubInfo;
  status: MyClubActivityStatus;
  distanceMs: number;
};

const calendarColors = [
  "bg-sky-500",
  "bg-emerald-500",
  "bg-amber-500",
  "bg-rose-500",
  "bg-violet-500",
  "bg-cyan-500",
];

export function Home() {
  const [clubs, setClubs] = useState<ClubInfo[]>([]);
  const [activities, setActivities] = useState<GeneralActivity[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const isLoggedIn = Boolean(localStorage.getItem("bnd_token"));

  useEffect(() => {
    let cancelled = false;
    const loadHome = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [clubResult, activityResult, announcementResult, userResult] = await Promise.all([
          client.GET("/api/v1/clubs/", { params: { query: { size: 24 } } }),
          client.GET("/api/v1/general-activities/", {
            params: { query: { size: 50 } },
          }),
          client.GET("/api/v1/announcements/", {
            params: { query: { size: 8, active_only: true } },
          }),
          isLoggedIn
            ? client.GET("/api/v1/users/me")
            : Promise.resolve({ data: null, error: null }),
        ]);

        if (cancelled) return;
        const firstError =
          clubResult.error || activityResult.error || announcementResult.error || userResult.error;
        if (firstError) setError(firstError);

        const allClubs = clubResult.data?.items || [];
        setUser(userResult.data || null);
        setActivities(activityResult.data?.items || []);
        setAnnouncements(announcementResult.data?.items || []);
        setClubs(allClubs);
      } catch (requestError) {
        if (!cancelled) setError(requestError);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    loadHome();
    return () => {
      cancelled = true;
    };
  }, [isLoggedIn]);

  const boardItems = useMemo(
    () => activities.filter((activity) => activity.poster_uri).slice(0, 5),
    [activities],
  );

  const calendar = useMemo(() => buildMonthCalendar(activities), [activities]);
  const showcaseClubs = clubs.slice(0, 6);
  const myClubActivities = useMemo(
    () => getMyClubActivities(clubs, user?.id).slice(0, 4),
    [clubs, user?.id],
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="grid gap-6 pb-20"
    >
      {error && <StatusMessage value={error} />}

      <div className="grid gap-6 lg:grid-cols-[1.55fr_0.85fr]">
        <div className="contents lg:flex lg:h-full lg:flex-col lg:gap-6">
          <section className="order-1 overflow-hidden rounded-md border border-slate-200 bg-white lg:h-[360px]">
            {isLoading ? (
              <div className="aspect-[16/7] animate-pulse bg-slate-100 lg:h-full lg:aspect-auto" />
            ) : boardItems.length ? (
              <BoardPanel items={boardItems} />
            ) : (
              <div className="aspect-[16/7] lg:h-full lg:aspect-auto">
                <EmptyPanel
                  icon={<Image size={28} />}
                  title="暂无展板内容"
                  description="发布大型活动的海报和文章链接后会显示在这里。"
                />
              </div>
            )}
          </section>

          <HomeClubPanel
            clubs={showcaseClubs}
            items={myClubActivities}
            isLoading={isLoading}
            isLoggedIn={isLoggedIn}
          />
        </div>

        <div className="contents lg:flex lg:h-full lg:flex-col lg:gap-6">
          <section className="order-4 rounded-md border border-slate-200 bg-white p-3 lg:order-1">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CalendarDays size={16} className="text-slate-500" />
                <h2 className="font-display text-base font-bold">活动日历</h2>
              </div>
              <span className="text-sm font-medium text-slate-500">{calendar.monthLabel}</span>
            </div>
            <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-slate-400">
              {["一", "二", "三", "四", "五", "六", "日"].map((day) => (
                <span key={day} className="py-1">
                  {day}
                </span>
              ))}
            </div>
            <div className="mt-1 grid grid-cols-7 gap-1">
              {calendar.days.map((day, index) => (
                <div
                  key={`${day.date || "blank"}-${index}`}
                  className={cn(
                    "group relative flex h-9 flex-col items-center justify-center rounded-sm border border-transparent text-sm",
                    day.activities.length && "hover:bg-sky-50 focus-within:bg-sky-50",
                  )}
                >
                  {day.date && (
                    <>
                      <button
                        type="button"
                        className="flex h-full w-full flex-col items-center justify-center rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
                        tabIndex={day.activities.length ? 0 : -1}
                        aria-label={
                          day.activities.length
                            ? `${day.date.getDate()} 日有 ${day.activities.length} 个活动`
                            : `${day.date.getDate()} 日暂无活动`
                        }
                      >
                        <span
                          className={cn(
                            "font-semibold",
                            day.activities.length ? "text-sky-700" : "text-slate-300",
                          )}
                        >
                          {day.date.getDate()}
                        </span>
                        <div className="mt-1 flex h-2 gap-0.5">
                          {day.activities.slice(0, 3).map((activity) => (
                            <span
                              key={activity.id}
                              className={cn(
                                "h-1.5 w-1.5 rounded-full",
                                calendarColors[Math.abs(activity.id) % calendarColors.length],
                              )}
                            />
                          ))}
                        </div>
                      </button>
                      {day.activities.length > 0 && (
                        <div
                          className={cn(
                            "pointer-events-none absolute left-1/2 top-full z-30 mt-2 w-64 -translate-x-1/2 rounded-md bg-slate-950 p-3 text-left text-white opacity-0 shadow-xl transition group-hover:opacity-100 group-focus-within:opacity-100",
                            index % 7 >= 5 && "left-auto right-0 translate-x-0",
                            index % 7 <= 1 && "left-0 translate-x-0",
                          )}
                        >
                          <div className="mb-2 text-xs font-semibold text-slate-300">
                            {day.date.getMonth() + 1} 月 {day.date.getDate()} 日
                          </div>
                          <div className="space-y-2">
                            {day.activities.slice(0, 3).map((activity) => (
                              <div key={activity.id}>
                                <p className="text-sm font-semibold">{activity.name}</p>
                                <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-slate-300">
                                  {activity.description || "暂无简介"}
                                </p>
                              </div>
                            ))}
                          </div>
                          {day.activities.length > 3 && (
                            <p className="mt-2 text-xs text-slate-400">
                              另有 {day.activities.length - 3} 个活动
                            </p>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </section>
          <AnnouncementPanel items={announcements} />
        </div>
      </div>
    </motion.div>
  );
}

function HomeClubPanel({
  clubs,
  items,
  isLoading,
  isLoggedIn,
}: {
  clubs: ClubInfo[];
  items: MyClubActivity[];
  isLoading: boolean;
  isLoggedIn: boolean;
}) {
  return (
    <section
      className={cn(
        "order-2 rounded-md border border-slate-200 bg-white p-5 lg:flex-1",
        isLoggedIn ? "min-h-[300px]" : "min-h-[220px]",
      )}
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isLoggedIn ? (
            <CalendarDays size={18} className="text-slate-500" />
          ) : (
            <Users size={18} className="text-slate-500" />
          )}
          <h2 className="font-display text-lg font-bold">
            {isLoggedIn ? "我的社团活动" : "社团风采"}
          </h2>
        </div>
        <Link
          to={isLoggedIn ? "/activities" : "/explore"}
          className="inline-flex items-center gap-1 text-sm font-semibold text-slate-600 hover:text-slate-900"
        >
          查看更多 <ArrowUpRight size={14} />
        </Link>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[...Array(4)].map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-md bg-slate-100" />
          ))}
        </div>
      ) : isLoggedIn ? (
        <MyClubActivityList items={items} emptyTitle="暂无我的社团活动" />
      ) : clubs.length ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {clubs.map((club) => (
            <Link
              key={club.id}
              to={`/club/${club.id}`}
              className="flex gap-3 rounded-md border border-slate-100 bg-slate-50 p-3 transition hover:border-slate-200 hover:bg-white"
            >
              <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-sm bg-white">
                {club.logo_uri ? (
                  <img src={club.logo_uri} alt={club.name} className="h-full w-full object-cover" />
                ) : (
                  <Users size={20} className="text-slate-400" />
                )}
              </div>
              <div className="min-w-0">
                <p className="truncate font-semibold text-slate-900">{club.name}</p>
                <p className="mt-1 line-clamp-2 text-sm text-slate-500">{club.summary}</p>
                <p className="mt-2 text-xs font-semibold text-slate-400">
                  {CATEGORY_MAP[club.category]}
                </p>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyPanel
          icon={<Users size={24} />}
          title="暂无公开社团"
          description="社团审核通过后会展示在这里。"
        />
      )}
    </section>
  );
}

function AnnouncementPanel({ items }: { items: Announcement[] }) {
  return (
    <section className="order-3 rounded-md border border-slate-200 bg-white p-5 lg:order-2 lg:flex-1">
      <div className="mb-4 flex items-center gap-2">
        <Megaphone size={18} className="text-slate-500" />
        <h2 className="font-display text-lg font-bold">公告</h2>
      </div>

      {items.length ? (
        <div className="space-y-3">
          {items.map((item) => (
            <a
              key={item.id}
              href={item.link_url || undefined}
              target={item.link_url ? "_blank" : undefined}
              rel="noreferrer"
              className="block rounded-md border border-slate-100 bg-slate-50 p-3 hover:bg-white"
            >
              <p className="font-semibold text-slate-900">{item.title}</p>
              <p className="mt-1 line-clamp-2 text-sm text-slate-500">{item.body}</p>
              <p className="mt-2 text-xs text-slate-400">{formatDate(item.created_at)}</p>
            </a>
          ))}
        </div>
      ) : (
        <EmptyPanel icon={<Bell size={24} />} title="暂无公告" />
      )}
    </section>
  );
}

function BoardPanel({ items }: { items: GeneralActivity[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const active = items[activeIndex] || items[0];

  useEffect(() => {
    if (items.length <= 1) return;
    const timer = window.setInterval(() => {
      setActiveIndex((index) => (index + 1) % items.length);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [items.length]);

  return (
    <a
      href={active.article_url || `/activities/${active.id}`}
      target={active.article_url ? "_blank" : undefined}
      rel="noreferrer"
      className="group relative block bg-[#020617] lg:h-full"
    >
      {active.poster_uri ? (
        <img
          src={active.poster_uri}
          alt={active.name}
          className="block h-auto w-full lg:h-full lg:object-fill"
        />
      ) : (
        <div className="flex aspect-[16/7] items-center justify-center bg-[#1e293b] text-slate-500">
          <Image size={42} />
        </div>
      )}
      <h1 className="absolute bottom-4 left-4 right-4 text-xl font-bold tracking-tight text-[white] drop-shadow-[0_2px_8px_rgba(15,23,42,0.9)]">
        {active.name}
      </h1>
    </a>
  );
}

function MyClubActivityList({
  items,
  emptyTitle = "暂无近期活动",
}: {
  items: MyClubActivity[];
  emptyTitle?: string;
}) {
  if (!items.length) {
    return <EmptyPanel icon={<CalendarDays size={24} />} title={emptyTitle} />;
  }
  return (
    <div className="space-y-3">
      {items.map((item) => (
        <Link
          key={`${item.club.id}-${item.activity.id}`}
          to={`/club/${item.club.id}`}
          className="block rounded-md border border-slate-100 bg-slate-50 p-3 hover:bg-white"
        >
          <div className="flex items-center justify-between gap-3">
            <p className="font-semibold text-slate-900">{item.activity.name}</p>
            <Badge tone={getMyClubActivityTone(item.status)}>
              {MY_CLUB_ACTIVITY_STATUS_TEXT[item.status]}
            </Badge>
          </div>
          <p className="mt-2 line-clamp-2 text-sm text-slate-500">{item.activity.description}</p>
          <p className="mt-2 text-xs text-slate-400">
            {item.club.name} · {formatDate(item.activity.start_time)}
          </p>
        </Link>
      ))}
    </div>
  );
}

function EmptyPanel({
  icon,
  title,
  description,
}: {
  icon: ReactNode;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex h-full min-h-40 flex-col items-center justify-center rounded-md border border-dashed border-slate-200 bg-slate-50 p-6 text-center text-slate-500">
      <div className="mb-3 text-slate-400">{icon}</div>
      <p className="font-semibold text-slate-700">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm">{description}</p>}
    </div>
  );
}

const MY_CLUB_ACTIVITY_STATUS_TEXT: Record<MyClubActivityStatus, string> = {
  ended: "已结束",
  ongoing: "进行中",
  upcoming: "即将开始",
};

function getMyClubActivityTone(status: MyClubActivityStatus) {
  if (status === "ongoing") return "green";
  if (status === "ended") return "slate";
  return "blue";
}

function getJoinedClubIds(clubs: ClubInfo[], userId?: number | null) {
  if (!userId) return new Set<number>();
  return new Set(
    clubs
      .filter((club) =>
        club.members.some(
          (member) =>
            member.user_id === userId &&
            ["member", "president", "vice_president"].includes(member.membership),
        ),
      )
      .map((club) => club.id),
  );
}

function getMyClubActivities(clubs: ClubInfo[], userId?: number | null) {
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
            start <= now && end >= now ? "ongoing" : end < now ? "ended" : "upcoming";
          const distanceMs =
            status === "ended" ? endedAgoMs : Math.abs(start.getTime() - now.getTime());
          return { activity, club, status, distanceMs };
        })
        .filter((item): item is MyClubActivity => Boolean(item)),
    )
    .sort((left, right) => left.distanceMs - right.distanceMs);
}

function buildMonthCalendar(items: GeneralActivity[]) {
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
