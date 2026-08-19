import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Filter, Hash, Plus, Search, Users } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { StatusMessage } from "../components/ui/AppPrimitives";
import { CategoryChip, categorySpine } from "../components/ui/CategoryChip";
import { StarLevel, StarLevelCompact } from "../components/ui/StarLevel";
import { CATEGORY_MAP } from "../lib/labels";
import { cn } from "../lib/utils";

type ClubSummaryInfo = components["schemas"]["ClubSummaryInfo"];
type ClubInfo = components["schemas"]["ClubInfo"];
type Category = components["schemas"]["ClubCategoryEnum"];

const CATEGORIES: { label: string; value: Category | "all" }[] = [
  { label: "全部", value: "all" },
  ...(
    [
      "science",
      "humanity",
      "arts",
      "sports",
      "business",
      "charity",
      "campus",
      "other",
    ] as Category[]
  ).map((value) => ({ label: CATEGORY_MAP[value], value })),
];

/**
 * 发现社团 — master–detail.
 *
 * Browsing and reading used to be separate screens: pick a club, land on its page,
 * press back, lose your place in the list. The list and the club now sit side by
 * side, so comparing clubs costs nothing.
 *
 * Selection lives in the query string (?club=), so a chosen club is linkable and
 * survives a reload — the thing local state would have quietly thrown away.
 *
 * Below xl there is no room for two panes, so the list fills the width and rows
 * navigate to the full club page instead. Same list, one pane.
 *
 * The list uses GET /clubs/summary; the detail pane fetches the full club only for
 * whichever one is selected, so browsing fifty clubs no longer means downloading
 * fifty membership lists.
 */
