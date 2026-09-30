import React, { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { Lock } from "@/src/components/ui/Icons";
import { useNavigate } from "react-router-dom";
import { client } from "../api/client";
import { StatusMessage } from "../components/ui/AppPrimitives";
import {
  AltchaVerification,
  type AltchaVerificationRef,
} from "../components/ui/AltchaVerification";
import { readAltchaPayload } from "../lib/altcha";

const FIELD_CLASS =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 " +
  "focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all " +
  "font-medium text-slate-900";

const MIN_LENGTH = 6;

const CHANNELS = [
  { value: "email", label: "邮箱" },
  { value: "sms", label: "手机短信" },
] as const;

type Channel = (typeof CHANNELS)[number]["value"];

export function PasswordReset() {
  const navigate = useNavigate();
  const altchaRef = useRef<AltchaVerificationRef>(null);

  const [username, setUsername] = useState("");
  const [channel, setChannel] = useState<Channel>("email");
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");

  const [codeRequested, setCodeRequested] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<unknown>(null);
  const [tone, setTone] = useState<"error" | "success">("error");

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleRequest = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const altcha = readAltchaPayload(e.currentTarget);
    if (!altcha) {
      setTone("error");
      setMessage("请先完成人机验证。");
      return;
    }

    setBusy(true);
    setMessage(null);
    try {
      const { data, error } = await client.POST("/api/v1/auth/password/reset/request", {
        body: { username: username.trim(), channel, altcha },
      });
      altchaRef.current?.reset();
      if (error) {
        setTone("error");
        setMessage(error);
      } else {
        setCodeRequested(true);
        setCooldown(data?.resend_after ?? 60);
        setTone("success");
        // Deliberately not "we sent you a code": the server answers the same
        // way for an account that does not exist, and saying otherwise here
        // would put back the oracle it went out of its way to remove.
        setMessage(
          `如果这个账号绑定了已验证的${channel === "email" ? "邮箱" : "手机号"}，` +
            `验证码已经发出，请在 ${Math.round((data?.expires_in ?? 0) / 60)} 分钟内填写。`,
        );
      }
    } catch (err) {
      altchaRef.current?.reset();
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const { error } = await client.POST("/api/v1/auth/password/reset/confirm", {
        body: {
          username: username.trim(),
          channel,
          code: code.trim(),
          new_password: password,
        },
      });
      if (error) {
        setTone("error");
        setMessage(error);
      } else {
        navigate("/login", { replace: true });
      }
    } catch (err) {
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  const ready = password.length >= MIN_LENGTH && password === repeat && code.length === 6;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col items-center justify-center min-h-[70vh] px-4"
    >
      <div className="w-full max-w-md bg-white p-8 rounded-md border border-slate-100 shadow-sm">
        <div className="flex flex-col gap-2 mb-8 text-center">
          <div className="mx-auto bg-primary-50 p-3 rounded-md text-primary-600 mb-2">
            <Lock size={28} />
          </div>
          <h1 className="text-2xl font-display font-bold text-slate-900">重置密码</h1>
          <p className="text-slate-500 text-sm">
            通过账号绑定并验证过的邮箱或手机号接收验证码。没有绑定过的账号无法用这种方式找回。
          </p>
        </div>

        {message != null && (
          <div className="mb-6">
            <StatusMessage value={message} tone={tone} />
          </div>
        )}

        <form onSubmit={handleRequest} className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className={FIELD_CLASS}
              placeholder="您的用户名"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">接收方式</label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value as Channel)}
              className={FIELD_CLASS}
            >
              {CHANNELS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <AltchaVerification ref={altchaRef} purpose="password_reset" />

          <button
            type="submit"
            disabled={busy || cooldown > 0 || !username.trim()}
            className="w-full py-3.5 bg-slate-900 text-white font-semibold rounded-md hover:bg-slate-800 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {cooldown > 0 ? `${cooldown} 秒后可重发` : codeRequested ? "重新发送" : "发送验证码"}
          </button>
        </form>

        {codeRequested && (
          <form
            onSubmit={handleConfirm}
            className="flex flex-col gap-4 mt-6 pt-6 border-t border-slate-100"
          >
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={code}
              placeholder="6 位验证码"
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className={FIELD_CLASS}
            />
            <input
              type="password"
              autoComplete="new-password"
              value={password}
              placeholder={`新密码（至少 ${MIN_LENGTH} 位）`}
              onChange={(e) => setPassword(e.target.value)}
              className={FIELD_CLASS}
            />
            <input
              type="password"
              autoComplete="new-password"
              value={repeat}
              placeholder="再次输入新密码"
              onChange={(e) => setRepeat(e.target.value)}
              className={FIELD_CLASS}
            />
            {repeat.length > 0 && password !== repeat && (
              <p className="ml-1 text-xs text-red-600">两次输入的新密码不一致。</p>
            )}
            <button
              type="submit"
              disabled={busy || !ready}
              className="w-full py-3.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-md transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
            >
              {busy ? "正在重置..." : "设置新密码"}
            </button>
            <p className="text-xs text-slate-500 text-center">
              重置成功后所有设备都会退出登录，请用新密码重新登录。
            </p>
          </form>
        )}

        <div className="mt-6 text-center text-sm text-slate-500">
          想起来了？{" "}
          <span
            onClick={() => navigate("/login")}
            className="text-primary-600 hover:text-primary-700 font-medium cursor-pointer"
          >
            返回登录
          </span>
        </div>
      </div>
    </motion.div>
  );
}
