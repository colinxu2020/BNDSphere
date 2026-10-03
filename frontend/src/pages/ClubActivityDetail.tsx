import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  EmptyState,
  PageHeader,
  SectionTitle,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";
import { PageLoading } from "../components/ui/PageStates";
import { formatDateTime } from "../lib/format";

type ClubInfo = components["schemas"]["ClubInfo"];

export function ClubActivityDetail() {
  const { id, activityId } = useParams<{ id: string; activityId: string }>();
  const [result, setResult] = useState<{
    clubId: string;
    club: ClubInfo | null;
    error: unknown;
  } | null>(null);
  const validIds =
    /^[1-9]\d*$/.test(id ?? "") &&
    /^[1-9]\d*$/.test(activityId ?? "") &&
    Number.isSafeInteger(Number(id)) &&
    Number.isSafeInteger(Number(activityId));

  useEffect(() => {
    if (!validIds || !id) return;
    let cancelled = false;
    const load = async () => {
      try {
        const { data, error } = await client.GET("/api/v1/clubs/{club_id}", {
          params: { path: { club_id: Number(id) } },
        });
        if (!cancelled) setResult({ clubId: id, club: error ? null : (data ?? null), error });
      } catch (error) {
        if (!cancelled) setResult({ clubId: id, club: null, error });
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [id, validIds]);

  const current = result?.clubId === id ? result : null;
  const activity = current?.club?.club_activities.find((item) => item.id === Number(activityId));

  return (
    <div className="flex flex-col gap-6 pb-20">
      <Link
        to={validIds ? `/club/${id}` : "/explore"}
        className="w-fit font-medium text-slate-500 hover:text-slate-900"
      >
        {validIds ? "返回社团" : "返回探索社团"}
      </Link>
      {!validIds ? (
        <EmptyState title="未找到社团活动" />
      ) : !current ? (
        <PageLoading title="正在加载活动" />
      ) : current.error ? (
        <StatusMessage value={current.error} />
      ) : activity ? (
        <>
          <Surface>
            <PageHeader eyebrow={current.club?.name} title={activity.name} />
            <dl className="mt-6 grid gap-4 text-sm text-slate-600">
              <div>
                <dt className="font-semibold">时间</dt>
                <dd>
                  {formatDateTime(activity.start_time)} 至 {formatDateTime(activity.end_time)}
                </dd>
              </div>
              <div>
                <dt className="font-semibold">地点</dt>
                <dd className="whitespace-pre-wrap break-words">
                  {activity.location || "暂无地点"}
                </dd>
              </div>
            </dl>
            <p className="mt-6 whitespace-pre-wrap break-words leading-7 text-slate-700">
              {activity.description || "暂无活动介绍。"}
            </p>
          </Surface>
          <Surface>
            <SectionTitle title="活动图片" />
            {activity.picture_urls.length ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {activity.picture_urls.map((url, index) => (
                  <a
                    key={`${url}-${index}`}
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="overflow-hidden rounded-md border border-slate-100 bg-slate-50"
                  >
                    <img
                      src={url}
                      alt={`${activity.name} 活动图片 ${index + 1}`}
                      loading="lazy"
                      className="aspect-[4/3] w-full object-contain"
                    />
                  </a>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无活动图片" />
            )}
          </Surface>
        </>
      ) : (
        <EmptyState title="未找到社团活动" />
      )}
    </div>
  );
}
