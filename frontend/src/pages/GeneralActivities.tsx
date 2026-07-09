import { useEffect, useState } from "react";
import { motion } from "motion/react";
import {
  ArrowUpRight,
  CalendarDays,
  Filter,
  Search,
} from "@/src/components/ui/Icons";
import { Link } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { ACTIVITY_LEVEL_MAP, ACTIVITY_LEVEL_OPTIONS } from "../lib/labels";
import { formatDate } from "../lib/format";
import {
  Badge,
  EmptyState,
  PageHeader,
  StatusMessage,
  inputClassName,
} from "../components/ui/AppPrimitives";
import { cn } from "../lib/utils";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ActivityLevel = components["schemas"]["GeneralActivityLevelEnum"];

const LEVEL_FILTERS: { label: string; value: ActivityLevel | "all" }[] = [
  { label: "全部", value: "all" },
  ...ACTIVITY_LEVEL_OPTIONS,
];

export function GeneralActivities() {
  const [items, setItems] = useState<GeneralActivity[]>([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [level, setLevel] = useState<ActivityLevel | "all">("all");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const fetchActivities = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET(
          "/api/v1/general-activities/",
          {
            params: {
              query: {
                size: 50,
                search: search || undefined,
                level: level !== "all" ? level : undefined,
              },
            },
          },
        );
        if (error) {
          setError(error);
          setItems([]);
          setTotal(0);
        } else {
          setItems(data?.items || []);
          setTotal(data?.total || 0);
        }
      } catch (requestError) {
        setError(requestError);
        setItems([]);
        setTotal(0);
      } finally {
        setIsLoading(false);
      }
    };

    fetchActivities();
  }, [search, level]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <PageHeader
        eyebrow="Activities"
        title="综评活动"
      />

      <div className="flex flex-col gap-4">
        <div className="relative w-full">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-slate-400" />
          </div>
          <input
            className={cn(inputClassName, "pl-11")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="搜索活动名称或描述..."
          />
        </div>

        <div className="w-full overflow-x-auto hide-scrollbar">
          <div className="flex gap-2 min-w-max pb-2">
            {LEVEL_FILTERS.map((option) => (
              <button
                key={option.value}
                onClick={() => setLevel(option.value)}
                className={cn(
                  "px-4 py-2 rounded-md text-sm font-semibold transition-all shadow-sm whitespace-nowrap",
                  level === option.value
                    ? "bg-slate-900 text-white shadow-slate-900/10"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50",
                )}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <StatusMessage value={error} />}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {[...Array(4)].map((_, index) => (
            <div
              key={index}
              className="animate-pulse bg-white h-40 rounded-md border border-slate-100"
            />
          ))}
        </div>
      ) : items.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {items.map((activityItem, index) => (
            <motion.div
              key={activityItem.id}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.04, duration: 0.25 }}
            >
              <Link
                to={`/activities/${activityItem.id}`}
                className="group block h-full bg-white p-6 rounded-md border border-slate-200/60 shadow-sm hover:shadow-sm hover:border-primary-100 transition-all duration-300"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="w-12 h-12 rounded-md bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">
                    <CalendarDays size={22} />
                  </div>
                  <ArrowUpRight
                    size={18}
                    className="text-slate-300 group-hover:text-primary-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all"
                  />
                </div>
                <div className="mt-5">
                  <Badge tone="primary">
                    {ACTIVITY_LEVEL_MAP[activityItem.level]}
                  </Badge>
                  <h3 className="mt-3 text-lg font-semibold text-slate-900 group-hover:text-primary-600 transition-colors">
                    {activityItem.name}
                  </h3>
                  <p className="text-sm text-slate-500 line-clamp-2 mt-2">
                    {activityItem.description}
                  </p>
                  <div className="flex items-center gap-3 mt-5 text-xs font-medium text-slate-400">
                    <span>{formatDate(activityItem.created_at)}</span>
                    <span>
                      {activityItem.club_records?.length || 0} 条社团记录
                    </span>
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={<Filter size={24} />}
          title="暂无活动"
          description={
            total ? "当前筛选条件下没有活动。" : "后端尚未返回活动数据。"
          }
        />
      )}
    </motion.div>
  );
}

