import { useCallback, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Check, ShieldCheck } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { StatusMessage } from "./ui/AppPrimitives";

type Status = components["schemas"]["TwoFactorStatus"];
type Enrollment = components["schemas"]["TotpEnrollment"];

const FIELD_CLASS =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 " +
  "focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all " +
  "font-medium text-slate-900 disabled:opacity-60";

const DARK_BUTTON =
  "shrink-0 px-4 py-2.5 bg-slate-900 text-white text-sm font-semibold rounded-md " +
  "hover:bg-slate-800 transition-all active:scale-95 disabled:opacity-50 " +
  "disabled:cursor-not-allowed disabled:active:scale-100";

const LIGHT_BUTTON =
  "shrink-0 px-4 py-2.5 border border-slate-200 bg-white text-slate-600 text-sm " +
  "font-semibold rounded-md hover:bg-slate-50 transition-all active:scale-95 " +
  "disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100";

/** The actions that re-ask for the password before they will run. */
const ACTIONS = {
  "totp-start": { path: "/api/v1/auth/2fa/totp/start", prompt: "输入当前密码以开始绑定认证器" },
  "totp-disable": { path: "/api/v1/auth/2fa/totp/disable", prompt: "输入当前密码以关闭认证器验证" },
  "sms-enable": { path: "/api/v1/auth/2fa/sms/enable", prompt: "输入当前密码以开启短信验证" },
  "sms-disable": { path: "/api/v1/auth/2fa/sms/disable", prompt: "输入当前密码以关闭短信验证" },
  recovery: { path: "/api/v1/auth/2fa/recovery-codes", prompt: "输入当前密码以重新生成恢复码" },
} as const;

type Action = keyof typeof ACTIONS;

function Badge({ on }: { on: boolean }) {
  return on ? (
    <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-md border border-emerald-100">
      <Check size={12} /> 已开启
    </span>
  ) : (
    <span className="px-2 py-0.5 bg-slate-100 text-slate-500 text-xs font-bold rounded-md border border-slate-200">
      未开启
    </span>
  );
}

/** The codes, shown once. The server keeps only hashes and cannot repeat them. */
function RecoveryCodePanel({ codes, onDismiss }: { codes: string[]; onDismiss: () => void }) {
  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
      <p className="text-xs font-bold text-amber-800">请立即保存这些恢复码，它们只会显示这一次。</p>
      <p className="mt-1 text-xs text-amber-700">
        手机丢失时，每个恢复码可以代替验证码登录一次。重新生成会让旧的全部失效。
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2 font-mono text-sm text-slate-800">
        {codes.map((code) => (
          <span key={code} className="rounded bg-white px-2 py-1 text-center">
            {code}
          </span>
        ))}
      </div>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => void navigator.clipboard?.writeText(codes.join("\n"))}
          className={LIGHT_BUTTON}
        >
          复制全部
        </button>
        <button type="button" onClick={onDismiss} className={DARK_BUTTON}>
          我已保存
        </button>
      </div>
    </div>
  );
}

