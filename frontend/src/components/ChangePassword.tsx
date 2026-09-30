import React, { useState } from "react";
import { Lock } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import { StatusMessage } from "./ui/AppPrimitives";

const FIELD_CLASS =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 " +
  "focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all " +
  "font-medium text-slate-900 disabled:opacity-60";

// Mirrors USER_MIN_PASSWORD_LENGTH; the server is what enforces it, this only
// keeps the form from posting something it already knows will come back 422.
const MIN_LENGTH = 6;

export function ChangePassword() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<unknown>(null);
  const [tone, setTone] = useState<"error" | "success">("error");

  const mismatch = repeat.length > 0 && next !== repeat;
  const ready = current.length > 0 && next.length >= MIN_LENGTH && next === repeat;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);

    try {
      const { error } = await client.POST("/api/v1/auth/password/change", {
        body: { current_password: current, new_password: next },
      });
      if (error) {
        setTone("error");
        setMessage(error);
      } else {
        setCurrent("");
        setNext("");
        setRepeat("");
        setTone("success");
        setMessage("密码已更新。其他设备上的登录已全部退出，本设备无需重新登录。");
      }
    } catch (err) {
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-white rounded-md border border-slate-100 shadow-sm p-8">
      <div className="flex items-center gap-2 mb-1">
        <Lock size={16} className="text-slate-400" />
        <h3 className="text-sm font-bold text-slate-800 font-display">修改密码</h3>
      </div>
      <p className="text-xs text-slate-500 mb-5">
        修改后，其他设备上的登录会全部退出，本设备会保持登录状态。
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <input
          type="password"
          autoComplete="current-password"
          value={current}
          placeholder="当前密码"
          onChange={(e) => setCurrent(e.target.value)}
          className={FIELD_CLASS}
        />
        <input
          type="password"
          autoComplete="new-password"
          value={next}
          placeholder={`新密码（至少 ${MIN_LENGTH} 位）`}
          onChange={(e) => setNext(e.target.value)}
          className={FIELD_CLASS}
        />
        <div>
          <input
            type="password"
            autoComplete="new-password"
            value={repeat}
            placeholder="再次输入新密码"
            onChange={(e) => setRepeat(e.target.value)}
            className={FIELD_CLASS}
          />
          {mismatch && <p className="mt-1.5 ml-1 text-xs text-red-600">两次输入的新密码不一致。</p>}
        </div>

        <button
          type="submit"
          disabled={busy || !ready}
          className="mt-1 w-full py-3.5 bg-slate-900 text-white font-semibold rounded-md hover:bg-slate-800 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
        >
          {busy ? "正在修改..." : "修改密码"}
        </button>

        {message != null && <StatusMessage value={message} tone={tone} />}
      </form>
    </div>
  );
}
