import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Check, Mail, Phone } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import { StatusMessage } from "./ui/AppPrimitives";

type UserInfo = components["schemas"]["UserInfo"];

const FIELD_CLASS =
  "w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 " +
  "focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all " +
  "font-medium text-slate-900 disabled:opacity-60";

const CHANNELS = {
  email: {
    label: "电子邮箱",
    icon: Mail,
    inputType: "email",
    placeholder: "you@example.com",
    hint: "绑定后可用于安全通知和后续的账号找回。",
  },
  phone: {
    label: "手机号码",
    icon: Phone,
    inputType: "tel",
    placeholder: "13800138000",
    hint: "仅支持中国内地手机号，绑定后可用于账号找回和两步验证。",
  },
} as const;

type Channel = keyof typeof CHANNELS;

/** The one place that knows a channel's two endpoints differ only by field name. */
function api(channel: Channel) {
  return {
    send: (target: string, password: string) =>
      channel === "email"
        ? client.POST("/api/v1/verification/email/send", {
            body: { email: target, password },
          })
        : client.POST("/api/v1/verification/phone/send", {
            body: { phone: target, password },
          }),
    confirm: (target: string, code: string) =>
      channel === "email"
        ? client.POST("/api/v1/verification/email/confirm", {
            body: { email: target, code },
          })
        : client.POST("/api/v1/verification/phone/confirm", {
            body: { phone: target, code },
          }),
  };
}

function ChannelRow({
  channel,
  user,
  onVerified,
}: {
  channel: Channel;
  user: UserInfo;
  onVerified: (user: UserInfo) => void;
}) {
  const config = CHANNELS[channel];
  const Icon = config.icon;
  const current = channel === "email" ? user.email : user.phone;
  const verifiedAt = channel === "email" ? user.email_verified_at : user.phone_verified_at;

  const [target, setTarget] = useState(current || "");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [codeSent, setCodeSent] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<unknown>(null);
  const [tone, setTone] = useState<"error" | "success">("error");

  // The server enforces the real interval; this only keeps the button from
  // inviting a request it already knows will come back 429.
  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setTimeout(() => setCooldown((seconds) => seconds - 1), 1000);
    return () => clearTimeout(timer);
  }, [cooldown]);

  const handleSend = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const { data, error } = await api(channel).send(target.trim(), password);
      if (error) {
        setTone("error");
        setMessage(error);
      } else {
        setCodeSent(true);
        setCooldown(data?.resend_after ?? 60);
        setTone("success");
        setMessage(`验证码已发送，请在 ${Math.round((data?.expires_in ?? 0) / 60)} 分钟内填写。`);
      }
    } catch (err) {
      // A network failure is ambiguous: the server may have committed a live
      // code before the response was lost, and the budget is spent either
      // way. Keep the code entry visible so a code that did arrive can still
      // be confirmed instead of forcing a resend.
      setCodeSent(true);
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  const handleConfirm = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const { data, error } = await api(channel).confirm(target.trim(), code.trim());
      if (error) {
        setTone("error");
        setMessage(error);
      } else if (data) {
        setCode("");
        setPassword("");
        setCodeSent(false);
        setCooldown(0);
        setTone("success");
        setMessage(`${config.label}绑定成功。`);
        onVerified(data);
      }
    } catch (err) {
      setTone("error");
      setMessage(err);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 py-5 first:pt-0 last:pb-0">
      <div className="flex items-center gap-2">
        <Icon size={16} className="text-slate-400" />
        <span className="text-sm font-bold text-slate-800">{config.label}</span>
        {verifiedAt ? (
          <span className="flex items-center gap-1 px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-md border border-emerald-100">
            <Check size={12} /> 已验证
          </span>
        ) : (
          current && (
            <span className="px-2 py-0.5 bg-amber-50 text-amber-700 text-xs font-bold rounded-md border border-amber-100">
              未验证
            </span>
          )
        )}
      </div>

      <p className="text-xs text-slate-500">{config.hint}</p>

      {/* The server refuses a send without it: a bound address is where
          password resets land, so a session left open must not be enough to
          move it. */}
      <input
        type="password"
        autoComplete="current-password"
        value={password}
        placeholder="账号密码"
        onChange={(e) => setPassword(e.target.value)}
        className={FIELD_CLASS}
      />

      <div className="flex gap-2">
        <input
          type={config.inputType}
          value={target}
          placeholder={config.placeholder}
          onChange={(e) => setTarget(e.target.value)}
          className={FIELD_CLASS}
        />
        <button
          type="button"
          onClick={handleSend}
          disabled={busy || cooldown > 0 || !target.trim() || !password}
          className="shrink-0 px-4 py-3 bg-slate-900 text-white text-sm font-semibold rounded-md hover:bg-slate-800 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
        >
          {cooldown > 0 ? `${cooldown} 秒后重发` : codeSent ? "重新发送" : "发送验证码"}
        </button>
      </div>

      {codeSent && (
        <div className="flex gap-2">
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
          <button
            type="button"
            onClick={handleConfirm}
            disabled={busy || code.length !== 6}
            className="shrink-0 px-4 py-3 bg-primary-500 hover:bg-primary-600 text-white text-sm font-semibold rounded-md transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            确认绑定
          </button>
        </div>
      )}

      {message != null && <StatusMessage value={message} tone={tone} />}
    </div>
  );
}

