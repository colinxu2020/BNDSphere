import { useState, useEffect } from "react";
import { motion } from "motion/react";
import {
  Plus,
  Search,
  Filter,
} from "@/src/components/ui/Icons";
import { client } from "../api/client";
import { Link } from "react-router-dom";
import { cn } from "../lib/utils";
import type { components } from "../api/schema";
import { StatusMessage } from "../components/ui/AppPrimitives";
import { ClubCard } from "../components/ui/ClubCard";

type ClubInfo = components["schemas"]["ClubInfo"];
type Category = components["schemas"]["ClubCategoryEnum"];

const CATEGORIES: { label: string; value: Category | "all" }[] = [
  { label: "全部", value: "all" },
  { label: "科学", value: "science" },
  { label: "人文", value: "humanity" },
  { label: "艺术", value: "arts" },
  { label: "体育", value: "sports" },
  { label: "商务", value: "business" },
  { label: "公益", value: "charity" },
  { label: "校园", value: "campus" },
  { label: "其他", value: "other" },
];

export function ExploreClubs() {
  const [clubs, setClubs] = useState<ClubInfo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<Category | "all">("all");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const fetchClubs = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET("/api/v1/clubs/", {
          params: {
            query: {
              size: 50,
              search: search || undefined,
              category: activeCategory !== "all" ? activeCategory : undefined,
            },
          },
        });

        if (error) {
          setError(error);
          setClubs([]);
        } else if (data?.items) {
          setClubs(data.items);
        } else {
          setClubs([]);
        }
      } catch (e) {
        setError(e);
        setClubs([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchClubs();
  }, [search, activeCategory]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col h-full gap-8"
    >
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mt-4">
        <div>
          <h1 className="text-4xl font-display font-bold text-content">
            探索社团
          </h1>
        </div>
        <Link
          to="/clubs/new"
          className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-brand hover:bg-brand-hover text-content-on-inverted rounded-md font-semibold shadow-md shadow-brand/20 transition-all active:scale-[0.98]"
        >
          <Plus size={18} /> 创建社团
        </Link>
      </div>

      {/* 搜索和标签布局：垂直排列 */}
      <div className="flex flex-col gap-4">
        {/* Search */}
        <div className="relative w-full">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-content-subtle" />
          </div>
          <input
            type="text"
            className="block w-full pl-11 pr-4 py-3 bg-surface border border-edge rounded-md shadow-sm focus:ring-2 focus:ring-brand/20 focus:border-brand transition-all font-medium text-content placeholder:text-content-subtle focus:outline-none"
            placeholder="通过社团名称或关键字搜索..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Categories */}
        <div className="w-full overflow-x-auto hide-scrollbar">
          <div className="flex gap-2 min-w-max pb-2">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setActiveCategory(cat.value)}
                className={cn(
                  "px-4 py-2 rounded-md text-sm font-semibold transition-all shadow-sm whitespace-nowrap",
                  activeCategory === cat.value
                    ? "bg-surface-inverted text-content-on-inverted shadow-black/10"
                    : "bg-surface text-content-muted border border-edge hover:bg-surface-sunken",
                )}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && <StatusMessage value={error} />}

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="animate-pulse bg-surface/50 h-32 rounded-md border border-edge-subtle flex items-center p-6 gap-4"
            >
              <div className="w-16 h-16 bg-surface-skeleton rounded-md shrink-0"></div>
              <div className="flex flex-col gap-2 w-full">
                <div className="h-4 bg-surface-skeleton rounded-md w-1/3"></div>
                <div className="h-5 bg-surface-skeleton rounded-md w-3/4"></div>
                <div className="h-3 bg-surface-skeleton rounded-md w-full mt-2"></div>
              </div>
            </div>
          ))}
        </div>
      ) : clubs.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {clubs.map((club, idx) => (
            <motion.div
              key={club.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: idx * 0.05, duration: 0.3 }}
            >
              <ClubCard club={club} />
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-surface border border-edge-subtle border-dashed rounded-md">
          <div className="bg-surface-sunken w-16 h-16 rounded-md flex items-center justify-center mb-4">
            <Filter className="text-content-subtle" size={24} />
          </div>
          <h3 className="text-xl font-display font-semibold text-content mb-2">
            未找到社团
          </h3>
          <p className="text-content-muted max-w-sm">
            我们找不到与当前条件匹配的社团。请尝试调整搜索关键字或社团类别。
          </p>
          <button
            onClick={() => {
              setSearch("");
              setActiveCategory("all");
            }}
            className="mt-6 px-6 py-2.5 bg-surface-inverted text-content-on-inverted rounded-md font-medium shadow-sm hover:bg-surface-inverted-hover transition-all active:scale-95"
          >
            清除筛选条件
          </button>
        </div>
      )}
    </motion.div>
  );
}
