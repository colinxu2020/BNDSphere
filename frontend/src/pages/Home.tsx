import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { ArrowRight, Sparkles, Users, Star, ArrowUpRight, Hash } from 'lucide-react';
import { Link } from 'react-router-dom';
import { client } from '../api/client';
import type { components } from '../api/schema';
import { CATEGORY_MAP } from '../lib/labels';
import { StatusMessage } from '../components/ui/AppPrimitives';

type ClubInfo = components['schemas']['ClubInfo'];

export function Home() {
  const [clubs, setClubs] = useState<ClubInfo[]>([]);
  const [clubTotal, setClubTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    const fetchFeaturedClubs = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const { data, error } = await client.GET('/api/v1/clubs/', {
          params: { query: { size: 3 } },
        });
        if (error) {
          setError(error);
          setClubs([]);
          setClubTotal(0);
        } else {
          setClubs(data?.items || []);
          setClubTotal(data?.total || 0);
        }
      } catch (requestError) {
        setError(requestError);
        setClubs([]);
        setClubTotal(0);
      } finally {
        setIsLoading(false);
      }
    };

    fetchFeaturedClubs();
  }, []);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-16 pb-20"
    >
      {/* Hero Section */}
      <section className="flex flex-col items-center text-center mt-12 md:mt-20 gap-6">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1, duration: 0.5, type: "spring" }}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200/60 shadow-sm text-sm font-medium text-slate-600 mb-2"
        >
          <span className="flex h-2 w-2 rounded-full bg-primary-500 animate-pulse"></span>
          在十一学校发现你的热爱
        </motion.div>
        
        <h1 className="text-5xl md:text-7xl font-display font-bold tracking-tight text-slate-900 leading-[1.1] max-w-4xl">
          当 <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-600 to-secondary-500">创意</span> 遇见社群
        </h1>
        
        <p className="text-lg md:text-xl text-slate-500 max-w-2xl text-balance">
          BNDSphere 是你在十一学校探索、加入和管理社团的入口。用清晰的流程处理社团、活动与审核。
        </p>

        <div className="flex flex-col sm:flex-row items-center gap-4 mt-6">
          <Link 
            to="/explore"
            className="flex items-center gap-2 px-8 py-4 bg-primary-500 hover:bg-primary-600 text-white rounded-2xl font-semibold shadow-lg shadow-primary-500/25 transition-all hover:-translate-y-0.5 active:scale-95"
          >
            探索社团 <ArrowRight size={18} />
          </Link>
          <Link 
            to="/workspace"
            className="flex items-center gap-2 px-8 py-4 bg-white border border-slate-200 hover:border-slate-300 text-slate-700 rounded-2xl font-semibold shadow-sm hover:bg-slate-50 transition-all hover:-translate-y-0.5 active:scale-95"
          >
            进入工作台
          </Link>
        </div>
      </section>

      {/* Featured Clubs */}
      <section className="flex flex-col gap-6 mt-8">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-display font-bold text-slate-900 flex items-center gap-2">
              热门社团 <Sparkles className="text-yellow-400" size={24} />
            </h2>
            <p className="text-slate-500 mt-1">发现本周校园热门。</p>
          </div>
          <Link to="/explore" className="hidden sm:flex text-sm font-medium text-primary-600 hover:text-primary-700 items-center gap-1 group transition-colors">
            查看全部 <ArrowUpRight size={16} className="group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </Link>
        </div>

        {error && <StatusMessage value={error} />}

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[...Array(3)].map((_, index) => (
              <div key={index} className="animate-pulse bg-white h-52 rounded-3xl border border-slate-100" />
            ))}
          </div>
        ) : clubs.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {clubs.map((club, idx) => (
            <motion.div
              key={club.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + idx * 0.1, duration: 0.5 }}
            >
              <Link to={`/club/${club.id}`} className="group relative flex flex-col bg-white p-6 rounded-3xl border border-slate-100 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.1)] transition-all duration-300 hover:border-primary-100 overflow-hidden text-left h-full">
                <div className="absolute top-0 right-0 p-6 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 group-hover:-translate-y-1 transition-all">
                   <ArrowUpRight className="text-slate-400" />
                </div>
                
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-14 h-14 rounded-2xl bg-slate-100 shadow-inner overflow-hidden flex items-center justify-center">
                    {club.logo_uri ? (
                      <img src={club.logo_uri} alt={club.name} className="w-full h-full object-cover" />
                    ) : (
                      <Hash className="text-slate-400" size={24} />
                    )}
                  </div>
                  <div>
                    <span className="text-[10px] font-bold tracking-wider uppercase text-primary-600 bg-primary-50 px-2.5 py-1 rounded-full mb-1 inline-block">
                      {CATEGORY_MAP[club.category]}
                    </span>
                    <h3 className="font-semibold text-lg text-slate-900 leading-tight group-hover:text-primary-600 transition-colors">{club.name}</h3>
                  </div>
                </div>
                
                <p className="text-slate-500 text-sm flex-grow line-clamp-2">
                  {club.summary}
                </p>

                <div className="flex items-center gap-2 mt-6">
                  <span className="px-2.5 py-1 bg-slate-50 text-slate-600 font-medium text-xs rounded-lg border border-slate-100">
                    {club.star_level === 'none' ? '无星级' : '星级社团'}
                  </span>
                  <span className="px-2.5 py-1 bg-slate-50 text-slate-600 font-medium text-xs rounded-lg border border-slate-100">
                    {club.members?.length || 0} 名成员
                  </span>
                </div>
              </Link>
            </motion.div>
          ))}
          </div>
        ) : (
          <div className="bg-white border border-slate-100 border-dashed rounded-[2rem] p-10 text-center text-slate-500">
            暂无社团数据。
          </div>
        )}
      </section>

      {/* Stats/Showcase Banner */}
      <section className="bg-slate-900 rounded-[2rem] p-8 md:p-12 text-white relative overflow-hidden mt-8 shadow-xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary-500 rounded-full blur-[100px] opacity-30 -mr-20 -mt-20"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-secondary-500 rounded-full blur-[100px] opacity-20 -ml-20 -mb-20"></div>
        
        <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8 text-center md:text-left">
          <div className="max-w-xl">
             <h2 className="text-3xl md:text-4xl font-display font-bold mb-4">释放你的潜能</h2>
             <p className="text-slate-400 text-lg">从发现社团到提交审核请求，把校园社团事务放在同一个清晰入口中处理。</p>
          </div>
          
          <div className="flex gap-8 md:gap-12">
             <div className="flex flex-col items-center md:items-start text-center md:text-left">
                <span className="flex items-center gap-2 text-primary-400 text-sm font-semibold uppercase tracking-wider mb-2"><Users size={16}/> 社团总数</span>
                <span className="text-4xl md:text-5xl font-display font-bold text-white">{clubTotal}</span>
             </div>
             <div className="flex flex-col items-center md:items-start text-center md:text-left">
                <span className="flex items-center gap-2 text-secondary-400 text-sm font-semibold uppercase tracking-wider mb-2"><Star size={16}/> 当前展示</span>
                <span className="text-4xl md:text-5xl font-display font-bold text-white">{clubs.length}</span>
             </div>
          </div>
        </div>
      </section>
    </motion.div>
  );
}
