import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Award,
  CalendarDays,
  Compass,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  Shield,
  User,
} from "@/src/components/ui/Icons";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AUTH_STATE_CHANGED_EVENT, clearAuthToken, client } from "../../api/client";
import type { components } from "../../api/schema";
import { cn } from "../../lib/utils";

type UserInfo = components["schemas"]["UserInfo"];

const navLinks = [
  { name: "发现社团", path: "/explore", icon: Compass },
  { name: "大型活动", path: "/activities", icon: CalendarDays },
  { name: "联合活动", path: "/joint-activities", icon: CalendarDays },
  { name: "星级评价", path: "/star-level", icon: Award },
];

export function RootLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("bnd_token");
    setIsLoggedIn(Boolean(token));
    if (!token) {
      setUser(null);
      return;
    }

    let cancelled = false;
    const fetchUser = async () => {
      const { data, error } = await client.GET("/api/v1/users/me");
      if (cancelled) return;
      if (error || !data) {
        setUser(null);
        return;
      }
      setUser(data);
    };
    fetchUser();
    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  useEffect(() => {
    const syncAuthState = () => {
      const hasToken = Boolean(localStorage.getItem("bnd_token"));
      setIsLoggedIn(hasToken);
      if (!hasToken) setUser(null);
    };
    window.addEventListener("storage", syncAuthState);
    window.addEventListener(AUTH_STATE_CHANGED_EVENT, syncAuthState);
    return () => {
      window.removeEventListener("storage", syncAuthState);
      window.removeEventListener(AUTH_STATE_CHANGED_EVENT, syncAuthState);
    };
  }, []);

  const canOpenFederation = useMemo(
    () => user?.role === "federation_staff" || user?.role === "admin" || user?.role === "dev",
    [user?.role],
  );
  const canOpenAdmin = user?.role === "admin" || user?.role === "dev";

  const handleLogout = () => {
    clearAuthToken();
    setIsLoggedIn(false);
    setUser(null);
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white">
        <nav className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-10 w-auto" />
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {navLinks.map((link) => {
              const isActive =
                location.pathname === link.path ||
                (link.path !== "/" && location.pathname.startsWith(link.path));
              return (
                <Link
                  key={link.name}
                  to={link.path}
                  className={cn(
                    "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold transition-colors",
                    isActive
                      ? "bg-slate-100 text-slate-950"
                      : "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
                  )}
                >
                  <link.icon size={16} />
                  {link.name}
                </Link>
              );
            })}
          </div>

          <div className="flex min-w-32 items-center justify-end gap-2">
            {!isLoggedIn ? (
              <>
                <Link
                  to="/login"
                  className="rounded-md border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
                >
                  登录
                </Link>
                <Link
                  to="/register"
                  className="rounded-md bg-primary-500 px-3 py-2 text-sm font-semibold text-white hover:bg-primary-600"
                >
                  注册
                </Link>
              </>
            ) : (
              <div className="group relative">
                <button
                  type="button"
                  className="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full border border-slate-200 bg-slate-50 text-slate-600"
                  aria-label="用户菜单"
                >
                  {user?.avatar_uri ? (
                    <img
                      src={user.avatar_uri}
                      alt={user.username}
                      className="h-full w-full object-cover"
                    />
                  ) : user?.username ? (
                    <span className="text-sm font-bold">
                      {user.username.slice(0, 1).toUpperCase()}
                    </span>
                  ) : (
                    <User size={18} />
                  )}
                </button>

                <div className="invisible absolute right-0 top-full z-50 w-56 translate-y-1 pt-2 opacity-0 transition group-hover:visible group-hover:translate-y-0 group-hover:opacity-100">
                  <div className="rounded-md border border-slate-200 bg-white p-2 shadow-lg">
                    <div className="px-3 py-2">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {user?.username || "已登录用户"}
                      </p>
                      <p className="truncate text-xs text-slate-500">
                        {user?.email || "未设置邮箱"}
                      </p>
                    </div>
                    <div className="my-1 h-px bg-slate-100" />
                    <MenuItem to="/profile" icon={<User size={16} />}>
                      个人主页
                    </MenuItem>
                    <MenuItem to="/workspace" icon={<Settings size={16} />}>
                      我管理的社团
                    </MenuItem>
                    {canOpenFederation && (
                      <MenuItem to="/federation" icon={<LayoutDashboard size={16} />}>
                        社联工作台
                      </MenuItem>
                    )}
                    {canOpenAdmin && (
                      <MenuItem to="/admin" icon={<Shield size={16} />}>
                        管理员控制台
                      </MenuItem>
                    )}
                    <button
                      type="button"
                      onClick={handleLogout}
                      className="mt-1 flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold text-red-600 hover:bg-red-50"
                    >
                      <LogOut size={16} />
                      退出登录
                    </button>
                  </div>
                </div>
              </div>
            )}
            <button
              type="button"
              className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 text-slate-600 md:hidden"
              aria-label="打开导航"
            >
              <Menu size={18} />
            </button>
          </div>
        </nav>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        {children}
      </main>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-slate-200 bg-white md:hidden">
        <div className="grid grid-cols-4 gap-1 px-2 py-2">
          {navLinks.map((link) => {
            const isActive =
              location.pathname === link.path ||
              (link.path !== "/" && location.pathname.startsWith(link.path));
            return (
              <Link
                key={link.name}
                to={link.path}
                className={cn(
                  "flex flex-col items-center gap-1 rounded-md px-2 py-2 text-xs font-semibold",
                  isActive ? "text-slate-950" : "text-slate-500",
                )}
              >
                <link.icon size={18} />
                {link.name}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function MenuItem({ to, icon, children }: { to: string; icon: ReactNode; children: ReactNode }) {
  return (
    <Link
      to={to}
      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"
    >
      {icon}
      {children}
    </Link>
  );
}
