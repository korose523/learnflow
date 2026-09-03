import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gamificationApi } from '../services/api';
import { TreePine, Lock, Star, Zap, ArrowLeft } from 'lucide-react';

interface Skill {
  id: string;
  name: string;
  icon: string;
  level: number;
  xp: number;
  xp_to_next: number;
  times_used: number;
  unlocked: boolean;
  progress_pct: number;
  next_bonus: string;
}

interface SkillCategory {
  skills: Skill[];
}

export default function SkillTreePage() {
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadSkillTree = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await gamificationApi.skillTree();
      setData(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || '加载技能树失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSkillTree();
  }, []);

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}>加载技能树中...</div>;
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>技能树暂时不可用</div>
      <div style={{ color: '#64748b', marginBottom: 20 }}>{error || '请稍后重试或联系客服'}</div>
      <button className="btn btn-primary" onClick={loadSkillTree}>重试加载</button>
    </div>
  );

  const categories = data.categories || {};

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="btn btn-ghost" onClick={() => navigate('/student')}><ArrowLeft size={18} /></button>
        <h1 style={{ fontSize: 24, fontWeight: 700 }}>🌳 学习技能树</h1>
      </div>

      <div className="card" style={{ marginBottom: 20, textAlign: 'center' }}>
        <div style={{ fontSize: 42, fontWeight: 700, color: '#6366f1' }}>Lv.{data.meta_level}</div>
        <div style={{ fontSize: 18, color: '#64748b' }}>{data.meta_title}</div>
        <div style={{ fontSize: 13, color: '#64748b', marginTop: 8 }}>
          总使用次数 {data.total_times_used} · 激活组合 {data.combo_bonus?.active_combos || 0}
        </div>
      </div>

      {data.combo_bonus?.bonuses?.length > 0 && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Zap size={18} color="#f59e0b" /> 技能组合加成
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {data.combo_bonus.bonuses.map((bonus: any, i: number) => (
              <div key={i} style={{ padding: '8px 12px', background: '#fefce8', borderRadius: 8, fontSize: 13 }}>
                <span style={{ marginRight: 4 }}>{bonus.icon}</span>
                <strong>{bonus.name}</strong> Lv.{bonus.level} · {bonus.effect}
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.entries(categories).map(([category, categoryData]: [string, any]) => (
        <div key={category} className="card" style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12, textTransform: 'capitalize' }}>
            {category === 'memory' && '🧠 记忆'}
            {category === 'understanding' && '💡 理解'}
            {category === 'practice' && '✏️ 练习'}
            {category === 'focus' && '🎯 专注'}
            {category === 'mindset' && '🌱 心态'}
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
            {categoryData.skills.map((skill: Skill) => (
              <div key={skill.id} style={{ padding: 14, borderRadius: 12, border: '1px solid #e2e8f0', background: skill.unlocked ? 'white' : '#f8fafc', opacity: skill.unlocked ? 1 : 0.7 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ fontSize: 24 }}>{skill.unlocked ? skill.icon : <Lock size={20} color="#94a3b8" />}</div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#6366f1' }}>Lv.{skill.level}</div>
                </div>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>{skill.name}</div>
                <div className="progress-bar" style={{ marginBottom: 8 }}>
                  <div className="progress-bar-fill" style={{ width: `${skill.progress_pct}%`, background: skill.unlocked ? '#6366f1' : '#cbd5e1' }} />
                </div>
                <div style={{ fontSize: 11, color: '#64748b' }}>
                  XP {skill.xp}/{skill.xp_to_next} · 使用 {skill.times_used} 次
                </div>
                {skill.unlocked && skill.next_bonus && skill.next_bonus !== '已满级' && (
                  <div style={{ fontSize: 11, color: '#f59e0b', marginTop: 6 }}>⭐ {skill.next_bonus}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
