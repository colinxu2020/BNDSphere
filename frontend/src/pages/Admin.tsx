import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { CalendarDays, HeartPulse, RefreshCw, Save, Shield, Users } from 'lucide-react';
import { client } from '../api/client';
import type { components } from '../api/schema';
import { adminGetClub, adminUpdateClub } from '../api/admin';
import {
  CLUB_STATUS_OPTIONS,
  ROLE_OPTIONS,
  STAR_LEVEL_OPTIONS,
} from '../lib/labels';
import { formatDate } from '../lib/format';
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
import { FileUploadField } from '../components/ui/FileUploadField';

type AcademicTerm = components['schemas']['AcademicTermInfo'];
type Role = components['schemas']['RoleEnum'];
type ClubStarLevel = components['schemas']['ClubStarLevelEnum'];
type ClubStatus = components['schemas']['ClubStatusEnum'];
type AdminUserUpdate = components['schemas']['AdminUserUpdate'];
type AdminClubUpdate = components['schemas']['AdminClubUpdate'];
type AcademicTermUpdate = components['schemas']['AcademicTermUpdate'];

export function Admin() {
  const [terms, setTerms] = useState<AcademicTerm[]>([]);
  const [isTermsLoading, setIsTermsLoading] = useState(true);
  const [termsError, setTermsError] = useState<unknown>(null);
  const [actionMessage, setActionMessage] = useState<unknown>(null);
  const [actionTone, setActionTone] = useState<'error' | 'success' | 'info'>('error');

  const [userId, setUserId] = useState('');
  const [userUsername, setUserUsername] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const [userAvatar, setUserAvatar] = useState('');
  const [userDescription, setUserDescription] = useState('');
  const [userRole, setUserRole] = useState<Role | ''>('');
  const [isUserSubmitting, setIsUserSubmitting] = useState(false);

  const [clubId, setClubId] = useState('');
  const [clubSummary, setClubSummary] = useState('');
  const [clubDescription, setClubDescription] = useState('');
  const [clubLogo, setClubLogo] = useState('');
  const [clubStarLevel, setClubStarLevel] = useState<ClubStarLevel | ''>('');
  const [clubStatus, setClubStatus] = useState<ClubStatus | ''>('');
  const [isClubSubmitting, setIsClubSubmitting] = useState(false);
  const [isClubLoading, setIsClubLoading] = useState(false);

  const [termId, setTermId] = useState('');
  const [termName, setTermName] = useState('');
  const [termStart, setTermStart] = useState('');
  const [termEnd, setTermEnd] = useState('');
  const [termIsCurrent, setTermIsCurrent] = useState(false);
  const [isTermSubmitting, setIsTermSubmitting] = useState(false);

  const fetchTerms = async () => {
    setIsTermsLoading(true);
    setTermsError(null);
    try {
      const { data, error } = await client.GET('/api/v1/admin/academic-terms/', {
        params: { query: { size: 50 } },
      });
      if (error) {
        setTermsError(error);
        setTerms([]);
      } else {
        setTerms(data?.items || []);
      }
    } catch (error) {
      setTermsError(error);
      setTerms([]);
    } finally {
      setIsTermsLoading(false);
    }
  };

  useEffect(() => {
    fetchTerms();
  }, []);

  const setResult = (error: unknown, data: unknown) => {
    if (error) {
      setActionTone('error');
      setActionMessage(error);
    } else {
      setActionTone('success');
      setActionMessage(data);
    }
  };

  const checkHealth = async () => {
    setActionMessage(null);
    try {
      const { error, response } = await client.GET('/health');
      if (error) {
        setActionTone('error');
        setActionMessage(error);
      } else {
        setActionTone('success');
        setActionMessage(`HTTP ${response.status}`);
      }
    } catch (error) {
      setActionTone('error');
      setActionMessage(error);
    }
  };

  const submitUser = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsUserSubmitting(true);
    setActionMessage(null);

    const body: AdminUserUpdate = {};
    if (userUsername.trim()) body.username = userUsername.trim();
    if (userEmail.trim()) body.email = userEmail.trim();
    if (userAvatar.trim()) body.avatar_uri = userAvatar.trim();
    if (userDescription.trim()) body.description = userDescription.trim();
    if (userRole) body.role = userRole;

    try {
      const { data, error } = await client.PATCH('/api/v1/admin/users/{user_id}', {
        params: { path: { user_id: Number(userId) } },
        body,
      });
      setResult(error, data);
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsUserSubmitting(false);
    }
  };

  const submitClub = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsClubSubmitting(true);
    setActionMessage(null);

    const body: AdminClubUpdate = {};
    if (clubSummary.trim()) body.summary = clubSummary.trim();
    if (clubDescription.trim()) body.description = clubDescription.trim();
    if (clubLogo.trim()) body.logo_uri = clubLogo.trim();
    if (clubStarLevel) body.star_level = clubStarLevel;
    if (clubStatus) body.status = clubStatus;

    try {
      const { data, error } = await adminUpdateClub(Number(clubId), body);
      setResult(error, data);
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsClubSubmitting(false);
    }
  };

  const loadClubForAdmin = async () => {
    setIsClubLoading(true);
    setActionMessage(null);

    try {
      const data = await adminGetClub(Number(clubId));
      setActionTone('success');
      setActionMessage(data);
      setClubSummary(data.summary || '');
      setClubDescription(data.description || '');
      setClubLogo(data.logo_uri || '');
      setClubStarLevel(data.star_level || '');
      setClubStatus(data.status || '');
    } catch (error) {
      setActionTone('error');
      setActionMessage(error);
    } finally {
      setIsClubLoading(false);
    }
  };

  const submitTermCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsTermSubmitting(true);
    setActionMessage(null);
    try {
      const { data, error } = await client.POST('/api/v1/admin/academic-terms/', {
        body: {
          term_name: termName.trim() || null,
          start_date: termStart,
          end_date: termEnd,
          is_current: termIsCurrent,
        },
      });
      setResult(error, data);
      if (!error) fetchTerms();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsTermSubmitting(false);
    }
  };

  const submitTermUpdate = async () => {
    setIsTermSubmitting(true);
    setActionMessage(null);

    const body: AcademicTermUpdate = {};
    if (termName.trim()) body.term_name = termName.trim();
    if (termStart) body.start_date = termStart;
    if (termEnd) body.end_date = termEnd;

    try {
      const { data, error } = await client.PATCH('/api/v1/admin/academic-terms/{term_id}', {
        params: { path: { term_id: Number(termId) } },
        body,
      });
      setResult(error, data);
      if (!error) fetchTerms();
    } catch (error) {
      setResult(error, null);
    } finally {
      setIsTermSubmitting(false);
    }
  };

  const getTerm = async (id: number) => {
    setActionMessage(null);
    try {
      const { data, error } = await client.GET('/api/v1/admin/academic-terms/{term_id}', {
        params: { path: { term_id: id } },
      });
      setResult(error, data);
      if (data) {
        setTermId(String(data.id));
        setTermName(data.term_name);
        setTermStart(data.start_date);
        setTermEnd(data.end_date);
        setTermIsCurrent(data.is_current);
      }
    } catch (error) {
      setResult(error, null);
    }
  };

  const setCurrentTerm = async (id: number) => {
    setActionMessage(null);
    try {
      const { data, error } = await client.POST('/api/v1/admin/academic-terms/{term_id}/set-current', {
        params: { path: { term_id: id } },
      });
      setResult(error, data);
      if (!error) fetchTerms();
    } catch (error) {
      setResult(error, null);
    }
  };

  const deleteTerm = async (id: number) => {
    if (!window.confirm(`确认删除学期 #${id}？`)) return;
    setActionMessage(null);
    try {
      const { data, error } = await client.DELETE('/api/v1/admin/academic-terms/{term_id}', {
        params: { path: { term_id: id } },
      });
      setResult(error, data);
      if (!error) fetchTerms();
    } catch (error) {
      setResult(error, null);
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
        eyebrow="Admin"
        title="管理员控制台"
        description="维护用户、社团和学期基础数据。所有反馈直接显示后端返回。"
        action={
          <SecondaryButton type="button" onClick={checkHealth}>
            <HeartPulse size={16} /> 健康检查
          </SecondaryButton>
        }
      />

      {actionMessage && <StatusMessage value={actionMessage} tone={actionTone} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Surface>
          <SectionTitle icon={<Users size={20} />} title="用户维护" />
          <form onSubmit={submitUser} className="flex flex-col gap-4">
            <Field label="用户 ID">
              <input className={inputClassName} value={userId} onChange={event => setUserId(event.target.value)} required />
            </Field>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="用户名">
                <input className={inputClassName} value={userUsername} onChange={event => setUserUsername(event.target.value)} />
              </Field>
              <Field label="邮箱">
                <input className={inputClassName} type="email" value={userEmail} onChange={event => setUserEmail(event.target.value)} />
              </Field>
            </div>
            <FileUploadField
              label="头像"
              scene="avatar"
              value={userAvatar}
              onChange={setUserAvatar}
              accept="image/*"
              hint="上传后写入用户头像字段。"
            />
            <Field label="角色">
              <select className={selectClassName} value={userRole} onChange={event => setUserRole(event.target.value as Role | '')}>
                <option value="">不修改</option>
                {ROLE_OPTIONS.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </Field>
            <Field label="简介">
              <textarea className={textareaClassName} value={userDescription} onChange={event => setUserDescription(event.target.value)} />
            </Field>
            <PrimaryButton type="submit" loading={isUserSubmitting}>
              <Save size={18} /> 保存用户
            </PrimaryButton>
          </form>
        </Surface>

        <Surface>
          <SectionTitle icon={<Shield size={20} />} title="社团维护" />
          <form onSubmit={submitClub} className="flex flex-col gap-4">
            <Field label="社团 ID">
              <input className={inputClassName} value={clubId} onChange={event => setClubId(event.target.value)} required />
            </Field>
            <SecondaryButton type="button" onClick={loadClubForAdmin} disabled={!clubId || isClubLoading}>
              <RefreshCw size={16} /> {isClubLoading ? '读取中...' : '管理员读取社团'}
            </SecondaryButton>
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
              hint="使用管理员接口保存到社团 Logo 字段。"
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="星级">
                <select className={selectClassName} value={clubStarLevel} onChange={event => setClubStarLevel(event.target.value as ClubStarLevel | '')}>
                  <option value="">不修改</option>
                  {STAR_LEVEL_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </Field>
              <Field label="状态">
                <select className={selectClassName} value={clubStatus} onChange={event => setClubStatus(event.target.value as ClubStatus | '')}>
                  <option value="">不修改</option>
                  {CLUB_STATUS_OPTIONS.map(option => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
              </Field>
            </div>
            <PrimaryButton type="submit" loading={isClubSubmitting}>
              <Save size={18} /> 保存社团
            </PrimaryButton>
          </form>
        </Surface>
      </div>

      <Surface>
        <SectionTitle
          icon={<CalendarDays size={20} />}
          title="学期管理"
          description="创建、更新、删除学期，并设置当前学期。"
        />

        <form onSubmit={submitTermCreate} className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Field label="学期 ID">
            <input className={inputClassName} value={termId} onChange={event => setTermId(event.target.value)} placeholder="更新时填写" />
          </Field>
          <Field label="学期名称">
            <input className={inputClassName} value={termName} onChange={event => setTermName(event.target.value)} />
          </Field>
          <Field label="开始日期">
            <input className={inputClassName} type="date" value={termStart} onChange={event => setTermStart(event.target.value)} required />
          </Field>
          <Field label="结束日期">
            <input className={inputClassName} type="date" value={termEnd} onChange={event => setTermEnd(event.target.value)} required />
          </Field>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700 md:col-span-2">
            <input
              type="checkbox"
              checked={termIsCurrent}
              onChange={event => setTermIsCurrent(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-primary-500 focus:ring-primary-500/20"
            />
            创建时设为当前学期
          </label>
          <div className="md:col-span-2 flex flex-col sm:flex-row gap-3 sm:justify-end">
            <PrimaryButton type="submit" loading={isTermSubmitting}>创建学期</PrimaryButton>
            <SecondaryButton type="button" onClick={submitTermUpdate} disabled={isTermSubmitting || !termId}>
              更新学期
            </SecondaryButton>
          </div>
        </form>

        {termsError && <div className="mb-5"><StatusMessage value={termsError} /></div>}

        {isTermsLoading ? (
          <div className="grid gap-4">
            {[...Array(3)].map((_, index) => (
              <div key={index} className="animate-pulse bg-slate-50 h-28 rounded-2xl border border-slate-100" />
            ))}
          </div>
        ) : terms.length ? (
          <div className="grid gap-4">
            {terms.map(term => (
              <div key={term.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-slate-900">{term.term_name}</h3>
                      {term.is_current && <Badge tone="green">当前</Badge>}
                    </div>
                    <p className="text-sm text-slate-500 mt-1">
                      #{term.id} · {formatDate(term.start_date)} - {formatDate(term.end_date)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <SecondaryButton type="button" onClick={() => getTerm(term.id)}>载入</SecondaryButton>
                    <SecondaryButton type="button" onClick={() => setCurrentTerm(term.id)}>
                      <RefreshCw size={16} /> 设为当前
                    </SecondaryButton>
                    <DangerButton type="button" onClick={() => deleteTerm(term.id)}>删除</DangerButton>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="暂无学期" />
        )}
      </Surface>
    </motion.div>
  );
}
