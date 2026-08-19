import { useState } from "react";
import { FileCheck2 } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import {
  Badge,
  EmptyState,
  Field,
  PrimaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  selectClassName,
} from "../../components/ui/AppPrimitives";
import { FileUploadField } from "../../components/ui/FileUploadField";
import {
  AUDIT_STATUS_MAP,
  PARTICIPATION_MAP,
  PARTICIPATION_OPTIONS,
} from "../../lib/labels";
import { formatDateTime, toNumberOrZero } from "../../lib/format";
import { AUDIT_TONE } from "../../lib/tones";
import { useActionFeedback } from "../../lib/useActionFeedback";
import { EditorHeader } from "./helpers";

type GeneralActivity = components["schemas"]["GeneralActivityInfo"];
type ClubGeneralActivity = components["schemas"]["ClubGeneralActivityInfo"];
type ParticipationType = components["schemas"]["ParticipationTypeEnum"];

/**
 * 综评活动记录 — a club's participation records for general activities, and the form
 * that submits or amends one.
 *
 * The concern whose first extraction attempt was reverted. The map that back-out
 * produced was the point: this section's state group is not the whole concern. Two
 * derived values (which activity is selected, and whether a record already exists for
 * it) and the selection handler that fills the form all belong here too, and moving
 * the state alone is what broke it before.
 *
 * The activity list, the club's existing records and a refresh callback are the shared
 * values and arrive as props.
 */
