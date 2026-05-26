import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Activity, ArrowLeft, CalendarDays, CheckCircle2, FileText } from 'lucide-react';
import { Link, useParams } from 'react-router-dom';
import { client } from '../api/client';
import type { components } from '../api/schema';
import { ACTIVITY_LEVEL_MAP, AUDIT_STATUS_MAP, PARTICIPATION_MAP } from '../lib/labels';
import { formatDate, formatDateTime } from '../lib/format';
import { Badge, EmptyState, PageHeader, SectionTitle, StatusMessage, Surface } from '../components/ui/AppPrimitives';

type GeneralActivity = components['schemas']['GeneralActivityInfo'];

export function GeneralActivityDetail() {
  const { id } = useParams<{ id: string }>();
  const [activityInfo, setActivityInfo] = useState<GeneralActivity | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const fetchActivity = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET('/api/v1/general-activities/{activity_id}', {
          params: { path: { activity_id: Number(id) } },
        });
        if (error) {
          setError(error);
          setActivityInfo(null);
        } else {
          setActivityInfo(data || null);
        }
      } catch (requestError) {
        setError(requestError);
        setActivityInfo(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchActivity();
  }, [id]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <Link to="/activities" className="inline-flex items-center gap-2 text-slate-500 hover:text-slate-900 font-medium w-fit transition-colors">
        <ArrowLeft size={18} /> 返回活动
      </Link>

      {isLoading ? (
        <div className="animate-pulse bg-white rounded-[2rem] h-72 border border-slate-100" />
      ) : error ? (
        <StatusMessage value={error} />
      ) : activityInfo ? (
        <>
          <Surface className="relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-secondary-50 rounded-full blur-[70px] opacity-80 -mr-24 -mt-24 pointer-events-none" />
            <div className="relative z-10">
              <div className="w-14 h-14 rounded-2xl bg-primary-50 text-primary-600 flex items-center justify-center mb-6">
                <Activity size={26} />
              </div>
              <PageHeader
                eyebrow={ACTIVITY_LEVEL_MAP[activityInfo.level]}
                title={activityInfo.name}
                description={activityInfo.description}
              />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-8 text-sm font-medium text-slate-500">
                <div className="flex items-center gap-2 bg-slate-50 rounded-xl px-3 py-2 border border-slate-100">
                  <CalendarDays size={16} /> 创建于 {formatDate(activityInfo.created_at)}
                </div>
                <div className="flex items-center gap-2 bg-slate-50 rounded-xl px-3 py-2 border border-slate-100">
                  <FileText size={16} /> 当前学期 {activityInfo.academic_term?.term_name || '未设置'}
                </div>
              </div>
            </div>
          </Surface>

          <Surface>
            <SectionTitle
              icon={<CheckCircle2 size={20} />}
              title="社团记录"
              description="后端返回的 club_records 会直接展示在这里。"
            />
            {activityInfo.club_records?.length ? (
              <div className="grid gap-4">
                {activityInfo.club_records.map(record => (
                  <div key={record.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-5">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge tone={record.audit_status === 'approved' ? 'green' : record.audit_status === 'rejected' ? 'red' : 'yellow'}>
                            {AUDIT_STATUS_MAP[record.audit_status]}
                          </Badge>
                          <Badge>{PARTICIPATION_MAP[record.participation_type]}</Badge>
                        </div>
                        <h3 className="font-semibold text-slate-900 mt-3">社团 #{record.club_id}</h3>
                        <p className="text-sm text-slate-500 mt-1">
                          申请分值 {record.requested_score}，提交于 {formatDateTime(record.created_at)}
                        </p>
                      </div>
                      <Link
                        to={`/club/${record.club_id}/manage`}
                        className="text-sm font-semibold text-primary-600 hover:text-primary-700"
                      >
                        进入社团工作台
                      </Link>
                    </div>
                    {record.proof_files?.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-4">
                        {record.proof_files.map(file => (
                          <a
                            key={file}
                            href={file}
                            target="_blank"
                            rel="noreferrer"
                            className="text-xs font-medium text-slate-600 bg-white border border-slate-100 rounded-lg px-2.5 py-1 hover:text-primary-600"
                          >
                            证明材料
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="暂无社团记录" />
            )}
          </Surface>
        </>
      ) : (
        <EmptyState title="未找到活动" />
      )}
    </motion.div>
  );
}
