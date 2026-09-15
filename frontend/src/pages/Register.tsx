import React, { useRef, useState } from "react";
import { motion } from "motion/react";
import { UserPlus } from "@/src/components/ui/Icons";
import { Link, useNavigate } from "react-router-dom";
import { client } from "../api/client";
import { StatusMessage } from "../components/ui/AppPrimitives";
import {
  AltchaVerification,
  type AltchaVerificationRef,
} from "../components/ui/AltchaVerification";
import { readAltchaPayload } from "../lib/altcha";

export function Register() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acceptedPrivacyPolicy, setAcceptedPrivacyPolicy] = useState(false);
  const [acceptedUserAgreement, setAcceptedUserAgreement] = useState(false);
  const [acceptedCrossBorderTransfer, setAcceptedCrossBorderTransfer] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false);
  const altchaRef = useRef<AltchaVerificationRef>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("两次输入的密码不一致。");
      return;
    }

    if (!acceptedPrivacyPolicy || !acceptedUserAgreement || !acceptedCrossBorderTransfer) {
      setError("请分别阅读并同意全部三份合规文件。");
      return;
    }

    const altcha = readAltchaPayload(e.currentTarget);
    if (!altcha) {
      setError("请先完成人机验证。");
      return;
    }

    setIsLoading(true);

    try {
      const { data, error: apiError } = await client.POST("/api/v1/auth/register", {
        body: {
          username,
          password,
          accepted_privacy_policy: acceptedPrivacyPolicy,
          accepted_user_agreement: acceptedUserAgreement,
          accepted_cross_border_transfer: acceptedCrossBorderTransfer,
          altcha,
        },
      });

      if (apiError) {
        setError(apiError);
        altchaRef.current?.reset();
        return;
      }

      if (data) {
        // Automatically login after register or redirect to login page
        navigate("/login");
      }
    } catch (err: any) {
      setError(err);
      altchaRef.current?.reset();
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
      <div className="w-full max-w-md bg-white p-8 rounded-md border border-slate-100 shadow-sm relative overflow-hidden">
        <div className="flex flex-col gap-2 mb-8 text-center relative z-10">
          <div className="mx-auto bg-primary-50 p-3 rounded-md text-primary-600 mb-2">
            <UserPlus size={28} />
          </div>
          <h1 className="text-2xl font-display font-bold text-slate-900">注册 BNDSphere</h1>
          <p className="text-slate-500 text-sm">创建您的新账号</p>
        </div>

        {error && (
          <div className="mb-6 relative z-10">
            <StatusMessage value={error} />
          </div>
        )}

        <form onSubmit={handleRegister} className="flex flex-col gap-5 relative z-10">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">用户名</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900"
              placeholder="您的用户名"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900"
              placeholder="••••••••"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5 ml-1">确认密码</label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-md focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 outline-none transition-all font-medium text-slate-900"
              placeholder="••••••••"
              required
            />
          </div>

          <fieldset className="flex flex-col gap-3 rounded-md border border-slate-200 bg-slate-50 p-4">
            <legend className="px-1 text-sm font-semibold text-slate-700">注册前请逐项确认</legend>
            <ConsentCheckbox
              id="accept-privacy-policy"
              checked={acceptedPrivacyPolicy}
              onChange={setAcceptedPrivacyPolicy}
              linkTo="/legal/privacy-policy"
              documentName="《BNDSphere 隐私政策》"
            />
            <ConsentCheckbox
              id="accept-user-agreement"
              checked={acceptedUserAgreement}
              onChange={setAcceptedUserAgreement}
              linkTo="/legal/user-agreement"
              documentName="《BNDSphere 用户协议》"
            />
            <ConsentCheckbox
              id="accept-cross-border-transfer"
              checked={acceptedCrossBorderTransfer}
              onChange={setAcceptedCrossBorderTransfer}
              linkTo="/legal/cross-border-transfer-consent"
              documentName="《BNDSphere 个人信息跨境传输单独同意书》"
              separate
            />
          </fieldset>

          <AltchaVerification ref={altchaRef} purpose="register" />

          <button
            type="submit"
            disabled={isLoading}
            className="mt-4 w-full py-3.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-md transition-all active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed shadow-md shadow-primary-500/20"
          >
            {isLoading ? "正在注册..." : "注册"}
          </button>

          <div className="mt-4 text-center text-sm text-slate-500">
            已有账号？{" "}
            <span
              onClick={() => navigate("/login")}
              className="text-primary-600 hover:text-primary-700 font-medium cursor-pointer"
            >
              返回登录
            </span>
          </div>
        </form>
      </div>
    </motion.div>
  );
}

function ConsentCheckbox({
  id,
  checked,
  onChange,
  linkTo,
  documentName,
  separate = false,
}: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  linkTo: string;
  documentName: string;
  separate?: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        required
        className="mt-0.5 h-4 w-4 shrink-0 accent-primary-500"
      />
      <div className="text-sm leading-5 text-slate-600">
        <label htmlFor={id} className="cursor-pointer">
          我已阅读并{separate ? "单独" : ""}同意
        </label>{" "}
        <Link
          to={linkTo}
          target="_blank"
          rel="noreferrer"
          className="font-semibold text-primary-600 hover:text-primary-700 hover:underline"
        >
          {documentName}
        </Link>
      </div>
    </div>
  );
}
