import { useState } from "react";
import { FilePenLine } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import { SectionTitle, Surface } from "../../components/ui/AppPrimitives";
import type { useActionFeedback } from "../../lib/useActionFeedback";
import { ActivityRequestList } from "./shared";

type ModerationStatus = components["schemas"]["ModerationStatusEnum"];
type ActivityCreateRequest = components["schemas"]["ClubActivityCreateRequestInfo"];
type ActivityUpdateRequest = components["schemas"]["ClubActivityUpdateRequestInfo"];
type ActivityModerationKind = "create" | "update";

/**
 * 审核社团活动 — the create and update request queues.
 *
 * The second of Federation's four concerns. Only `busyActivityRequest` — which row
 * is mid-flight — was ever local to it; both queues come from the shared loader and
 * arrive as props, so nothing about state ownership is invented here.
 */
export function ActivityRequestsPanel({
  createRequests,
  updateRequests,
  feedback,
  onModerated,
}: {
  createRequests: ActivityCreateRequest[];
  updateRequests: ActivityUpdateRequest[];
  feedback: ReturnType<typeof useActionFeedback>;
  onModerated: () => void;
}) {
  const [busyActivityRequest, setBusyActivityRequest] = useState<string | null>(null);

  const moderateClubActivityRequest = async (
    kind: ActivityModerationKind,
    requestId: number,
    moderationStatus: ModerationStatus,
  ) => {
    setBusyActivityRequest(`${kind}-${requestId}`);
    feedback.clear();
    const body = { moderation_status: moderationStatus };
    try {
      const result =
        kind === "create"
          ? await client.PATCH("/api/v1/moderations/club-activities/create-requests/{request_id}", {
              params: { path: { request_id: requestId } },
              body,
            })
          : await client.PATCH("/api/v1/moderations/club-activities/update-requests/{request_id}", {
              params: { path: { request_id: requestId } },
              body,
            });

      feedback.report(
        result.error,
        moderationStatus === "approved" ? "社团活动申请已通过" : "社团活动申请已驳回",
      );
      if (!result.error) onModerated();
    } catch (error) {
      feedback.report(error, "");
    } finally {
      setBusyActivityRequest(null);
    }
  };

  return (
    <Surface density="compact">
      <SectionTitle
        density="compact"
        icon={<FilePenLine size={20} />}
        title="审核社团活动"
        description="处理社团提交的活动创建和修改申请。"
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <ActivityRequestList
          title="活动创建申请"
          kind="create"
          items={createRequests}
          busyKey={busyActivityRequest}
          onModerate={moderateClubActivityRequest}
        />
        <ActivityRequestList
          title="活动修改申请"
          kind="update"
          items={updateRequests}
          busyKey={busyActivityRequest}
          onModerate={moderateClubActivityRequest}
        />
      </div>
    </Surface>
  );
}
