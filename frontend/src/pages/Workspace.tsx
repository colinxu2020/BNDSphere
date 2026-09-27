import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { Building2, ChevronRight, Plus, RefreshCw, Users } from "@/src/components/ui/Icons";
import { Link, useNavigate } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { CATEGORY_MAP, CLUB_STATUS_MAP, MEMBERSHIP_MAP, STAR_LEVEL_MAP } from "../lib/labels";
import { formatDate } from "../lib/format";
import {
  Badge,
  EmptyState,
  PageHeader,
  SecondaryButton,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";
import { PageLoading } from "../components/ui/PageStates";

type UserClubMembership = components["schemas"]["UserClubMembership"];

const MANAGER_ROLES = new Set(["president", "vice_president"]);

export function Workspace() {
  const navigate = useNavigate();
  const [memberships, setMemberships] = useState<UserClubMembership[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);

  const managedClubs = useMemo(
    () =>
      memberships
        .filter(
          ({ membership, club }) => MANAGER_ROLES.has(membership) && club.status !== "archived",
        )
        .sort((left, right) => left.club.name.localeCompare(right.club.name, "zh-Hans-CN")),
    [memberships],
  );

  const fetchManagedClubs = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const response = await client.GET("/api/v1/users/me/clubs/");
      if (response.response.status === 401) {
        navigate("/login");
        return;
      }
      if (response.error) {
        setLoadError(response.error);
        setMemberships([]);
      } else {
        setMemberships(response.data || []);
      }
    } catch (error) {
      setLoadError(error);
      setMemberships([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchManagedClubs();
    // Load once with the authenticated user captured on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-6 pb-20"
    >
      <PageHeader
        eyebrow="My Clubs"
        title="我管理的社团"
        action={
          <div className="flex flex-wrap justify-between gap-2">
            <Link
              to="/clubs/new"
              className="inline-flex items-center justify-center gap-2 rounded-md bg-primary-500 px-4 py-2.5 font-semibold text-white shadow-md shadow-primary-500/20 hover:bg-primary-600"
            >
              <Plus size={16} /> 创建社团
            </Link>
            <SecondaryButton type="button" onClick={fetchManagedClubs} disabled={isLoading}>
              <RefreshCw size={16} /> 刷新
            </SecondaryButton>
          </div>
        }
      />

      {loadError && <StatusMessage value={loadError} />}

      {isLoading ? (
        <PageLoading compact />
      ) : managedClubs.length ? (
        <div className="grid gap-4 md:grid-cols-2">
          {managedClubs.map(({ club, membership }) => (
            <Link key={club.id} to={`/club/${club.id}/manage`} className="group block">
              <Surface className="h-full p-5 transition group-hover:border-primary-100 group-hover:shadow-[0_10px_30px_-12px_rgba(15,23,42,0.22)]">
                <div className="flex items-start gap-4">
                  <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-md border border-slate-100 bg-slate-50 text-slate-400">
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
                        <h2 className="truncate text-lg font-bold text-slate-900 group-hover:text-primary-600">
                          {club.name}
                        </h2>
                        <p className="mt-1 line-clamp-2 text-sm leading-6 text-slate-500">
                          {club.summary}
                        </p>
                      </div>
                      <ChevronRight
                        size={18}
                        className="mt-1 shrink-0 text-slate-300 group-hover:text-primary-500"
                      />
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <Badge tone="primary">{MEMBERSHIP_MAP[membership]}</Badge>
                      <Badge tone="slate">{CATEGORY_MAP[club.category]}</Badge>
                      <Badge tone="blue">{CLUB_STATUS_MAP[club.status]}</Badge>
                      {club.star_level !== "none" && (
                        <Badge tone="yellow">{STAR_LEVEL_MAP[club.star_level]}</Badge>
                      )}
                    </div>

                    <div className="mt-4 flex flex-wrap items-center gap-4 text-xs font-medium text-slate-400">
                      <span>创建于 {formatDate(club.created_at)}</span>
                      <span className="inline-flex items-center gap-1">
                        <Users size={14} />
                        {club.president ? `社长 ${club.president.username}` : "暂无社长"}
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
