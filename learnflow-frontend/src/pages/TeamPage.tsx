import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { gamificationApi } from '../services/api';
import Celebration from '../components/common/Celebration';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT } from '../theme/tokens';
import { Users, ArrowLeft, Crown, Swords, LogOut, Plus } from 'lucide-react';

export default function TeamPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [createForm, setCreateForm] = useState({ name: '', tag: '', description: '' });
  const [joinCode, setJoinCode] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [message, setMessage] = useState('');
  const [celebrate, setCelebrate] = useState(false);
  const { reduced } = useMotionPref();

  const loadTeam = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await gamificationApi.team();
      setData(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '加载战队信息失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTeam();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');
    try {
      await gamificationApi.createTeam(createForm);
      setMessage('战队创建成功');
      setShowCreate(false);
      setCreateForm({ name: '', tag: '', description: '' });
      setCelebrate(true); // 战队组建成功：协作里程碑庆祝（非攀比压力）
      loadTeam();
    } catch (err: any) {
      setMessage(err.response?.data?.detail || '创建失败');
    }
  };

  const handleLeave = async () => {
    try {
      await gamificationApi.leaveTeam();
      setMessage('已离开战队');
      loadTeam();
    } catch (err: any) {
      setMessage(err.response?.data?.detail || '离开失败');
    }
  };

  const handleJoin = async (teamId: string) => {
    try {
      await gamificationApi.joinTeam(teamId);
      setMessage('加入成功');
      setCelebrate(true);
      loadTeam();
    } catch (err: any) {
      setMessage(err.response?.data?.detail || '加入失败');
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载战队中...</div>;
  if (error) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>战队中心加载失败</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error}</div>
      <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
        <button className="lf-btn lf-btn-primary" onClick={loadTeam}>重试</button>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')}>返回首页</button>
      </div>
    </div>
  );

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')}><ArrowLeft size={18} /></button>
          <h1 style={{ fontSize: 24, fontWeight: 700 }}>⚔️ 战队</h1>
        </div>
        {!data?.has_team && (
          <button className="lf-btn lf-btn-primary" onClick={() => setShowCreate(true)} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={18} /> 创建战队
          </button>
        )}
      </div>

      {message && (
        <div className="lf-card" style={{ marginBottom: 16, background: message.includes('失败') ? '#fef2f2' : '#f0fdf4', color: message.includes('失败') ? '#ef4444' : '#22c55e' }}>
          {message}
        </div>
      )}

      {data?.has_team ? (
        <>
          <div className="lf-card" style={{ marginBottom: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 48 }}>⚔️</div>
            <div style={{ fontSize: 24, fontWeight: 700 }}>{data.team.name} [{data.team.tag}]</div>
            <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
              队长 {data.team.captain} · 成员 {data.team.member_count}/{data.team.max_members}
            </div>
            <div style={{ fontSize: 14, color: '#64748b', marginTop: 8 }}>
              总贡献 {data.team.total_xp} XP · 段位 {data.team.team_tier.toUpperCase()}
            </div>
            <button className="lf-btn" style={{ marginTop: 16, background: '#fef2f2', color: '#ef4444', display: 'inline-flex', alignItems: 'center', gap: 6 }} onClick={handleLeave}>
              <LogOut size={16} /> 离开战队
            </button>
          </div>

          <div className="lf-card">
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Users size={18} color="#2C6E8F" /> 成员
            </h2>
            <div style={{ display: 'grid', gap: 10 }}>
              {data.team.members.map((m: any, i: number) => (
                <motion.div
                  key={i}
                  initial={reduced ? false : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, delay: i * 0.05, ease: EASE_SOFT }}
                  whileHover={reduced ? undefined : { y: -2 }}
                  style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, background: '#f8fafc', borderRadius: 10 }}
                >
                  <div className={m.role === 'captain' ? 'lf-glow' : ''} style={{ fontSize: 20, borderRadius: '50%', padding: 4 }}>
                    {m.role === 'captain' ? <Crown size={20} color="#f59e0b" /> : '👤'}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600 }}>{m.name} {m.role === 'captain' && '(队长)'}</div>
                  </div>
                  <div style={{ fontSize: 13, color: '#64748b' }}>贡献 {m.contribution} XP</div>
                </motion.div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <>
          <div className="lf-card" style={{ marginBottom: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 48, marginBottom: 8 }}>🛡️</div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>你还没有加入战队</div>
            <p style={{ color: '#64748b', fontSize: 14, marginTop: 8 }}>加入战队和同学一起学习，共同冲击更高段位。</p>
          </div>

          {data?.public_teams?.teams?.length > 0 && (
            <div className="lf-card">
              <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>公开战队</h2>
              <div style={{ display: 'grid', gap: 10 }}>
                {data.public_teams.teams.map((t: any) => (
                  <div key={t.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 12, background: '#f8fafc', borderRadius: 10 }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{t.name} [{t.tag}]</div>
                      <div style={{ fontSize: 12, color: '#64748b' }}>成员 {t.member_count} · 总贡献 {t.total_xp} XP</div>
                    </div>
                    <button className="lf-btn" style={{ background: 'var(--lf-sem-hint-soft)', color: '#2C6E8F' }} onClick={() => handleJoin(t.id)}>加入</button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="lf-card" style={{ marginTop: 16, background: '#f8fafc' }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>使用邀请码加入战队</h2>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <input
                className="input"
                placeholder="输入战队邀请码"
                value={joinCode}
                onChange={(e) => setJoinCode(e.target.value)}
                style={{ minWidth: 220, flex: 1 }}
              />
              <button className="lf-btn lf-btn-primary" onClick={() => handleJoin(joinCode)} disabled={!joinCode}>
                加入战队
              </button>
            </div>
            <p style={{ fontSize: 12, color: '#64748b', marginTop: 10 }}>
              输入同学分享的战队邀请码，可直接加入保密战队。
            </p>
          </div>
        </>
      )}

      {showCreate && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
          <div className="lf-card" style={{ width: 400 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>创建战队</h2>
            <form onSubmit={handleCreate} style={{ display: 'grid', gap: 12 }}>
              <input className="input" placeholder="战队名称" value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })} required />
              <input className="input" placeholder="简称 2-4字符" value={createForm.tag} onChange={(e) => setCreateForm({ ...createForm, tag: e.target.value })} required maxLength={4} />
              <textarea className="input" placeholder="战队描述（可选）" rows={2} value={createForm.description} onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })} />
              <div style={{ display: 'flex', gap: 10 }}>
                <button type="button" className="lf-btn lf-btn-ghost" style={{ flex: 1 }} onClick={() => setShowCreate(false)}>取消</button>
                <button type="submit" className="lf-btn lf-btn-primary" style={{ flex: 1 }}>创建</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 战队组建/加入成功：协作里程碑庆祝 */}
      <Celebration
        fire={celebrate}
        emoji="🤝"
        message="战队就位！和伙伴们一起进步吧～"
        onDone={() => setCelebrate(false)}
      />
    </div>
  );
}
