import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import {
  CalendarDays,
  Image,
  Inbox,
  Megaphone,
  Users,
} from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { Badge, StatusMessage } from "../components/ui/AppPrimitives";
import { ActivityLevelChip } from "../components/ui/ActivityCard";
import { ClubCard } from "../components/ui/ClubCard";
import { formatDate } from "../lib/format";
import { cn } from "../lib/utils";
import {
  buildMonthCalendar,
  getMyClubActivities,
  getMyClubActivityTone,
  MY_CLUB_ACTIVITY_STATUS_TEXT,
  type MyClubActivity,
} from "./home/logic";

type ClubSummaryInfo = components["schemas"]["ClubSummaryInfo"];
type ClubInfo = components["schemas"]["ClubInfo"];
type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type Announcement = components["schemas"]["AnnouncementInfo"];
type UserInfo = components["schemas"]["UserInfo"];

/**
 * 展板 — the board.
 *
 * The front door is the wall itself. Club recruitment at this school happens on a
 * board of posters, so this is one scannable surface of posted things rather than a
 * dashboard of panels: poster tiles, club cards with their category spine and rank,
 * the notices slip, activity tiles, the month grid.
 *
 * Masonry via CSS columns, so tiles of genuinely different heights pack without a
 * grid forcing them onto shared rows — which is what left the previous two-column
 * layout with large gaps.
 *
 * One clubs request either way. Logged out it uses GET /clubs/summary, the light
 * payload built for card surfaces. Logged in it uses the full list, because "my
 * club activities" needs each club's nested activities and membership, and the
 * showcase is then derived from what is already in hand rather than fetched twice.
 */
export function Home() {
  const [clubCards, setClubCards] = useState<ClubSummaryInfo[]>([]);
  const [fullClubs, setFullClubs] = useState<ClubInfo[]>([]);
  const [activities, setActivities] = useState<GeneralActivity[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  const isLoggedIn = Boolean(localStorage.getItem("bnd_token"));

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const [clubsResult, activitiesResult, announcementsResult, meResult] =
          await Promise.all([
            isLoggedIn
              ? client.GET("/api/v1/clubs/", { params: { query: { size: 24 } } })
              : client.GET("/api/v1/clubs/summary", {
                  params: { query: { size: 24 } },
                }),
            client.GET("/api/v1/general-activities/", {
              params: { query: { size: 12 } },
            }),
            client.GET("/api/v1/announcements/", {
              params: { query: { size: 6 } },
            }),
            isLoggedIn ? client.GET("/api/v1/users/me") : null,
          ]);
        if (cancelled) return;

        const failure =
          clubsResult.error ||
          activitiesResult.error ||
          announcementsResult.error;
        if (failure) setError(failure);

        if (isLoggedIn) {
          const clubs = (clubsResult.data?.items ?? []) as ClubInfo[];
          setFullClubs(clubs);
          setClubCards(
            clubs.map((club) => ({
              ...club,
              member_count: club.members.length,
            })),
          );
        } else {
          setFullClubs([]);
          setClubCards((clubsResult.data?.items ?? []) as ClubSummaryInfo[]);
        }
        setActivities(activitiesResult.data?.items ?? []);
        setAnnouncements(announcementsResult.data?.items ?? []);
        setUser(meResult && !meResult.error ? (meResult.data ?? null) : null);
      } catch (requestError) {
        if (!cancelled) setError(requestError);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [isLoggedIn]);

  const posters = activities.filter((activity) => activity.poster_uri);
  const featured = posters[0] ?? activities[0];
  const restActivities = activities.filter((item) => item.id !== featured?.id);
  const myActivities = getMyClubActivities(fullClubs, user?.id);
  const calendar = buildMonthCalendar(activities);

  const isEmpty =
    !isLoading &&
    clubCards.length === 0 &&
    activities.length === 0 &&
    announcements.length === 0;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="w-full px-4 py-5 sm:px-5 lg:px-6"
    >
      <h1 className="sr-only">十一学校社团云平台 · 展板</h1>

      {error != null && (
        <div className="mb-4">
          <StatusMessage value={error} />
        </div>
      )}

      {isLoading ? (
        <BoardSkeleton />
      ) : isEmpty ? (
        <EmptyBoard />
      ) : (
        <div className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4 [&>*]:mb-4">
          {featured && <PosterTile activity={featured} />}

          {myActivities.length > 0 && <MyActivitiesTile items={myActivities} />}

          {announcements.length > 0 && (
            <AnnouncementsTile items={announcements} />
          )}

          {clubCards.slice(0, 5).map((club) => (
            <div key={club.id} className="break-inside-avoid">
              <ClubCard club={club} density="compact" />
            </div>
          ))}

          {restActivities.slice(0, 4).map((activity) => (
            <ActivityTile key={activity.id} activity={activity} />
          ))}

          {clubCards.slice(5).map((club) => (
            <div key={club.id} className="break-inside-avoid">
              <ClubCard club={club} density="compact" />
            </div>
          ))}

          <CalendarTile calendar={calendar} />
        </div>
      )}
    </motion.div>
  );
}

