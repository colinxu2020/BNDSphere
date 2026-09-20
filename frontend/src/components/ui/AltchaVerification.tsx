import { createElement, forwardRef } from "react";
import type { AltchaWidgetElement } from "altcha/types/generic";

export type AltchaPurpose = "login" | "register" | "password_reset";
export type AltchaVerificationRef = AltchaWidgetElement;

interface AltchaVerificationProps {
  purpose: AltchaPurpose;
}

export const AltchaVerification = forwardRef<AltchaWidgetElement, AltchaVerificationProps>(
  function AltchaVerification({ purpose }, ref) {
    const challengeUrl = `/api/v1/auth/altcha/challenge?purpose=${purpose}`;

    return (
      <div className="w-full">
        {createElement("altcha-widget", {
          ref,
          challenge: challengeUrl,
          language: "zh-cn",
          name: "altcha",
          type: "checkbox",
          style: { "--altcha-max-width": "100%" },
        })}
      </div>
    );
  },
);