export function ClubRecordsSection({
  clubId,
  generalActivities,
  records,
  onSubmitted,
}: {
  clubId: number;
  generalActivities: GeneralActivity[];
  records: ClubGeneralActivity[];
  onSubmitted: () => void;
}) {
  const [generalActivityId, setGeneralActivityId] = useState("");
  const [participationType, setParticipationType] =
    useState<ParticipationType>("participate_only");
  const [requestedScore, setRequestedScore] = useState("");
  const [proofFileUrls, setProofFileUrls] = useState<string[]>([]);
  const recordFeedback = useActionFeedback();
  const [isRecordSubmitting, setIsRecordSubmitting] = useState(false);

  const selectedGeneralActivity = generalActivities.find(
    (activityItem) => String(activityItem.id) === generalActivityId,
  );
  const selectedGeneralRecord =
    records.find(
      (record) => String(record.activity_id) === generalActivityId,
    ) || null;

  const selectGeneralActivityForRecord = (activityItem: GeneralActivity) => {
    const existingRecord = records.find(
      (record) => record.activity_id === activityItem.id,
    );
    setGeneralActivityId(String(activityItem.id));
    if (existingRecord) {
      setParticipationType(existingRecord.participation_type);
      setRequestedScore(String(existingRecord.requested_score));
      setProofFileUrls(existingRecord.proof_files || []);
    } else {
      setParticipationType("participate_only");
      setRequestedScore("");
      setProofFileUrls([]);
    }
    recordFeedback.clear();
  };

  const submitRecord = async (mode: "create" | "update") => {
    setIsRecordSubmitting(true);
    recordFeedback.clear();
    const payload = {
      activity_id: toNumberOrZero(generalActivityId),
      participation_type: participationType,
      proof_files: proofFileUrls,
      requested_score: toNumberOrZero(requestedScore),
    };

    try {
      const request =
        mode === "create"
          ? client.POST("/api/v1/clubs/{club_id}/general-activities/", {
              params: { path: { club_id: clubId } },
              body: payload,
            })
          : client.PATCH("/api/v1/clubs/{club_id}/general-activities/", {
              params: { path: { club_id: clubId } },
              body: payload,
            });

      const { data, error } = await request;
      if (error) {
        recordFeedback.fail(error);
      } else {
        recordFeedback.succeed(data);
        onSubmitted();
      }
    } catch (error) {
      recordFeedback.fail(error);
    } finally {
      setIsRecordSubmitting(false);
    }
  };

  return (
    <Surface density="compact">
      <SectionTitle density="compact"
        icon={<FileCheck2 size={20} />}
        title="综评活动记录"
        description="点击“未提交”的大型活动可新建记录；点击已提交的活动可查看或修改记录。"
      />
      <div
        className={`grid gap-6 ${
          selectedGeneralActivity
            ? "lg:grid-cols-[0.95fr_1.05fr]"
            : "grid-cols-1"
        }`}
      >
        <div className="grid gap-3">
          {generalActivities.length ? (
            generalActivities.map((activityItem) => {
              const record = records.find(
                (item) => item.activity_id === activityItem.id,
              );
              const isSelected =
                generalActivityId === String(activityItem.id);
              return (
                <button
                  key={activityItem.id}
                  type="button"
                  onClick={() =>
                    selectGeneralActivityForRecord(activityItem)
                  }
                  className={`rounded-md p-4 text-left transition hover:bg-surface ${
                    isSelected
                      ? "bg-brand-subtle ring-[1.5px] ring-brand-strong/40"
                      : "bg-surface-sunken ring-[1.5px] ring-edge"
                  }`}
                >
                  <div className="flex flex-wrap items-center gap-2">
                    {record ? (
                      <>
                        <Badge tone={AUDIT_TONE[record.audit_status]}>
                          {AUDIT_STATUS_MAP[record.audit_status]}
                        </Badge>
                        <Badge>
                          {PARTICIPATION_MAP[record.participation_type]}
                        </Badge>
                      </>
                    ) : (
                      <Badge tone="neutral">未提交</Badge>
                    )}
                  </div>
                  <h3 className="mt-3 font-semibold text-content">
                    {activityItem.name}
                  </h3>
                  <p className="mt-1 line-clamp-2 text-sm text-content-muted">
                    {activityItem.description}
                  </p>
                  <p className="mt-2 text-xs font-medium text-content-subtle">
                    #{activityItem.id} ·{" "}
                    {formatDateTime(
                      activityItem.starts_at || activityItem.created_at,
                    )}
                    {record ? ` · 申请 ${record.requested_score} 分` : ""}
                  </p>
                </button>
              );
            })
          ) : (
            <EmptyState title="暂无综评活动" />
          )}
        </div>

        {selectedGeneralActivity && (
          <div className="rounded-md bg-surface p-5 ring-[1.5px] ring-edge">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                submitRecord(selectedGeneralRecord ? "update" : "create");
              }}
              className="flex flex-col gap-4"
            >
              <div>
                <EditorHeader
                  eyebrow={
                    selectedGeneralRecord ? "当前记录" : "新建记录"
                  }
                  title={selectedGeneralActivity.name}
                  onClose={() => setGeneralActivityId("")}
                />
                {selectedGeneralRecord && (
                  <p className="mt-1 text-sm text-content-muted">
                    记录 #{selectedGeneralRecord.id}
                  </p>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="参与类型">
                  <select
                    className={selectClassName}
                    value={participationType}
                    onChange={(event) =>
                      setParticipationType(
                        event.target.value as ParticipationType,
                      )
                    }
                  >
                    {PARTICIPATION_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="申请分值">
                  <input
                    className={inputClassName}
                    type="number"
                    value={requestedScore}
                    onChange={(event) =>
                      setRequestedScore(event.target.value)
                    }
                    required
                  />
                </Field>
              </div>
              <FileUploadField
                label="证明材料"
                scene="application_file"
                values={proofFileUrls}
                onValuesChange={setProofFileUrls}
                multiple
              />
              {selectedGeneralRecord?.audit_status !== "pending" &&
                selectedGeneralRecord && (
                  <StatusMessage
                    value="已审核的综评记录不能在这里更新。"
                    tone="info"
                  />
                )}
              <StatusMessage value={recordFeedback.message} tone={recordFeedback.tone} />
              <PrimaryButton
                type="submit"
                loading={isRecordSubmitting}
                disabled={
                  selectedGeneralRecord?.audit_status !== "pending" &&
                  Boolean(selectedGeneralRecord)
                }
              >
                {selectedGeneralRecord ? "更新记录" : "创建记录"}
              </PrimaryButton>
            </form>
          </div>
        )}
      </div>
    </Surface>
  );
}
