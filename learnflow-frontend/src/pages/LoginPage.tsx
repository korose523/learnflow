import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../contexts/ToastContext';

const ROLES = [
  { value: 'student', label: '🧑‍🎓 学生', desc: '开始学习', emoji: '🧑‍🎓' },
  { value: 'teacher', label: '👩‍🏫 教师', desc: '管理班级', emoji: '👩‍🏫' },
  { value: 'parent', label: '👨‍👩‍👧 家长', desc: '查看进度', emoji: '👨‍👩‍👧' },
  { value: 'admin', label: '⚙️ 管理员', desc: '平台运营', emoji: '⚙️' },
];

const DEMO_ACCOUNTS: Record<string, { email: string; password: string }> = {
  student: { email: 'student@learnflow.com', password: 'Student123!' },
  teacher: { email: 'teacher@learnflow.com', password: 'Teacher123!' },
  parent: { email: 'parent@learnflow.com', password: 'Parent123!' },
  admin: { email: 'admin@learnflow.com', password: 'Admin1234!' },
};

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, register, oauthLogin, isAuthenticated, user } = useAuth();
  const { showToast } = useToast();
  const [email, setEmail] = useState('student@learnflow.com');
  const [password, setPassword] = useState('Student123!');
  const [selectedRole, setSelectedRole] = useState<string>('student');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showRegister, setShowRegister] = useState(false);
  const [regName, setRegName] = useState('');
  const [regGrade, setRegGrade] = useState('');

  useEffect(() => {
    if (!isAuthenticated) return;
    if (user?.role) {
      const target = user.role === 'student' ? '/student' : user.role === 'teacher' ? '/teacher' : user.role === 'parent' ? '/parent' : '/admin';
      navigate(target, { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  const handleRoleSelect = (role: string) => {
    setSelectedRole(role);
    const demo = DEMO_ACCOUNTS[role];
    if (demo) { setEmail(demo.email); setPassword(demo.password); }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
      showToast('登录成功，正在跳转...', 'success');
    } catch (err: any) {
      const detail = err.response?.data?.detail || '登录失败，请检查账号密码';
      setError(detail);
      showToast(detail, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regName.trim()) { setError('请输入姓名'); return; }
    setLoading(true);
    setError('');
    try {
      await register(email, password, regName.trim(), selectedRole, regGrade || undefined);
      showToast('注册成功，正在跳转...', 'success');
    } catch (err: any) {
      const detail = err.response?.data?.detail?.[0]?.msg || err.response?.data?.detail || '注册失败';
      setError(detail);
      showToast(detail, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = async (provider: 'qq' | 'wechat') => {
    const mockUid = `${provider}_demo_${Date.now()}`;
    const mockName = provider === 'qq' ? `QQ演示用户` : `微信演示用户`;
    setLoading(true);
    setError('');
    try {
      await oauthLogin(provider, mockUid, mockName, selectedRole);
      showToast('OAuth 登录成功，正在跳转...', 'success');
    } catch (err: any) {
      const detail = err.response?.data?.detail || 'OAuth登录失败';
      setError(detail);
      showToast(detail, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-bg" style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: 20, flexDirection: 'column',
    }}>
      {/* Main content */}
      <div style={{ width: 440, maxWidth: '100%' }}>
        {/* Title */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <h1 style={{
            fontFamily: "'Montserrat', sans-serif", fontSize: 48, fontWeight: 800,
            background: 'linear-gradient(135deg, #FBBF24, #F59E0B)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            margin: '0 0 8px', textShadow: '0 0 32px rgba(251, 191, 36, 0.3)',
          }}>
            LearnFlow
          </h1>
          <p style={{ color: '#94A3B8', fontSize: 15, fontFamily: "'Inter', sans-serif" }}>
            开启你的学习冒险之旅
          </p>
        </div>

        {/* Role Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 24 }}>
          {ROLES.map(r => {
            const active = selectedRole === r.value;
            return (
              <button
                key={r.value}
                type="button"
                onClick={() => handleRoleSelect(r.value)}
                className="card-dark"
                style={{
                  padding: '24px 16px', cursor: 'pointer', textAlign: 'center',
                  border: active ? '2px solid #8B5CF6' : '1px solid #27273B',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                  transition: 'all 0.2s',
                }}
              >
                <span style={{ fontSize: 36 }}>{r.emoji}</span>
                <span style={{
                  fontFamily: "'Montserrat', sans-serif", fontWeight: 700, fontSize: 15,
                  color: '#F8FAFC',
                }}>{r.label.replace(/[^\u4e00-\u9fa5\w]/g, '')}</span>
                <span style={{ fontSize: 11, color: '#64748B', fontFamily: "'Inter', sans-serif" }}>{r.desc}</span>
              </button>
            );
          })}
        </div>

        {/* Form Card */}
        <div className="card-dark" style={{ padding: 24 }}>
          {/* Error */}
          {error && (
            <div style={{ background: 'rgba(239,68,68,0.15)', color: '#EF4444', padding: 10, borderRadius: 8, marginBottom: 16, fontSize: 13, fontFamily: "'Inter', sans-serif" }}>
              {error}
            </div>
          )}

          {/* Tab Switch */}
          <div style={{ display: 'flex', marginBottom: 20, gap: 4 }}>
            <button type="button" onClick={() => setShowRegister(false)}
              style={{
                flex: 1, padding: '10px 0', border: 'none', borderRadius: 10,
                cursor: 'pointer', fontFamily: "'Montserrat', sans-serif",
                fontWeight: 700, fontSize: 14,
                background: !showRegister ? '#8B5CF6' : '#27273B',
                color: !showRegister ? 'white' : '#94A3B8',
                transition: 'all 0.15s',
              }}>登录</button>
            <button type="button" onClick={() => setShowRegister(true)}
              style={{
                flex: 1, padding: '10px 0', border: 'none', borderRadius: 10,
                cursor: 'pointer', fontFamily: "'Montserrat', sans-serif",
                fontWeight: 700, fontSize: 14,
                background: showRegister ? '#8B5CF6' : '#27273B',
                color: showRegister ? 'white' : '#94A3B8',
                transition: 'all 0.15s',
              }}>注册</button>
          </div>

          {!showRegister ? (
            <form onSubmit={handleLogin}>
              <div style={{ ...inputDarkStyle, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>📧</span>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="邮箱地址" style={inputInnerStyle} />
              </div>
              <div style={{ ...inputDarkStyle, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🔒</span>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="密码" style={inputInnerStyle} />
              </div>
              <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%', height: 48, justifyContent: 'center', fontSize: 16 }}>
                {loading ? '登录中...' : '🚀 开始冒险'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleRegister}>
              <div style={{ ...inputDarkStyle, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>📧</span>
                <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="邮箱地址" style={inputInnerStyle} />
              </div>
              <div style={{ ...inputDarkStyle, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>👤</span>
                <input value={regName} onChange={e => setRegName(e.target.value)}
                  placeholder="姓名" style={inputInnerStyle} />
              </div>
              <div style={{ ...inputDarkStyle, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🔒</span>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="密码（大写+小写+数字，8位+）" style={inputInnerStyle} />
              </div>
              <div style={{ ...inputDarkStyle, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>📚</span>
                <input value={regGrade} onChange={e => setRegGrade(e.target.value)}
                  placeholder="年级（选填）" style={inputInnerStyle} />
              </div>
              <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%', height: 48, justifyContent: 'center', fontSize: 16 }}>
                {loading ? '注册中...' : '注册并进入 LearnFlow'}
              </button>
            </form>
          )}

          {/* Social Login */}
          <div style={{ marginTop: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
              <div style={{ flex: 1, height: 1, background: '#27273B' }} />
              <span style={{ fontSize: 12, color: '#64748B', fontFamily: "'Inter', sans-serif" }}>或</span>
              <div style={{ flex: 1, height: 1, background: '#27273B' }} />
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button type="button" onClick={() => handleOAuthLogin('qq')} disabled={loading}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 10, border: 'none', cursor: 'pointer',
                  background: '#27273B', color: '#94A3B8', fontSize: 13, fontFamily: "'Inter', sans-serif", fontWeight: 500,
                }}>
                🐧 QQ登录
              </button>
              <button type="button" onClick={() => handleOAuthLogin('wechat')} disabled={loading}
                style={{
                  flex: 1, padding: '10px 0', borderRadius: 10, border: 'none', cursor: 'pointer',
                  background: '#27273B', color: '#94A3B8', fontSize: 13, fontFamily: "'Inter', sans-serif", fontWeight: 500,
                }}>
                💬 微信登录
              </button>
            </div>
          </div>
        </div>

        {/* Demo hint */}
        <p style={{ textAlign: 'center', marginTop: 20, color: '#475569', fontSize: 12, fontFamily: "'Inter', sans-serif" }}>
          演示账号: student@learnflow.com
        </p>
      </div>
    </div>
  );
}

const inputDarkStyle: React.CSSProperties = {
  background: '#27273B', borderRadius: 10, padding: '0 12px', height: 44,
  border: '1px solid #4C1D95',
};

const inputInnerStyle: React.CSSProperties = {
  flex: 1, border: 'none', background: 'transparent', outline: 'none',
  color: '#F8FAFC', fontSize: 14, fontFamily: "'Inter', sans-serif",
};
