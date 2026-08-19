import { useEffect, useState } from "react";
import { Save } from "@/src/components/ui/Icons";
import { client } from "../../api/client";
import {
  Field,
  PrimaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  textareaClassName,
} from "../../components/ui/AppPrimitives";
import { FileUploadField } from "../../components/ui/FileUploadField";
import { nullableText } from "../../lib/format";
import { useActionFeedback } from "../../lib/useActionFeedback";

/**
 * 社团资料变更申请 — a club submitting changes to its own profile for moderation.
 *
 * The first concern extracted from ClubWorkspace. Its four state values, its feedback
 * hook and its submit handler are referenced nowhere else, and unlike the other
 * sections it reaches for no shared memo or selection handler.
 *
 * One dependency did cross the boundary: the page's loader pre-filled these fields
 * from the club it fetched. Rather than reach back for that, the loaded values arrive
 * as props and seed the form here — including on a later reload, so the behaviour is
 * the same as when the loader wrote the state directly.
 */
export function ClubProfileRequestSection({
  clubId,
  initialSummary,
  initialDescription,
  initialLogo,
}: {
  clubId: number;
  initialSummary: string;
  initialDescription: string;
  initialLogo: string;
}) {
  const [clubSummary, setClubSummary] = useState(initialSummary);
  const [clubDescription, setClubDescription] = useState(initialDescription);
  const [clubLogo, setClubLogo] = useState(initialLogo);

  // Re-seed when the page reloads the club, matching what the loader used to do.
  useEffect(() => {
    setClubSummary(initialSummary);
    setClubDescription(initialDescription);
    setClubLogo(initialLogo);
  }, [initialSummary, initialDescription, initialLogo]);
  const clubFeedback = useActionFeedback();
  const [isClubSubmitting, setIsClubSubmitting] = useState(false);

  const submitClubUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsClubSubmitting(true);
    clubFeedback.clear();
    try {
      const { data, error } = await client.POST(
        "/api/v1/clubs/{club_id}/update-requests",
        {
          params: { path: { club_id: clubId } },
          body: {
            summary: nullableText(clubSummary),
            description: nullableText(clubDescription),
            logo_uri: nullableText(clubLogo),
          },
        },
      );
      if (error) {
        clubFeedback.fail(error);
      } else {
        clubFeedback.succeed(data);
      }
    } catch (error) {
      clubFeedback.fail(error);
    } finally {
      setIsClubSubmitting(false);
    }
  };

  return (
    <Surface density="compact">
      <SectionTitle density="compact" icon={<Save size={20} />} title="社团资料变更申请" />
      <form onSubmit={submitClubUpdate} className="flex flex-col gap-4">
        <Field label="简介">
          <input
            className={inputClassName}
            value={clubSummary}
            onChange={(event) => setClubSummary(event.target.value)}
          />
        </Field>
        <Field label="详细介绍">
          <textarea
            className={textareaClassName}
            value={clubDescription}
            onChange={(event) => setClubDescription(event.target.value)}
          />
        </Field>
        <FileUploadField
          label="Logo"
          scene="club_logo"
          value={clubLogo}
          onChange={setClubLogo}
          accept="image/*"
          hint="上传后作为社团资料变更申请的 Logo。"
        />
        <StatusMessage value={clubFeedback.message} tone={clubFeedback.tone} />
        <PrimaryButton type="submit" loading={isClubSubmitting}>
          提交变更申请
        </PrimaryButton>
      </form>
    </Surface>
  );
}
