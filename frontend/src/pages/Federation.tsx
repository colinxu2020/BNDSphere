import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Activity, RefreshCw, Save, ShieldCheck, Trash2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { client } from '../api/client';
import type { components } from '../api/schema';
import {
  ACTIVITY_LEVEL_MAP,
  ACTIVITY_LEVEL_OPTIONS,
  AUDIT_STATUS_OPTIONS,
} from '../lib/labels';
import { formatDate, nullableText, nullableNumber } from '../lib/format';
import {
  Badge,
  DangerButton,
  EmptyState,
  Field,
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

type GeneralActivity = components['schemas']['GeneralActivityInfo'];
type ActivityLevel = components['schemas']['GeneralActivityLevelEnum'];
type AuditStatus = components['schemas']['AuditStatusEnum'];

export function Federation() {
  const [activities, setActivities] = useState<GeneralActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<unknown>(null);
  const [message, setMessage] = useState<unknown>(null);
  const [messageTone, setMessageTone] = useState<'error' | 'success'>('error');

  const [activityName, setActivityName] = useState('');
  const [activityDescription, setActivityDescription] = useState('');
  const [activityLevel, setActivityLevel] = useState<ActivityLevel>('club_federation');
  const [isCreating, setIsCreating] = useState(false);

  const [editActivityId, setEditActivityId] = useState('');
  const [editActivityName, setEditActivityName] = useState('');
  const [editActivityDescription, setEditActivityDescription] = useState('');
  const [editActivityLevel, setEditActivityLevel] = useState<ActivityLevel | ''>('');
  const [isEditing, setIsEditing] = useState(false);

  const [recordId, setRecordId] = useState('');
  const [recordStatus, setRecordStatus] = useState<AuditStatus>('pending');
  const [recordScore, setRecordScore] = useState('');
  const [isRecordUpdating, setIsRecordUpdating] = useState(false);

  const fetchActivities = async () => {
    setIsLoading(true);
    setLoadError(null);
    try {
      const { data, error } = await client.GET('/api/v1/general-activities/', {
        params: { query: { size: 50 } },
      });
      if (error) {
        setLoadError(error);
        setActivities([]);
      } else {
        setActivities(data?.items || []);
      }
    } catch (error) {
      setLoadError(error);
      setActivities([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchActivities();
  }, []);

  const setResult = (error: unknown, data: unknown) => {
    if (error) {
      setMessageTone('error');
      setMessage(error);
    } else {
      setMessageTone('success');
      setMessage(data);
    }
  };

  const createActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsCreating(true);
    setMessage(null);
    try {
      const { data, error } = await client.POST('/api/v1/club-federation/general-activity/', {
        body: {
          name: activityName,
          description: activityDescription,
          level: activityLevel,
        },
      });
      setResult(error, data);
      if (!error) fetchActivities();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsCreating(false);
    }
  };

  const updateActivity = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsEditing(true);
    setMessage(null);
    try {
      const { data, error } = await client.PATCH('/api/v1/club-federation/general-activity/{activity_id}', {
        params: { path: { activity_id: Number(editActivityId) } },
        body: {
          name: nullableText(editActivityName),
          description: nullableText(editActivityDescription),
          level: editActivityLevel || null,
        },
      });
      setResult(error, data);
      if (!error) fetchActivities();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsEditing(false);
    }
  };

  const deleteActivity = async (activityId: number) => {
    if (!window.confirm(`确认删除活动 #${activityId}？`)) return;
    setMessage(null);
    try {
      const { data, error } = await client.DELETE('/api/v1/club-federation/general-activity/{activity_id}', {
        params: { path: { activity_id: activityId } },
      });
      setResult(error, data);
      if (!error) fetchActivities();
    } catch (error) {
      setResult(error, null);
    }
  };

  const updateRecord = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsRecordUpdating(true);
    setMessage(null);
    try {
      const { data, error } = await client.PATCH('/api/v1/club-federation/general-activity/club-records/{record_id}', {
        params: { path: { record_id: Number(recordId) } },
        body: {
          audit_status: recordStatus,
          final_score: nullableNumber(recordScore),
        },
      });
      setResult(error, data);
      if (!error) fetchActivities();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsRecordUpdating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <PageHeader
        eyebrow="Federation"
        title="社联工作台"
        description="维护综评活动，并审核社团提交的活动记录。"
        action={
          <SecondaryButton type="button" onClick={fetchActivities} disabled={isLoading}>
            <RefreshCw size={16} /> 刷新
          </SecondaryButton>
        }
      />

      {message && <StatusMessage value={message} tone={messageTone} />}
      {loadError && <StatusMessage value={loadError} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Surface>
          <SectionTitle icon={<Activity size={20} />} title="创建综评活动" />
          <form onSubmit={createActivity} className="flex flex-col gap-4">
            <Field label="活动名称">
              <input className={inputClassName} value={activityName} onChange={event => setActivityName(event.target.value)} required />
            </Field>
            <Field label="活动层级">
              <select className={selectClassName} value={activityLevel} onChange={event => setActivityLevel(event.target.value as ActivityLevel)}>
                {ACTIVITY_LEVEL_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </Field>
            <Field label="活动描述">
              <textarea className={textareaClassName} value={activityDescription} onChange={event => setActivityDescription(event.target.value)} required />
            </Field>
            <PrimaryButton type="submit" loading={isCreating}>
              <Save size={18} /> 创建活动
            </PrimaryButton>
          </form>
        </Surface>

        <Surface>
          <SectionTitle icon={<ShieldCheck size={20} />} title="审核社团记录" />
          <form onSubmit={updateRecord} className="flex flex-col gap-4">
            <Field label="记录 ID">
              <input className={inputClassName} value={recordId} onChange={event => setRecordId(event.target.value)} required />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="审核状态">
                <select className={selectClassName} value={recordStatus} onChange={event => setRecordStatus(event.target.value as AuditStatus)}>
                  {AUDIT_STATUS_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </Field>
              <Field label="最终分值">
                <input className={inputClassName} type="number" value={recordScore} onChange={event => setRecordScore(event.target.value)} />
              </Field>
            </div>
            <PrimaryButton type="submit" loading={isRecordUpdating}>
              <Save size={18} /> 更新记录
            </PrimaryButton>
          </form>
        </Surface>
      </div>

      <Surface>
        <SectionTitle icon={<Activity size={20} />} title="活动维护" />
        <form onSubmit={updateActivity} className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <Field label="活动 ID">
            <input className={inputClassName} value={editActivityId} onChange={event => setEditActivityId(event.target.value)} required />
          </Field>
          <Field label="活动层级">
            <select className={selectClassName} value={editActivityLevel} onChange={event => setEditActivityLevel(event.target.value as ActivityLevel | '')}>
              <option value="">不修改</option>
              {ACTIVITY_LEVEL_OPTIONS.map(option => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </Field>
          <Field label="活动名称">
            <input className={inputClassName} value={editActivityName} onChange={event => setEditActivityName(event.target.value)} />
          </Field>
          <Field label="活动描述">
            <textarea className={textareaClassName} value={editActivityDescription} onChange={event => setEditActivityDescription(event.target.value)} />
          </Field>
          <div className="md:col-span-2 flex justify-end">
            <PrimaryButton type="submit" loading={isEditing}>更新活动</PrimaryButton>
          </div>
        </form>

        {isLoading ? (
          <div className="grid gap-4">
            {[...Array(3)].map((_, index) => (
              <div key={index} className="animate-pulse bg-slate-50 h-36 rounded-2xl border border-slate-100" />
            ))}
          </div>
        ) : activities.length ? (
          <div className="grid gap-4">
            {activities.map(activityItem => (
              <div key={activityItem.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div>
                    <div className="flex flex-wrap gap-2">
                      <Badge tone="primary">{ACTIVITY_LEVEL_MAP[activityItem.level]}</Badge>
                      <Badge>{activityItem.club_records?.length || 0} 条记录</Badge>
                    </div>
                    <h3 className="font-semibold text-slate-900 mt-3">{activityItem.name}</h3>
                    <p className="text-sm text-slate-500 mt-1 line-clamp-2">{activityItem.description}</p>
                    <p className="text-xs text-slate-400 font-medium mt-2">#{activityItem.id} · {formatDate(activityItem.created_at)}</p>
                  </div>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    <SecondaryButton
                      type="button"
                      onClick={() => {
                        setEditActivityId(String(activityItem.id));
                        setEditActivityName(activityItem.name);
                        setEditActivityDescription(activityItem.description);
                        setEditActivityLevel(activityItem.level);
                      }}
                    >
                      载入
                    </SecondaryButton>
                    <Link
                      to={`/activities/${activityItem.id}`}
                      className="inline-flex items-center justify-center px-4 py-2.5 bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-semibold rounded-xl transition-all"
                    >
                      详情
                    </Link>
                    <DangerButton type="button" onClick={() => deleteActivity(activityItem.id)}>
                      <Trash2 size={16} /> 删除
                    </DangerButton>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="暂无综评活动" />
        )}
      </Surface>
    </motion.div>
  );
}
