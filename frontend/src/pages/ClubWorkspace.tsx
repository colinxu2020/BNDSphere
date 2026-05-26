import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import {
  Activity,
  ArrowLeft,
  Award,
  ClipboardList,
  FileCheck2,
  Hash,
  RefreshCw,
  Save,
  Search,
  Sparkles,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { client } from '../api/client';
import type { components } from '../api/schema';
import {
  AUDIT_STATUS_MAP,
  CATEGORY_MAP,
  PARTICIPATION_MAP,
  PARTICIPATION_OPTIONS,
  STAR_LEVEL_MAP,
} from '../lib/labels';
import {
  formatDateTime,
  fromDateTimeLocalValue,
  nullableNumber,
  nullableText,
  stringifyBackendValue,
  toNumberOrZero,
} from '../lib/format';
import {
  Badge,
  EmptyState,
  Field,
  InlineError,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  SectionTitle,
  StatusMessage,
  Surface,
  inputClassName,
  selectClassName,
  textareaClassName,
} from '../components/ui/AppPrimitives';
import { FileUploadField } from '../components/ui/FileUploadField';

type Club = components['schemas']['ClubInfo'];
type ClubActivity = components['schemas']['ClubActivityInfo'];
type ClubGeneralActivity = components['schemas']['ClubGeneralActivityInfo'];
type StarApplication = components['schemas']['StarLevelApplicationInfo'];
type StarRating = components['schemas']['StarRatingResponse'];
type ParticipationType = components['schemas']['ParticipationTypeEnum'];

export function ClubWorkspace() {
  const { id } = useParams<{ id: string }>();
  const clubId = Number(id);

  const [club, setClub] = useState<Club | null>(null);
  const [activities, setActivities] = useState<ClubActivity[]>([]);
  const [records, setRecords] = useState<ClubGeneralActivity[]>([]);
  const [starApplications, setStarApplications] = useState<StarApplication[]>([]);
  const [starRating, setStarRating] = useState<StarRating | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadErrors, setLoadErrors] = useState<Record<string, unknown>>({});

  const [clubSummary, setClubSummary] = useState('');
  const [clubDescription, setClubDescription] = useState('');
  const [clubLogo, setClubLogo] = useState('');
  const [clubMessage, setClubMessage] = useState<unknown>(null);
  const [clubTone, setClubTone] = useState<'error' | 'success'>('error');
  const [isClubSubmitting, setIsClubSubmitting] = useState(false);

  const [activityName, setActivityName] = useState('');
  const [activityDescription, setActivityDescription] = useState('');
  const [activityStart, setActivityStart] = useState('');
  const [activityEnd, setActivityEnd] = useState('');
  const [activityLocation, setActivityLocation] = useState('');
  const [activityCreateMessage, setActivityCreateMessage] = useState<unknown>(null);
  const [activityCreateTone, setActivityCreateTone] = useState<'error' | 'success'>('error');
  const [isActivityCreating, setIsActivityCreating] = useState(false);

  const [updateActivityId, setUpdateActivityId] = useState('');
  const [updateActivityName, setUpdateActivityName] = useState('');
  const [updateActivityDescription, setUpdateActivityDescription] = useState('');
  const [updateActivityStart, setUpdateActivityStart] = useState('');
  const [updateActivityEnd, setUpdateActivityEnd] = useState('');
  const [updateActivityLocation, setUpdateActivityLocation] = useState('');
  const [updateActivityPictureUrls, setUpdateActivityPictureUrls] = useState<string[]>([]);
  const [activityUpdateMessage, setActivityUpdateMessage] = useState<unknown>(null);
  const [activityUpdateTone, setActivityUpdateTone] = useState<'error' | 'success'>('error');
  const [isActivityUpdating, setIsActivityUpdating] = useState(false);

  const [generalActivityId, setGeneralActivityId] = useState('');
  const [participationType, setParticipationType] = useState<ParticipationType>('participate_only');
  const [requestedScore, setRequestedScore] = useState('');
  const [proofFileUrls, setProofFileUrls] = useState<string[]>([]);
  const [recordMessage, setRecordMessage] = useState<unknown>(null);
  const [recordTone, setRecordTone] = useState<'error' | 'success'>('error');
  const [isRecordSubmitting, setIsRecordSubmitting] = useState(false);

  const [starAttachment, setStarAttachment] = useState('');
  const [starScore, setStarScore] = useState('');
  const [starStatement, setStarStatement] = useState('');
  const [starCreateMessage, setStarCreateMessage] = useState<unknown>(null);
  const [starCreateTone, setStarCreateTone] = useState<'error' | 'success'>('error');
  const [isStarCreating, setIsStarCreating] = useState(false);

  const [starLookupId, setStarLookupId] = useState('');
  const [starUpdateId, setStarUpdateId] = useState('');
  const [starUpdateAttachment, setStarUpdateAttachment] = useState('');
  const [starUpdateScore, setStarUpdateScore] = useState('');
  const [starUpdateStatement, setStarUpdateStatement] = useState('');
  const [starLookupMessage, setStarLookupMessage] = useState<unknown>(null);
  const [starUpdateTone, setStarUpdateTone] = useState<'error' | 'success'>('error');
  const [isStarUpdating, setIsStarUpdating] = useState(false);

  const refresh = async () => {
    setIsLoading(true);
    const errors: Record<string, unknown> = {};

    const clubResponse = await client.GET('/api/v1/clubs/{club_id}', {
      params: { path: { club_id: clubId } },
    });
    if (clubResponse.error) {
      errors.club = clubResponse.error;
      setClub(null);
    } else {
      const nextClub = clubResponse.data || null;
      setClub(nextClub);
      if (nextClub) {
        setClubSummary(nextClub.summary || '');
        setClubDescription(nextClub.description || '');
        setClubLogo(nextClub.logo_uri || '');
      }
    }

    const activitiesResponse = await client.GET('/api/v1/clubs/{club_id}/activities/', {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (activitiesResponse.error) {
      errors.activities = activitiesResponse.error;
      setActivities([]);
    } else {
      setActivities(activitiesResponse.data?.items || []);
    }

    const recordsResponse = await client.GET('/api/v1/clubs/{club_id}/general-activities/', {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (recordsResponse.error) {
      errors.records = recordsResponse.error;
      setRecords([]);
    } else {
      setRecords(recordsResponse.data?.items || []);
    }

    const applicationsResponse = await client.GET('/api/v1/clubs/{club_id}/star-level/', {
      params: { path: { club_id: clubId }, query: { size: 50 } },
    });
    if (applicationsResponse.error) {
      errors.starApplications = applicationsResponse.error;
      setStarApplications([]);
    } else {
      setStarApplications(applicationsResponse.data?.items || []);
    }

    const ratingResponse = await client.GET('/api/v1/clubs/{club_id}/star-rating/', {
      params: { path: { club_id: clubId } },
    });
    if (ratingResponse.error) {
      errors.starRating = ratingResponse.error;
      setStarRating(null);
    } else {
      setStarRating(ratingResponse.data || null);
    }

    setLoadErrors(errors);
    setIsLoading(false);
  };

  useEffect(() => {
    refresh().catch(error => {
      setLoadErrors({ workspace: error });
      setIsLoading(false);
    });
  }, [clubId]);

  const submitClubUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsClubSubmitting(true);
    setClubMessage(null);
    try {
      const { data, error } = await client.POST('/api/v1/clubs/{club_id}/update-requests', {
        params: { path: { club_id: clubId } },
        body: {
          summary: nullableText(clubSummary),
          description: nullableText(clubDescription),
          logo_uri: nullableText(clubLogo),
        },
      });
      if (error) {
        setClubTone('error');
        setClubMessage(error);
      } else {
        setClubTone('success');
        setClubMessage(data);
      }
    } catch (error) {
      setClubTone('error');
      setClubMessage(error);
    } finally {
      setIsClubSubmitting(false);
    }
  };

  const submitActivityCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsActivityCreating(true);
    setActivityCreateMessage(null);
    try {
      const { data, error } = await client.POST('/api/v1/clubs/{club_id}/activities/create-requests', {
        params: { path: { club_id: clubId } },
        body: {
          name: activityName,
          description: activityDescription,
          start_time: fromDateTimeLocalValue(activityStart),
          end_time: fromDateTimeLocalValue(activityEnd),
          location: activityLocation,
        },
      });
      if (error) {
        setActivityCreateTone('error');
        setActivityCreateMessage(error);
      } else {
        setActivityCreateTone('success');
        setActivityCreateMessage(data);
      }
    } catch (error) {
      setActivityCreateTone('error');
      setActivityCreateMessage(error);
    } finally {
      setIsActivityCreating(false);
    }
  };

  const submitActivityUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsActivityUpdating(true);
    setActivityUpdateMessage(null);
    try {
      const { data, error } = await client.POST('/api/v1/clubs/{club_id}/activities/update-requests/{activity_id}', {
        params: { path: { club_id: clubId, activity_id: Number(updateActivityId) } },
        body: {
          name: nullableText(updateActivityName),
          description: nullableText(updateActivityDescription),
          start_time: updateActivityStart ? fromDateTimeLocalValue(updateActivityStart) : null,
          end_time: updateActivityEnd ? fromDateTimeLocalValue(updateActivityEnd) : null,
          location: nullableText(updateActivityLocation),
          picture_urls: updateActivityPictureUrls.length ? updateActivityPictureUrls : null,
        },
      });
      if (error) {
        setActivityUpdateTone('error');
        setActivityUpdateMessage(error);
      } else {
        setActivityUpdateTone('success');
        setActivityUpdateMessage(data);
      }
    } catch (error) {
      setActivityUpdateTone('error');
      setActivityUpdateMessage(error);
    } finally {
      setIsActivityUpdating(false);
    }
  };

  const submitRecord = async (mode: 'create' | 'update') => {
    setIsRecordSubmitting(true);
    setRecordMessage(null);
    const payload = {
      activity_id: toNumberOrZero(generalActivityId),
      participation_type: participationType,
      proof_files: proofFileUrls.length ? proofFileUrls : null,
      requested_score: toNumberOrZero(requestedScore),
    };

    try {
      const request =
        mode === 'create'
          ? client.POST('/api/v1/clubs/{club_id}/general-activities/', {
              params: { path: { club_id: clubId } },
              body: payload,
            })
          : client.PATCH('/api/v1/clubs/{club_id}/general-activities/', {
              params: { path: { club_id: clubId } },
              body: payload,
            });

      const { data, error } = await request;
      if (error) {
        setRecordTone('error');
        setRecordMessage(error);
      } else {
        setRecordTone('success');
        setRecordMessage(data);
        refresh();
      }
    } catch (error) {
      setRecordTone('error');
      setRecordMessage(error);
    } finally {
      setIsRecordSubmitting(false);
    }
  };

  const submitStarCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarCreating(true);
    setStarCreateMessage(null);
    try {
      const { data, error } = await client.POST('/api/v1/clubs/{club_id}/star-level/', {
        params: { path: { club_id: clubId } },
        body: {
          contest_attachment: nullableText(starAttachment),
          requested_contest_score: nullableNumber(starScore),
          uniqueness_statement: nullableText(starStatement),
        },
      });
      if (error) {
        setStarCreateTone('error');
        setStarCreateMessage(error);
      } else {
        setStarCreateTone('success');
        setStarCreateMessage(data);
        refresh();
      }
    } catch (error) {
      setStarCreateTone('error');
      setStarCreateMessage(error);
    } finally {
      setIsStarCreating(false);
    }
  };

  const lookupStarApplication = async () => {
    setStarLookupMessage(null);
    try {
      const { data, error } = await client.GET('/api/v1/star-level/{star_level_id}', {
        params: { path: { star_level_id: Number(starLookupId) } },
      });
      if (error) {
        setStarUpdateTone('error');
        setStarLookupMessage(error);
      } else if (data) {
        setStarUpdateTone('success');
        setStarLookupMessage(data);
        setStarUpdateId(String(data.id));
        setStarUpdateAttachment(data.contest_attachment || '');
        setStarUpdateScore(data.requested_contest_score == null ? '' : String(data.requested_contest_score));
        setStarUpdateStatement(data.uniqueness_statement || '');
      }
    } catch (error) {
      setStarUpdateTone('error');
      setStarLookupMessage(error);
    }
  };

  const submitStarUpdate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsStarUpdating(true);
    setStarLookupMessage(null);
    try {
      const { data, error } = await client.PATCH('/api/v1/star-level/{star_level_id}', {
        params: { path: { star_level_id: Number(starUpdateId) } },
        body: {
          contest_attachment: nullableText(starUpdateAttachment),
          requested_contest_score: nullableNumber(starUpdateScore),
          uniqueness_statement: nullableText(starUpdateStatement),
        },
      });
      if (error) {
        setStarUpdateTone('error');
        setStarLookupMessage(error);
      } else {
        setStarUpdateTone('success');
        setStarLookupMessage(data);
        refresh();
      }
    } catch (error) {
      setStarUpdateTone('error');
      setStarLookupMessage(error);
    } finally {
      setIsStarUpdating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <Link to={`/club/${clubId}`} className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 font-medium w-fit transition-colors">
        <ArrowLeft size={18} /> 返回社团
      </Link>

      <PageHeader
        eyebrow="Workspace"
        title={club?.name || `社团 #${clubId} 工作台`}
        description="这里集中处理社团资料、活动、综评记录和星级相关申请。"
        action={
          <SecondaryButton onClick={() => refresh()} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {isLoading ? (
        <div className="animate-pulse bg-white rounded-[2rem] h-72 border border-slate-100" />
      ) : (
        <>
          {Object.keys(loadErrors).length > 0 && (
            <Surface>
              <SectionTitle title="加载反馈" description="以下内容直接来自后端响应。" />
              <div className="grid gap-3">
                {Object.entries(loadErrors).map(([key, value]) => (
                  <div key={key}>
                    <InlineError value={`${key}: ${stringifyBackendValue(value)}`} />
                  </div>
                ))}
              </div>
            </Surface>
          )}

          {club && (
            <Surface>
              <div className="flex flex-col md:flex-row md:items-center gap-5">
                <div className="w-20 h-20 rounded-2xl bg-slate-100 flex items-center justify-center shrink-0 overflow-hidden border border-slate-200">
                  {club.logo_uri ? (
                    <img src={club.logo_uri} alt={club.name} className="w-full h-full object-cover" />
                  ) : (
                    <Hash className="text-slate-400" size={30} />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex flex-wrap gap-2 mb-2">
                    <Badge tone="primary">{CATEGORY_MAP[club.category]}</Badge>
                    <Badge tone="yellow">{STAR_LEVEL_MAP[club.star_level]}</Badge>
                  </div>
                  <h2 className="text-2xl font-display font-bold text-slate-900">{club.name}</h2>
                  <p className="text-slate-500 mt-1">{club.summary}</p>
                </div>
              </div>
            </Surface>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Surface>
              <SectionTitle icon={<Save size={20} />} title="社团资料变更申请" />
              <form onSubmit={submitClubUpdate} className="flex flex-col gap-4">
                <Field label="简介">
                  <input className={inputClassName} value={clubSummary} onChange={event => setClubSummary(event.target.value)} />
                </Field>
                <Field label="详细介绍">
                  <textarea className={textareaClassName} value={clubDescription} onChange={event => setClubDescription(event.target.value)} />
                </Field>
                <FileUploadField
                  label="Logo"
                  scene="club_logo"
                  value={clubLogo}
                  onChange={setClubLogo}
                  accept="image/*"
                  hint="上传后作为社团资料变更申请的 Logo。"
                />
                <StatusMessage value={clubMessage} tone={clubTone} />
                <PrimaryButton type="submit" loading={isClubSubmitting}>提交变更申请</PrimaryButton>
              </form>
            </Surface>

            <Surface>
              <SectionTitle icon={<Activity size={20} />} title="创建社团活动申请" />
              <form onSubmit={submitActivityCreate} className="flex flex-col gap-4">
                <Field label="活动名称">
                  <input className={inputClassName} value={activityName} onChange={event => setActivityName(event.target.value)} required />
                </Field>
                <Field label="活动描述">
                  <textarea className={textareaClassName} value={activityDescription} onChange={event => setActivityDescription(event.target.value)} required />
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="开始时间">
                    <input className={inputClassName} type="datetime-local" value={activityStart} onChange={event => setActivityStart(event.target.value)} required />
                  </Field>
                  <Field label="结束时间">
                    <input className={inputClassName} type="datetime-local" value={activityEnd} onChange={event => setActivityEnd(event.target.value)} required />
                  </Field>
                </div>
                <Field label="地点">
                  <input className={inputClassName} value={activityLocation} onChange={event => setActivityLocation(event.target.value)} required />
                </Field>
                <StatusMessage value={activityCreateMessage} tone={activityCreateTone} />
                <PrimaryButton type="submit" loading={isActivityCreating}>提交活动申请</PrimaryButton>
              </form>
            </Surface>
          </div>

          <Surface>
            <SectionTitle icon={<ClipboardList size={20} />} title="已创建活动" description="来自社团活动列表接口。" />
            {activities.length ? (
              <div className="grid gap-4">
                {activities.map(activityItem => (
                  <div key={activityItem.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div>
                        <h3 className="font-semibold text-slate-900">{activityItem.name}</h3>
                        <p className="text-sm text-slate-500 mt-1 line-clamp-2">{activityItem.description}</p>
                        <p className="text-xs text-slate-400 font-medium mt-2">
                          #{activityItem.id} · {formatDateTime(activityItem.start_time)} · {activityItem.location}
                        </p>
                      </div>
                      <button
                        onClick={() => setUpdateActivityId(String(activityItem.id))}
                        className="text-sm font-semibold text-primary-600 hover:text-primary-700"
                      >
                        填入修改
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无社团活动" />
            )}
          </Surface>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Surface>
              <SectionTitle icon={<Activity size={20} />} title="修改社团活动申请" />
              <form onSubmit={submitActivityUpdate} className="flex flex-col gap-4">
                <Field label="活动 ID">
                  <input className={inputClassName} value={updateActivityId} onChange={event => setUpdateActivityId(event.target.value)} required />
                </Field>
                <Field label="新名称">
                  <input className={inputClassName} value={updateActivityName} onChange={event => setUpdateActivityName(event.target.value)} />
                </Field>
                <Field label="新描述">
                  <textarea className={textareaClassName} value={updateActivityDescription} onChange={event => setUpdateActivityDescription(event.target.value)} />
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="新开始时间">
                    <input className={inputClassName} type="datetime-local" value={updateActivityStart} onChange={event => setUpdateActivityStart(event.target.value)} />
                  </Field>
                  <Field label="新结束时间">
                    <input className={inputClassName} type="datetime-local" value={updateActivityEnd} onChange={event => setUpdateActivityEnd(event.target.value)} />
                  </Field>
                </div>
                <Field label="新地点">
                  <input className={inputClassName} value={updateActivityLocation} onChange={event => setUpdateActivityLocation(event.target.value)} />
                </Field>
                <FileUploadField
                  label="活动图片"
                  scene="application_file"
                  values={updateActivityPictureUrls}
                  onValuesChange={setUpdateActivityPictureUrls}
                  multiple
                  accept="image/*"
                  hint="可一次选择多个图片文件。"
                />
                <StatusMessage value={activityUpdateMessage} tone={activityUpdateTone} />
                <PrimaryButton type="submit" loading={isActivityUpdating}>提交修改申请</PrimaryButton>
              </form>
            </Surface>

            <Surface>
              <SectionTitle icon={<FileCheck2 size={20} />} title="综评活动记录" />
              <form
                onSubmit={event => {
                  event.preventDefault();
                  submitRecord('create');
                }}
                className="flex flex-col gap-4"
              >
                <Field label="综评活动 ID">
                  <input className={inputClassName} value={generalActivityId} onChange={event => setGeneralActivityId(event.target.value)} required />
                </Field>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Field label="参与类型">
                    <select className={selectClassName} value={participationType} onChange={event => setParticipationType(event.target.value as ParticipationType)}>
                      {PARTICIPATION_OPTIONS.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="申请分值">
                    <input className={inputClassName} type="number" value={requestedScore} onChange={event => setRequestedScore(event.target.value)} required />
                  </Field>
                </div>
                <FileUploadField
                  label="证明材料"
                  scene="application_file"
                  values={proofFileUrls}
                  onValuesChange={setProofFileUrls}
                  multiple
                  hint="可上传多个证明材料文件。"
                />
                <StatusMessage value={recordMessage} tone={recordTone} />
                <div className="flex flex-col sm:flex-row gap-3">
                  <PrimaryButton type="submit" loading={isRecordSubmitting}>创建记录</PrimaryButton>
                  <SecondaryButton type="button" onClick={() => submitRecord('update')} disabled={isRecordSubmitting}>
                    更新记录
                  </SecondaryButton>
                </div>
              </form>
            </Surface>
          </div>

          <Surface>
            <SectionTitle icon={<FileCheck2 size={20} />} title="已提交综评记录" />
            {records.length ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {records.map(record => (
                  <div key={record.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone={record.audit_status === 'approved' ? 'green' : record.audit_status === 'rejected' ? 'red' : 'yellow'}>
                        {AUDIT_STATUS_MAP[record.audit_status]}
                      </Badge>
                      <Badge>{PARTICIPATION_MAP[record.participation_type]}</Badge>
                    </div>
                    <h3 className="font-semibold text-slate-900 mt-3">记录 #{record.id}</h3>
                    <p className="text-sm text-slate-500 mt-1">
                      活动 #{record.activity_id}，申请 {record.requested_score} 分
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无综评记录" />
            )}
          </Surface>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Surface>
              <SectionTitle icon={<Sparkles size={20} />} title="星级评分" />
              {starRating ? (
                <div className="flex flex-col gap-5">
                  <div className="rounded-[2rem] bg-slate-900 text-white p-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-48 h-48 bg-primary-500 rounded-full blur-[80px] opacity-30 -mr-16 -mt-16" />
                    <div className="relative z-10">
                      <p className="text-sm text-slate-400 font-medium">当前总分</p>
                      <p className="text-5xl font-display font-bold mt-2">{starRating.total_score}</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <Badge tone="primary">会议出勤 {starRating.breakdown.meeting_attendance}</Badge>
                    <Badge tone="primary">活动参与 {starRating.breakdown.activity_participation}</Badge>
                    <Badge tone="primary">内部活动 {starRating.breakdown.internal_activities}</Badge>
                    <Badge tone="primary">社团历史 {starRating.breakdown.club_history}</Badge>
                  </div>
                  <p className="text-sm text-slate-500">
                    内部活动 {starRating.internal_activity_count} 次，社团年限 {starRating.club_age_years} 年。
                  </p>
                </div>
              ) : (
                <EmptyState title="暂无星级评分" />
              )}
            </Surface>

            <Surface>
              <SectionTitle icon={<Award size={20} />} title="创建星级申请" />
              <form onSubmit={submitStarCreate} className="flex flex-col gap-4">
                <FileUploadField
                  label="竞赛附件"
                  scene="application_file"
                  value={starAttachment}
                  onChange={setStarAttachment}
                  hint="上传后作为星级申请附件。"
                />
                <Field label="申请竞赛分">
                  <input className={inputClassName} type="number" value={starScore} onChange={event => setStarScore(event.target.value)} />
                </Field>
                <Field label="独特性说明">
                  <textarea className={textareaClassName} value={starStatement} onChange={event => setStarStatement(event.target.value)} />
                </Field>
                <StatusMessage value={starCreateMessage} tone={starCreateTone} />
                <PrimaryButton type="submit" loading={isStarCreating}>提交星级申请</PrimaryButton>
              </form>
            </Surface>
          </div>

          <Surface>
            <SectionTitle icon={<Award size={20} />} title="星级申请列表" />
            {starApplications.length ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {starApplications.map(application => (
                  <div key={application.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                    <div className="flex flex-wrap gap-2">
                      <Badge tone={application.audit_status === 'approved' ? 'green' : application.audit_status === 'rejected' ? 'red' : 'yellow'}>
                        {application.audit_status ? AUDIT_STATUS_MAP[application.audit_status] : '未审核'}
                      </Badge>
                      {application.approved_level && <Badge tone="primary">{STAR_LEVEL_MAP[application.approved_level]}</Badge>}
                    </div>
                    <h3 className="font-semibold text-slate-900 mt-3">申请 #{application.id}</h3>
                    <p className="text-sm text-slate-500 mt-1">
                      申请竞赛分 {application.requested_contest_score ?? '未填'}，核定分 {application.approved_score ?? '未定'}
                    </p>
                    <button
                      onClick={() => {
                        setStarLookupId(String(application.id));
                        setStarUpdateId(String(application.id));
                        setStarUpdateAttachment(application.contest_attachment || '');
                        setStarUpdateScore(application.requested_contest_score == null ? '' : String(application.requested_contest_score));
                        setStarUpdateStatement(application.uniqueness_statement || '');
                      }}
                      className="text-sm font-semibold text-primary-600 hover:text-primary-700 mt-3"
                    >
                      填入修改
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无星级申请" />
            )}
          </Surface>

          <Surface>
            <SectionTitle icon={<Search size={20} />} title="查询或更新星级申请" />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="flex flex-col gap-4">
                <Field label="申请 ID">
                  <input className={inputClassName} value={starLookupId} onChange={event => setStarLookupId(event.target.value)} />
                </Field>
                <SecondaryButton type="button" onClick={lookupStarApplication}>
                  查询申请
                </SecondaryButton>
                <StatusMessage value={starLookupMessage} tone={starUpdateTone} />
              </div>
              <form onSubmit={submitStarUpdate} className="flex flex-col gap-4">
                <Field label="更新申请 ID">
                  <input className={inputClassName} value={starUpdateId} onChange={event => setStarUpdateId(event.target.value)} required />
                </Field>
                <FileUploadField
                  label="竞赛附件"
                  scene="application_file"
                  value={starUpdateAttachment}
                  onChange={setStarUpdateAttachment}
                  hint="上传后替换星级申请附件。"
                />
                <Field label="申请竞赛分">
                  <input className={inputClassName} type="number" value={starUpdateScore} onChange={event => setStarUpdateScore(event.target.value)} />
                </Field>
                <Field label="独特性说明">
                  <textarea className={textareaClassName} value={starUpdateStatement} onChange={event => setStarUpdateStatement(event.target.value)} />
                </Field>
                <PrimaryButton type="submit" loading={isStarUpdating}>更新申请</PrimaryButton>
              </form>
            </div>
          </Surface>
        </>
      )}
    </motion.div>
  );
}
