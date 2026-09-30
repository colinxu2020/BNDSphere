import { useEffect, useState, type FormEvent } from "react";
import { ShieldCheck } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { TwoFactorChallenge, TwoFactorMethod as Method } from "../lib/twoFactor";
import { StatusMessage } from "./ui/AppPrimitives";

const METHOD_LABELS: Record<Method, string> = {
  totp: "认证器应用",
  sms: "短信验证码",
  recovery: "恢复码",
};

const METHOD_HINTS: Record<Method, string> = {
  totp: "打开认证器应用，输入当前显示的 6 位验证码。",
  sms: "点击下方按钮，我们会向你绑定的手机号发送一条 6 位验证码。",
  recovery: "输入开启两步验证时保存的任意一个恢复码，每个只能使用一次。",
};

const FIELD_CLASS =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 " +
  "focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all " +
  "font-medium text-slate-900 disabled:opacity-60";

export function TwoFactorPrompt({
  challenge,
  onAuthenticated,
  onCancel,
}: {
  challenge: TwoFactorChallenge;
  onAuthenticated: () => void;
  onCancel: () => void;
}) {
  const [method, setMethod] = useState<Method>(challenge.methods[0]);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [message, setMessage] = useState<unknown>(null);
  const [tone, setTone] = useState<"error" | "success">("error");

  // Mirrors the resend interval the server enforces; this only keeps the
  // button from inviting a request it already knows will come back 429.
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const numeric = method !== "recovery";
  const ready = numeric ? code.length === 6 : code.trim().length > 0;

  const handleSend = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const { data, error } = await client.POST("/api/v1/auth/login/2fa/send", {
        body: { two_factor_token: challenge.token },
      });
      if (error) {
        setTone("error");
        setMessage(error);
      } else {
        setCooldown(data?.resend_after ?? 60);
        setTone("success");
        setMessage(`验证码已发送，请在 ${Math.round((data?.expires_in ?? 0) / 60)} 分钟内填写。`);
      }
    } catch (err) {
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const { data, error } = await client.POST("/api/v1/auth/login/2fa", {
        body: { two_factor_token: challenge.token, method, code: code.trim() },
      });
      if (error) {
        setTone("error");
        setMessage(error);
      } else if (data?.access_token) {
        onAuthenticated();
      } else {
        throw new Error("未获取到授权令牌。");
      }
    } catch (err) {
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2 text-center">
        <div className="mx-auto bg-primary-50 p-3 rounded-md text-primary-600 mb-2">
          <ShieldCheck size={28} />
        </div>
        <h1 className="text-2xl font-display font-bold text-slate-900">两步验证</h1>
        <p className="text-slate-500 text-sm">密码已通过，请再完成一次验证。</p>
      </div>

      {challenge.methods.length > 1 && (
        <div className="flex gap-2">
          {challenge.methods.map((candidate) => (
            <button
              key={candidate}
              type="button"
              onClick={() => {
                setMethod(candidate);
                setCode("");
                setMessage(null);
              }}
              className={
                candidate === method
                  ? "flex-1 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
                  : "flex-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50"
              }
            >
              {METHOD_LABELS[candidate]}
            </button>
          ))}
        </div>
      )}

      <p className="text-xs text-slate-500">{METHOD_HINTS[method]}</p>

      {method === "sms" && (
        <button
          type="button"
          onClick={handleSend}
          disabled={busy || cooldown > 0}
          className="w-full py-3 bg-slate-900 text-white text-sm font-semibold rounded-md hover:bg-slate-800 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
        >
          {cooldown > 0 ? `${cooldown} 秒后重发` : "发送短信验证码"}
        </button>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <input
          type="text"
          autoFocus
          autoComplete="one-time-code"
          inputMode={numeric ? "numeric" : "text"}
          maxLength={numeric ? 6 : 32}
          value={code}
          placeholder={numeric ? "6 位验证码" : "xxxx-xxxx-xxxx-xxxx"}
          onChange={(e) => setCode(numeric ? e.target.value.replace(/\D/g, "") : e.target.value)}
          className={FIELD_CLASS}
        />
        <button
          type="submit"
          disabled={busy || !ready}
          className="w-full py-3.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-md transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-primary-500/20"
        >
          {busy ? "正在验证..." : "完成登录"}
        </button>
      </form>

      {message != null && <StatusMessage value={message} tone={tone} />}

      <button
        type="button"
        onClick={onCancel}
        className="text-center text-sm text-slate-500 hover:text-slate-700"
      >
        返回重新登录
      </button>
    </div>
  );
}
