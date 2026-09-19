import { useEffect, useState } from "react";
import { Check, Clock, ShieldCheck, X } from "@/src/components/ui/Icons";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  Badge,
  EmptyState,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
} from "../components/ui/AppPrimitives";
import { PageLoading } from "../components/ui/PageStates";
import { formatDateTime } from "../lib/format";

type ClubClaim = components["schemas"]["ClubClaimRequestReviewInfo"];

export function FederationClubClaims({
  refreshToken,
  onLoadingChange,
}: {
  refreshToken: number;
  onLoadingChange: (isLoading: boolean) => void;
}) {
  const [claims, setClaims] = useState<ClubClaim[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [message, setMessage] = useState<unknown>(null);
  const [messageTone, setMessageTone] = useState<"error" | "success">("error");

  const refresh = async () => {
    setIsLoading(true);
    onLoadingChange(true);
    try {
      const response = await client.GET("/api/v1/club-federation/club-claims/", {
        params: { query: { size: 100 } },
      });
      setClaims(response.error ? [] : response.data?.items || []);
      if (response.error) {
        setMessageTone("error");
        setMessage(response.error);
      }
    } catch (error) {
      setClaims([]);
      setMessageTone("error");
      setMessage(error);
    } finally {
      setIsLoading(false);
      onLoadingChange(false);
    }
  };

  useEffect(() => {
    refresh();
    // Refresh only when requested by the parent workspace.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshToken]);

  const review = async (requestId: number, status: "approved" | "rejected") => {
    setBusyId(requestId);
    setMessage(null);
    try {
      const response = await client.PATCH("/api/v1/club-federation/club-claims/{request_id}", {
        params: { path: { request_id: requestId } },
        body: { verification_status: status },
      });
      setMessageTone(response.error ? "error" : "success");
      setMessage(response.error || `社团认领申请已${status === "approved" ? "通过" : "驳回"}`);
      if (!response.error) await refresh();
    } catch (error) {
      setMessageTone("error");
      setMessage(error);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {message && <StatusMessage value={message} tone={messageTone} />}
      <Surface>
        <SectionTitle
          icon={<ShieldCheck size={20} />}
          title="审核社团认领申请"
          description="通过后，申请人将成为该社团社长；同一社团的其他待审核申请会自动驳回。"
        />
        {isLoading ? (
          <PageLoading compact />
        ) : claims.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {claims.map((claim) => (
              <article
                key={claim.id}
                className="rounded-md border border-slate-100 bg-slate-50 p-5"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="yellow">待审核</Badge>
                  <span className="text-xs font-medium text-slate-400">申请 #{claim.id}</span>
                </div>
                <h3 className="mt-3 text-lg font-bold text-slate-900">{claim.club.name}</h3>
                <p className="mt-1 text-sm font-medium text-slate-500">
                  申请人：{claim.applicant.username}
                </p>
                <p className="mt-3 min-h-12 whitespace-pre-wrap text-sm leading-6 text-slate-600">
                  {claim.message || "未填写附言。"}
                </p>
                <p className="mt-3 text-xs font-medium text-slate-400">
                  <Clock size={14} className="mr-1 inline" />
                  {formatDateTime(claim.apply_at)}
                </p>
                <div className="mt-5 flex flex-wrap gap-2">
                  <PrimaryButton
                    type="button"
                    onClick={() => review(claim.id, "approved")}
                    loading={busyId === claim.id}
                  >
                    <Check size={16} /> 通过认领
                  </PrimaryButton>
                  <SecondaryButton
                    type="button"
                    onClick={() => review(claim.id, "rejected")}
                    disabled={busyId === claim.id}
                    className="text-red-600"
                  >
                    <X size={16} /> 驳回
                  </SecondaryButton>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState title="暂无待审核认领申请" />
        )}
      </Surface>
    </div>
  );
}
