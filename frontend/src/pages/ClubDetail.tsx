import {
  Sparkles,
  Calendar,
  MapPin,
  Hash,
  ArrowLeft,
  Settings,
  Check,
  QrCode,
  Share3,
  X,
} from "@/src/components/ui/Icons";
import { QRCodeSVG } from "qrcode.react";
import { useParams, Link, useSearchParams } from "react-router-dom";
import { motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { StatusMessage } from "../components/ui/AppPrimitives";
import { PageLoading } from "../components/ui/PageStates";
import { MEMBERSHIP_MAP } from "../lib/labels";

type ClubInfo = components["schemas"]["ClubInfo"];
type UserInfo = components["schemas"]["UserInfo"];

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

const MANAGER_ROLES = new Set(["president", "vice_president"]);

export function ClubDetail() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const sharedActivityId = searchParams.get("activity");
  const activityRefs = useRef(new Map<number, HTMLDivElement>());
  const [club, setClub] = useState<ClubInfo | null>(null);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [actionMessage, setActionMessage] = useState<unknown>(null);
  const [actionTone, setActionTone] = useState<"error" | "success">("error");
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [hasSubmittedJoinRequest, setHasSubmittedJoinRequest] = useState(false);
  const [highlightedActivityId, setHighlightedActivityId] = useState<number | null>(null);
  const [copiedActivityId, setCopiedActivityId] = useState<number | null>(null);
  const [isQrShareOpen, setIsQrShareOpen] = useState(false);
  const [isClubLinkCopied, setIsClubLinkCopied] = useState(false);

  useEffect(() => {
    const fetchClubInfo = async () => {
      setIsLoading(true);
      setError(null);
      setHasSubmittedJoinRequest(false);
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

  useEffect(() => {
    if (!club || !sharedActivityId) return;

    const activityId = Number(sharedActivityId);
    if (
      !Number.isInteger(activityId) ||
      !club.club_activities.some((item) => item.id === activityId)
    ) {
      return;
    }

    const scrollTimer = window.setTimeout(() => {
      const target = activityRefs.current.get(activityId);
      if (!target) return;

      setHighlightedActivityId(activityId);
      target.scrollIntoView({ behavior: "smooth", block: "center" });
      target.focus({ preventScroll: true });
    }, 250);
    const highlightTimer = window.setTimeout(() => setHighlightedActivityId(null), 4250);

    return () => {
      window.clearTimeout(scrollTimer);
      window.clearTimeout(highlightTimer);
    };
  }, [club, sharedActivityId]);

  const shareActivity = async (activityId: number, activityName: string) => {
    const url = new URL(`/club/${club?.id}?activity=${activityId}`, window.location.origin);
    const shareData = {
      title: `${activityName} · ${club?.name || "BNDSphere"}`,
      text: `查看 ${club?.name || "社团"} 的活动「${activityName}」`,
      url: url.toString(),
    };

    try {
      if (navigator.share) {
        await navigator.share(shareData);
        return;
      }
      await navigator.clipboard.writeText(shareData.url);
      setCopiedActivityId(activityId);
    } catch (shareError) {
      if (shareError instanceof DOMException && shareError.name === "AbortError") return;
      setActionTone("error");
      setActionMessage("分享失败，请稍后重试");
    }
  };

  useEffect(() => {
    if (copiedActivityId == null) return;
    const timer = window.setTimeout(() => setCopiedActivityId(null), 2200);
    return () => window.clearTimeout(timer);
  }, [copiedActivityId]);

  const clubShareUrl = club ? new URL(`/club/${club.id}`, window.location.origin).toString() : "";

  const copyClubShareLink = async () => {
    try {
      await navigator.clipboard.writeText(clubShareUrl);
      setIsClubLinkCopied(true);
    } catch {
      setActionTone("error");
      setActionMessage("复制链接失败，请稍后重试");
    }
  };

  const downloadClubQrCode = () => {
    const svg = document.getElementById("club-share-qr-code");
    if (!(svg instanceof SVGElement)) return;

    const blob = new Blob([new XMLSerializer().serializeToString(svg)], {
      type: "image/svg+xml;charset=utf-8",
    });
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `${club?.name || "社团"}-二维码.svg`;
    link.click();
    URL.revokeObjectURL(downloadUrl);
  };

  useEffect(() => {
    if (!isClubLinkCopied) return;
    const timer = window.setTimeout(() => setIsClubLinkCopied(false), 2200);
    return () => window.clearTimeout(timer);
  }, [isClubLinkCopied]);

  useEffect(() => {
    if (!isQrShareOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsQrShareOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [isQrShareOpen]);

  const currentMembership = useMemo(
    () =>
      club?.members.find((member) => member.user_id === user?.id && member.membership !== "left")
        ?.membership || null,
    [club?.members, user?.id],
  );
  const canJoin = !currentMembership && !hasSubmittedJoinRequest;
  const canLeave = currentMembership === "member" || currentMembership === "pending";
  const canManage = currentMembership ? MANAGER_ROLES.has(currentMembership) : false;
  const activeMembers = useMemo(
    () =>
      (club?.members || []).filter((member) =>
        ["member", "president", "vice_president"].includes(member.membership),
      ),
    [club?.members],
  );

  const joinClub = async () => {
    const message = window.prompt("请输入入社申请留言（可以留空）", "");
    if (message === null) return;

    setIsActionLoading(true);
    setActionMessage(null);
    try {
      const { error } = await client.POST("/api/v1/clubs/{club_id}/membership-requests", {
        params: { path: { club_id: Number(id) } },
        body: { message },
      });
      if (error) {
        setActionTone("error");
        setActionMessage(error);
      } else {
        setActionTone("success");
        setActionMessage("加入申请已提交");
        setHasSubmittedJoinRequest(true);
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
      const { error, response } = await client.DELETE("/api/v1/clubs/{club_id}/members/me", {
        params: { path: { club_id: Number(id) } },
      });
      if (error) {
        setActionTone("error");
        setActionMessage(error);
      } else {
        setActionTone("success");
        setActionMessage(`已退出社团（HTTP ${response.status}）`);
        if (user && club) {
          setClub({
            ...club,
            members: club.members.map((member) =>
              member.user_id === user.id ? { ...member, membership: "left" } : member,
            ),
          });
        }
      }
    } catch (requestError) {
      setActionTone("error");
      setActionMessage(requestError);
    } finally {
      setIsActionLoading(false);
    }
  };

  if (isLoading) {
    return <PageLoading />;
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

      <div className="bg-white p-8 md:p-12 rounded-md border border-slate-100 shadow-sm relative overflow-hidden">
        <div className="flex flex-col md:flex-row gap-8 relative z-10 items-start md:items-center">
          <div className="w-28 h-28 md:w-40 md:h-40 rounded-md bg-slate-100 flex items-center justify-center shrink-0 shadow-inner overflow-hidden border border-slate-200">
            {club.logo_uri ? (
              <img src={club.logo_uri} alt={club.name} className="w-full h-full object-cover" />
            ) : (
              <Hash className="text-slate-400 stroke-[1.5]" size={48} />
            )}
          </div>

          <div className="flex flex-col flex-grow">
            <div className="flex gap-2 items-center mb-3">
              <span className="text-xs font-bold tracking-wider text-primary-600 bg-primary-50 px-3 py-1 rounded-md border border-primary-100">
                {CATEGORY_MAP[club.category] || club.category}
              </span>
              {club.star_level && club.star_level !== "none" && (
                <span className="flex items-center gap-1 text-xs font-bold text-yellow-600 bg-yellow-50 px-3 py-1 rounded-md border border-yellow-100">
                  <Sparkles size={14} className="fill-yellow-500 text-yellow-500" />
                  {STAR_LEVEL_MAP[club.star_level] || club.star_level}
                </span>
              )}
            </div>

            <h1 className="text-3xl md:text-5xl font-display font-bold text-slate-900 tracking-tight leading-[1.1] mb-2">
              {club.name}
            </h1>
            <p className="text-lg md:text-xl text-slate-500 font-medium">{club.summary}</p>
          </div>

          <div className="flex md:flex-col gap-3 w-full md:w-auto">
            <button
              type="button"
              onClick={() => setIsQrShareOpen(true)}
              className="flex-1 md:flex-none px-6 py-3 bg-slate-50 hover:bg-primary-50 border border-slate-200 hover:border-primary-200 active:scale-95 text-slate-700 hover:text-primary-700 font-semibold rounded-md transition-all text-center inline-flex items-center justify-center gap-2"
            >
              <QrCode size={17} /> 分享社团
            </button>
            {canJoin && (
              <button
                onClick={joinClub}
                disabled={isActionLoading}
                className="flex-1 md:flex-none px-6 py-3 bg-primary-500 hover:bg-primary-600 active:scale-95 text-white font-semibold rounded-md shadow-lg shadow-primary-500/25 transition-all text-center disabled:opacity-70"
              >
                加入社团
              </button>
            )}
            {canLeave && (
              <button
                onClick={leaveClub}
                disabled={isActionLoading}
                className="flex-1 md:flex-none px-6 py-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 active:scale-95 text-slate-800 font-semibold rounded-md transition-all text-center disabled:opacity-70"
              >
                退出社团
              </button>
            )}
            {canManage && (
              <Link
                to={`/club/${club.id}/manage`}
                className="flex-1 md:flex-none px-6 py-3 bg-slate-900 hover:bg-slate-800 active:scale-95 text-white font-semibold rounded-md transition-all text-center inline-flex items-center justify-center gap-2"
              >
                <Settings size={16} /> 管理
              </Link>
            )}
          </div>
        </div>
      </div>

      {actionMessage && <StatusMessage value={actionMessage} tone={actionTone} />}

      {isQrShareOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/45 p-4 backdrop-blur-sm"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setIsQrShareOpen(false);
          }}
        >
          <motion.section
            role="dialog"
            aria-modal="true"
            aria-labelledby="club-share-title"
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            className="relative w-full max-w-sm overflow-hidden rounded-md border border-slate-100 bg-white p-6 shadow-2xl shadow-slate-950/20"
          >
            <div className="absolute inset-x-0 top-0 h-1 bg-primary-500" />
            <button
              type="button"
              onClick={() => setIsQrShareOpen(false)}
              aria-label="关闭社团分享二维码"
              className="absolute right-4 top-4 rounded-md p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30"
            >
              <X size={18} />
            </button>
            <div className="pr-10">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary-600">
                Share club
              </p>
              <h2
                id="club-share-title"
                className="mt-1 font-display text-2xl font-bold text-slate-900"
              >
                分享 {club.name}
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                扫码即可打开社团详情，了解社团介绍和近期活动。
              </p>
            </div>

            <div className="mt-6 flex justify-center rounded-md border border-slate-100 bg-slate-50 p-5">
              <div className="rounded-md bg-white p-3 shadow-sm">
                <QRCodeSVG
                  id="club-share-qr-code"
                  value={clubShareUrl}
                  size={208}
                  level="M"
                  includeMargin={false}
                  fgColor="#0f172a"
                  bgColor="#ffffff"
                  title={`${club.name} 社团分享二维码`}
                />
              </div>
            </div>

            <div className="mt-5 rounded-md border border-slate-100 bg-slate-50 p-3">
              <p className="truncate text-xs text-slate-500" title={clubShareUrl}>
                {clubShareUrl}
              </p>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={copyClubShareLink}
                className="inline-flex items-center justify-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 active:scale-[0.98]"
              >
                {isClubLinkCopied ? <Check size={17} /> : <Share3 size={17} />}
                {isClubLinkCopied ? "已复制" : "复制链接"}
              </button>
              <button
                type="button"
                onClick={downloadClubQrCode}
                className="inline-flex items-center justify-center gap-2 rounded-md bg-primary-500 px-4 py-3 text-sm font-semibold text-white shadow-md shadow-primary-500/20 transition hover:bg-primary-600 active:scale-[0.98]"
              >
                <QrCode size={17} /> 下载二维码
              </button>
            </div>
          </motion.section>
        </div>
      )}

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column - Main Details */}
        <div className="lg:col-span-2 flex flex-col gap-8">
          <section className="bg-white p-8 rounded-md border border-slate-100 shadow-sm">
            <h2 className="text-xl font-display font-bold text-slate-900 mb-4 flex items-center gap-2">
              关于社团
            </h2>
            <div className="prose prose-slate prose-p:leading-relaxed prose-p:text-slate-600 max-w-none text-[17px]">
              <p>{club.description || "暂无详细介绍。"}</p>
            </div>
          </section>

          <section className="flex flex-col gap-4">
            <div className="flex flex-wrap items-center justify-between gap-3 px-2">
              <h2 className="text-xl font-display font-bold text-slate-900 flex items-center gap-2">
                <Calendar className="text-slate-500" /> 社团活动
              </h2>
              <div className="text-right">
                <p className="text-sm text-slate-500 font-medium">已组织活动</p>
                <p className="text-base font-semibold text-slate-900">
                  {club.club_activities?.length || 0} 场 / 学期
                </p>
              </div>
            </div>
            {club.club_activities && club.club_activities.length > 0 ? (
              <div className="grid gap-4">
                {club.club_activities.map((act) => (
                  <div
                    key={act.id}
                    id={`activity-${act.id}`}
                    ref={(element) => {
                      if (element) activityRefs.current.set(act.id, element);
                      else activityRefs.current.delete(act.id);
                    }}
                    tabIndex={-1}
                    className={`relative overflow-hidden bg-white border p-6 rounded-md flex flex-col sm:flex-row gap-5 sm:items-center justify-between shadow-sm transition-all duration-700 group outline-none ${
                      highlightedActivityId === act.id
                        ? "border-primary-400 bg-primary-50/30 ring-4 ring-primary-500/15 shadow-lg shadow-primary-500/10"
                        : Number(sharedActivityId) === act.id
                          ? "border-primary-200 bg-primary-50/20 shadow-md"
                          : "border-slate-200 hover:border-primary-200 hover:shadow-md"
                    }`}
                  >
                    {highlightedActivityId === act.id && (
                      <motion.div
                        aria-hidden="true"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: [0, 0.12, 0.04] }}
                        transition={{ duration: 2.6 }}
                        className="pointer-events-none absolute inset-0 bg-primary-500"
                      />
                    )}
                    <div className="relative flex min-w-0 flex-col gap-1">
                      <h3 className="font-semibold text-lg text-slate-900 group-hover:text-primary-600 transition-colors">
                        {act.name}
                      </h3>
                      <p className="text-slate-500 text-sm line-clamp-1">{act.description}</p>
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-xs font-medium text-slate-400">
                        <span className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-md">
                          <Calendar size={14} /> {new Date(act.start_time).toLocaleDateString()}
                        </span>
                        <span className="flex items-center gap-1.5 bg-slate-50 px-2 py-1 rounded-md">
                          <MapPin size={14} /> {act.location}
                        </span>
                      </div>
                    </div>
                    <div className="relative flex w-full shrink-0 flex-col gap-2 sm:w-auto sm:flex-row">
                      {canManage && (
                        <Link
                          to={`/club/${club.id}/manage?activity=${act.id}`}
                          aria-label={`管理活动：${act.name}`}
                          title="管理活动"
                          className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-800 bg-slate-900 px-3.5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-slate-800 active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-slate-500/30 focus-visible:outline-none sm:w-auto"
                        >
                          <Settings size={17} /> 管理
                        </Link>
                      )}
                      <button
                        type="button"
                        onClick={() => shareActivity(act.id, act.name)}
                        aria-label={`分享活动：${act.name}`}
                        title="分享活动"
                        className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm font-semibold text-slate-600 transition-all hover:border-primary-200 hover:bg-primary-50 hover:text-primary-700 active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-primary-500/30 focus-visible:outline-none sm:w-auto"
                      >
                        {copiedActivityId === act.id ? (
                          <>
                            <Check size={17} /> 已复制链接
                          </>
                        ) : (
                          <>
                            <Share3 size={17} /> 分享
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-slate-50 border border-slate-100 border-dashed rounded-md p-8 text-center text-slate-500">
                当前暂无即将举办的活动，请后续关注！
              </div>
            )}
          </section>
        </div>

        {/* Right Column - Sidestats */}
        <div className="flex flex-col gap-6">
          <div className="bg-white p-6 rounded-md border border-slate-100 shadow-sm flex flex-col gap-4">
            <h3 className="font-display font-bold text-lg text-slate-900">成员</h3>
            <div>
              <p className="text-sm font-medium text-slate-600">{activeMembers.length} 名成员</p>
            </div>
            {activeMembers.length ? (
              <div className="flex flex-col gap-2">
                {activeMembers.slice(0, 8).map((member) => (
                  <Link
                    key={member.id}
                    to={`/users/${member.user_id}`}
                    className="flex items-center justify-between gap-3 rounded-md bg-slate-50 border border-slate-100 px-3 py-2 text-sm font-medium text-slate-600 hover:text-primary-600 transition-colors"
                  >
                    <span>{member.user.username}</span>
                    <span className="text-xs text-slate-400">
                      {MEMBERSHIP_MAP[member.membership]}
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
