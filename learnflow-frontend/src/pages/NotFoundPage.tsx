import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Home, AlertCircle } from 'lucide-react';

export default function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20, background: '#F8FAFC' }}>
      <div className="lf-card" style={{ textAlign: 'center', maxWidth: 400 }}>
        <div style={{ fontSize: 64, marginBottom: 16 }}>🌌</div>
        <h1 style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>404</h1>
        <p style={{ color: '#64748b', fontSize: 15, marginBottom: 24 }}>
          页面迷失在学习星云中了
        </p>
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button className="lf-btn lf-btn-primary" onClick={() => navigate('/')}>
            <Home size={18} />
            返回首页
          </button>
          <button className="lf-btn" style={{ background: '#f1f5f9', color: '#64748b' }} onClick={() => navigate('/login')}>
            去登录
          </button>
        </div>
      </div>
    </div>
  );
}
