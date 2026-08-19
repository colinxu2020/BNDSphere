/**
 * Layout option A — sidebar shell + master–detail. DEV-ONLY prototype.
 *
 * The thesis: this product has 16 routes and 6 roles, and five destinations are
 * currently hidden inside an avatar dropdown. A persistent rail makes every
 * destination a visible, one-click target and gives the content area full width.
 * Lists and detail sit side by side, so reviewing an item never means losing the
 * list — which is exactly what the audit queues do today.
 */
import {
  Award,
  Bell,
  CalendarDays,
  Compass,
  Gavel,
  LayoutDashboard,
  Settings,
  Shield,
  Users,
} from "@/src/components/ui/Icons";
import { Badge } from "../../components/ui/AppPrimitives";
import { CategoryChip } from "../../components/ui/CategoryChip";
import { StarLevel, StarLevelCompact } from "../../components/ui/StarLevel";
import { cn } from "../../lib/utils";
import { SAMPLE_CLUBS, SAMPLE_QUEUE } from "../sampleData";

const NAV = [
  {
    section: "浏览",
    items: [
      { icon: Compass, label: "发现社团", active: true },
      { icon: CalendarDays, label: "大型活动" },
      { icon: Award, label: "星级评价" },
    ],
  },
  {
    section: "我的",
    items: [
      { icon: Users, label: "我的社团" },
      { icon: Settings, label: "个人设置" },
    ],
  },
  {
    section: "工作台",
    items: [
      { icon: Gavel, label: "审核队列", badge: 3 },
      { icon: LayoutDashboard, label: "社联工作台" },
      { icon: Shield, label: "管理员控制台" },
    ],
  },
];

export default function LayoutA() {
  const selected = SAMPLE_CLUBS[0];

  return (
    <div className="flex min-h-screen bg-surface-sunken">
      {/* Rail */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-edge bg-surface lg:flex">
        <div className="flex h-16 items-center gap-2 border-b border-edge px-5">
          <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-8 w-auto" />
        </div>
        <nav className="flex-1 overflow-y-auto p-3">
          {NAV.map((group) => (
            <div key={group.section} className="mb-5">
              <p className="font-display mb-2 px-2 text-[11px] font-bold tracking-[0.18em] text-content-subtle uppercase">
                {group.section}
              </p>
              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => (
                  <button
                    key={item.label}
                    type="button"
                    className={cn(
                      "flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-semibold transition-colors",
                      item.active
                        ? "bg-brand-subtle text-tone-brand-fg"
                        : "text-content-muted hover:bg-surface-hover hover:text-content",
                    )}
                  >
                    <item.icon size={17} />
                    <span className="flex-1 text-left">{item.label}</span>
                    {item.badge && (
                      <span className="rounded-full bg-tone-warning-bg px-1.5 py-0.5 text-[10px] font-bold text-tone-warning-fg">
                        {item.badge}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="border-t border-edge p-3">
          <div className="flex items-center gap-2.5 rounded-md px-2.5 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-edge bg-surface-sunken text-xs font-bold text-content-muted">
              十
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-content">王同学</p>
              <p className="truncate text-xs text-content-subtle">社联工作人员</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Content */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center justify-between gap-4 border-b border-edge bg-surface px-6">
          <div>
            <p className="text-xs font-semibold text-content-subtle">浏览 / 发现社团</p>
            <h1 className="font-display text-xl font-bold text-content">发现社团</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="inline-flex h-9 items-center gap-1.5 rounded-md border border-edge px-3 text-sm font-semibold text-content hover:bg-surface-sunken"
            >
              <Bell size={15} /> 通知
            </button>
            <button
              type="button"
              className="inline-flex h-9 items-center rounded-md bg-brand px-3.5 text-sm font-semibold text-brand-on hover:bg-brand-hover"
            >
              创建社团
            </button>
          </div>
        </header>

        <div className="flex min-h-0 flex-1">
          {/* Master */}
          <div className="w-full shrink-0 overflow-y-auto border-r border-edge p-4 xl:w-96">
            <div className="mb-3 flex items-center gap-2">
              <input
                placeholder="搜索社团"
                className="min-w-0 flex-1 rounded-md border border-edge bg-surface px-3 py-2 text-sm text-content placeholder:text-content-subtle"
              />
            </div>
            <div className="flex flex-col gap-2">
              {SAMPLE_CLUBS.map((club, i) => (
                <button
                  key={club.id}
                  type="button"
                  className={cn(
                    "flex flex-col gap-1.5 rounded-md border border-l-4 p-3 text-left transition-colors",
                    i === 0
                      ? "border-edge border-l-brand bg-brand-subtle"
                      : "border-edge border-l-edge bg-surface hover:bg-surface-hover",
                  )}
                >
                  <div className="flex items-center gap-2">
                    <CategoryChip category={club.category} size="sm" />
                    {club.star_level !== "none" && <StarLevelCompact level={club.star_level} />}
                  </div>
                  <p className="font-semibold text-content">{club.name}</p>
                  <p className="line-clamp-1 text-xs text-content-muted">{club.summary}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Detail */}
          <div className="hidden min-w-0 flex-1 overflow-y-auto p-6 xl:block">
            <div className="flex items-start gap-4">
              <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-md border border-edge bg-surface text-2xl font-bold text-content-muted">
                天
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <CategoryChip category={selected.category} />
                  <StarLevel level={selected.star_level} />
                </div>
                <h2 className="font-display text-3xl font-bold text-content">{selected.name}</h2>
                <p className="mt-1 text-content-muted">{selected.summary}</p>
              </div>
              <button
                type="button"
                className="shrink-0 rounded-md bg-brand px-5 py-2.5 text-sm font-semibold text-brand-on hover:bg-brand-hover"
              >
                加入社团
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {[
                ["成员", "48"],
                ["本学期活动", "12"],
                ["星级总分", "92"],
              ].map(([k, v]) => (
                <div key={k} className="rounded-md border border-edge bg-surface p-4 shadow-sm">
                  <p className="text-xs font-semibold text-content-subtle">{k}</p>
                  <p className="font-display mt-1 text-2xl font-bold text-content">{v}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-md border border-edge bg-surface shadow-sm">
              <div className="flex items-center justify-between border-b border-edge px-4 py-3">
                <h3 className="font-display font-bold text-content">待处理事项</h3>
                <Badge tone="warning">3 条待审核</Badge>
              </div>
              <table className="w-full text-sm">
                <tbody>
                  {SAMPLE_QUEUE.map((row) => (
                    <tr key={row.id} className="border-b border-edge-subtle last:border-0">
                      <td className="px-4 py-2.5 font-semibold text-content">{row.club}</td>
                      <td className="px-4 py-2.5 text-content-muted">{row.kind}</td>
                      <td className="px-4 py-2.5">
                        <Badge
                          tone={
                            row.status === "pending"
                              ? "warning"
                              : row.status === "approved"
                                ? "success"
                                : "danger"
                          }
                        >
                          {row.status === "pending"
                            ? "待审核"
                            : row.status === "approved"
                              ? "已通过"
                              : "已驳回"}
                        </Badge>
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-content-subtle">
                        {row.at}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
