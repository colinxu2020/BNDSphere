import { useState } from "react";
import { Award, Plus, Save, X } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import type { components } from "../../api/schema";
import {
  Badge,
  EmptyState,
  Field,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { FileUploadField } from "../../components/ui/FileUploadField";
import { StarLevelCompact } from "../../components/ui/StarLevel";
import { AUDIT_STATUS_MAP } from "../../lib/labels";
import {
  formatDateTime,
  nullableNumber,
  nullableText,
  toNumberOrZero,
} from "../../lib/format";
import { AUDIT_TONE } from "../../lib/tones";
import { useActionFeedback } from "../../lib/useActionFeedback";
import { cn } from "../../lib/utils";
import { EditorHeader } from "./helpers";

type StarApplication = components["schemas"]["StarLevelApplicationInfo"];

/**
 * 星级申请 — a club's star-level applications, and the create/amend editor.
 *
 * Unlike 综评活动记录 this concern has no derived values: its selection is held in
 * state rather than computed, so the state group plus its three handlers is the whole
 * of it. It keeps two feedback hooks because create and amend report separately, which
 * is how the page behaved before.
 */
export function ClubStarApplicationsSection({
  clubId,
  starApplications,
  onChanged,
}: {
  clubId: number;
  starApplications: StarApplication[];
  onChanged: () => void;
}) {
  const [starAttachment, setStarAttachment] = useState("");
  const [starScore, setStarScore] = useState("");
  const [starStatement, setStarStatement] = useState("");
  const starCreateFeedback = useActionFeedback();
  const [isStarCreating, setIsStarCreating] = useState(false);
  const [starEditorMode, setStarEditorMode] = useState<
    "create" | "update" | null
  >(null);

  const [starUpdateId, setStarUpdateId] = useState("");
  const [starUpdateAttachment, setStarUpdateAttachment] = useState("");
  const [starUpdateScore, setStarUpdateScore] = useState("");
  const [starUpdateStatement, setStarUpdateStatement] = useState("");
  const starUpdateFeedback = useActionFeedback();
  const [isStarUpdating, setIsStarUpdating] = useState(false);

  const submitStarCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarCreating(true);
    starCreateFeedback.clear();
    try {
      const { data, error } = await client.POST(
        "/api/v1/clubs/{club_id}/star-level/",
        {
          params: { path: { club_id: clubId } },
          body: {
            contest_attachment: nullableText(starAttachment),
            requested_contest_score: nullableNumber(starScore),
            uniqueness_statement: nullableText(starStatement),
          },
        },
      );
      if (error) {
        starCreateFeedback.fail(error);
      } else {
        starCreateFeedback.succeed(data);
        onChanged();
      }
    } catch (error) {
      starCreateFeedback.fail(error);
    } finally {
      setIsStarCreating(false);
    }
  };

  const selectStarApplication = (application: StarApplication) => {
    setStarEditorMode("update");
    starUpdateFeedback.succeed(null);
    setStarUpdateId(String(application.id));
    setStarUpdateAttachment(application.contest_attachment || "");
    setStarUpdateScore(
      application.requested_contest_score == null
        ? ""
        : String(application.requested_contest_score),
    );
    setStarUpdateStatement(application.uniqueness_statement || "");
  };

  const openStarCreate = () => {
    setStarEditorMode("create");
    setStarUpdateId("");
    setStarAttachment("");
    setStarScore("");
    setStarStatement("");
    starCreateFeedback.clear();
  };

  const closeStarEditor = () => {
    setStarEditorMode(null);
    setStarUpdateId("");
  };

  const submitStarUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarUpdating(true);
    starUpdateFeedback.clear();
    try {
      const { data, error } = await client.PATCH(
        "/api/v1/star-level/{star_level_id}",
        {
          params: { path: { star_level_id: Number(starUpdateId) } },
          body: {
            contest_attachment: nullableText(starUpdateAttachment),
            requested_contest_score: nullableNumber(starUpdateScore),
            uniqueness_statement: nullableText(starUpdateStatement),
          },
        },
      );
      if (error) {
        starUpdateFeedback.fail(error);
      } else {
        starUpdateFeedback.succeed(data);
        onChanged();
      }
    } catch (error) {
      starUpdateFeedback.fail(error);
    } finally {
      setIsStarUpdating(false);
    }
  };

  return (
    <Surface density="compact">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <SectionTitle density="compact"
          className="mb-0"
          icon={<Award size={20} />}
          title="星级申请"
        />
        <SecondaryButton
          type="button"
          onClick={openStarCreate}
          className="w-full whitespace-nowrap sm:w-auto"
        >
          <Plus size={16} /> 新建星级申请
        </SecondaryButton>
      </div>
      <div
        className={`grid gap-6 ${
          starEditorMode ? "lg:grid-cols-[0.95fr_1.05fr]" : "grid-cols-1"
        }`}
      >
        <div className="grid gap-3">
          {starApplications.length ? (
            starApplications.map((application) => (
              <button
                type="button"
                key={application.id}
                onClick={() => selectStarApplication(application)}
                className={`rounded-md border p-5 text-left transition hover:bg-surface ${
                  starUpdateId === String(application.id)
                    ? "border-tone-brand-edge bg-brand-subtle"
                    : "border-edge-subtle bg-surface-sunken"
                }`}
              >
                <div className="flex flex-wrap gap-2">
                  <Badge
                    tone={AUDIT_TONE[application.audit_status ?? "pending"]}
                  >
                    {application.audit_status
                      ? AUDIT_STATUS_MAP[application.audit_status]
                      : "未审核"}
                  </Badge>
                  {application.approved_level && (
                    <StarLevelCompact level={application.approved_level} />
                  )}
                </div>
                <h3 className="mt-3 font-semibold text-content">
                  申请 #{application.id}
                </h3>
                <p className="mt-1 text-sm text-content-muted">
                  申请竞赛分{" "}
                  {application.requested_contest_score ?? "未填"}
                  ，核定分 {application.approved_score ?? "未定"}
                </p>
              </button>
            ))
          ) : (
            <EmptyState title="暂无星级申请" />
          )}
        </div>

        {starEditorMode && (
          <div className="rounded-md border border-edge-subtle bg-surface p-5">
            {starEditorMode === "create" ? (
              <form
                onSubmit={submitStarCreate}
                className="flex flex-col gap-4"
              >
                <EditorHeader
                  eyebrow="新建申请"
                  title="创建星级申请"
                  onClose={closeStarEditor}
                />
                <FileUploadField
                  label="竞赛附件"
                  scene="application_file"
                  value={starAttachment}
                  onChange={setStarAttachment}
                  hint="上传后作为星级申请附件。"
                />
                <Field label="申请竞赛分">
                  <input
                    className={inputClassName}
                    type="number"
                    value={starScore}
                    onChange={(event) => setStarScore(event.target.value)}
                  />
                </Field>
                <Field label="独特性说明">
                  <textarea
                    className={textareaClassName}
                    value={starStatement}
                    onChange={(event) =>
                      setStarStatement(event.target.value)
                    }
                  />
                </Field>
                <StatusMessage
                  value={starCreateFeedback.message}
                  tone={starCreateFeedback.tone}
                />
                <PrimaryButton type="submit" loading={isStarCreating}>
                  提交星级申请
                </PrimaryButton>
              </form>
            ) : starUpdateId ? (
              <form
                onSubmit={submitStarUpdate}
                className="flex flex-col gap-4"
              >
                <EditorHeader
                  eyebrow="当前编辑"
                  title={`星级申请 #${starUpdateId}`}
                  onClose={closeStarEditor}
                />
                <FileUploadField
                  label="竞赛附件"
                  scene="application_file"
                  value={starUpdateAttachment}
                  onChange={setStarUpdateAttachment}
                  hint="上传后替换星级申请附件。"
                />
                <Field label="申请竞赛分">
                  <input
                    className={inputClassName}
                    type="number"
                    value={starUpdateScore}
                    onChange={(event) =>
                      setStarUpdateScore(event.target.value)
                    }
                  />
                </Field>
                <Field label="独特性说明">
                  <textarea
                    className={textareaClassName}
                    value={starUpdateStatement}
                    onChange={(event) =>
                      setStarUpdateStatement(event.target.value)
                    }
                  />
                </Field>
                <PrimaryButton type="submit" loading={isStarUpdating}>
                  更新申请
                </PrimaryButton>
                <StatusMessage
                  value={starUpdateFeedback.message}
                  tone={starUpdateFeedback.tone}
                />
              </form>
            ) : (
              <EmptyState title="请选择星级申请" />
            )}
          </div>
        )}
      </div>
    </Surface>
  );
}