export function TwoFactorSettings() {
  const [status, setStatus] = useState<Status | null>(null);
  const [action, setAction] = useState<Action | null>(null);
  const [password, setPassword] = useState("");
  const [enrollment, setEnrollment] = useState<Enrollment | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<unknown>(null);
  const [tone, setTone] = useState<"error" | "success">("error");

  const refresh = useCallback(async () => {
    const { data } = await client.GET("/api/v1/auth/2fa");
    if (data) setStatus(data);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const reset = () => {
    setAction(null);
    setPassword("");
  };

  const runAction = async () => {
    if (!action) return;
    setBusy(true);
    setMessage(null);
    try {
      const { data, error } = await client.POST(ACTIONS[action].path, {
        body: { password },
      });
      if (error) {
        setTone("error");
        setMessage(error);
        return;
      }
      reset();
      if (action === "totp-start") {
        setEnrollment(data as Enrollment);
      } else {
        // Everything else either returns a fresh set of codes or nothing
        // at all (the disable routes answer 204).
        const fresh = (data as components["schemas"]["RecoveryCodes"] | undefined)?.recovery_codes;
        if (fresh) setCodes(fresh);
        setTone("success");
        setMessage(
          action === "recovery" ? "恢复码已重新生成，旧的恢复码已全部失效。" : "设置已更新。",
        );
        await refresh();
      }
    } catch (err) {
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  const confirmTotp = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const { data, error } = await client.POST("/api/v1/auth/2fa/totp/confirm", {
        body: { code: totpCode },
      });
      if (error) {
        setTone("error");
        setMessage(error);
      } else if (data) {
        setEnrollment(null);
        setTotpCode("");
        setCodes(data.recovery_codes);
        setTone("success");
        setMessage("认证器已绑定，下次登录时会要求输入验证码。");
        await refresh();
      }
    } catch (err) {
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  if (!status) return null;

  return (
    <div className="bg-white rounded-md border border-slate-100 shadow-sm p-8">
      <div className="flex items-center gap-2 mb-1">
        <ShieldCheck size={16} className="text-slate-400" />
        <h3 className="text-sm font-bold text-slate-800 font-display">两步验证</h3>
      </div>
      <p className="text-xs text-slate-500 mb-2">
        开启后，登录时除了密码还需要一次验证码。两种方式可以同时开启。
      </p>

      <div className="divide-y divide-slate-100">
        <div className="flex flex-col gap-3 py-5 first:pt-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-800">认证器应用</span>
            <Badge on={status.totp_enabled} />
          </div>
          <p className="text-xs text-slate-500">
            用 Google Authenticator、Microsoft Authenticator 等应用扫码，离线也能生成验证码。
          </p>

          {enrollment ? (
            <div className="flex flex-col gap-3">
              <div className="flex justify-center rounded-md border border-slate-100 bg-slate-50 p-5">
                <div className="rounded-md bg-white p-3 shadow-sm">
                  <QRCodeSVG
                    value={enrollment.provisioning_uri}
                    size={176}
                    level="M"
                    fgColor="#0f172a"
                    bgColor="#ffffff"
                    title="两步验证绑定二维码"
                  />
                </div>
              </div>
              <p className="text-xs text-slate-500">
                无法扫码时，手动输入密钥：
                <span className="ml-1 font-mono text-slate-800 break-all">{enrollment.secret}</span>
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  value={totpCode}
                  placeholder="应用显示的 6 位验证码"
                  onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ""))}
                  className={FIELD_CLASS}
                />
                <button
                  type="button"
                  onClick={confirmTotp}
                  disabled={busy || totpCode.length !== 6}
                  className={DARK_BUTTON}
                >
                  确认绑定
                </button>
              </div>
              <button
                type="button"
                onClick={() => {
                  setEnrollment(null);
                  setTotpCode("");
                }}
                className="self-start text-xs text-slate-500 hover:text-slate-700"
              >
                取消绑定
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setAction(status.totp_enabled ? "totp-disable" : "totp-start")}
              disabled={busy}
              className={`self-start ${status.totp_enabled ? LIGHT_BUTTON : DARK_BUTTON}`}
            >
              {status.totp_enabled ? "关闭认证器验证" : "绑定认证器"}
            </button>
          )}
        </div>

        <div className="flex flex-col gap-3 py-5">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-800">短信验证码</span>
            <Badge on={status.sms_enabled} />
          </div>
          <p className="text-xs text-slate-500">
            {status.sms_available
              ? "登录时向绑定的手机号发送一次性验证码。"
              : "需要先在上方绑定并验证手机号，才能开启短信验证。"}
          </p>
          <button
            type="button"
            onClick={() => setAction(status.sms_enabled ? "sms-disable" : "sms-enable")}
            disabled={busy || (!status.sms_available && !status.sms_enabled)}
            className={`self-start ${status.sms_enabled ? LIGHT_BUTTON : DARK_BUTTON}`}
          >
            {status.sms_enabled ? "关闭短信验证" : "开启短信验证"}
          </button>
        </div>

        <div className="flex flex-col gap-3 py-5 last:pb-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-800">恢复码</span>
            <span className="text-xs text-slate-500">
              剩余 {status.recovery_codes_remaining} 个
            </span>
          </div>
          <p className="text-xs text-slate-500">
            手机丢失时用来登录，每个只能使用一次。关闭全部两步验证方式后会自动作废。
          </p>
          <button
            type="button"
            onClick={() => setAction("recovery")}
            disabled={busy || !(status.totp_enabled || status.sms_enabled)}
            className={`self-start ${LIGHT_BUTTON}`}
          >
            重新生成恢复码
          </button>
        </div>
      </div>

      {action && (
        <div className="mt-5 flex flex-col gap-2 rounded-md border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs font-semibold text-slate-700">{ACTIONS[action].prompt}</p>
          <div className="flex gap-2">
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              placeholder="当前密码"
              onChange={(e) => setPassword(e.target.value)}
              className={FIELD_CLASS}
            />
            <button
              type="button"
              onClick={runAction}
              disabled={busy || password.length === 0}
              className={DARK_BUTTON}
            >
              确认
            </button>
            <button type="button" onClick={reset} disabled={busy} className={LIGHT_BUTTON}>
              取消
            </button>
          </div>
        </div>
      )}

      {codes && (
        <div className="mt-5">
          <RecoveryCodePanel codes={codes} onDismiss={() => setCodes(null)} />
        </div>
      )}

      {message != null && (
        <div className="mt-4">
          <StatusMessage value={message} tone={tone} />
        </div>
      )}
    </div>
  );
}
