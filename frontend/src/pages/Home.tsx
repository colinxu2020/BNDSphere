import { useEffect, useMemo, useState, type ReactNode } from "react";
import { motion } from "motion/react";
import {
  ArrowUpRight,
  Bell,
  CalendarDays,
  Image,
  Pause,
  Play,
  Megaphone,
  Users,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import { ClubCard } from "../components/ui/ClubCard";
import type { Tone } from "../lib/tones";
import type { components } from "../api/schema";
import { formatDate } from "../lib/format";
import { Badge, StatusMessage } from "../components/ui/AppPrimitives";
import { cn } from "../lib/utils";
import { usePrefersReducedMotion } from "../lib/usePrefersReducedMotion";

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

// Rotating accents that distinguish adjacent calendar entries. These carry no
// meaning, which is why they are the accent-* tokens and not the club category
// hues — those do carry meaning and must stay stable per category.
const calendarColors = [
  "bg-accent-1",
  "bg-accent-2",
  "bg-accent-3",
  "bg-accent-4",
  "bg-accent-5",
  "bg-accent-6",
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
        const [clubResult, activityResult, announcementResult, userResult] =
          await Promise.all([
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
          clubResult.error ||
          activityResult.error ||
          announcementResult.error ||
          userResult.error;
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
      className="grid gap-6"
    >
      {/* The board is the hero, so the page title is not shown — but the page
          still needs one heading for structure and screen readers. */}
      <h1 className="sr-only">十一学校社团云平台 · 展板</h1>

      {error && <StatusMessage value={error} />}

      <div className="grid gap-6 lg:grid-cols-[1.55fr_0.85fr]">
        <div className="contents lg:flex lg:h-full lg:flex-col lg:gap-6">
          <section className="order-1 lg:h-[360px]">
            {isLoading ? (
              <div className="aspect-[16/7] animate-pulse bg-surface-hover lg:h-full lg:aspect-auto" />
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
          <section className="order-2 rounded-md border border-edge bg-surface p-3">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CalendarDays size={16} className="text-content-muted" />
                <h2 className="font-display text-base font-bold">活动日历</h2>
              </div>
              <span className="text-sm font-medium text-content-muted">
                {calendar.monthLabel}
              </span>
            </div>
            <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-content-subtle">
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
                    day.activities.length &&
                      "hover:bg-tone-info-bg focus-within:bg-tone-info-bg",
                  )}
                >
                  {day.date && (
                    <>
                      <button
                        type="button"
                        className="flex h-full w-full flex-col items-center justify-center rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-tone-info-edge"
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
                            day.activities.length
                              ? "text-tone-info-fg"
                              : "text-content-subtle",
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
                                calendarColors[
                                  Math.abs(activity.id) % calendarColors.length
                                ],
                              )}
                            />
                          ))}
                        </div>
                      </button>
                      {day.activities.length > 0 && (
                        <div
                          className={cn(
                            "pointer-events-none absolute left-1/2 top-full z-30 mt-2 w-64 -translate-x-1/2 rounded-md bg-surface-inverted p-3 text-left text-content-on-inverted opacity-0 shadow-xl transition group-hover:opacity-100 group-focus-within:opacity-100",
                            index % 7 >= 5 && "left-auto right-0 translate-x-0",
                            index % 7 <= 1 && "left-0 translate-x-0",
                          )}
                        >
                          <div className="mb-2 text-xs font-semibold text-content-on-inverted-muted">
                            {day.date.getMonth() + 1} 月 {day.date.getDate()} 日
                          </div>
                          <div className="space-y-2">
                            {day.activities.slice(0, 3).map((activity) => (
                              <div key={activity.id}>
                                <p className="text-sm font-semibold">
                                  {activity.name}
                                </p>
                                <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-content-on-inverted-muted">
                                  {activity.description || "暂无简介"}
                                </p>
                              </div>
                            ))}
                          </div>
                          {day.activities.length > 3 && (
                            <p className="mt-2 text-xs text-content-subtle">
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
        "order-3 rounded-md border border-edge bg-surface p-5 lg:flex-1",
        isLoggedIn ? "min-h-[300px]" : "min-h-[220px]",
      )}
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isLoggedIn ? (
            <CalendarDays size={18} className="text-content-muted" />
          ) : (
            <Users size={18} className="text-content-muted" />
          )}
          <h2 className="font-display text-lg font-bold">
            {isLoggedIn ? "我的社团活动" : "社团风采"}
          </h2>
        </div>
        <Link
          to={isLoggedIn ? "/activities" : "/explore"}
          className="inline-flex items-center gap-1 text-sm font-semibold text-content-muted hover:text-content"
        >
          查看更多 <ArrowUpRight size={14} />
        </Link>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[...Array(4)].map((_, index) => (
            <div
              key={index}
              className="h-28 animate-pulse rounded-md bg-surface-hover"
            />
          ))}
        </div>
      ) : isLoggedIn ? (
        <MyClubActivityList items={items} emptyTitle="暂无我的社团活动" />
      ) : clubs.length ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {clubs.map((club) => (
            <ClubCard key={club.id} club={club} density="compact" />
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
    <section className="order-4 rounded-md border border-edge bg-surface p-5 lg:flex-1">
      <div className="mb-4 flex items-center gap-2">
        <Megaphone size={18} className="text-content-muted" />
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
              className="block rounded-md border border-edge-subtle bg-surface-sunken p-3 hover:bg-surface"
            >
              <p className="font-semibold text-content">{item.title}</p>
              <p className="mt-1 line-clamp-2 text-sm text-content-muted">
                {item.body}
              </p>
              <p className="mt-2 text-xs text-content-subtle">
                {formatDate(item.created_at)}
              </p>
            </a>
          ))}
        </div>
      ) : (
        <EmptyPanel icon={<Bell size={24} />} title="暂无公告" />
      )}
    </section>
  );
}

