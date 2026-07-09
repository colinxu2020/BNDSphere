import { useEffect, useState, type Key } from "react";
import { motion } from "motion/react";
import {
  Award,
  Building2,
  CalendarDays,
  ExternalLink,
  FileText,
  RefreshCw,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  AUDIT_STATUS_MAP,
  CATEGORY_MAP,
  STAR_LEVEL_MAP,
} from "../lib/labels";
import { formatDateTime } from "../lib/format";
import {
  Badge,
  EmptyState,
  PageHeader,
  SecondaryButton,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";

type StarApplication =
  components["schemas"]["StarLevelApplicationPublicInfo"];
type AuditStatus = components["schemas"]["AuditStatusEnum"];
type UserGrade = components["schemas"]["UserGradeEnum"];

const GRADE_MAP: Record<UserGrade, string> = {
  grade_7: "初一",
  grade_8: "初二",
  grade_9: "初三",
  grade_10: "高一",
  grade_11: "高二",
  grade_12: "高三",
  inter_grade_9: "国际初三",
  inter_grade_10: "国际高一",
  inter_grade_11: "国际高二",
  inter_grade_12: "国际高三",
};

const AUDIT_TONE: Record<AuditStatus, "yellow" | "green" | "red"> = {
  pending: "yellow",
  approved: "green",
  rejected: "red",
};

export function StarLevelApplications() {
  const [applications, setApplications] = useState<StarApplication[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);

  const fetchApplications = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const { data, error } = await client.GET("/api/v1/star-level/", {
        params: { query: { size: 50 } },
      });
      if (error) {
        setLoadError(error);
        setApplications([]);
      } else {
        setApplications(data?.items || []);
      }
    } catch (error) {
      setLoadError(error);
      setApplications([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-6 pb-20"
    >
      <PageHeader
        eyebrow="Star Level"
        title="星级评价"
        action={
          <SecondaryButton
            type="button"
            onClick={fetchApplications}
            disabled={isLoading}
          >
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {loadError && <StatusMessage value={loadError} />}

      {isLoading ? (
        <Surface className="flex items-center justify-center py-16 text-slate-500">
          正在加载星级评价表...
        </Surface>
      ) : applications.length ? (
        <div className="flex flex-col gap-4">
          {applications.map((application) => (
            <StarApplicationCard
              key={application.id}
              application={application}
            />
          ))}
        </div>
      ) : (
        <EmptyState title="暂无星级评价表" icon={<Award size={24} />} />
      )}
    </motion.div>
  );
}

function StarApplicationCard({
  application,
}: {
  key?: Key;
  application: StarApplication;
}) {
  const auditStatus = application.audit_status;
  const targetGrades = [
    application.target_grade_1 ? GRADE_MAP[application.target_grade_1] : null,
    application.target_grade_2 ? GRADE_MAP[application.target_grade_2] : null,
  ].filter(Boolean);

  return (
    <Surface className="p-5 md:p-6">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-md border border-slate-100 bg-slate-50 text-slate-400">
            {application.club.logo_uri ? (
              <img
                src={application.club.logo_uri}
                alt={application.club.name}
                className="h-full w-full object-cover"
              />
            ) : (
              <Building2 size={24} />
            )}
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Link
                to={`/club/${application.club_id}`}
                className="truncate text-lg font-bold text-slate-900 hover:text-primary-600"
              >
                {application.club.name}
              </Link>
              <Badge tone="slate">{CATEGORY_MAP[application.club.category]}</Badge>
              {auditStatus && (
                <Badge tone={AUDIT_TONE[auditStatus]}>
                  {AUDIT_STATUS_MAP[auditStatus]}
                </Badge>
              )}
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-slate-500">
              <span className="inline-flex items-center gap-1">
                <CalendarDays size={15} />
                {application.academic_term.term_name}
              </span>
              <span>提交于 {formatDateTime(application.created_at)}</span>
              <span>当前星级 {STAR_LEVEL_MAP[application.club.star_level]}</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4 lg:min-w-[360px]">
          <Metric label="申请竞赛分" value={application.requested_contest_score} />
          <Metric label="最终竞赛分" value={application.final_contest_score} />
          <Metric label="审核总分" value={application.approved_score} />
          <Metric
            label="评定星级"
            value={
              application.approved_level
                ? STAR_LEVEL_MAP[application.approved_level]
                : "未评定"
            }
          />
        </div>
      </div>

      <div className="mt-5 grid gap-4 border-t border-slate-100 pt-5 lg:grid-cols-[1fr_280px]">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
            <FileText size={16} />
            特色说明
          </div>
          <p className="whitespace-pre-wrap text-sm leading-6 text-slate-600">
            {application.uniqueness_statement || "未填写特色说明。"}
          </p>
        </div>
        <div className="flex flex-col gap-2 text-sm text-slate-600">
          <InfoRow
            label="目标级部"
            value={targetGrades.length ? targetGrades.join("、") : "未填写"}
          />
          <InfoRow
            label="特色认可"
            value={approvalText(application.uniqueness_approved)}
          />
          <InfoRow
            label="成长故事"
            value={approvalText(application.growth_story_approved)}
          />
          <div className="mt-1 flex flex-wrap gap-2">
            <ExternalLinkButton href={application.contest_attachment}>
              竞赛附件
            </ExternalLinkButton>
            <ExternalLinkButton href={application.growth_story_url}>
              成长故事
            </ExternalLinkButton>
          </div>
        </div>
      </div>
    </Surface>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value?: number | string | null;
}) {
  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 px-3 py-2">
      <div className="text-xs font-semibold text-slate-400">{label}</div>
      <div className="mt-1 font-bold text-slate-900">{value ?? "未填写"}</div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-slate-400">{label}</span>
      <span className="font-semibold text-slate-700">{value}</span>
    </div>
  );
}

function ExternalLinkButton({
  href,
  children,
}: {
  href?: string | null;
  children: string;
}) {
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:border-primary-100 hover:text-primary-600"
    >
      {children}
      <ExternalLink size={13} />
    </a>
  );
}

function approvalText(value?: boolean | null): string {
  if (value === true) return "已认可";
  if (value === false) return "未认可";
  return "待审核";
}
