import {
  Award,
  CalendarDays,
  Compass,
  Gavel,
  LayoutDashboard,
  Settings,
  Shield,
  Users,
  type IconProps,
} from "@/src/components/ui/Icons";
import type { components } from "../../api/schema";

type Role = components["schemas"]["RoleEnum"];

export type NavItem = {
  label: string;
  path: string;
  icon: (props: IconProps) => React.ReactNode;
  /** Undefined means public. Otherwise the roles the BACKEND accepts. */
  roles?: Role[];
  /** Requires a session, regardless of role. */
  authed?: boolean;
};

export type NavGroup = { section: string; items: NavItem[] };

/**
 * The single navigation definition.
 *
 * Rendered twice — as the persistent rail on desktop and inside the drawer on
 * mobile — so the two presentations cannot drift. Before this, the three public
 * links lived in a topbar array, five role-gated destinations were hand-written
 * inside an avatar dropdown, and /moderation was in neither.
 *
 * Role sets mirror what the backend enforces rather than being invented here, so a
 * link never appears for someone who would be refused:
 *   /moderation  RoleChecker([moderator, admin, dev])
 *   /federation  federation_staff, admin, dev
 *   /admin       admin, dev
 */
export const NAV: NavGroup[] = [
  {
    section: "浏览",
    items: [
      { label: "展板", path: "/", icon: LayoutDashboard },
      { label: "发现社团", path: "/explore", icon: Compass },
      { label: "大型活动", path: "/activities", icon: CalendarDays },
      { label: "星级评价", path: "/star-level", icon: Award },
    ],
  },
  {
    section: "我的",
    items: [
      { label: "我管理的社团", path: "/workspace", icon: Users, authed: true },
      { label: "个人主页", path: "/profile", icon: Settings, authed: true },
    ],
  },
  {
    section: "工作台",
    items: [
      {
        label: "审核队列",
        path: "/moderation",
        icon: Gavel,
        roles: ["moderator", "admin", "dev"],
      },
      {
        label: "社联工作台",
        path: "/federation",
        icon: LayoutDashboard,
        roles: ["federation_staff", "admin", "dev"],
      },
      {
        label: "管理员控制台",
        path: "/admin",
        icon: Shield,
        roles: ["admin", "dev"],
      },
    ],
  },
];

/** Groups with nothing visible to this viewer are dropped entirely. */
export function visibleNav(
  role: Role | undefined,
  isLoggedIn: boolean,
): NavGroup[] {
  return NAV.map((group) => ({
    section: group.section,
    items: group.items.filter((item) => {
      if (item.roles) return Boolean(role) && item.roles.includes(role!);
      if (item.authed) return isLoggedIn;
      return true;
    }),
  })).filter((group) => group.items.length > 0);
}

/** Exact match for the board, prefix match for everything else. */
export function isNavItemActive(pathname: string, path: string): boolean {
  return path === "/" ? pathname === "/" : pathname.startsWith(path);
}
