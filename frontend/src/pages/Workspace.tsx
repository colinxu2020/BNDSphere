import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import {
  Building2,
  ChevronRight,
  Plus,
  RefreshCw,
  Users,
} from "@/src/components/ui/Icons";
import { Link, useNavigate } from "react-router-dom";
import { client } from "../api/client";
import { CategoryChip } from "../components/ui/CategoryChip";
import { StarLevelCompact } from "../components/ui/StarLevel";
import { CLUB_STATUS_TONE } from "../lib/tones";
import type { components } from "../api/schema";
import {
  CLUB_STATUS_MAP,
  MEMBERSHIP_MAP,
} from "../lib/labels";
import { formatDate } from "../lib/format";
import {
  Badge,
  EmptyState,
  PageHeader,
  SecondaryButton,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";

type Club = components["schemas"]["ClubInfo"];
type UserInfo = components["schemas"]["UserInfo"];

const MANAGER_ROLES = new Set(["president", "vice_president"]);

export function Workspace() {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [clubs, setClubs] = useState<Club[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);

  const managedClubs = useMemo(() => {
    if (!user) return [];
    return clubs
      .map((club) => ({
        club,
        membership: club.members.find(
          (member) =>
            member.user_id === user.id && MANAGER_ROLES.has(member.membership),
        ),
      }))
      .filter((item) => item.membership)
      .sort((left, right) =>
        left.club.name.localeCompare(right.club.name, "zh-Hans-CN"),
      );
  }, [clubs, user]);

  const fetchManagedClubs = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const meResponse = await client.GET("/api/v1/users/me");
      if (meResponse.response.status === 401) {
        navigate("/login");
        return;
      }
      if (meResponse.error || !meResponse.data) {
        setLoadError(meResponse.error || "无法获取当前用户信息");
        setUser(null);
        setClubs([]);
        return;
      }

      setUser(meResponse.data);
      const clubsResponse = await client.GET("/api/v1/clubs/", {
        params: { query: { size: 100 } },
      });
      if (clubsResponse.error) {
        setLoadError(clubsResponse.error);
        setClubs([]);
      } else {
        setClubs(clubsResponse.data?.items || []);
      }
    } catch (error) {
      setLoadError(error);
      setClubs([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchManagedClubs();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex flex-col gap-6"
    >
      <PageHeader density="compact"
        eyebrow="My Clubs"
        title="我管理的社团"
        action={
          <div className="flex flex-wrap gap-2">
            <SecondaryButton
              type="button"
              onClick={fetchManagedClubs}
              disabled={isLoading}
            >
              <RefreshCw size={16} /> 刷新
            </SecondaryButton>
            <Link
              to="/clubs/new"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-brand px-4 py-2.5 font-semibold text-brand-on shadow-md shadow-brand/20 hover:bg-brand-hover"
            >
              <Plus size={16} /> 创建社团
            </Link>
          </div>
        }
      />

      {loadError && <StatusMessage value={loadError} />}

      {isLoading ? (
        <Surface density="compact" className="flex items-center justify-center py-16 text-content-muted">
          正在加载你管理的社团...
        </Surface>
      ) : managedClubs.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {managedClubs.map(({ club, membership }) => (
            <Link
              key={club.id}
              to={`/club/${club.id}/manage`}
              className="group block"
            >
              <Surface density="compact" className="h-full p-5 transition group-hover:border-tone-brand-edge group-hover:shadow-lg">
                <div className="flex items-start gap-4">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-md border border-edge-subtle bg-surface-sunken text-content-subtle">
                    {club.logo_uri ? (
                      <img
                        src={club.logo_uri}
                        alt={club.name}
                        className="h-full w-full object-cover"
                      />
                    ) : (
                      <Building2 size={26} />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h2 className="truncate text-lg font-bold text-content group-hover:text-tone-brand-fg">
                          {club.name}
                        </h2>
                        <p className="mt-1 line-clamp-2 text-sm leading-6 text-content-muted">
                          {club.summary}
                        </p>
                      </div>
                      <ChevronRight
                        size={18}
                        className="mt-1 shrink-0 text-content-subtle group-hover:text-brand"
                      />
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Badge tone="brand">
                        {membership
                          ? MEMBERSHIP_MAP[membership.membership]
                          : ""}
                      </Badge>
                      <CategoryChip category={club.category} size="sm" />
                      <Badge tone={CLUB_STATUS_TONE[club.status]}>
                        {CLUB_STATUS_MAP[club.status]}
                      </Badge>
                      {club.star_level !== "none" && (
                        <StarLevelCompact level={club.star_level} />
                      )}
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-4 text-xs font-medium text-content-subtle">
                      <span>创建于 {formatDate(club.created_at)}</span>
                      <span className="inline-flex items-center gap-1">
                        <Users size={14} />
                        {
                          club.members.filter(
                            (member) => member.membership !== "left",
                          ).length
                        }{" "}
                        名成员
                      </span>
                    </div>
                  </div>
                </div>
              </Surface>
            </Link>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Building2 size={24} />}
          title="暂无可管理社团"
          description="当你成为社长或副社长后，社团会出现在这里。"
        />
      )}
    </motion.div>
  );
}