function Tile({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={cn(
        "break-inside-avoid rounded-md border border-edge bg-surface p-4 shadow-sm",
        className,
      )}
    >
      {children}
    </section>
  );
}

function TileHeading({
  icon,
  children,
  action,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-3 flex items-center justify-between gap-2">
      <h2 className="font-display flex items-center gap-2 text-base font-bold text-content">
        <span className="text-content-subtle">{icon}</span>
        {children}
      </h2>
      {action}
    </div>
  );
}

/** The board's focal tile: the poster, at poster proportions. */
function PosterTile({ activity }: { activity: GeneralActivity }) {
  const href = activity.article_url || `/activities/${activity.id}`;
  const isExternal = Boolean(activity.article_url);
  const shell =
    "group block break-inside-avoid overflow-hidden rounded-md border border-edge bg-surface-media shadow-md outline-none transition-all duration-200 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-lg focus-visible:ring-4 focus-visible:ring-brand-strong/40 motion-reduce:transform-none motion-reduce:transition-none";

  const body = (
    <>
      {activity.poster_uri ? (
        <img
          src={activity.poster_uri}
          alt={activity.name}
          className="block aspect-[4/5] w-full object-cover"
        />
      ) : (
        <div className="flex aspect-[4/5] items-center justify-center bg-surface-media">
          <Image size={40} className="text-content-on-inverted-muted" />
        </div>
      )}
      <div className="flex items-center justify-between gap-2 bg-surface-inverted px-3 py-2.5">
        <span className="font-display min-w-0 truncate text-sm font-bold text-content-on-inverted">
          {activity.name}
        </span>
        <span className="shrink-0 text-xs font-semibold text-content-on-inverted-muted">
          {formatDate(activity.starts_at || activity.created_at)}
        </span>
      </div>
    </>
  );

  return isExternal ? (
    <a href={href} target="_blank" rel="noreferrer" className={shell}>
      {body}
    </a>
  ) : (
    <Link to={href} className={shell}>
      {body}
    </Link>
  );
}

function ActivityTile({ activity }: { activity: GeneralActivity }) {
  return (
    <Link
      to={`/activities/${activity.id}`}
      className="group block break-inside-avoid rounded-md border border-edge bg-surface p-4 shadow-sm outline-none transition-all duration-200 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-lg focus-visible:ring-4 focus-visible:ring-brand-strong/40 motion-reduce:transform-none motion-reduce:transition-none"
    >
      <ActivityLevelChip level={activity.level} />
      <h3 className="font-display mt-2 text-base font-bold text-content">
        {activity.name}
      </h3>
      <p className="mt-1 line-clamp-3 text-sm text-content-muted">
        {activity.description}
      </p>
      <p className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-content-subtle">
        <CalendarDays size={13} />
        {formatDate(activity.starts_at || activity.created_at)}
      </p>
    </Link>
  );
}

