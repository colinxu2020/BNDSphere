import { Link, useLocation, useNavigate } from "react-router-dom";
import { LogIn, LogOut, Menu, User, X } from "@/src/components/ui/Icons";
import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  AUTH_STATE_CHANGED_EVENT,
  clearAuthToken,
  client,
} from "../../api/client";
import type { components } from "../../api/schema";
import { ROLE_MAP } from "../../lib/labels";
import { cn } from "../../lib/utils";
import { isNavItemActive, visibleNav, type NavGroup } from "./nav";

type UserInfo = components["schemas"]["UserInfo"];

/**
 * The application shell: a persistent navigation rail on desktop, the same
 * navigation in a drawer on mobile.
 *
 * Replaces a topbar that showed three links and hid five role-gated destinations
 * inside an avatar dropdown. With nine destinations across six roles a rail is the
 * shape that fits: every destination this viewer may use is visible, and the
 * content area gets the full width that master–detail pages need.
 *
 * Mobile has one navigation mechanism, not two. The drawer renders the same NAV
 * definition as the rail, so they cannot drift, and the previous bottom tab bar is
 * gone — it could only ever hold three of the nine destinations, and keeping both
 * would mean maintaining two partial navigations. The hamburger is back because it
 * now has something real to open.
 *
 * Pages own their own padding from here on: a master–detail page needs to fill the
 * content area edge to edge, which the old centred `max-w-7xl` main could not do.
 */
