/**
 * Layout option B — board-first, minimal chrome. DEV-ONLY prototype.
 *
 * The thesis: the front door is the 展板 itself. Club recruitment at this school
 * happens on a physical wall of posters, so the home screen IS the wall — a dense,
 * scannable mix of posters, club cards and notices, browsed directly rather than
 * navigated to. Chrome recedes to a thin bar; category colour does the wayfinding.
 *
 * The honest weakness: this shape serves students well and the 社联/admin
 * workbenches badly, so those would need their own separate shell.
 */
import { Award, CalendarDays, Compass, Search } from "@/src/components/ui/Icons";
import { ActivityLevelChip } from "../../components/ui/ActivityCard";
import { CategoryChip, categorySpine } from "../../components/ui/CategoryChip";
import { StarLevel } from "../../components/ui/StarLevel";
import { cn } from "../../lib/utils";
import { SAMPLE_ACTIVITIES, SAMPLE_ANNOUNCEMENTS, SAMPLE_CLUBS } from "../sampleData";

export default function LayoutB() {
  return (
    <div className="min-h-screen bg-surface-sunken">
      {/* Thin chrome */}
      <header className="sticky top-0 z-40 border-b border-edge bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-4 px-5">
          <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-7 w-auto" />
          <div className="relative ml-2 hidden min-w-0 flex-1 items-center md:flex">
            <Search size={15} className="absolute left-3 text-content-subtle" />
            <input
              placeholder="搜索社团、活动、星级评价…"
              className="w-full rounded-full border border-edge bg-surface-sunken py-1.5 pr-3 pl-9 text-sm text-content placeholder:text-content-subtle"
            />
          </div>
          <nav className="flex items-center gap-1">
            {[
              [Compass, "社团"],
              [CalendarDays, "活动"],
              [Award, "星级"],
            ].map(([Icon, label]) => {
              const I = Icon as typeof Compass;
              return (
                <button
                  key={label as string}
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold text-content-muted hover:bg-surface-hover hover:text-content"
                >
                  <I size={15} /> {label as string}
                </button>
              );
            })}
          </nav>
          <div className="ml-1 flex h-8 w-8 items-center justify-center rounded-full border border-edge bg-surface-sunken text-xs font-bold text-content-muted">
            十
          </div>
        </div>
      </header>

      {/* The wall */}
      <main className="mx-auto max-w-[1400px] px-5 py-5">
        <div className="columns-1 gap-4 sm:columns-2 lg:columns-3 xl:columns-4 [&>*]:mb-4">
          {/* Feature poster */}
          <article className="break-inside-avoid overflow-hidden rounded-md border border-edge bg-surface-media shadow-md">
            <div className="flex aspect-[4/5] items-center justify-center bg-surface-media">
              <span className="font-display px-6 text-center text-2xl font-bold text-content-on-inverted">
                秋季社团招新
                <br />
                嘉年华
              </span>
            </div>
            <div className="flex items-center justify-between gap-2 bg-surface-inverted px-3 py-2.5">
              <ActivityLevelChip level="school" />
              <span className="text-xs font-semibold text-content-on-inverted-muted">9月5日</span>
            </div>
          </article>

          {SAMPLE_CLUBS.slice(0, 4).map((club) => (
            <article
              key={club.id}
              className={cn(
                "break-inside-avoid rounded-md border border-l-4 border-edge bg-surface p-4 shadow-sm",
                categorySpine(club.category),
              )}
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <CategoryChip category={club.category} size="sm" />
                {club.star_level !== "none" && (
                  <StarLevel level={club.star_level} size="sm" showLabel={false} />
                )}
              </div>
              <h3 className="font-display text-lg font-bold text-content">{club.name}</h3>
              <p className="mt-1 text-sm text-content-muted">{club.summary}</p>
              <p className="mt-3 text-xs font-semibold text-content-subtle">
                {club.members.length} 名成员 · 招新中
              </p>
            </article>
          ))}

          {/* Notices as a pinned slip */}
          <article className="break-inside-avoid rounded-md border border-edge bg-tone-warning-bg p-4 shadow-sm">
            <p className="font-display mb-2 text-xs font-bold tracking-[0.18em] text-tone-warning-fg uppercase">
              公告
            </p>
            <ul className="flex flex-col gap-2">
              {SAMPLE_ANNOUNCEMENTS.map((a) => (
                <li key={a.id} className="text-sm font-semibold text-content">
                  {a.title}
                  <span className="ml-1 text-xs font-normal text-content-muted">{a.at}</span>
                </li>
              ))}
            </ul>
          </article>

          {SAMPLE_ACTIVITIES.slice(1).map((act) => (
            <article
              key={act.id}
              className="break-inside-avoid rounded-md border border-edge bg-surface p-4 shadow-sm"
            >
              <ActivityLevelChip level={act.level} />
              <h3 className="font-display mt-2 text-lg font-bold text-content">{act.name}</h3>
              <p className="mt-1 line-clamp-3 text-sm text-content-muted">{act.description}</p>
            </article>
          ))}

          {SAMPLE_CLUBS.slice(4).map((club) => (
            <article
              key={club.id}
              className={cn(
                "break-inside-avoid rounded-md border border-l-4 border-edge bg-surface p-4 shadow-sm",
                categorySpine(club.category),
              )}
            >
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <CategoryChip category={club.category} size="sm" />
                {club.star_level !== "none" && (
                  <StarLevel level={club.star_level} size="sm" showLabel={false} />
                )}
              </div>
              <h3 className="font-display text-lg font-bold text-content">{club.name}</h3>
              <p className="mt-1 text-sm text-content-muted">{club.summary}</p>
            </article>
          ))}
        </div>
      </main>
    </div>
  );
}
