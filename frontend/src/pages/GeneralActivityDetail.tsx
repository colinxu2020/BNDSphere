import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, CheckCircle2 } from "@/src/components/ui/Icons";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  ACTIVITY_LEVEL_MAP,
  AUDIT_STATUS_MAP,
  PARTICIPATION_MAP,
} from "../lib/labels";
import { formatDateTime } from "../lib/format";
import {
  Badge,
  EmptyState,
  PageHeader,
  SectionTitle,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];

export function GeneralActivityDetail() {
  const { id } = useParams<{ id: string }>();
  const [activityInfo, setActivityInfo] = useState<GeneralActivity | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const fetchActivity = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET(
          "/api/v1/general-activities/{activity_id}",
          {
            params: { path: { activity_id: Number(id) } },
          },
        );
        if (error) {
          setError(error);
          setActivityInfo(null);
        } else {
          setActivityInfo(data || null);
        }
      } catch (requestError) {
        setError(requestError);
        setActivityInfo(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchActivity();
  }, [id]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8"
    >
      <Link
        to="/activities"
        className="inline-flex items-center gap-2 text-content-muted hover:text-content font-medium w-fit transition-colors"
      >
        <ArrowLeft size={18} /> 返回活动
      </Link>

      {isLoading ? (
        <div className="animate-pulse bg-surface rounded-md h-72 border border-edge-subtle" />
      ) : error ? (
        <StatusMessage value={error} />
      ) : activityInfo ? (
        <>
          <Surface className="relative overflow-hidden">
            <div className="relative z-10">
              <PageHeader
                eyebrow={ACTIVITY_LEVEL_MAP[activityInfo.level]}
                title={activityInfo.name}
                description={activityInfo.description}
              />
            </div>
          </Surface>

          <Surface>
            <SectionTitle
              icon={<CheckCircle2 size={20} />}
              className="items-center"
              iconClassName="border border-edge-subtle bg-surface-sunken text-content-muted"
              title="社团记录"
            />
            {activityInfo.club_records?.length ? (
              <div className="grid gap-4">
                {activityInfo.club_records.map((record) => (
                  <div
                    key={record.id}
                    className="rounded-md border border-edge-subtle bg-surface-sunken p-5"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge
                            tone={
                              record.audit_status === "approved"
                                ? "green"
                                : record.audit_status === "rejected"
                                  ? "red"
                                  : "yellow"
                            }
                          >
                            {AUDIT_STATUS_MAP[record.audit_status]}
                          </Badge>
                          <Badge>
                            {PARTICIPATION_MAP[record.participation_type]}
                          </Badge>
                        </div>
                        <h3 className="mt-3">
                          <Link
                            to={`/club/${record.club_id}`}
                            className="font-semibold text-content hover:text-tone-brand-fg transition-colors"
                          >
                            社团 #{record.club_id}
                          </Link>
                        </h3>
                        <p className="text-sm text-content-muted mt-1">
                          申请分值 {record.requested_score}，提交于{" "}
                          {formatDateTime(record.created_at)}
                        </p>
                      </div>
                    </div>
                    {record.proof_files?.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-4">
                        {record.proof_files.map((file) => (
                          <a
                            key={file}
                            href={file}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs font-medium text-content-muted bg-surface border border-edge-subtle rounded-lg px-2.5 py-1 hover:text-tone-brand-fg"
                          >
                            证明材料
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无社团记录" />
            )}
          </Surface>
        </>
      ) : (
        <EmptyState title="未找到活动" />
      )}
    </motion.div>
  );
}
