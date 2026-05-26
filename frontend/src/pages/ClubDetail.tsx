import {
  Sparkles,
  Calendar,
  MapPin,
  Users,
  Activity,
  Hash,
  ArrowLeft,
  Settings,
} from "lucide-react";
import { useParams, Link } from "react-router-dom";
import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { StatusMessage } from "../components/ui/AppPrimitives";

type ClubInfo = components["schemas"]["ClubInfo"];

const CATEGORY_MAP: Record<string, string> = {
  science: "科学",
  humanity: "人文",
  arts: "艺术",
  sports: "体育",
  business: "商业",
  charity: "公益",
  campus: "校园",
  other: "其他",
};

const STAR_LEVEL_MAP: Record<string, string> = {
  one_star: "一星社团",
  two_star: "二星社团",
  three_star: "三星社团",
  four_star: "四星社团",
  five_star: "五星社团",
  honorary: "荣誉社团",
};

const STATUS_MAP: Record<string, string> = {
  unreviewed: "未审核",
  normal: "正常运行",
  archived: "已归档",
};

export function ClubDetail() {
  const { id } = useParams<{ id: string }>();
  const [club, setClub] = useState<ClubInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [actionMessage, setActionMessage] = useState<unknown>(null);
  const [actionTone, setActionTone] = useState<"error" | "success">("error");
  const [isActionLoading, setIsActionLoading] = useState(false);

  useEffect(() => {
    const fetchClubInfo = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET("/api/v1/clubs/{club_id}", {
          params: { path: { club_id: Number(id) } },
        });
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

  const joinClub = async () => {
    setIsActionLoading(true);
    setActionMessage(null);
    try {
      const { data, error } = await client.POST(
        "/api/v1/clubs/{club_id}/members",
        {
          params: { path: { club_id: Number(id) } },
        },
      );
      if (error) {
        setActionTone("error");
        setActionMessage(error);
      } else {
        setActionTone("success");
        setActionMessage(data);
      }
    } catch (requestError) {
      setActionTone("error");
      setActionMessage(requestError);
    } finally {
      setIsActionLoading(false);
    }
  };

  const leaveClub = async () => {
    setIsActionLoading(true);
    setActionMessage(null);
    try {
      const { error, response } = await client.DELETE(
        "/api/v1/clubs/{club_id}/members/me",
        {
          params: { path: { club_id: Number(id) } },
        },
      );
      if (error) {
        setActionTone("error");
        setActionMessage(error);
      } else {
        setActionTone("success");
        setActionMessage(`HTTP ${response.status}`);
      }
    } catch (requestError) {
      setActionTone("error");
      setActionMessage(requestError);
    } finally {
      setIsActionLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-8 flex flex-col">
        <div className="h-64 bg-slate-200 rounded-[3rem] w-full mt-4"></div>
      </div>
    );
  }

  if (error) {
    return <StatusMessage value={error} />;
  }

  if (!club) return <div className="text-slate-500">未找到社团信息</div>;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <Link
        to="/explore"
        className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 font-medium w-fit transition-colors"
      >
        <ArrowLeft size={18} /> 返回探索
      </Link>

      {/* Header Info Card */}
      <div className="bg-white p-8 md:p-12 rounded-[2.5rem] border border-slate-100 shadow-[0_8px_30px_-4px_rgba(0,0,0,0.06)] relative overflow-hidden">
        {/* Decorative background blob for card */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary-100 rounded-full blur-[80px] opacity-60 -mr-20 -mt-20 pointer-events-none"></div>

        <div className="flex flex-col md:flex-row gap-8 relative z-10 items-start md:items-center">
          <div className="w-28 h-28 md:w-40 md:h-40 rounded-3xl bg-slate-100 flex items-center justify-center shrink-0 shadow-inner overflow-hidden border border-slate-200">
            {club.logo_uri ? (
              <img
                src={club.logo_uri}
                alt={club.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <Hash className="text-slate-400 stroke-[1.5]" size={48} />
            )}
          </div>

          <div className="flex flex-col flex-grow">
            <div className="flex gap-2 items-center mb-3">
              <span className="text-xs font-bold tracking-wider text-primary-600 bg-primary-50 px-3 py-1 rounded-full border border-primary-100">
                {CATEGORY_MAP[club.category] || club.category}
              </span>
              {club.star_level && club.star_level !== "none" && (
                <span className="flex items-center gap-1 text-xs font-bold text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full border border-yellow-100">
                  <Sparkles
                    size={14}
                    className="fill-yellow-500 text-yellow-500"
                  />
                  {STAR_LEVEL_MAP[club.star_level] || club.star_level}
                </span>
              )}
            </div>

            <h1 className="text-3xl md:text-5xl font-display font-bold text-slate-900 tracking-tight leading-[1.1] mb-2">
              {club.name}
            </h1>
            <p className="text-lg md:text-xl text-slate-500 font-medium">
              {club.summary}
            </p>
          </div>

          <div className="flex md:flex-col gap-3 w-full md:w-auto">
            <button
              onClick={joinClub}
              disabled={isActionLoading}
              className="flex-1 md:flex-none px-6 py-3 bg-primary-500 hover:bg-primary-600 active:scale-95 text-white font-semibold rounded-2xl shadow-lg shadow-primary-500/25 transition-all text-center disabled:opacity-70"
            >
              加入社团
            </button>
            <button
              onClick={leaveClub}
              disabled={isActionLoading}
              className="flex-1 md:flex-none px-6 py-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 active:scale-95 text-slate-800 font-semibold rounded-2xl transition-all text-center disabled:opacity-70"
            >
              退出社团
            </button>
            <Link
              to={`/club/${club.id}/manage`}
              className="flex-1 md:flex-none px-6 py-3 bg-slate-900 hover:bg-slate-800 active:scale-95 text-white font-semibold rounded-2xl transition-all text-center inline-flex items-center justify-center gap-2"
            >
              <Settings size={16} /> 管理
            </Link>
          </div>
        </div>
      </div>

      {actionMessage && (
        <StatusMessage value={actionMessage} tone={actionTone} />
      )}

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Main Details */}
        <div className="lg:col-span-2 flex flex-col gap-8">
          <section className="bg-white p-8 rounded-[2rem] border border-slate-100 shadow-sm">
            <h2 className="text-xl font-display font-bold text-slate-900 mb-4 flex items-center gap-2">
              关于社团
            </h2>
            <div className="prose prose-slate prose-p:leading-relaxed prose-p:text-slate-600 max-w-none text-[17px]">
              <p>{club.description || "暂无详细介绍。"}</p>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <h2 className="text-xl font-display font-bold text-slate-900 flex items-center gap-2 px-2">
              <Activity className="text-secondary-500" /> 近期活动
            </h2>
            {club.club_activities && club.club_activities.length > 0 ? (
              <div className="grid gap-4">
                {club.club_activities.map((act) => (
                  <div
                    key={act.id}
                    className="bg-white border border-slate-200 p-6 rounded-[2rem] flex flex-col sm:flex-row gap-4 sm:items-center justify-between shadow-sm hover:shadow-md transition-shadow group"
                  >
                    <div className="flex flex-col gap-1">
                      <h3 className="font-semibold text-lg text-slate-900 group-hover:text-primary-600 transition-colors">
                        {act.name}
                      </h3>
                      <p className="text-slate-500 text-sm line-clamp-1">
                        {act.description}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs font-medium text-slate-400">
                        <span className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-md">
                          <Calendar size={14} />{" "}
                          {new Date(act.start_time).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-md">
                          <MapPin size={14} /> {act.location}
                        </span>
                      </div>
                    </div>
                    <button className="px-4 py-2 bg-slate-50 text-slate-700 font-medium rounded-xl border border-slate-200 hover:bg-slate-900 hover:text-white transition-colors shrink-0">
                      查看详情
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-100 border-dashed rounded-[2rem] p-8 text-center text-slate-500">
                当前暂无即将举办的活动，请后续关注！
              </div>
            )}
          </section>
        </div>

        {/* Right Column - Sidestats */}
        <div className="flex flex-col gap-6">
          <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm flex flex-col gap-6">
            <h3 className="font-display font-bold text-lg text-slate-900">
              社团概览
            </h3>

            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-primary-50 rounded-xl flex items-center justify-center shrink-0">
                <Users className="text-primary-600" size={20} />
              </div>
              <div>
                <p className="text-sm text-slate-500 font-medium">成员数</p>
                <p className="text-lg font-bold text-slate-900">
                  {club.members?.length || 0} 名成员
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-secondary-50 rounded-xl flex items-center justify-center shrink-0">
                <Activity className="text-secondary-600" size={20} />
              </div>
              <div>
                <p className="text-sm text-slate-500 font-medium">已组织活动</p>
                <p className="text-lg font-bold text-slate-900">
                  {club.club_activities?.length || 0} 场 / 学期
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-emerald-50 rounded-xl flex items-center justify-center shrink-0">
                <Sparkles className="text-emerald-600" size={20} />
              </div>
              <div>
                <p className="text-sm text-slate-500 font-medium">社团状态</p>
                <p className="text-lg font-bold text-slate-900 text-emerald-700">
                  {STATUS_MAP[club.status] || club.status}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-[2rem] border border-slate-100 shadow-sm flex flex-col gap-4">
            <h3 className="font-display font-bold text-lg text-slate-900">
              成员
            </h3>
            {club.members?.length ? (
              <div className="flex flex-col gap-2">
                {club.members.slice(0, 8).map((member) => (
                  <Link
                    key={member.id}
                    to={`/users/${member.user_id}`}
                    className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 border border-slate-100 px-3 py-2 text-sm font-medium text-slate-600 hover:text-primary-600 transition-colors"
                  >
                    <span>用户 #{member.user_id}</span>
                    <span className="text-xs text-slate-400">
                      {member.membership}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">暂无成员数据。</p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
