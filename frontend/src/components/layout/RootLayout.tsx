import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'motion/react';
import { cn } from '../../lib/utils';
import { Activity, Compass, Home, LayoutDashboard, LogOut, User, Sparkles } from 'lucide-react';
import { useEffect, useState, type ReactNode } from 'react';

// 在此处替换为你的自定义 Logo URL，例如 "https://example.com/logo.png"
// 留空则使用默认文字 Logo
const CUSTOM_LOGO_URL = ""; 

export function RootLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  useEffect(() => {
    setIsLoggedIn(Boolean(localStorage.getItem('bnd_token')));
  }, [location.pathname]);

  useEffect(() => {
    const syncAuthState = () => setIsLoggedIn(Boolean(localStorage.getItem('bnd_token')));
    window.addEventListener('storage', syncAuthState);
    return () => window.removeEventListener('storage', syncAuthState);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('bnd_token');
    setIsLoggedIn(false);
    navigate('/login');
  };

  const navLinks = [
    { name: '首页', path: '/', icon: Home },
    { name: '探索', path: '/explore', icon: Compass },
    { name: '活动', path: '/activities', icon: Activity },
    { name: '工作台', path: '/workspace', icon: LayoutDashboard },
    { name: '我的档案', path: '/profile', icon: User },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Decorative background blobs */}
      <div className="absolute top-0 inset-x-0 h-[40vh] bg-gradient-to-b from-primary-50 to-transparent -z-10" />
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full opacity-20 blur-3xl bg-primary-500 -z-10" />
      <div className="absolute top-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full opacity-20 blur-3xl bg-secondary-500 -z-10" />

      {/* Navigation */}
      <header className="sticky top-0 z-50 md:px-6 md:py-4 w-full flex justify-center bg-white border-b border-slate-100 md:bg-transparent md:border-none">
        <nav className="flex items-center justify-between px-5 py-3.5 md:px-6 md:py-3 md:bg-white/70 md:backdrop-blur-xl md:border md:border-white/40 md:shadow-[0_8px_30px_rgb(0,0,0,0.04)] md:rounded-2xl w-full max-w-7xl">
          <Link to="/" className="flex items-center gap-2 group">
            {CUSTOM_LOGO_URL ? (
               <img src={CUSTOM_LOGO_URL} alt="Logo" className="h-8 object-contain" />
            ) : (
               <div className="bg-primary-500 p-1.5 rounded-xl text-white group-hover:rotate-12 transition-transform duration-300">
                 <Sparkles size={20} className="fill-white/20" />
               </div>
            )}
            <span className="font-display font-bold text-xl tracking-tight text-slate-800">
              BNDSphere
            </span>
          </Link>
          
          <div className="hidden md:flex items-center space-x-1">
            {navLinks.map((link) => {
              const isActive = location.pathname === link.path || (link.path !== '/' && location.pathname.startsWith(link.path));
              return (
                <Link
                  key={link.name}
                  to={link.path}
                  className={cn(
                    "relative px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200",
                    isActive ? "text-primary-600" : "text-slate-500 hover:text-slate-800 hover:bg-slate-100/50"
                  )}
                >
                  {isActive && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute inset-0 bg-primary-50 rounded-lg -z-10"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <span className="flex items-center gap-2">
                    <link.icon size={16} className={cn(isActive && "stroke-[2.5]")} />
                    {link.name}
                  </span>
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2">
            {isLoggedIn ? (
              <>
                <Link
                  to="/profile"
                  className="hidden sm:inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 hover:-translate-y-0.5 transition-all shadow-sm active:scale-95"
                >
                  <User size={16} /> 我的档案
                </Link>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-red-600 bg-red-50 border border-red-100 rounded-xl hover:bg-red-100 hover:-translate-y-0.5 transition-all active:scale-95"
                >
                  <LogOut size={16} /> 退出
                </button>
              </>
            ) : (
              <Link
                to="/login"
                className="px-5 py-2.5 text-sm font-semibold text-white bg-slate-900 rounded-xl hover:bg-slate-800 hover:-translate-y-0.5 transition-all shadow-sm shadow-slate-900/10 active:scale-95"
              >
                登录
              </Link>
            )}
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-8 flex flex-col relative">
         {children}
      </main>

      {/* Mobile Bottom Navigation */}
      <div className="md:hidden fixed bottom-0 inset-x-0 bg-white/80 backdrop-blur-xl border-t border-slate-100 pb-safe z-50">
        <div className="flex justify-around px-2 py-3">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.path || (link.path !== '/' && location.pathname.startsWith(link.path));
            return (
              <Link
                key={link.name}
                to={link.path}
                className={cn(
                  "flex flex-col items-center p-2 rounded-xl text-[10px] sm:text-xs font-medium gap-1 transition-colors",
                  isActive ? "text-primary-600" : "text-slate-500"
                )}
              >
                <link.icon size={20} className={cn(isActive && "stroke-[2.5]")} />
                {link.name}
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  );
}
