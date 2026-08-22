import { useEffect, useMemo, useState, type FormEvent } from "react";
import { motion } from "motion/react";
import {
  ArrowLeft,
  CalendarDays,
  FileText,
  MapPin,
  Plus,
  RefreshCw,
  Save,
  UserPlus,
  Users,
} from "@/src/components/ui/Icons";
import { Link, useParams } from "react-router-dom";
import { client } from "../api/client";
import type { components } from "../api/schema";
import {
  Badge,
  EmptyState,
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  textareaClassName,
} from "../components/ui/AppPrimitives";
import { FileUploadField } from "../components/ui/FileUploadField";
import { AUDIT_STATUS_MAP } from "../lib/labels";
import { formatDateTime, fromDateTimeLocalValue, toDateTimeLocalValue } from "../lib/format";

type JointActivity = components["schemas"]["JointActivityInfo"];
type JointActivityPublic = components["schemas"]["JointActivityPublicInfo"];
type Club = components["schemas"]["ClubInfo"];

const emptyForm = { name: "", description: "", location: "", startsAt: "", endsAt: "" };

export function JointActivityWorkspace() {
  const { id } = useParams<{ id: string }>();
  const clubId = Number(id);
  const [club, setClub] = useState<Club | null>(null);
  const [clubActivities, setClubActivities] = useState<JointActivity[]>([]);
  const [publicActivities, setPublicActivities] = useState<JointActivityPublic[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [message, setMessage] = useState<unknown>(null);
  const [messageTone, setMessageTone] = useState<"error" | "success">("error");

  const registeredIds = useMemo(
    () => new Set(clubActivities.map((activity) => activity.id)),
    [clubActivities],
  );
  const availableActivities = useMemo(
    () =>
      publicActivities.filter(
        (activity) =>
          !registeredIds.has(activity.id) && new Date(activity.ends_at).getTime() > Date.now(),
      ),
    [publicActivities, registeredIds],
  );

  const refresh = async () => {
    setIsLoading(true);
    const [clubResponse, managedResponse, publicResponse] = await Promise.all([
      client.GET("/api/v1/clubs/{club_id}", { params: { path: { club_id: clubId } } }),
      client.GET("/api/v1/clubs/{club_id}/joint-activities/", {
        params: { path: { club_id: clubId }, query: { size: 100 } },
      }),
      client.GET("/api/v1/joint-activities/", { params: { query: { size: 100 } } }),
    ]);
    const error = clubResponse.error || managedResponse.error || publicResponse.error;
    if (error) {
      setMessageTone("error");
      setMessage(error);
    }
    setClub(clubResponse.error ? null : clubResponse.data || null);
    setClubActivities(managedResponse.error ? [] : managedResponse.data?.items || []);
    setPublicActivities(publicResponse.error ? [] : publicResponse.data?.items || []);
    setIsLoading(false);
  };

  useEffect(() => {
    refresh().catch((error) => {
      setMessage(error);
      setMessageTone("error");
      setIsLoading(false);
    });
    // Refresh when the routed club changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clubId]);

  const createActivity = async (event: FormEvent) => {
    event.preventDefault();
    setIsCreating(true);
    const response = await client.POST("/api/v1/clubs/{club_id}/joint-activities/", {
      params: { path: { club_id: clubId } },
      body: {
        name: form.name,
        description: form.description,
        location: form.location,
        starts_at: fromDateTimeLocalValue(form.startsAt),
        ends_at: fromDateTimeLocalValue(form.endsAt),
      },
    });
    setIsCreating(false);
    setMessageTone(response.error ? "error" : "success");
    setMessage(response.error || "联合活动已提交社联预审");
    if (!response.error) {
      setForm(emptyForm);
      await refresh();
    }
  };

  const register = async (activityId: number) => {
    const response = await client.POST(
      "/api/v1/clubs/{club_id}/joint-activities/{activity_id}/participations",
      { params: { path: { club_id: clubId, activity_id: activityId } } },
    );
    setMessageTone(response.error ? "error" : "success");
    setMessage(response.error || "已代表社团登记参与");
    if (!response.error) await refresh();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-8 pb-20"
    >
      <Link
        to={`/club/${clubId}/manage`}
        className="inline-flex w-fit items-center gap-2 font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft size={18} /> 返回社团工作台
      </Link>
      <PageHeader
        eyebrow="Joint Activities"
        title={`${club?.name || `社团 #${clubId}`} · 联合活动`}
        action={
          <SecondaryButton type="button" onClick={refresh} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />
      {message && <StatusMessage value={message} tone={messageTone} />}

      <Surface>
        <SectionTitle
          icon={<Plus size={20} />}
          title="发起联合活动"
          description="校外合作社团在介绍中直接说明即可"
        />
        <form onSubmit={createActivity} className="grid gap-4 md:grid-cols-2">
          <Field label="活动名称">
            <input
              className={inputClassName}
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
            />
          </Field>
          <Field label="地点">
            <input
              className={inputClassName}
              value={form.location}
              onChange={(event) => setForm({ ...form, location: event.target.value })}
              required
            />
          </Field>
          <Field label="开始时间">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.startsAt}
              onChange={(event) => setForm({ ...form, startsAt: event.target.value })}
              required
            />
          </Field>
          <Field label="结束时间">
            <input
              className={inputClassName}
              type="datetime-local"
              value={form.endsAt}
              onChange={(event) => setForm({ ...form, endsAt: event.target.value })}
              required
            />
          </Field>
          <div className="md:col-span-2">
            <Field label="活动介绍" hint="校外合作社团请写在这里。">
              <textarea
                className={textareaClassName}
                value={form.description}
                onChange={(event) => setForm({ ...form, description: event.target.value })}
                required
              />
            </Field>
          </div>
          <PrimaryButton type="submit" loading={isCreating} className="md:col-span-2 md:w-fit">
            <Save size={17} /> 提交预审
          </PrimaryButton>
        </form>
      </Surface>

      <Surface>
        <SectionTitle
          icon={<CalendarDays size={20} />}
          title="本社团的联合活动"
          description="包括本社团发起和登记参与的活动。"
        />
        {isLoading ? (
          <div className="h-40 animate-pulse rounded-md bg-slate-50" />
        ) : clubActivities.length ? (
          <div className="grid gap-5">
            {clubActivities.map((activity) => (
              <div key={activity.id}>
                <ManagedActivityCard
                  activity={activity}
                  clubId={clubId}
                  onChanged={refresh}
                  onMessage={(value, tone) => {
                    setMessage(value);
                    setMessageTone(tone);
                  }}
                />
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="本社团暂无联合活动" />
        )}
      </Surface>

      <Surface>
        <SectionTitle icon={<UserPlus size={20} />} title="登记参与公开活动" />
        <div className="grid gap-4 md:grid-cols-2">
          {availableActivities.map((activity) => (
            <div key={activity.id} className="rounded-md border border-slate-100 bg-slate-50 p-5">
              <Badge tone="primary">{activity.initiator_club.name} 发起</Badge>
              <h3 className="mt-3 font-bold text-slate-900">{activity.name}</h3>
              <p className="mt-2 line-clamp-2 text-sm text-slate-500">{activity.description}</p>
              <p className="mt-3 inline-flex items-center gap-2 text-xs font-medium text-slate-500">
                <MapPin size={14} /> {activity.location}
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <SecondaryButton type="button" onClick={() => register(activity.id)}>
                  <Users size={16} /> 登记参与
                </SecondaryButton>
                <Link
                  to={`/joint-activities/${activity.id}`}
                  className="rounded-md px-4 py-2.5 text-sm font-semibold text-primary-600 hover:bg-white"
                >
                  查看详情
                </Link>
              </div>
            </div>
          ))}
        </div>
        {!availableActivities.length && <EmptyState title="暂无可登记的公开活动" />}
      </Surface>
    </motion.div>
  );
}

function ManagedActivityCard({
  activity,
  clubId,
  onChanged,
  onMessage,
}: {
  activity: JointActivity;
  clubId: number;
  onChanged: () => Promise<void>;
  onMessage: (value: unknown, tone: "error" | "success") => void;
}) {
  const isInitiator = activity.initiator_club_id === clubId;
  const hasEnded = new Date(activity.ends_at).getTime() <= Date.now();
  const canEdit = isInitiator && activity.preliminary_status !== "approved";
  const canArchive =
    isInitiator &&
    activity.preliminary_status === "approved" &&
    hasEnded &&
    activity.final_status !== "pending" &&
    activity.final_status !== "approved";
  const [name, setName] = useState(activity.name);
  const [description, setDescription] = useState(activity.description);
  const [location, setLocation] = useState(activity.location);
  const [startsAt, setStartsAt] = useState(toDateTimeLocalValue(activity.starts_at));
  const [endsAt, setEndsAt] = useState(toDateTimeLocalValue(activity.ends_at));
  const [archiveText, setArchiveText] = useState(activity.archive_text || "");
  const [archiveFiles, setArchiveFiles] = useState(activity.archive_files || []);
  const [busy, setBusy] = useState(false);

  const saveDetails = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    const response = await client.PATCH("/api/v1/clubs/{club_id}/joint-activities/{activity_id}", {
      params: { path: { club_id: clubId, activity_id: activity.id } },
      body: {
        name,
        description,
        location,
        starts_at: fromDateTimeLocalValue(startsAt),
        ends_at: fromDateTimeLocalValue(endsAt),
      },
    });
    setBusy(false);
    onMessage(response.error || "联合活动已重新提交预审", response.error ? "error" : "success");
    if (!response.error) await onChanged();
  };

  const saveArchive = async () => {
    setBusy(true);
    const response = await client.PATCH(
      "/api/v1/clubs/{club_id}/joint-activities/{activity_id}/archive",
      {
        params: { path: { club_id: clubId, activity_id: activity.id } },
        body: { archive_text: archiveText || null, archive_files: archiveFiles },
      },
    );
    setBusy(false);
    onMessage(response.error || "活动档案已保存", response.error ? "error" : "success");
    if (!response.error) await onChanged();
  };

  const submitFinal = async () => {
    setBusy(true);
    const archiveResponse = await client.PATCH(
      "/api/v1/clubs/{club_id}/joint-activities/{activity_id}/archive",
      {
        params: { path: { club_id: clubId, activity_id: activity.id } },
        body: { archive_text: archiveText || null, archive_files: archiveFiles },
      },
    );
    if (archiveResponse.error) {
      setBusy(false);
      onMessage(archiveResponse.error, "error");
      return;
    }
    const response = await client.POST(
      "/api/v1/clubs/{club_id}/joint-activities/{activity_id}/final-submission",
      {
        params: { path: { club_id: clubId, activity_id: activity.id } },
      },
    );
    setBusy(false);
    onMessage(response.error || "活动档案已提交社联终审", response.error ? "error" : "success");
    if (!response.error) await onChanged();
  };

  return (
    <div className="rounded-md border border-slate-100 bg-slate-50 p-5">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={isInitiator ? "primary" : "slate"}>
          {isInitiator ? "发起社团" : "参与社团"}
        </Badge>
        <Badge
          tone={
            activity.preliminary_status === "approved"
              ? "green"
              : activity.preliminary_status === "rejected"
                ? "red"
                : "yellow"
          }
        >
          预审：{AUDIT_STATUS_MAP[activity.preliminary_status]}
        </Badge>
        {activity.final_status && (
          <Badge
            tone={
              activity.final_status === "approved"
                ? "green"
                : activity.final_status === "rejected"
                  ? "red"
                  : "yellow"
            }
          >
            终审：{AUDIT_STATUS_MAP[activity.final_status]}
          </Badge>
        )}
      </div>
      <h3 className="mt-3 text-lg font-bold text-slate-900">{activity.name}</h3>
      <p className="mt-2 text-sm text-slate-500">
        {formatDateTime(activity.starts_at)} · {activity.location}
      </p>

      {canEdit && (
        <form onSubmit={saveDetails} className="mt-5 grid gap-3 md:grid-cols-2">
          <Field label="活动名称">
            <input
              className={inputClassName}
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
            />
          </Field>
          <Field label="地点">
            <input
              className={inputClassName}
              value={location}
              onChange={(event) => setLocation(event.target.value)}
              required
            />
          </Field>
          <Field label="开始时间">
            <input
              className={inputClassName}
              type="datetime-local"
              value={startsAt}
              onChange={(event) => setStartsAt(event.target.value)}
              required
            />
          </Field>
          <Field label="结束时间">
            <input
              className={inputClassName}
              type="datetime-local"
              value={endsAt}
              onChange={(event) => setEndsAt(event.target.value)}
              required
            />
          </Field>
          <div className="md:col-span-2">
            <Field label="活动介绍">
              <textarea
                className={textareaClassName}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                required
              />
            </Field>
          </div>
          <PrimaryButton type="submit" loading={busy} className="md:w-fit">
            <Save size={16} /> 保存并重新预审
          </PrimaryButton>
        </form>
      )}

      {canArchive && (
        <div className="mt-5 grid gap-4 border-t border-slate-200 pt-5">
          <Field label="文字资料">
            <textarea
              className={textareaClassName}
              value={archiveText}
              onChange={(event) => setArchiveText(event.target.value)}
              placeholder="记录活动过程与成果..."
            />
          </Field>
          <FileUploadField
            label="图片资料"
            scene="joint_activity_archive"
            values={archiveFiles}
            onValuesChange={setArchiveFiles}
            multiple
            accept="image/jpeg,image/png,image/webp"
            hint="文字或图片至少提交一项。"
          />
          <div className="flex flex-wrap gap-2">
            <SecondaryButton type="button" onClick={saveArchive} disabled={busy}>
              <FileText size={16} /> 保存档案
            </SecondaryButton>
            <PrimaryButton type="button" onClick={submitFinal} loading={busy}>
              <Save size={16} /> 提交终审
            </PrimaryButton>
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs font-medium text-slate-400">
        <span>{activity.participations.length} 个校内社团参与</span>
        {activity.final_status === "approved" && <span>终审 {activity.final_score} 分</span>}
        {activity.preliminary_status === "approved" && (
          <Link to={`/joint-activities/${activity.id}`} className="text-primary-600">
            公开详情
          </Link>
        )}
      </div>
    </div>
  );
}
