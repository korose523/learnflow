import React from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, GraduationCap, Users, Shield, LogOut, Activity } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useMotionPref } from '../../contexts/MotionContext';
import { EASE_SOFT } from '../../theme/tokens';
import AmbientOrbs from './AmbientOrbs';

const navItems = [
  { path: '/student', label: '学生端', icon: BookOpen, role: 'student' },
  { path: '/student/ai-risk', label: 'AI 风险', icon: Activity, role: 'student' },
  { path: '/teacher', label: '教师端', icon: GraduationCap, role: 'teacher' },
  { path: '/teacher/ai-analytics', label: 'AI 分析', icon: Activity, role: 'teacher' },
  { path: '/parent', label: '家长端', icon: Users, role: 'parent' },
  { path: '/admin', label: '管理端', icon: Shield, role: 'admin' },
];

const roleLabels: Record<string, string> = {
  student: '学生',
  teacher: '教师',
  parent: '家长',
  admin: '管理员',
};

export default function Layout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const { reduced, toggle } = useMotionPref();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const filteredNav = navItems.filter(item => item.role === user?.role);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'transparent' }}>
      {/* 全局柔光氛围背景（纯装饰、pointer-events:none、减弱动效时不渲染） */}
      <AmbientOrbs />
      <header style={{
        background: 'rgba(255,255,255,0.82)',
        backdropFilter: 'blur(14px) saturate(150%)',
        WebkitBackdropFilter: 'blur(14px) saturate(150%)',
        borderBottom: '1px solid rgba(44,110,143,0.08)',
        padding: '10px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        boxShadow: '0 4px 18px rgba(59,169,201,0.07)',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        {/* 左侧 Logo（童趣圆润 + 渐变芯片） */}
        <Link to={`/${user?.role || 'student'}`} style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span
            style={{
              fontSize: 26, width: 44, height: 44, display: 'inline-flex',
              alignItems: 'center', justifyContent: 'center',
              background: 'linear-gradient(135deg, #3BA9C9, #9B7EDE)',
              borderRadius: 14, boxShadow: '0 6px 16px rgba(44,110,143,0.28)',
            }}
          >🎓</span>
          <span className="lf-gradient-text" style={{ fontSize: 21, fontWeight: 800, fontFamily: "'Baloo 2','Nunito','Noto Sans SC',sans-serif" }}>LearnFlow</span>
        </Link>

        {/* 中间导航 */}
        <nav style={{ display: 'flex', gap: 6 }}>
          {filteredNav.map(({ path, label, icon: Icon }) => {
            const isRoleTab = ['/student', '/teacher', '/parent', '/admin'].includes(path);
            const isActive = isRoleTab
              ? (location.pathname === path || (path === '/student' && location.pathname === '/'))
              : location.pathname.startsWith(path);
            return (
              <Link
                key={path}
                to={path}
                className="tap-target"
                style={{
                  padding: '8px 16px',
                  borderRadius: 14,
                  textDecoration: 'none',
                  color: isActive ? '#fff' : '#64748B',
                  background: isActive ? 'linear-gradient(135deg, #3BA9C9, #2C6E8F)' : 'transparent',
                  boxShadow: isActive ? '0 6px 16px rgba(44,110,143,0.28)' : 'none',
                  fontWeight: isActive ? 700 : 500,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  fontSize: 14,
                  fontFamily: "'Inter','Noto Sans SC',sans-serif",
                  transition: 'all 0.2s cubic-bezier(.22,1,.36,1)',
                }}
              >
                <Icon size={16} />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* 右侧：动效开关 + 用户 + 退出 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={toggle}
            title={reduced ? '动效已减弱，点击开启' : '减弱动效'}
            aria-pressed={reduced}
            className="tap-target"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 14, border: '1px solid #E3EEF3',
              background: reduced ? '#EAF6FB' : '#fff', color: reduced ? '#2C6E8F' : '#94A3B8',
              fontSize: 13, cursor: 'pointer', fontFamily: "'Inter','Noto Sans SC',sans-serif",
            }}
          >
            <Activity size={15} />
            {reduced ? '动效减弱' : '动效'}
          </button>

          {user && (
            <span style={{
              fontSize: 13, color: '#64748B', background: '#F1F5F9',
              padding: '6px 12px', borderRadius: 14, fontFamily: "'Inter','Noto Sans SC',sans-serif",
            }}>
              {roleLabels[user.role] || user.role} · {user.name || user.email}
            </span>
          )}

          <button
            onClick={handleLogout}
            className="tap-target"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              padding: '6px 12px', borderRadius: 14, border: 'none',
              background: 'transparent', cursor: 'pointer', color: '#94A3B8',
              fontSize: 13, fontFamily: "'Inter','Noto Sans SC',sans-serif",
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#FEE2E2'; e.currentTarget.style.color = '#E0533D'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94A3B8'; }}
            title="退出登录"
          >
            <LogOut size={16} />
            退出
          </button>
        </div>
      </header>

      <main style={{ flex: 1, padding: '24px 16px', maxWidth: 1200, margin: '0 auto', width: '100%', position: 'relative', zIndex: 1 }}>
        <motion.div
          initial={reduced ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: EASE_SOFT }}
        >
          <Outlet />
        </motion.div>
      </main>
    </div>
  );
}
