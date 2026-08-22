import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowUpRight, CalendarDays, MapPin, Search, Users } from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  Badge,
  EmptyState,
  PageHeader,
  StatusMessage,
  inputClassName,
} from "../components/ui/AppPrimitives";
import { formatDateTime } from "../lib/format";

type JointActivity = components["schemas"]["JointActivityInfo"];

export function JointActivities() {
  const [items, setItems] = useState<JointActivity[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setIsLoading(true);
      setError(null);
      const response = await client.GET("/api/v1/joint-activities/", {
        params: { query: { size: 50, search: search || undefined } },
      });
      if (cancelled) return;
      if (response.error) {
        setError(response.error);
        setItems([]);
      } else {
        setItems(response.data?.items || []);
      }
      setIsLoading(false);
    };
    load().catch((requestError) => {
      if (!cancelled) {
        setError(requestError);
        setItems([]);
        setIsLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [search]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <PageHeader eyebrow="Joint Activities" title="社团联合活动" />

      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-3.5 h-5 w-5 text-slate-400" />
        <input
          className={`${inputClassName} pl-11`}
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="搜索联合活动..."
        />
      </div>

      {error && <StatusMessage value={error} />}
      {isLoading ? (
        <div className="flex min-h-64 items-center justify-center rounded-md border border-slate-100 bg-white text-sm font-medium text-slate-500">
          正在加载联合活动...
        </div>
      ) : items.length ? (
        <div className="grid gap-5 md:grid-cols-2">
          {items.map((activity) => (
            <div key={activity.id}>
              <Link
                to={`/joint-activities/${activity.id}`}
                className="group block h-full rounded-md border border-slate-200 bg-white p-6 shadow-sm transition hover:border-primary-200 hover:shadow-md"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-md bg-primary-50 text-primary-600">
                    <Users size={22} />
                  </div>
                  <ArrowUpRight
                    className="text-slate-300 transition group-hover:text-primary-600"
                    size={18}
                  />
                </div>
                <Badge tone="primary">{activity.initiator_club.name} 发起</Badge>
                <h2 className="mt-3 text-xl font-bold text-slate-900">{activity.name}</h2>
                <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-500">
                  {activity.description}
                </p>
                <div className="mt-5 grid gap-2 text-sm text-slate-500">
                  <span className="inline-flex items-center gap-2">
                    <CalendarDays size={16} /> {formatDateTime(activity.starts_at)}
                  </span>
                  <span className="inline-flex items-center gap-2">
                    <MapPin size={16} /> {activity.location}
                  </span>
                </div>
                <p className="mt-4 text-xs font-semibold text-slate-400">
                  {activity.participations.length} 个校内社团登记参与
                </p>
              </Link>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="暂无公开的联合活动" description="联合活动通过社联预审后会显示在这里。" />
      )}
    </motion.div>
  );
}
