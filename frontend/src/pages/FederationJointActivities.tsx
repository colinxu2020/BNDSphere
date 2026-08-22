import { useEffect, useMemo, useState, type ReactNode } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  Award,
  CalendarDays,
  Check,
  FileText,
  MapPin,
  RefreshCw,
  X,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  Badge,
  EmptyState,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
} from "../components/ui/AppPrimitives";
import { AUDIT_STATUS_MAP } from "../lib/labels";
import { formatDateTime } from "../lib/format";

type JointActivity = components["schemas"]["JointActivityInfo"];

export function FederationJointActivities() {
  const [items, setItems] = useState<JointActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<unknown>(null);
  const [messageTone, setMessageTone] = useState<"error" | "success">("error");
  const [scores, setScores] = useState<Record<number, string>>({});
  const [busyId, setBusyId] = useState<number | null>(null);

  const preliminaryItems = useMemo(
    () => items.filter((activity) => activity.preliminary_status === "pending"),
    [items],
  );
  const finalItems = useMemo(
    () => items.filter((activity) => activity.final_status === "pending"),
    [items],
  );

  const refresh = async () => {
    setIsLoading(true);
    const response = await client.GET("/api/v1/club-federation/joint-activities/", {
      params: { query: { size: 100 } },
    });
    setItems(response.error ? [] : response.data?.items || []);
    if (response.error) {
      setMessage(response.error);
      setMessageTone("error");
    }
    setIsLoading(false);
  };

  useEffect(() => {
    refresh().catch((error) => {
      setMessage(error);
      setMessageTone("error");
      setIsLoading(false);
    });
  }, []);

  const preliminaryReview = async (activityId: number, status: "approved" | "rejected") => {
    setBusyId(activityId);
    const response = await client.PATCH(
      "/api/v1/club-federation/joint-activities/{activity_id}/preliminary-review",
      { params: { path: { activity_id: activityId } }, body: { status } },
    );
    setBusyId(null);
    setMessageTone(response.error ? "error" : "success");
    setMessage(response.error || `联合活动预审已${status === "approved" ? "通过" : "驳回"}`);
    if (!response.error) await refresh();
  };

  const finalReview = async (activityId: number, status: "approved" | "rejected") => {
    const finalScore = Number(scores[activityId] || 0);
    if (status === "approved" && (finalScore < 6 || finalScore > 8)) {
      setMessageTone("error");
      setMessage("联合活动通过终审时，最终分值必须为 6–8 分");
      return;
    }
    setBusyId(activityId);
    const response = await client.PATCH(
      "/api/v1/club-federation/joint-activities/{activity_id}/final-review",
      {
        params: { path: { activity_id: activityId } },
        body: {
          status,
          final_score: status === "approved" ? finalScore : 0,
        },
      },
    );
    setBusyId(null);
    setMessageTone(response.error ? "error" : "success");
    setMessage(response.error || `联合活动终审已${status === "approved" ? "通过" : "驳回"}`);
    if (!response.error) await refresh();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-8 pb-20"
    >
      <Link
        to="/federation"
        className="inline-flex w-fit items-center gap-2 font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft size={18} /> 返回社联工作台
      </Link>
      <PageHeader
        eyebrow="Federation"
        title="联合活动审核"
        action={
          <SecondaryButton type="button" onClick={refresh} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />
      {message && <StatusMessage value={message} tone={messageTone} />}

      <Surface>
        <SectionTitle icon={<CalendarDays size={20} />} title="待预审" />
        {isLoading ? (
          <Loading />
        ) : preliminaryItems.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {preliminaryItems.map((activity) => (
              <div key={activity.id}>
                <ReviewCard activity={activity}>
                  <div className="flex flex-wrap gap-2">
                    <PrimaryButton
                      type="button"
                      onClick={() => preliminaryReview(activity.id, "approved")}
                      loading={busyId === activity.id}
                    >
                      <Check size={16} /> 通过并公开
                    </PrimaryButton>
                    <SecondaryButton
                      type="button"
                      onClick={() => preliminaryReview(activity.id, "rejected")}
                      disabled={busyId === activity.id}
                      className="text-red-600"
                    >
                      <X size={16} /> 驳回
                    </SecondaryButton>
                  </div>
                </ReviewCard>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="暂无待预审联合活动" />
        )}
      </Surface>

      <Surface>
        <SectionTitle
          icon={<Award size={20} />}
          title="待终审"
          description="查看文字或图片档案，并填写本次活动的星级评价分值。"
        />
        {isLoading ? (
          <Loading />
        ) : finalItems.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {finalItems.map((activity) => (
              <div key={activity.id}>
                <ReviewCard activity={activity} showArchive>
                  <Field label="最终分值">
                    <input
                      className={inputClassName}
                      type="number"
                      min="6"
                      max="8"
                      value={scores[activity.id] || ""}
                      onChange={(event) =>
                        setScores({ ...scores, [activity.id]: event.target.value })
                      }
                    />
                  </Field>
                  <div className="flex flex-wrap gap-2">
                    <PrimaryButton
                      type="button"
                      onClick={() => finalReview(activity.id, "approved")}
                      loading={busyId === activity.id}
                    >
                      <Check size={16} /> 通过终审
                    </PrimaryButton>
                    <SecondaryButton
                      type="button"
                      onClick={() => finalReview(activity.id, "rejected")}
                      disabled={busyId === activity.id}
                      className="text-red-600"
                    >
                      <X size={16} /> 驳回
                    </SecondaryButton>
                  </div>
                </ReviewCard>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="暂无待终审联合活动" />
        )}
      </Surface>

      <Surface>
        <SectionTitle icon={<FileText size={20} />} title="全部联合活动" />
        <div className="grid gap-3">
          {items.map((activity) => (
            <div
              key={activity.id}
              className="flex flex-col gap-3 rounded-md border border-slate-100 bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between"
            >
              <div>
                <div className="flex flex-wrap gap-2">
                  <Badge
                    tone={
                      activity.preliminary_status === "approved"
                        ? "green"
                        : activity.preliminary_status === "rejected"
                          ? "red"
                          : "yellow"
                    }
                  >
                    预审 {AUDIT_STATUS_MAP[activity.preliminary_status]}
                  </Badge>
                  {activity.final_status && (
                    <Badge>终审 {AUDIT_STATUS_MAP[activity.final_status]}</Badge>
                  )}
                </div>
                <h3 className="mt-2 font-bold text-slate-900">{activity.name}</h3>
                <p className="mt-1 text-sm text-slate-500">
                  {activity.initiator_club.name} · {formatDateTime(activity.starts_at)}
                </p>
              </div>
              {activity.preliminary_status === "approved" && (
                <Link
                  to={`/joint-activities/${activity.id}`}
                  className="text-sm font-semibold text-primary-600"
                >
                  公开页面
                </Link>
              )}
            </div>
          ))}
        </div>
      </Surface>
    </motion.div>
  );
}

function ReviewCard({
  activity,
  showArchive,
  children,
}: {
  activity: JointActivity;
  showArchive?: boolean;
  children: ReactNode;
}) {
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 p-5">
      <Badge tone="primary">{activity.initiator_club.name} 发起</Badge>
      <h3 className="mt-3 text-lg font-bold text-slate-900">{activity.name}</h3>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-600">
        {activity.description}
      </p>
      <div className="mt-3 grid gap-2 text-xs font-medium text-slate-500">
        <span className="inline-flex items-center gap-2">
          <CalendarDays size={14} /> {formatDateTime(activity.starts_at)} 至{" "}
          {formatDateTime(activity.ends_at)}
        </span>
        <span className="inline-flex items-center gap-2">
          <MapPin size={14} /> {activity.location}
        </span>
        <span>{activity.participations.length} 个校内社团登记参与</span>
      </div>
      {showArchive && (
        <div className="mt-4 rounded-md border border-slate-100 bg-white p-4">
          <p className="whitespace-pre-wrap text-sm text-slate-600">
            {activity.archive_text || "无文字档案"}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {activity.archive_files.map((file, index) => (
              <a
                key={file}
                href={file}
                target="_blank"
                rel="noreferrer"
                className="text-sm font-semibold text-primary-600"
              >
                图片 {index + 1}
              </a>
            ))}
          </div>
        </div>
      )}
      <div className="mt-5 grid gap-3">{children}</div>
    </div>
  );
}

function Loading() {
  return <div className="h-40 animate-pulse rounded-md bg-slate-50" />;
}
