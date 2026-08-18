import { useState, useEffect } from "react";
import { motion } from "motion/react";
import {
  Plus,
  Search,
  Filter,
  Hash,
  Sparkles,
} from "@/src/components/ui/Icons";
import { client } from "../api/client";
import { Link } from "react-router-dom";
import { cn } from "../lib/utils";
import type { components } from "../api/schema";
import { CATEGORY_MAP } from "../lib/labels";
import { StatusMessage } from "../components/ui/AppPrimitives";

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
      className="flex flex-col h-full gap-8 pb-20"
    >
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mt-4">
        <div>
          <h1 className="text-4xl font-display font-bold text-slate-900 tracking-tight">
            探索社团
          </h1>
        </div>
        <Link
          to="/clubs/new"
          className="inline-flex items-center justify-center gap-2 px-5 py-3 bg-primary-500 hover:bg-primary-600 text-white rounded-md font-semibold shadow-md shadow-primary-500/20 transition-all active:scale-[0.98]"
        >
          <Plus size={18} /> 创建社团
        </Link>
      </div>

      {/* 搜索和标签布局：垂直排列 */}
      <div className="flex flex-col gap-4">
        {/* Search */}
        <div className="relative w-full">
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
            <Search className="h-5 w-5 text-slate-400" />
          </div>
          <input
            type="text"
            className="block w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-md shadow-sm focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all font-medium text-slate-900 placeholder:text-slate-400 focus:outline-none"
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
                    ? "bg-slate-900 text-white shadow-slate-900/10"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50",
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
              className="animate-pulse bg-white/50 h-32 rounded-md border border-slate-100 flex items-center p-6 gap-4"
            >
              <div className="w-16 h-16 bg-slate-200 rounded-md shrink-0"></div>
              <div className="flex flex-col gap-2 w-full">
                <div className="h-4 bg-slate-200 rounded-md w-1/3"></div>
                <div className="h-5 bg-slate-200 rounded-md w-3/4"></div>
                <div className="h-3 bg-slate-200 rounded-md w-full mt-2"></div>
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
              <Link
                to={`/club/${club.id}`}
                className="group flex items-start gap-4 p-5 bg-white rounded-md border border-slate-200/60 shadow-sm hover:shadow-sm hover:border-primary-100 transition-all duration-300 h-full"
              >
                <div className="w-16 h-16 rounded-md bg-slate-100 flex items-center justify-center shrink-0 shadow-inner group-hover:scale-105 transition-transform overflow-hidden">
                  {club.logo_uri ? (
                    <img
                      src={club.logo_uri}
                      alt={club.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <Hash className="text-slate-400 stroke-[1.5]" size={28} />
                  )}
                </div>
                <div className="flex flex-col">
                  <div className="flex gap-2 items-center mb-1">
                    <span className="text-[10px] font-bold tracking-wider uppercase text-primary-600 bg-primary-50 px-2.5 py-0.5 rounded-md">
                      {CATEGORY_MAP[club.category] || club.category}
                    </span>
                    {club.star_level !== "none" && (
                      <span className="flex text-yellow-400 bg-yellow-50 p-0.5 rounded-md">
                        <Sparkles size={12} className="fill-yellow-400" />
                      </span>
                    )}
                  </div>
                  <h3 className="font-semibold text-[17px] text-slate-900 leading-tight group-hover:text-primary-600 transition-colors">
                    {club.name}
                  </h3>
                  <p className="text-slate-500 text-sm mt-1.5 line-clamp-2">
                    {club.summary}
                  </p>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-white border border-slate-100 border-dashed rounded-md">
          <div className="bg-slate-50 w-16 h-16 rounded-md flex items-center justify-center mb-4">
            <Filter className="text-slate-400" size={24} />
          </div>
          <h3 className="text-xl font-display font-semibold text-slate-800 mb-2">
            未找到社团
          </h3>
          <p className="text-slate-500 max-w-sm">
            我们找不到与当前条件匹配的社团。请尝试调整搜索关键字或社团类别。
          </p>
          <button
            onClick={() => {
              setSearch("");
              setActiveCategory("all");
            }}
            className="mt-6 px-6 py-2.5 bg-slate-900 text-white rounded-md font-medium shadow-sm hover:bg-slate-800 transition-all active:scale-95"
          >
            清除筛选条件
          </button>
        </div>
      )}
    </motion.div>
  );
}