export function RootLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const drawerTriggerRef = useRef<HTMLButtonElement>(null);

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

  // The drawer closes on navigation, on Escape with focus returned to its
  // trigger, and on a pointer press outside it.
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setDrawerOpen(false);
      drawerTriggerRef.current?.focus();
    };
    const onPointerDown = (event: PointerEvent) => {
      if (!drawerRef.current?.contains(event.target as Node)) {
        setDrawerOpen(false);
      }
    };

    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [drawerOpen]);

  const handleLogout = () => {
    clearAuthToken();
    setIsLoggedIn(false);
    setUser(null);
    setDrawerOpen(false);
    navigate("/login");
  };

  const groups = visibleNav(user?.role, isLoggedIn);

  return (
    <div className="flex min-h-screen bg-surface-sunken">
      {/* Rail — desktop */}
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-edge bg-surface lg:flex">
        <Link
          to="/"
          className="flex h-16 shrink-0 items-center border-b border-edge px-5 outline-none focus-visible:ring-4 focus-visible:ring-brand-strong/40"
        >
          <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-8 w-auto" />
        </Link>
        <NavList groups={groups} pathname={location.pathname} />
        <AccountFooter
          user={user}
          isLoggedIn={isLoggedIn}
          onLogout={handleLogout}
        />
      </aside>

      {/* Drawer — mobile */}
      {drawerOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-surface-inverted/40" />
          <div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="导航"
            className="absolute inset-y-0 left-0 flex w-72 max-w-[85vw] flex-col border-r border-edge bg-surface"
          >
            <div className="flex h-16 shrink-0 items-center justify-between border-b border-edge px-4">
              <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-8 w-auto" />
              <button
                type="button"
                onClick={() => {
                  setDrawerOpen(false);
                  drawerTriggerRef.current?.focus();
                }}
                aria-label="关闭导航"
                className="inline-flex h-11 w-11 items-center justify-center rounded-md text-content-muted outline-none hover:bg-surface-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40"
              >
                <X size={18} />
              </button>
            </div>
            <NavList
              groups={groups}
              pathname={location.pathname}
              onNavigate={() => setDrawerOpen(false)}
              touch
            />
            <AccountFooter
              user={user}
              isLoggedIn={isLoggedIn}
              onLogout={handleLogout}
              touch
            />
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-3 border-b border-edge bg-surface px-4 lg:hidden">
          <button
            type="button"
            ref={drawerTriggerRef}
            onClick={() => setDrawerOpen(true)}
            aria-label="打开导航"
            aria-expanded={drawerOpen}
            className="inline-flex h-11 w-11 items-center justify-center rounded-md border border-edge text-content-muted outline-none focus-visible:ring-4 focus-visible:ring-brand-strong/40"
          >
            <Menu size={18} />
          </button>
          <Link to="/" className="min-w-0 flex-1 outline-none">
            <img src="/LOGO_FULL.png" alt="BNDSphere" className="h-7 w-auto" />
          </Link>
          {!isLoggedIn && (
            <Link
              to="/login"
              className="inline-flex min-h-11 items-center gap-1.5 rounded-md bg-brand px-3 text-sm font-semibold text-brand-on"
            >
              <LogIn size={15} /> 登录
            </Link>
          )}
        </header>

        <main className="flex min-w-0 flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}

function NavList({
  groups,
  pathname,
  onNavigate,
  touch,
}: {
  groups: NavGroup[];
  pathname: string;
  onNavigate?: () => void;
  touch?: boolean;
}) {
  return (
    <nav className="min-h-0 flex-1 overflow-y-auto p-3">
      {groups.map((group) => (
        <div key={group.section} className="mb-5 last:mb-0">
          <p className="font-display mb-2 px-2 text-[11px] font-bold tracking-[0.18em] text-content-subtle uppercase">
            {group.section}
          </p>
          <div className="flex flex-col gap-0.5">
            {group.items.map((item) => {
              const active = isNavItemActive(pathname, item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={onNavigate}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2.5 rounded-md px-2.5 text-sm font-semibold transition-colors outline-none focus-visible:ring-4 focus-visible:ring-brand-strong/40",
                    touch ? "min-h-11 py-2" : "py-2",
                    active
                      ? "bg-brand-subtle text-tone-brand-fg"
                      : "text-content-muted hover:bg-surface-hover hover:text-content",
                  )}
                >
                  <item.icon size={17} />
                  <span className="min-w-0 flex-1 truncate">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

function AccountFooter({
  user,
  isLoggedIn,
  onLogout,
  touch,
}: {
  user: UserInfo | null;
  isLoggedIn: boolean;
  onLogout: () => void;
  touch?: boolean;
}) {
  if (!isLoggedIn) {
    return (
      <div className="shrink-0 border-t border-edge p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <div className="flex flex-col gap-2">
          <Link
            to="/login"
            className="inline-flex min-h-11 items-center justify-center rounded-md bg-brand px-3 text-sm font-semibold text-brand-on outline-none hover:bg-brand-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40"
          >
            登录
          </Link>
          <Link
            to="/register"
            className="inline-flex min-h-11 items-center justify-center rounded-md border border-edge px-3 text-sm font-semibold text-content outline-none hover:bg-surface-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40"
          >
            注册
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="shrink-0 border-t border-edge p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
      <Link
        to="/profile"
        className="flex items-center gap-2.5 rounded-md px-2 py-2 outline-none hover:bg-surface-hover focus-visible:ring-4 focus-visible:ring-brand-strong/40"
      >
        <span className="flex h-9 w-9 shrink-0 items-center justify-center overflow-hidden rounded-full border border-edge bg-surface-sunken text-xs font-bold text-content-muted">
          {user?.avatar_uri ? (
            <img
              src={user.avatar_uri}
              alt={user.username}
              className="h-full w-full object-cover"
            />
          ) : user?.username ? (
            user.username.slice(0, 1).toUpperCase()
          ) : (
            <User size={16} />
          )}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold text-content">
            {user?.username || "已登录用户"}
          </span>
          <span className="block truncate text-xs text-content-subtle">
            {user?.role ? ROLE_MAP[user.role] : "普通成员"}
          </span>
        </span>
      </Link>
      <button
        type="button"
        onClick={onLogout}
        className={cn(
          "mt-1 flex w-full items-center gap-2.5 rounded-md px-2.5 text-sm font-semibold text-tone-danger-fg outline-none hover:bg-tone-danger-bg focus-visible:ring-4 focus-visible:ring-tone-danger-fg/40",
          touch ? "min-h-11 py-2" : "py-2",
        )}
      >
        <LogOut size={16} />
        退出登录
      </button>
    </div>
  );
}