export function ContactVerification({
  user,
  onVerified,
}: {
  user: UserInfo;
  onVerified: (user: UserInfo) => void;
}) {
  return <ContactVerificationForm key={user.id} user={user} onVerified={onVerified} />;
}

function ContactVerificationForm({
  user,
  onVerified,
}: {
  user: UserInfo;
  onVerified: (user: UserInfo) => void;
}) {
  const [policy, setPolicy] = useState<components["schemas"]["ContactPolicyStatus"] | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPolicy(null);
    setAccepted(false);
    setError(null);
    client
      .GET("/api/v1/verification/contact-policy", { signal: controller.signal })
      .then(({ data, error }) => {
        if (controller.signal.aborted) return;
        if (error) setError(error);
        else if (data) setPolicy(data);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setError(error);
      });
    return () => controller.abort();
  }, [user.id, retry]);

  const acceptPolicy = async () => {
    if (!policy || !accepted || busy) return;
    setBusy(true);
    setError(null);
    try {
      const { data, error } = await client.POST("/api/v1/verification/contact-policy", {
        body: { version: policy.version, accepted: true },
      });
      if (error) setError(error);
      else if (data) setPolicy(data);
    } catch (error) {
      setError(error);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="bg-white rounded-md border border-slate-100 shadow-sm p-8">
      <h3 className="text-sm font-bold text-slate-800 mb-1 font-display">联系方式验证</h3>
      <p className="text-xs text-slate-500 mb-2">
        绑定邮箱或手机号是可选的，我们只会用它们发送验证码和账号安全通知。
      </p>
      {error != null && <StatusMessage value={error} />}
      {!policy && error != null && (
        <button
          type="button"
          onClick={() => setRetry((value) => value + 1)}
          className="text-sm text-primary-600 underline"
        >
          重新检查
        </button>
      )}
      {!policy && !error && <p className="text-sm text-slate-500">正在检查隐私政策同意记录...</p>}
      {policy && !policy.accepted && (
        <div className="flex flex-col gap-3 py-3">
          <p className="text-sm text-slate-600">
            绑定联系方式前，请阅读更新后的隐私政策，其中说明了邮箱、手机号以及邮件和短信服务商的数据处理方式。
          </p>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={accepted}
              onChange={(event) => setAccepted(event.target.checked)}
            />
            <span>
              我已阅读并同意{" "}
              <Link
                className="text-primary-600 underline"
                to="/legal/privacy-policy"
                target="_blank"
                rel="noopener noreferrer"
              >
                隐私政策（{policy.version}）
              </Link>
            </span>
          </label>
          <button
            type="button"
            disabled={!accepted || busy}
            onClick={() => void acceptPolicy()}
            className="self-start rounded-md bg-primary-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "保存中..." : "同意并继续"}
          </button>
        </div>
      )}
      {policy?.accepted && (
        <div className="divide-y divide-slate-100">
          <ChannelRow channel="email" user={user} onVerified={onVerified} />
          <ChannelRow channel="phone" user={user} onVerified={onVerified} />
        </div>
      )}
    </div>
  );
}
