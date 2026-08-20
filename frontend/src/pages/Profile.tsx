import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { User, LogOut, Edit3, X } from "@/src/components/ui/Icons";
import { useNavigate } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { ROLE_MAP } from "../lib/labels";
import { StatusMessage } from "../components/ui/AppPrimitives";
import { FileUploadField } from "../components/ui/FileUploadField";

type UserInfo = components["schemas"]["UserInfo"];

export function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Update Profile Request State
  const [isUpdateModalOpen, setIsUpdateModalOpen] = useState(false);
  const [updateUsername, setUpdateUsername] = useState("");
  const [updateDescription, setUpdateDescription] = useState("");
  const [updateAvatar, setUpdateAvatar] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [updateMessage, setUpdateMessage] = useState<unknown>(null);
  const [updateTone, setUpdateTone] = useState<"error" | "success">("error");
  const [loadError, setLoadError] = useState<unknown>(null);

  useEffect(() => {
    const fetchUser = async () => {
      setIsLoading(true);
      const token = localStorage.getItem("bnd_token");
      if (!token) {
        navigate("/login");
        return;
      }

      try {
        const { data, error, response } = await client.GET("/api/v1/users/me");
        if (response.status === 401) {
          navigate("/login");
        } else if (error) {
          setLoadError(error);
        } else if (data) {
          setUser(data);
          setUpdateUsername(data.username || "");
          setUpdateDescription(data.description || "");
          setUpdateAvatar(data.avatar_uri || "");
        }
      } catch (e) {
        setLoadError(e);
      } finally {
        setIsLoading(false);
      }
    };
    fetchUser();
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem("bnd_token");
    navigate("/login");
  };

  const submitUpdateRequest = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setUpdateMessage(null);

    try {
      const { data, error } = await client.POST("/api/v1/users/update-requests", {
        body: {
          username: updateUsername !== user?.username ? updateUsername : null,
          description: updateDescription !== user?.description ? updateDescription : null,
          avatar_uri: updateAvatar !== user?.avatar_uri ? updateAvatar : null,
        },
      });

      if (error) {
        setUpdateTone("error");
        setUpdateMessage(error);
      } else {
        setUpdateTone("success");
        setUpdateMessage(data);
        setTimeout(() => {
          setIsUpdateModalOpen(false);
          setUpdateMessage(null);
        }, 2000);
      }
    } catch (err: any) {
      setUpdateTone("error");
      setUpdateMessage(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="w-8 h-8 rounded-full border-4 border-slate-200 border-t-primary-500 animate-spin"></div>
      </div>
    );
  }

  if (loadError) return <StatusMessage value={loadError} />;

  if (!user) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20 max-w-3xl mx-auto w-full mt-4"
    >
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-display font-bold text-slate-900">我的主页</h1>
        <button
          onClick={handleLogout}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 rounded-md hover:bg-red-100 transition-colors"
        >
          <LogOut size={16} /> 退出登录
        </button>
      </div>

      <div className="bg-white rounded-md border border-slate-100 shadow-sm overflow-hidden">
        <div className="h-32 bg-slate-100 w-full relative"></div>

        <div className="px-8 pb-8 relative">
          <div className="flex justify-between items-end -mt-12 mb-6">
            <div className="w-24 h-24 rounded-md bg-white p-1.5 shadow-md relative">
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

            <button
              onClick={() => setIsUpdateModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 bg-slate-900 text-white text-sm font-semibold rounded-md hover:bg-slate-800 transition-all active:scale-95"
            >
              <Edit3 size={16} /> 修改资料
            </button>
          </div>

          <div className="flex flex-col gap-1">
            <h2 className="text-2xl font-bold text-slate-900">{user.username}</h2>
            {user.email && <p className="text-slate-500 font-medium">{user.email}</p>}

            <div className="flex items-center gap-2 mt-3">
              <span className="px-2.5 py-1 bg-primary-50 text-primary-700 text-xs font-bold uppercase tracking-wider rounded-lg border border-primary-100">
                {ROLE_MAP[user.role] || user.role}
              </span>
              <span className="text-xs text-slate-400 font-medium">
                加入于 {new Date(user.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          {user.description && (
            <div className="mt-8 p-5 bg-slate-50 rounded-md border border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 mb-2 font-display">个人简介</h3>
              <p className="text-slate-600 leading-relaxed">{user.description}</p>
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {isUpdateModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center px-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/40 "
              onClick={() => setIsUpdateModalOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="relative bg-white w-full max-w-md p-8 rounded-md shadow-md z-10"
            >
              <button
                onClick={() => setIsUpdateModalOpen(false)}
                className="absolute top-6 right-6 text-slate-400 hover:text-slate-600 bg-slate-50 hover:bg-slate-100 p-2 rounded-md transition-colors"
              >
                <X size={20} />
              </button>

              <h2 className="text-2xl font-display font-bold text-slate-900 mb-2">修改资料</h2>
              <p className="text-sm text-slate-500 mb-6">
                修改资料将被提交至管理员审核，审核通过后生效。
              </p>

              {updateMessage && (
                <div className="mb-6">
                  <StatusMessage value={updateMessage} tone={updateTone} />
                </div>
              )}

              <form onSubmit={submitUpdateRequest} className="flex flex-col gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">
                    用户名
                  </label>
                  <input
                    type="text"
                    value={updateUsername}
                    onChange={(e) => setUpdateUsername(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900"
                  />
                </div>
                <FileUploadField
                  label="头像图片"
                  scene="avatar"
                  value={updateAvatar}
                  onChange={setUpdateAvatar}
                  accept="image/*"
                  hint="上传后会自动使用新的头像访问地址。"
                />
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">
                    个人简介
                  </label>
                  <textarea
                    value={updateDescription}
                    onChange={(e) => setUpdateDescription(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900 min-h-[100px] resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="mt-4 w-full py-3.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-md transition-all shadow-md active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? "正在提交..." : "提交审核请求"}
                </button>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
