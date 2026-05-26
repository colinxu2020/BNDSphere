import { useState } from 'react';
import { motion } from 'motion/react';
import { Activity, Building2, ClipboardCheck, Shield, Sparkles, UserSearch, Users } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Field,
  PageHeader,
  PrimaryButton,
  SecondaryButton,
  Surface,
  inputClassName,
} from '../components/ui/AppPrimitives';

const TOOLS = [
  {
    title: '创建社团',
    description: '提交新的社团条目。',
    path: '/clubs/new',
    icon: Building2,
  },
  {
    title: '综评活动',
    description: '浏览活动和社团记录。',
    path: '/activities',
    icon: Activity,
  },
  {
    title: '审核台',
    description: '审核资料和活动请求。',
    path: '/moderation',
    icon: ClipboardCheck,
  },
  {
    title: '社联工作台',
    description: '维护综评活动并审核记录。',
    path: '/federation',
    icon: Users,
  },
  {
    title: '管理员控制台',
    description: '维护用户、社团和学期。',
    path: '/admin',
    icon: Shield,
  },
];

export function Workspace() {
  const navigate = useNavigate();
  const [clubId, setClubId] = useState('');
  const [userId, setUserId] = useState('');

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-col gap-8 pb-20"
    >
      <PageHeader
        eyebrow="Workspace"
        title="工作台"
        description="进入社团、活动、审核和管理员功能。权限由后端接口判断。"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Surface>
          <div className="w-12 h-12 rounded-2xl bg-primary-50 text-primary-600 flex items-center justify-center mb-5">
            <Sparkles size={22} />
          </div>
          <h2 className="text-xl font-display font-bold text-slate-900">社团工作台</h2>
          <p className="text-sm text-slate-500 mt-2">输入社团 ID，管理资料、活动、综评记录和星级申请。</p>
          <div className="flex flex-col sm:flex-row gap-3 mt-6">
            <Field label="社团 ID">
              <input className={inputClassName} value={clubId} onChange={event => setClubId(event.target.value)} />
            </Field>
            <div className="flex items-end">
              <PrimaryButton type="button" onClick={() => clubId && navigate(`/club/${clubId}/manage`)}>
                进入
              </PrimaryButton>
            </div>
          </div>
        </Surface>

        <Surface>
          <div className="w-12 h-12 rounded-2xl bg-secondary-50 text-secondary-600 flex items-center justify-center mb-5">
            <UserSearch size={22} />
          </div>
          <h2 className="text-xl font-display font-bold text-slate-900">公开用户</h2>
          <p className="text-sm text-slate-500 mt-2">输入用户 ID，查看后端返回的公开用户档案。</p>
          <div className="flex flex-col sm:flex-row gap-3 mt-6">
            <Field label="用户 ID">
              <input className={inputClassName} value={userId} onChange={event => setUserId(event.target.value)} />
            </Field>
            <div className="flex items-end">
              <PrimaryButton type="button" onClick={() => userId && navigate(`/users/${userId}`)}>
                查看
              </PrimaryButton>
            </div>
          </div>
        </Surface>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {TOOLS.map(tool => (
          <Link
            key={tool.path}
            to={tool.path}
            className="group bg-white p-6 rounded-[2rem] border border-slate-200/60 shadow-sm hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.06)] hover:border-primary-100 transition-all duration-300"
          >
            <div className="w-12 h-12 rounded-2xl bg-slate-50 text-slate-500 flex items-center justify-center mb-5 group-hover:bg-primary-50 group-hover:text-primary-600 transition-colors">
              <tool.icon size={22} />
            </div>
            <h3 className="font-semibold text-lg text-slate-900 group-hover:text-primary-600 transition-colors">
              {tool.title}
            </h3>
            <p className="text-sm text-slate-500 mt-2">{tool.description}</p>
          </Link>
        ))}
      </div>
    </motion.div>
  );
}
