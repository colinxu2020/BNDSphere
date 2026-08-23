import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, Award, CalendarDays, FileText, MapPin, Users } from "@/src/components/ui/Icons";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  Badge,
  EmptyState,
  PageHeader,
  SectionTitle,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";
import { formatDateTime } from "../lib/format";

type JointActivity = components["schemas"]["JointActivityPublicInfo"];

export function JointActivityDetail() {
  const { id } = useParams<{ id: string }>();
  const [activity, setActivity] = useState<JointActivity | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      const response = await client.GET("/api/v1/joint-activities/{activity_id}", {
        params: { path: { activity_id: Number(id) } },
      });
      setError(response.error || null);
      setActivity(response.error ? null : response.data || null);
      setIsLoading(false);
    };
    load().catch((requestError) => {
      setError(requestError);
      setActivity(null);
      setIsLoading(false);
    });
  }, [id]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-8 pb-20"
    >
      <Link
        to="/joint-activities"
        className="inline-flex w-fit items-center gap-2 font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft size={18} /> 返回联合活动
      </Link>
      {isLoading ? (
        <div className="h-72 animate-pulse rounded-md border bg-white" />
      ) : error ? (
        <StatusMessage value={error} />
      ) : activity ? (
        <>
          <Surface>
            <PageHeader
              eyebrow={`${activity.initiator_club.name} 发起`}
              title={activity.name}
              description={activity.description}
            />
            <div className="mt-6 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
              <span className="inline-flex items-center gap-2">
                <CalendarDays size={17} /> {formatDateTime(activity.starts_at)} 至{" "}
                {formatDateTime(activity.ends_at)}
              </span>
              <span className="inline-flex items-center gap-2">
                <MapPin size={17} /> {activity.location}
              </span>
            </div>
          </Surface>

          <Surface>
            <SectionTitle icon={<Users size={20} />} title="参与社团" />
            <div className="flex flex-wrap gap-3">
              {activity.participations.map((participation) => (
                <Link
                  key={participation.id}
                  to={`/club/${participation.club_id}`}
                  className="rounded-md border border-slate-100 bg-slate-50 px-4 py-3 font-semibold text-slate-700 hover:text-primary-600"
                >
                  {participation.club.name}
                  {participation.is_initiator && <Badge tone="primary">发起</Badge>}
                </Link>
              ))}
            </div>
          </Surface>

          <Surface>
            <SectionTitle icon={<FileText size={20} />} title="活动档案" />
            {activity.archive_text || activity.archive_files.length ? (
              <div className="grid gap-5">
                {activity.archive_text && (
                  <p className="whitespace-pre-wrap leading-7 text-slate-700">
                    {activity.archive_text}
                  </p>
                )}
                {activity.archive_files.length > 0 && (
                  <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {activity.archive_files.map((file, index) => (
                      <a
                        key={file}
                        href={file}
                        target="_blank"
                        rel="noreferrer"
                        className="overflow-hidden rounded-md border border-slate-100 bg-slate-50"
                      >
                        <img
                          src={file}
                          alt={`${activity.name} 活动资料 ${index + 1}`}
                          className="aspect-[4/3] w-full object-cover"
                        />
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <EmptyState title="活动资料尚未上传" />
            )}
          </Surface>

          {activity.final_status === "approved" && (
            <Surface className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-md bg-yellow-50 text-yellow-700">
                <Award size={22} />
              </div>
              <div>
                <p className="text-sm text-slate-500">社联终审星级评价分值</p>
                <p className="text-2xl font-bold text-slate-900">{activity.final_score} 分</p>
              </div>
            </Surface>
          )}
        </>
      ) : (
        <EmptyState title="未找到联合活动" />
      )}
    </motion.div>
  );
}