/** Notices read as a slip pinned to the board, so they carry the warning tone. */
function AnnouncementsTile({ items }: { items: Announcement[] }) {
  return (
    <Tile className="border-tone-warning-edge bg-tone-warning-bg">
      <h2 className="font-display mb-2 flex items-center gap-2 text-xs font-bold tracking-[0.18em] text-tone-warning-fg uppercase">
        <Megaphone size={14} /> 公告
      </h2>
      <ul className="flex flex-col gap-2.5">
        {items.map((item) => (
          <li key={item.id}>
            <p className="text-sm font-semibold text-content">{item.title}</p>
            <p className="mt-0.5 text-xs text-content-muted">
              {formatDate(item.created_at)}
            </p>
          </li>
        ))}
      </ul>
    </Tile>
  );
}

function MyActivitiesTile({ items }: { items: MyClubActivity[] }) {
  return (
    <Tile>
      <TileHeading icon={<Users size={15} />}>我的社团活动</TileHeading>
      <ul className="flex flex-col gap-2.5">
        {items.slice(0, 5).map((item) => (
          <li key={`${item.club.id}-${item.activity.id}`}>
            <Link
              to={`/club/${item.club.id}`}
              className="block rounded-md border border-edge bg-surface-sunken p-2.5 outline-none transition-colors hover:bg-surface-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="min-w-0 text-sm font-semibold text-content">
                  {item.activity.name}
                </p>
                <Badge tone={getMyClubActivityTone(item.status)}>
                  {MY_CLUB_ACTIVITY_STATUS_TEXT[item.status]}
                </Badge>
              </div>
              <p className="mt-1 text-xs text-content-subtle">
                {item.club.name} · {formatDate(item.activity.start_time)}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </Tile>
  );
}

function CalendarTile({
  calendar,
}: {
  calendar: ReturnType<typeof buildMonthCalendar>;
}) {
  return (
    <Tile>
      <TileHeading
        icon={<CalendarDays size={15} />}
        action={
          <span className="text-xs font-semibold text-content-subtle">
            {calendar.monthLabel}
          </span>
        }
      >
        活动日历
      </TileHeading>
      <div className="grid grid-cols-7 gap-1 text-center">
        {["一", "二", "三", "四", "五", "六", "日"].map((label) => (
          <span
            key={label}
            className="py-1 text-[11px] font-bold text-content-subtle"
          >
            {label}
          </span>
        ))}
        {calendar.days.map((day, index) => (
          <span
            key={index}
            className={cn(
              "flex h-7 items-center justify-center rounded-sm text-xs",
              !day.date && "opacity-0",
              day.activities.length > 0
                ? "bg-brand-subtle font-bold text-tone-brand-fg"
                : "text-content-muted",
            )}
          >
            {day.date?.getDate() ?? ""}
          </span>
        ))}
      </div>
    </Tile>
  );
}

function BoardSkeleton() {
  const heights = [
    "h-72",
    "h-40",
    "h-52",
    "h-36",
    "h-60",
    "h-44",
    "h-48",
    "h-40",
  ];
  return (
    <div className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4 [&>*]:mb-4">
      {heights.map((height, index) => (
        <div
          key={index}
          className={cn(
            "break-inside-avoid animate-pulse rounded-md border border-edge bg-surface-skeleton motion-reduce:animate-none",
            height,
          )}
        />
      ))}
    </div>
  );
}

function EmptyBoard() {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center rounded-md border border-dashed border-edge bg-surface p-10 text-center">
      <Inbox size={30} className="mb-3 text-content-subtle" />
      <p className="font-display text-lg font-bold text-content">展板还空着</p>
      <p className="mt-1 max-w-md text-sm text-content-muted">
        社团通过审核、发布大型活动海报或公告后，都会出现在这里。
      </p>
      <Link
        to="/explore"
        className="mt-4 inline-flex min-h-11 items-center rounded-md bg-brand px-4 text-sm font-semibold text-brand-on outline-none hover:bg-brand-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40"
      >
        去发现社团
      </Link>
    </div>
  );
}
