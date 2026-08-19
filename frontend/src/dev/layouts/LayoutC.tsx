/**
 * Layout option C — keep the topbar, restructure the pages. DEV-ONLY prototype.
 *
 * The thesis: the shell is not the problem; the page templates are. Every page today
 * is one long vertical stack of panels in a centred column, so a club page and an
 * audit queue have the same shape despite doing unrelated jobs. This keeps the
 * familiar topbar and changes what sits underneath it: tabbed sections instead of
 * panel stacks, a real stat header, and dense tables where the work is operational.
 *
 * Smallest structural risk of the three, and the least change to how navigating feels.
 */
import { Award, CalendarDays, Compass, Users } from "@/src/components/ui/Icons";
import { Badge } from "../../components/ui/AppPrimitives";
import { CategoryChip } from "../../components/ui/CategoryChip";
import { StarLevel, StarLevelCompact } from "../../components/ui/StarLevel";
import { cn } from "../../lib/utils";
import { SAMPLE_CLUBS, SAMPLE_QUEUE } from "../sampleData";

const TABS = ["概览", "成员", "活动记录", "星级评价", "设置"];

export default function LayoutC() {
  const club = SAMPLE_CLUBS[0];

  return (
    <div className="min-h-screen bg-surface-sunken">
      {/* Familiar topbar */}
      <header className="sticky top-0 z-40 border-b border-edge bg-surface">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-8 w-auto" />
          <nav className="hidden items-center gap-1 md:flex">
            {[[Compass, "发现社团"], [CalendarDays, "大型活动"], [Award, "星级评价"]].map(([Icon, label], i) => {
              const I = Icon as typeof Compass;
              return (
                <button
                  key={label as string}
                  type="button"
                  className={cn(
                    "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold",
                    i === 0 ? "bg-surface-hover text-content" : "text-content-muted hover:text-content",
                  )}
                >
                  <I size={16} /> {label as string}
                </button>
              );
            })}
          </nav>
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-edge bg-surface-sunken text-sm font-bold text-content-muted">
            十
          </div>
        </div>
      </header>

      {/* Page: stat header + tabs, instead of a stack of panels */}
      <div className="border-b border-edge bg-surface">
        <div className="mx-auto max-w-7xl px-6 pt-6">
          <div className="flex flex-wrap items-start gap-4">
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md border border-edge bg-surface-sunken text-xl font-bold text-content-muted">
              天
            </div>
            <div className="min-w-0 flex-1">
              <div className="mb-1.5 flex flex-wrap items-center gap-2">
                <CategoryChip category={club.category} />
                <StarLevel level={club.star_level} />
              </div>
              <h1 className="font-display text-3xl font-bold text-content">{club.name}</h1>
              <p className="mt-1 max-w-2xl text-content-muted">{club.summary}</p>
            </div>
            <div className="flex gap-6 pt-1">
              {[["成员", "48"], ["活动", "12"], ["星级总分", "92"]].map(([k, v]) => (
                <div key={k}>
                  <p className="font-display text-2xl font-bold text-content">{v}</p>
                  <p className="text-xs font-semibold text-content-subtle">{k}</p>
                </div>
              ))}
            </div>
          </div>

          <nav className="-mb-px mt-5 flex gap-1 overflow-x-auto">
            {TABS.map((tab, i) => (
              <button
                key={tab}
                type="button"
                className={cn(
                  "shrink-0 border-b-2 px-3.5 py-2.5 text-sm font-semibold transition-colors",
                  i === 2
                    ? "border-brand text-content"
                    : "border-transparent text-content-muted hover:text-content",
                )}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Dense operational table, not a panel stack */}
      <main className="mx-auto max-w-7xl px-6 py-6">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Badge tone="warning">3 条待审核</Badge>
            <span className="text-sm text-content-muted">共 5 条记录</span>
          </div>
          <div className="flex gap-2">
            <select className="rounded-md border border-edge bg-surface px-2.5 py-1.5 text-sm font-semibold text-content">
              <option>全部状态</option>
            </select>
            <button type="button" className="rounded-md bg-brand px-3.5 py-1.5 text-sm font-semibold text-brand-on hover:bg-brand-hover">
              新建记录
            </button>
          </div>
        </div>

        <div className="overflow-hidden rounded-md border border-edge bg-surface shadow-sm">
          <table className="w-full text-sm">
            <thead className="border-b border-edge bg-surface-sunken">
              <tr className="text-left">
                {["社团", "类型", "星级", "状态", "提交时间", ""].map((h) => (
                  <th key={h} className="px-4 py-2.5 text-xs font-bold tracking-wider text-content-subtle uppercase">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SAMPLE_QUEUE.map((row, i) => (
                <tr key={row.id} className="border-b border-edge-subtle last:border-0 hover:bg-surface-hover">
                  <td className="px-4 py-2.5 font-semibold text-content">{row.club}</td>
                  <td className="px-4 py-2.5 text-content-muted">{row.kind}</td>
                  <td className="px-4 py-2.5">
                    <StarLevelCompact level={SAMPLE_CLUBS[i].star_level} />
                  </td>
                  <td className="px-4 py-2.5">
                    <Badge tone={row.status === "pending" ? "warning" : row.status === "approved" ? "success" : "danger"}>
                      {row.status === "pending" ? "待审核" : row.status === "approved" ? "已通过" : "已驳回"}
                    </Badge>
                  </td>
                  <td className="px-4 py-2.5 text-content-subtle">{row.at}</td>
                  <td className="px-4 py-2.5 text-right">
                    <button type="button" className="rounded-md border border-edge px-2.5 py-1 text-xs font-semibold text-content hover:bg-surface-sunken">
                      审核
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="mt-4 flex items-center gap-2 text-sm text-content-muted">
          <Users size={15} /> 成员变动与活动记录合并显示在同一张表中，减少页面跳转。
        </div>
      </main>
    </div>
  );
}
