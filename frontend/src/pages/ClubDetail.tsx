import {
  Calendar,
  MapPin,
  Hash,
  ArrowLeft,
  Settings,
} from "@/src/components/ui/Icons";
import { useParams, Link } from "react-router-dom";
import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { client } from "../api/client";
import { cn } from "../lib/utils";
import { useActionFeedback } from "../lib/useActionFeedback";
import type { Tone } from "../lib/tones";
import type { components } from "../api/schema";
import { StatusMessage } from "../components/ui/AppPrimitives";
import { CategoryChip, categorySpine } from "../components/ui/CategoryChip";
import { StarLevel } from "../components/ui/StarLevel";

type ClubInfo = components["schemas"]["ClubInfo"];
type UserInfo = components["schemas"]["UserInfo"];

const MANAGER_ROLES = new Set(["president", "vice_president"]);

export function ClubDetail() {
  const { id } = useParams<{ id: string }>();
  const [club, setClub] = useState<ClubInfo | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const action = useActionFeedback();
  const [isActionLoading, setIsActionLoading] = useState(false);

  useEffect(() => {
    const fetchClubInfo = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET("/api/v1/clubs/{club_id}", {
          params: { path: { club_id: Number(id) } },
        });
        const token = localStorage.getItem("bnd_token");
        if (token) {
          const userResult = await client.GET("/api/v1/users/me");
          setUser(userResult.error ? null : userResult.data || null);
        } else {
          setUser(null);
        }
        if (error) {
          setError(error);
          setClub(null);
        } else {
          setClub(data || null);
        }
      } catch (e) {
        setError(e);
        setClub(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchClubInfo();
  }, [id]);

  const currentMembership = useMemo(
    () =>
      club?.members.find(
        (member) => member.user_id === user?.id && member.membership !== "left",
      )?.membership || null,
    [club?.members, user?.id],
  );
  const canJoin = !currentMembership;
  const canLeave =
    currentMembership === "member" || currentMembership === "pending";
  const canManage = currentMembership
    ? MANAGER_ROLES.has(currentMembership)
    : false;
  const activeMembers = useMemo(
    () =>
      (club?.members || []).filter((member) =>
        ["member", "president", "vice_president"].includes(member.membership),
      ),
    [club?.members],
  );

  const joinClub = async () => {
    setIsActionLoading(true);
    action.clear();
    try {
      const { data, error } = await client.POST(
        "/api/v1/clubs/{club_id}/members",
        {
          params: { path: { club_id: Number(id) } },
        },
      );
      if (error) {
        action.fail(error);
      } else {
        action.succeed("加入申请已提交");
        if (data && club) {
          setClub({
            ...club,
            members: [
              ...club.members.filter(
                (member) => member.user_id !== data.user_id,
              ),
              data,
            ],
          });
        }
      }
    } catch (requestError) {
      action.fail(requestError);
    } finally {
      setIsActionLoading(false);
    }
  };

  const leaveClub = async () => {
    setIsActionLoading(true);
    action.clear();
    try {
      const { error, response } = await client.DELETE(
        "/api/v1/clubs/{club_id}/members/me",
        {
          params: { path: { club_id: Number(id) } },
        },
      );
      if (error) {
        action.fail(error);
      } else {
        action.succeed(`已退出社团（HTTP ${response.status}）`);
        if (user && club) {
          setClub({
            ...club,
            members: club.members.map((member) =>
              member.user_id === user.id
                ? { ...member, membership: "left" }
                : member,
            ),
          });
        }
      }
    } catch (requestError) {
      action.fail(requestError);
    } finally {
      setIsActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-8 flex flex-col">
        <div className="h-64 bg-surface-skeleton rounded-md w-full mt-4"></div>
      </div>
    );
  }

  if (error) {
    return <StatusMessage value={error} />;
  }

  if (!club) return <div className="text-content-muted">未找到社团信息</div>;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8"
    >
      <Link
        to="/explore"
        className="inline-flex items-center gap-2 text-content-muted hover:text-content font-medium w-fit transition-colors"
      >
        <ArrowLeft size={18} /> 返回探索
      </Link>

      <div
        className={cn(
          "relative overflow-hidden rounded-md border border-l-4 border-edge bg-surface p-8 shadow-md md:p-12",
          categorySpine(club.category),
        )}
      >
        <div className="flex flex-col md:flex-row gap-8 relative z-10 items-start md:items-center">
          <div className="w-28 h-28 md:w-40 md:h-40 rounded-md bg-surface-hover flex items-center justify-center shrink-0 shadow-inner overflow-hidden border border-edge">
            {club.logo_uri ? (
              <img
                src={club.logo_uri}
                alt={club.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <Hash className="text-content-subtle stroke-[1.5]" size={48} />
            )}
          </div>

          <div className="flex flex-col flex-grow">
            <div className="flex gap-2 items-center mb-3">
              <CategoryChip category={club.category} size="lg" />
              {club.star_level && (
                <StarLevel level={club.star_level} size="lg" />
              )}
            </div>

            <h1 className="text-3xl md:text-5xl font-display font-bold text-content mb-2">
              {club.name}
            </h1>
            <p className="text-lg md:text-xl text-content-muted font-medium">
              {club.summary}
            </p>
          </div>

          <div className="flex md:flex-col gap-3 w-full md:w-auto">
            {canJoin && (
              <button
                onClick={joinClub}
                disabled={isActionLoading}
                className="flex-1 md:flex-none px-6 py-3 bg-brand hover:bg-brand-hover active:scale-95 text-brand-on font-semibold rounded-md shadow-lg shadow-brand/25 transition-all text-center disabled:opacity-70"
              >
                加入社团
              </button>
            )}
            {canLeave && (
              <button
                onClick={leaveClub}
                disabled={isActionLoading}
                className="flex-1 md:flex-none px-6 py-3 bg-surface-sunken hover:bg-surface-hover border border-edge active:scale-95 text-content font-semibold rounded-md transition-all text-center disabled:opacity-70"
              >
                退出社团
              </button>
            )}
            {canManage && (
              <Link
                to={`/club/${club.id}/manage`}
                className="flex-1 md:flex-none px-6 py-3 bg-surface-inverted hover:bg-surface-inverted-hover active:scale-95 text-content-on-inverted font-semibold rounded-md transition-all text-center inline-flex items-center justify-center gap-2"
              >
                <Settings size={16} /> 管理
              </Link>
            )}
          </div>
        </div>
      </div>

      {action.message && (
        <StatusMessage value={action.message} tone={action.tone} />
      )}

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Main Details */}
        <div className="lg:col-span-2 flex flex-col gap-8">
          <section className="bg-surface p-8 rounded-md border border-edge shadow-sm">
            <h2 className="text-xl font-display font-bold text-content mb-4 flex items-center gap-2">
              关于社团
            </h2>
            <div className="text-[17px] leading-relaxed text-content-muted">
              <p>{club.description || "暂无详细介绍。"}</p>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3 px-2">
              <h2 className="text-xl font-display font-bold text-content flex items-center gap-2">
                <Calendar className="text-content-muted" /> 社团活动
              </h2>
              <div className="text-right">
                <p className="text-sm text-content-muted font-medium">已组织活动</p>
                <p className="text-base font-semibold text-content">
                  {club.club_activities?.length || 0} 场 / 学期
                </p>
              </div>
            </div>
            {club.club_activities && club.club_activities.length > 0 ? (
              <div className="grid gap-4">
                {club.club_activities.map((act) => (
                  <div
                    key={act.id}
                    className="group flex flex-col justify-between gap-4 rounded-md border border-edge bg-surface p-6 shadow-sm transition-all duration-200 hover:-translate-x-0.5 hover:-translate-y-0.5 hover:shadow-lg motion-reduce:transform-none motion-reduce:transition-none sm:flex-row sm:items-center"
                  >
                    <div className="flex flex-col gap-1">
                      <h3 className="font-semibold text-lg text-content group-hover:text-tone-brand-fg transition-colors">
                        {act.name}
                      </h3>
                      <p className="text-content-muted text-sm line-clamp-1">
                        {act.description}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs font-medium text-content-subtle">
                        <span className="flex items-center gap-1.5 bg-surface-sunken px-2 py-1 rounded-md">
                          <Calendar size={14} />{" "}
                          {new Date(act.start_time).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1.5 bg-surface-sunken px-2 py-1 rounded-md">
                          <MapPin size={14} /> {act.location}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-surface-sunken border border-edge-subtle border-dashed rounded-md p-8 text-center text-content-muted">
                当前暂无即将举办的活动，请后续关注！
              </div>
            )}
          </section>
        </div>

        {/* Right Column - Sidestats */}
        <div className="flex flex-col gap-6">
          <div className="bg-surface p-6 rounded-md border border-edge shadow-sm flex flex-col gap-4">
            <h3 className="font-display font-bold text-lg text-content">
              成员
            </h3>
            <div>
              <p className="text-sm font-medium text-content-muted">
                {activeMembers.length} 名成员
              </p>
            </div>
            {activeMembers.length ? (
              <div className="flex flex-col gap-2">
                {activeMembers.slice(0, 8).map((member) => (
                  <Link
                    key={member.id}
                    to={`/users/${member.user_id}`}
                    className="flex items-center justify-between gap-3 rounded-md bg-surface-sunken border border-edge-subtle px-3 py-2 text-sm font-medium text-content-muted hover:text-tone-brand-fg transition-colors"
                  >
                    <span>用户 #{member.user_id}</span>
                    <span className="text-xs text-content-subtle">
                      {member.membership}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-content-muted">暂无成员数据。</p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
