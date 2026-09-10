import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gamificationApi } from '../services/api';
import { Skeleton } from '../components/common/Skeleton';
import { Trophy, ArrowLeft, Medal, Crown, Sprout } from 'lucide-react';

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

  if (loading) {
    return (
      <div style={{ display: 'grid', gap: 16 }}>
        <Skeleton height={120} rounded="lg" />
        <Skeleton height={200} rounded="lg" />
      </div>
    );
  }
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>排行榜暂时不可用</div>
      <div style={{ color: 'var(--lf-neutral-500)', marginBottom: 20 }}>{error || '请稍后重试'}</div>
      <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
        <button className="lf-btn lf-btn-primary" onClick={loadLeaderboard}>重试</button>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
      </div>
    </div>
  );

  const top3 = data.top3 || [];
  const nearby = data.nearby || [];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')} aria-label="返回首页"><ArrowLeft size={18} /></button>
        <h1 style={{ fontSize: 'var(--lf-text-2xl)', fontWeight: 800 }}>🏆 学习榜</h1>
      </div>

      {/* 顶部声明：明确这是鼓励而非竞争，杜绝排名羞辱（伦理红线） */}
      <div className="lf-card" style={{ marginBottom: 20, background: 'var(--lf-sem-hint-soft, #E6F4F9)', borderLeft: '4px solid var(--lf-primary-low)' }}>
        <p style={{ margin: 0, fontSize: 'var(--lf-text-sm)', color: 'var(--lf-primary-high)', lineHeight: 1.6 }}>
          🌿 这里只展示「大家都在进步」，不与你比较。你的学习节奏最重要，慢慢来也可以很棒。
        </p>
      </div>

      {/* 你的学习里程（以个人进步为主，排名仅作信息，不作羞辱） */}
      <div className="lf-card" style={{ marginBottom: 20, textAlign: 'center', background: 'linear-gradient(135deg, var(--lf-sem-hint-soft, #E6F4F9), var(--lf-neutral-50))' }}>
        <div style={{ fontSize: 'var(--lf-text-sm)', color: 'var(--lf-neutral-500)', marginBottom: 8 }}>当前联赛 · {data.league?.toUpperCase()}</div>
        <div style={{ fontSize: 48, fontWeight: 800, color: 'var(--lf-primary-high)' }}>#{data.user_rank}</div>
        <div style={{ fontSize: 'var(--lf-text-base)', color: 'var(--lf-neutral-500)' }}>共 {data.total_in_league} 人 · {data.message}</div>
      </div>

      {/* 本周进步榜样（庆祝成就，正向激励；不标注落后者、不做负面对比） */}
      <div className="lf-card" style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 'var(--lf-text-md)', fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Crown size={18} color="var(--lf-warning)" /> 本周进步榜样
        </h2>
        <div style={{ display: 'grid', gap: 10 }}>
          {top3.map((u: any, i: number) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, borderRadius: 'var(--lf-radius-md)', background: i === 0 ? 'var(--lf-warning-soft, #FEF3C7)' : i === 1 ? 'var(--lf-neutral-100)' : 'var(--lf-neutral-50)' }}>
              <div style={{ fontSize: 24 }}>{i === 0 ? '🥇' : i === 1 ? '🥈' : '🥉'}</div>
              <div style={{ flex: 1, fontWeight: 600 }}>{u.name}</div>
              <div style={{ fontWeight: 700, color: 'var(--lf-primary-high)' }}>{u.xp} XP</div>
            </div>
          ))}
        </div>
      </div>

      {/* 你身边的伙伴（只展示你附近的上下文，不暴露末位，避免社交比较羞辱） */}
      <div className="lf-card">
        <h2 style={{ fontSize: 'var(--lf-text-md)', fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Sprout size={18} color="var(--lf-sem-success)" /> 你身边的伙伴
        </h2>
        <div style={{ display: 'grid', gap: 10 }}>
          {nearby.map((u: any, i: number) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, borderRadius: 'var(--lf-radius-md)', background: u.is_you ? 'var(--lf-sem-hint-soft, #E6F4F9)' : 'var(--lf-neutral-50)', border: u.is_you ? '2px solid var(--lf-primary-low)' : '1px solid transparent' }}>
              <div style={{ width: 24, textAlign: 'center', fontWeight: 700, color: 'var(--lf-neutral-500)' }}>{i + 1}</div>
              <div style={{ flex: 1, fontWeight: u.is_you ? 700 : 500 }}>{u.name} {u.is_you && '(你)'}</div>
              <div style={{ fontWeight: 700, color: u.is_you ? 'var(--lf-primary-high)' : 'var(--lf-neutral-500)' }}>{u.xp} XP</div>
            </div>
          ))}
        </div>
        <p style={{ margin: '16px 0 0', fontSize: 'var(--lf-text-micro)', color: 'var(--lf-neutral-400)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Medal size={14} /> 每位伙伴都在用自己的节奏前进，排名只是参考，不必和别人比。
        </p>
      </div>
    </div>
  );
}