/**
 * The 展板 — the board itself, and the front door of the product.
 *
 * Three corrections to the previous version:
 *
 *  - It auto-advanced every five seconds with no way to stop it, which fails
 *    WCAG 2.2.2 (Pause, Stop, Hide). Hover and focus pausing is a courtesy, not a
 *    conforming mechanism — 2.2.2 wants a control the user can actually operate,
 *    and a keyboard or touch user has no way to "hover away". There is now an
 *    explicit pause/resume button, and the auto-advance additionally never starts
 *    for anyone who has asked for reduced motion.
 *  - There was no way to tell how many posters existed or to reach a specific
 *    one. The indicators are real buttons, so the board is keyboard-operable.
 *  - The caption floated over the artwork behind a hardcoded rgba halo. It now
 *    sits in a solid bar on the inverted surface, which is legible over any
 *    poster and follows the scheme. It is also no longer an <h1>: it is one
 *    panel among several, and the page's other panels use <h2>.
 */
function BoardPanel({ items }: { items: GeneralActivity[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [userPaused, setUserPaused] = useState(false);
  const [pointerPaused, setPointerPaused] = useState(false);
  const prefersReducedMotion = usePrefersReducedMotion();
  const active = items[activeIndex] || items[0];

  const canRotate = items.length > 1 && !prefersReducedMotion;
  const rotating = canRotate && !userPaused && !pointerPaused;

  useEffect(() => {
    if (!rotating) return;
    const timer = window.setInterval(() => {
      setActiveIndex((index) => (index + 1) % items.length);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [rotating, items.length]);

  // Guard against the list shrinking under us.
  useEffect(() => {
    if (activeIndex >= items.length) setActiveIndex(0);
  }, [activeIndex, items.length]);

  return (
    <div
      className="relative flex h-full flex-col overflow-hidden rounded-md border border-edge bg-surface-media shadow-md"
      onMouseEnter={() => setPointerPaused(true)}
      onMouseLeave={() => setPointerPaused(false)}
      onFocusCapture={() => setPointerPaused(true)}
      onBlurCapture={() => setPointerPaused(false)}
    >
      <a
        href={active.article_url || `/activities/${active.id}`}
        target={active.article_url ? "_blank" : undefined}
        rel="noreferrer"
        className="group relative block flex-1 outline-none focus-visible:ring-4 focus-visible:ring-brand/40"
      >
        {active.poster_uri ? (
          <img
            src={active.poster_uri}
            alt={active.name}
            className="block h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full min-h-48 items-center justify-center text-content-on-inverted-muted">
            <Image size={42} />
          </div>
        )}
      </a>

      <div className="flex items-center justify-between gap-3 bg-surface-inverted px-4 py-3">
        <h2 className="min-w-0 truncate font-display text-lg font-bold text-content-on-inverted">
          {active.name}
        </h2>
        {items.length > 1 && (
          <div className="flex shrink-0 items-center gap-2">
            {canRotate && (
              <button
                type="button"
                onClick={() => setUserPaused((wasPaused) => !wasPaused)}
                aria-pressed={userPaused}
                aria-label={userPaused ? "继续自动轮播" : "暂停自动轮播"}
                className="inline-flex h-8 w-8 items-center justify-center rounded-md text-content-on-inverted outline-none hover:bg-surface-inverted-hover focus-visible:ring-2 focus-visible:ring-brand/60"
              >
                {userPaused ? <Play size={15} /> : <Pause size={15} />}
              </button>
            )}
            <div className="flex items-center gap-1.5">
            {items.map((item, index) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setActiveIndex(index)}
                aria-label={`显示第 ${index + 1} 张展板:${item.name}`}
                aria-current={index === activeIndex}
                className={cn(
                  "h-2.5 w-2.5 rounded-full outline-none transition-colors focus-visible:ring-2 focus-visible:ring-brand/60",
                  index === activeIndex
                    ? "bg-content-on-inverted"
                    : "bg-content-on-inverted-muted hover:bg-content-on-inverted",
                )}
              />
            ))}
            </div>
          </div>
        )}
      </div>
    </div>
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
          className="block rounded-md border border-edge-subtle bg-surface-sunken p-3 hover:bg-surface"
        >
          <div className="flex items-center justify-between gap-3">
            <p className="font-semibold text-content">{item.activity.name}</p>
            <Badge tone={getMyClubActivityTone(item.status)}>
              {MY_CLUB_ACTIVITY_STATUS_TEXT[item.status]}
            </Badge>
          </div>
          <p className="mt-2 line-clamp-2 text-sm text-content-muted">
            {item.activity.description}
          </p>
          <p className="mt-2 text-xs text-content-subtle">
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
    <div className="flex h-full min-h-40 flex-col items-center justify-center rounded-md border border-dashed border-edge bg-surface-sunken p-6 text-center text-content-muted">
      <div className="mb-3 text-content-subtle">{icon}</div>
      <p className="font-semibold text-content">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm">{description}</p>}
    </div>
  );
}

const MY_CLUB_ACTIVITY_STATUS_TEXT: Record<MyClubActivityStatus, string> = {
  ended: "已结束",
  ongoing: "进行中",
  upcoming: "即将开始",
};

function getMyClubActivityTone(status: MyClubActivityStatus): Tone {
  if (status === "ongoing") return "success";
  if (status === "ended") return "neutral";
  return "info";
}

function getJoinedClubIds(clubs: ClubInfo[], userId?: number | null) {
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