export function ExploreClubs() {
  const [clubs, setClubs] = useState<ClubSummaryInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<Category | "all">("all");
  const [error, setError] = useState<unknown>(null);
  const [params, setParams] = useSearchParams();

  const selectedId = Number(params.get("club")) || null;

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error: requestError } = await client.GET(
          "/api/v1/clubs/summary",
          {
            params: {
              query: {
                size: 50,
                search: search || undefined,
                category: activeCategory !== "all" ? activeCategory : undefined,
              },
            },
          },
        );
        if (cancelled) return;
        if (requestError) {
          setError(requestError);
          setClubs([]);
        } else {
          setClubs(data?.items ?? []);
        }
      } catch (requestError) {
        if (!cancelled) setError(requestError);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    const timer = window.setTimeout(load, search ? 300 : 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [search, activeCategory]);

  const select = (id: number) => {
    const next = new URLSearchParams(params);
    next.set("club", String(id));
    setParams(next, { replace: true });
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col xl:flex-row">
      {/* Master */}
      <div className="flex min-w-0 flex-col border-edge xl:w-[26rem] xl:shrink-0 xl:border-r">
        <div className="border-b border-edge bg-surface px-4 py-4 sm:px-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-display text-[11px] font-bold tracking-[0.18em] text-tone-brand-fg uppercase">
                Explore
              </p>
              <h1 className="font-display text-2xl font-bold text-content">
                发现社团
              </h1>
            </div>
            <Link
              to="/clubs/new"
              className="inline-flex min-h-11 shrink-0 items-center gap-1.5 rounded-md bg-brand px-3 text-sm font-semibold text-brand-on outline-none hover:bg-brand-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40 md:min-h-0 md:py-2"
            >
              <Plus size={15} /> 创建
            </Link>
          </div>

          <div className="relative mt-3">
            <Search
              size={15}
              className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-content-subtle"
            />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="搜索社团名称或简介"
              aria-label="搜索社团"
              className="w-full rounded-md border border-edge bg-surface-sunken py-2.5 pr-3 pl-9 text-sm font-medium text-content outline-none placeholder:text-content-subtle focus-visible:border-brand focus-visible:ring-2 focus-visible:ring-brand-strong/30"
            />
          </div>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {CATEGORIES.map((category) => {
              const active = activeCategory === category.value;
              return (
                <button
                  key={category.value}
                  type="button"
                  onClick={() => setActiveCategory(category.value)}
                  aria-pressed={active}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-xs font-bold outline-none focus-visible:ring-4 focus-visible:ring-brand-strong/40",
                    active
                      ? "border-content bg-surface-inverted text-content-on-inverted"
                      : "border-edge bg-surface text-content-muted hover:bg-surface-hover hover:text-content",
                  )}
                >
                  {category.label}
                </button>
              );
            })}
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {error != null && (
            <div className="mb-3">
              <StatusMessage value={error} />
            </div>
          )}

          {isLoading ? (
            <ListSkeleton />
          ) : clubs.length === 0 ? (
            <EmptyList hasFilters={Boolean(search) || activeCategory !== "all"} />
          ) : (
            <ul className="flex flex-col gap-2">
              {clubs.map((club) => (
                <li key={club.id}>
                  <ClubRow
                    club={club}
                    selected={club.id === selectedId}
                    onSelect={() => select(club.id)}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Detail — only where there is room for a second pane */}
      <div className="hidden min-w-0 flex-1 overflow-y-auto xl:block">
        {selectedId ? (
          <ClubDetailPane clubId={selectedId} />
        ) : (
          <div className="flex h-full min-h-64 flex-col items-center justify-center p-10 text-center">
            <Hash size={28} className="mb-3 text-content-subtle" />
            <p className="font-display text-lg font-bold text-content">
              从左侧选择一个社团
            </p>
            <p className="mt-1 max-w-sm text-sm text-content-muted">
              社团详情会显示在这里，浏览时不会离开列表。
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * A list row. On wide screens it selects into the detail pane; below xl there is no
 * pane, so it is a link to the full club page.
 */
function ClubRow({
  club,
  selected,
  onSelect,
}: {
  club: ClubSummaryInfo;
  selected: boolean;
  onSelect: () => void;
}) {
  const inner = (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <CategoryChip category={club.category} size="sm" />
        {club.star_level !== "none" && (
          <StarLevelCompact level={club.star_level} />
        )}
      </div>
      <p className="mt-1.5 font-semibold text-content">{club.name}</p>
      <p className="mt-0.5 line-clamp-2 text-xs text-content-muted">
        {club.summary}
      </p>
      <p className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-semibold text-content-subtle">
        <Users size={12} />
        {club.member_count} 名成员
      </p>
    </>
  );

  const shell = cn(
    "block w-full rounded-md border border-l-4 p-3 text-left outline-none transition-colors focus-visible:ring-4 focus-visible:ring-brand-strong/40",
    selected
      ? "border-edge bg-brand-subtle"
      : "border-edge bg-surface hover:bg-surface-hover",
    categorySpine(club.category),
  );

  return (
    <>
      <button
        type="button"
        onClick={onSelect}
        aria-current={selected ? "true" : undefined}
        className={cn(shell, "hidden xl:block")}
      >
        {inner}
      </button>
      <Link to={`/club/${club.id}`} className={cn(shell, "xl:hidden")}>
        {inner}
      </Link>
    </>
  );
}

/** The detail pane fetches only the selected club, so the list stays light. */
function ClubDetailPane({ clubId }: { clubId: number }) {
  const [club, setClub] = useState<ClubInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      setError(null);
      setClub(null);
      try {
        const { data, error: requestError } = await client.GET(
          "/api/v1/clubs/{club_id}",
          { params: { path: { club_id: clubId } } },
        );
        if (cancelled) return;
        if (requestError) setError(requestError);
        else setClub(data ?? null);
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
  }, [clubId]);

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="h-24 animate-pulse rounded-md bg-surface-skeleton motion-reduce:animate-none" />
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <div
              key={index}
              className="h-20 animate-pulse rounded-md bg-surface-skeleton motion-reduce:animate-none"
            />
          ))}
        </div>
      </div>
    );
  }

  if (error != null) {
    return (
      <div className="p-6">
        <StatusMessage value={error} />
      </div>
    );
  }

  if (!club) return null;

  const memberCount = club.members.length;
  const presidents = club.members.filter(
    (member) => member.membership === "president",
  );

  return (
    <article className="p-6">
      <div className="flex flex-wrap items-start gap-4">
        <div
          className={cn(
            "flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-md border border-l-4 border-edge bg-surface",
            categorySpine(club.category),
          )}
        >
          {club.logo_uri ? (
            <img
              src={club.logo_uri}
              alt={club.name}
              className="h-full w-full object-cover"
            />
          ) : (
            <Hash size={26} className="text-content-subtle" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <CategoryChip category={club.category} />
            <StarLevel level={club.star_level} />
          </div>
          <h2 className="font-display text-3xl font-bold text-content">
            {club.name}
          </h2>
          <p className="mt-1 text-content-muted">{club.summary}</p>
        </div>
        <Link
          to={`/club/${club.id}`}
          className="inline-flex min-h-11 shrink-0 items-center rounded-md bg-brand px-4 text-sm font-semibold text-brand-on outline-none hover:bg-brand-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40"
        >
          查看社团主页
        </Link>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        {[
          ["成员", String(memberCount)],
          ["社团活动", String(club.club_activities?.length ?? 0)],
          ["大型活动记录", String(club.general_activity_records?.length ?? 0)],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-md border border-edge bg-surface p-4 shadow-sm"
          >
            <p className="text-xs font-semibold text-content-subtle">{label}</p>
            <p className="font-display mt-1 text-2xl font-bold text-content">
              {value}
            </p>
          </div>
        ))}
      </div>

      <section className="mt-6 rounded-md border border-edge bg-surface p-5 shadow-sm">
        <h3 className="font-display mb-2 text-lg font-bold text-content">
          关于社团
        </h3>
        <p className="text-[15px] leading-relaxed text-content-muted">
          {club.description || "暂无详细介绍。"}
        </p>
        {presidents.length > 0 && (
          <p className="mt-4 text-sm text-content-subtle">
            社长：
            {presidents.map((member) => `#${member.user_id}`).join("、")}
          </p>
        )}
      </section>
    </article>
  );
}

function ListSkeleton() {
  return (
    <ul className="flex flex-col gap-2">
      {[0, 1, 2, 3, 4, 5].map((index) => (
        <li
          key={index}
          className="h-24 animate-pulse rounded-md border border-edge bg-surface-skeleton motion-reduce:animate-none"
        />
      ))}
    </ul>
  );
}

function EmptyList({ hasFilters }: { hasFilters: boolean }) {
  return (
    <div className="flex min-h-56 flex-col items-center justify-center rounded-md border border-dashed border-edge bg-surface p-8 text-center">
      <Filter size={24} className="mb-3 text-content-subtle" />
      <p className="font-semibold text-content">
        {hasFilters ? "没有符合条件的社团" : "暂无公开社团"}
      </p>
      <p className="mt-1 max-w-xs text-sm text-content-muted">
        {hasFilters
          ? "试试更换关键词或类别。"
          : "社团通过审核后会展示在这里。"}
      </p>
    </div>
  );
}
