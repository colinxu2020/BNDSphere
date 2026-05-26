import React, { useState } from "react";
import { motion } from "motion/react";
import { LogIn } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { client } from "../api/client";
import { StatusMessage } from "../components/ui/AppPrimitives";

export function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const { data, error, response } = await client.POST(
        "/api/v1/auth/login",
        {
          body: {
            username: username,
            password: password,
            grant_type: "password",
          } as any,
          bodySerializer(body) {
            const params = new URLSearchParams();
            for (const [key, value] of Object.entries(
              body as Record<string, string>,
            )) {
              params.append(key, value);
            }
            return params.toString();
          },
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        },
      );

      if (error) {
        setError(error);
        return;
      }

      if (data?.access_token) {
        localStorage.setItem("bnd_token", data.access_token);
        navigate("/profile");
      } else {
        throw new Error("未获取到授权令牌。");
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
      className="flex flex-col items-center justify-center min-h-[70vh] px-4"
    >
      <div className="w-full max-w-md bg-white p-8 rounded-[2rem] border border-slate-100 shadow-[0_8px_30px_-4px_rgba(0,0,0,0.06)] relative overflow-hidden">
        <div className="flex flex-col gap-2 mb-8 text-center relative z-10">
          <div className="mx-auto bg-primary-50 p-3 rounded-2xl text-primary-600 mb-2">
            <LogIn size={28} />
          </div>
          <h1 className="text-2xl font-display font-bold text-slate-900">
            登录 BNDSphere
          </h1>
          <p className="text-slate-500 text-sm">请输入您的账号密码</p>
        </div>

        {error && (
          <div className="mb-6 relative z-10">
            <StatusMessage value={error} />
          </div>
        )}

        <form
          onSubmit={handleLogin}
          className="flex flex-col gap-5 relative z-10"
        >
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900"
              placeholder="您的用户名"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="mt-4 w-full py-3.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed shadow-md shadow-primary-500/20"
          >
            {isLoading ? "正在登录..." : "登录"}
          </button>

          <div className="mt-4 text-center text-sm text-slate-500">
            没有账号？{" "}
            <span
              onClick={() => navigate("/register")}
              className="text-primary-600 hover:text-primary-700 font-medium cursor-pointer"
            >
              立即注册
            </span>
          </div>
        </form>
      </div>
    </motion.div>
  );
}
