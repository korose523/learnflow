import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gamificationApi } from '../services/api';
import { Flame, ArrowLeft, Calendar, Trophy } from 'lucide-react';

export default function StreakPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadStreak = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await gamificationApi.streak();
      setData(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载连胜数据失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStreak();
  }, []);

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载连胜中...</div>;
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>连胜中心暂时不可用</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error || '请稍后重试'}</div>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button className="lf-btn lf-btn-primary" onClick={loadStreak}>重试</button>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
      </div>
    </div>
  );

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')}><ArrowLeft size={18} /></button>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>🔥 连胜中心</h1>
      </div>

      <div className="lf-card" style={{ textAlign: 'center', marginBottom: 20, background: 'linear-gradient(135deg, #fef3c7 0%, #fee2e2 100%)' }}>
        <div style={{ fontSize: 72, marginBottom: 8 }}>{data.fire_icons}</div>
        <div style={{ fontSize: 48, fontWeight: 700, color: '#ef4444' }}>{data.current_streak}</div>
        <div style={{ fontSize: 18, color: '#64748b', marginBottom: 8 }}>连续学习天数</div>
        <div style={{ fontSize: 14, color: '#a16207' }}>{data.message}</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        <div className="lf-card" style={{ textAlign: 'center' }}>
          <Trophy size={28} color="#f59e0b" style={{ marginBottom: 8 }} />
          <div style={{ fontSize: 28, fontWeight: 700 }}>{data.best_streak}</div>
          <div style={{ fontSize: 13, color: '#64748b' }}>历史最高</div>
        </div>
        <div className="lf-card" style={{ textAlign: 'center' }}>
          <Calendar size={28} color="#2C6E8F" style={{ marginBottom: 8 }} />
          <div style={{ fontSize: 28, fontWeight: 700 }}>{data.streak_freezes_available}</div>
          <div style={{ fontSize: 13, color: '#64748b' }}>冻结卡</div>
        </div>
      </div>

      <div className="lf-card">
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Flame size={18} color="#ef4444" /> 连胜里程碑
        </h2>
        <div style={{ display: 'grid', gap: 10 }}>
          {[
            { days: 3, label: '三天火焰', desc: '连续学习3天，习惯开始形成' },
            { days: 7, label: '一周连胜', desc: '整整一周，你已经超越了大多数人' },
            { days: 30, label: '连胜社团', desc: '连续30天，进入连胜社团' },
            { days: 100, label: '连胜传奇', desc: '100天，你是真正的学习传奇' },
          ].map((m) => (
            <div key={m.days} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, borderRadius: 10, background: data.current_streak >= m.days ? '#f0fdf4' : '#f8fafc' }}>
              <div style={{ fontSize: 24 }}>{data.current_streak >= m.days ? '🔥' : '⚪'}</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{m.label}</div>
                <div style={{ fontSize: 12, color: '#64748b' }}>{m.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
