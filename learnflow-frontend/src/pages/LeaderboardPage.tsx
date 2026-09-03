import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gamificationApi } from '../services/api';
import { Trophy, ArrowLeft, Medal, Crown } from 'lucide-react';

export default function LeaderboardPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadLeaderboard = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await gamificationApi.leaderboard();
      setData(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载排行榜失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLeaderboard();
  }, []);

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载排行榜中...</div>;
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>排行榜暂时不可用</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error || '请稍后重试'}</div>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button className="btn btn-primary" onClick={loadLeaderboard}>重试</button>
        <button className="btn btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
      </div>
    </div>
  );

  const top3 = data.top3 || [];
  const nearby = data.nearby || [];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="btn btn-ghost" onClick={() => navigate('/student')}><ArrowLeft size={18} /></button>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>🏆 排行榜</h1>
      </div>

      <div className="card" style={{ marginBottom: 20, textAlign: 'center' }}>
        <div style={{ fontSize: 18, color: '#64748b', marginBottom: 8 }}>当前联赛 · {data.league?.toUpperCase()}</div>
        <div style={{ fontSize: 48, fontWeight: 700, color: '#6366f1' }}>#{data.user_rank}</div>
        <div style={{ fontSize: 14, color: '#64748b' }}>共 {data.total_in_league} 人 · {data.message}</div>
      </div>

      <div className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Crown size={18} color="#f59e0b" /> 前三名
        </h2>
        <div style={{ display: 'grid', gap: 10 }}>
          {top3.map((u: any, i: number) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, borderRadius: 10, background: i === 0 ? '#fef3c7' : i === 1 ? '#f1f5f9' : '#faf5f0' }}>
              <div style={{ fontSize: 24 }}>{i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}</div>
              <div style={{ flex: 1, fontWeight: 600 }}>{u.name}</div>
              <div style={{ fontWeight: 700, color: '#6366f1' }}>{u.xp} XP</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Medal size={18} color="#6366f1" /> 附近排名
        </h2>
        <div style={{ display: 'grid', gap: 10 }}>
          {nearby.map((u: any, i: number) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, borderRadius: 10, background: u.is_you ? '#eef2ff' : '#f8fafc', border: u.is_you ? '2px solid #6366f1' : '1px solid transparent' }}>
              <div style={{ width: 24, textAlign: 'center', fontWeight: 700, color: '#64748b' }}>{i + 1}</div>
              <div style={{ flex: 1, fontWeight: u.is_you ? 700 : 500 }}>{u.name} {u.is_you && '(你)'}</div>
              <div style={{ fontWeight: 700, color: u.is_you ? '#6366f1' : '#64748b' }}>{u.xp} XP</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
