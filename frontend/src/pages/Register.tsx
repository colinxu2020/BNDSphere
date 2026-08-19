import React, { useState } from "react";
import { motion } from "motion/react";
import { UserPlus } from "@/src/components/ui/Icons";
import { useNavigate } from "react-router-dom";
import { client } from "../api/client";
import { StatusMessage } from "../components/ui/AppPrimitives";

export function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("两次输入的密码不一致。");
      return;
    }

    setIsLoading(true);

    try {
      const { data, error: apiError } = await client.POST(
        "/api/v1/auth/register",
        {
          body: {
            username,
            password,
          },
        },
      );

      if (apiError) {
        setError(apiError);
        return;
      }

      if (data) {
        // Automatically login after register or redirect to login page
        navigate("/login");
      }
    } catch (err: any) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 flex flex-col items-center justify-center min-h-[70vh] px-4"
    >
      <div className="w-full max-w-md bg-surface p-8 rounded-md border border-edge-subtle shadow-sm relative overflow-hidden">
        <div className="flex flex-col gap-2 mb-8 text-center relative z-10">
          <div className="mx-auto bg-brand-subtle p-3 rounded-md text-tone-brand-fg mb-2">
            <UserPlus size={28} />
          </div>
          <h1 className="text-2xl font-display font-bold text-content">
            注册 BNDSphere
          </h1>
          <p className="text-content-muted text-sm">创建您的新账号</p>
        </div>

        {error && (
          <div className="mb-6 relative z-10">
            <StatusMessage value={error} />
          </div>
        )}

        <form
          onSubmit={handleRegister}
          className="flex flex-col gap-5 relative z-10"
        >
          <div>
            <label className="block text-sm font-medium text-content mb-1.5 ml-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-surface-sunken border border-edge rounded-md focus:ring-2 focus:ring-brand-strong/20 focus:border-brand outline-none transition-all font-medium text-content"
              placeholder="您的用户名"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1.5 ml-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-surface-sunken border border-edge rounded-md focus:ring-2 focus:ring-brand-strong/20 focus:border-brand outline-none transition-all font-medium text-content"
              placeholder="••••••••"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-content mb-1.5 ml-1">
              确认密码
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-3 bg-surface-sunken border border-edge rounded-md focus:ring-2 focus:ring-brand-strong/20 focus:border-brand outline-none transition-all font-medium text-content"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="mt-4 w-full py-3.5 bg-brand hover:bg-brand-hover text-brand-on font-semibold rounded-md transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed shadow-md shadow-brand/20"
          >
            {isLoading ? "正在注册..." : "注册"}
          </button>

          <div className="mt-4 text-center text-sm text-content-muted">
            已有账号？{" "}
            <span
              onClick={() => navigate("/login")}
              className="text-tone-brand-fg hover:text-tone-brand-fg font-medium cursor-pointer"
            >
              返回登录
            </span>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
