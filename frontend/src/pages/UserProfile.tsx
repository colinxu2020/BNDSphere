import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { ArrowLeft, User } from "@/src/components/ui/Icons";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { formatDate } from "../lib/format";
import { EmptyState, PageHeader, StatusMessage, Surface } from "../components/ui/AppPrimitives";

type PublicUserInfo = components["schemas"]["PublicUserInfo"];

export function UserProfile() {
  const { id } = useParams<{ id: string }>();
  const [user, setUser] = useState<PublicUserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const fetchUser = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET("/api/v1/users/{user_id}", {
          params: { path: { user_id: Number(id) } },
        });
        if (error) {
          setError(error);
          setUser(null);
        } else {
          setUser(data || null);
        }
      } catch (requestError) {
        setError(requestError);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUser();
  }, [id]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20 max-w-3xl mx-auto w-full"
    >
      <Link
        to="/explore"
        className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 font-medium w-fit transition-colors"
      >
        <ArrowLeft size={18} /> 返回探索
      </Link>

      <PageHeader title="用户档案" />

      {isLoading ? (
        <div className="animate-pulse bg-white rounded-md h-72 border border-slate-100" />
      ) : error ? (
        <StatusMessage value={error} />
      ) : user ? (
        <Surface className="overflow-hidden p-0">
          <div className="h-28 bg-slate-100 w-full" />
          <div className="px-8 pb-8">
            <div className="w-24 h-24 rounded-md bg-white p-1.5 shadow-md -mt-12 mb-6">
              {user.avatar_uri ? (
                <img
                  src={user.avatar_uri}
                  alt={user.username}
                  className="w-full h-full object-cover rounded-md"
                />
              ) : (
                <div className="w-full h-full bg-slate-100 rounded-md flex items-center justify-center">
                  <User size={32} className="text-slate-400" />
                </div>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <h2 className="text-2xl font-bold text-slate-900">{user.username}</h2>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-xs text-slate-400 font-medium">
                  加入于 {formatDate(user.created_at)}
                </span>
              </div>
            </div>

            <div className="mt-8 p-5 bg-slate-50 rounded-md border border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 mb-2 font-display">个人简介</h3>
              <p className="text-slate-600 leading-relaxed">
                {user.description || "暂无个人简介。"}
              </p>
            </div>
          </div>
        </Surface>
      ) : (
        <EmptyState title="未找到用户" />
      )}
    </motion.div>
  );
}
