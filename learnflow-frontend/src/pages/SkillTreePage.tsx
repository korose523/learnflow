import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gamificationApi } from '../services/api';
import { Skeleton } from '../components/common/Skeleton';
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

  if (loading) {
    return (
      <div style={{ display: 'grid', gap: 16 }}>
        <Skeleton height={96} rounded="lg" />
        <Skeleton height={200} rounded="lg" />
        <Skeleton height={160} rounded="lg" />
      </div>
    );
  }
  if (!data) return (
    <div style={{ textAlign: 'center', padding: 80 }}>
      <div style={{ fontSize: 24, fontWeight: 700, marginBottom: 12 }}>技能树暂时不可用</div>
      <div style={{ color: 'var(--lf-neutral-500)', marginBottom: 20 }}>{error || '请稍后重试或联系客服'}</div>
      <button className="lf-btn lf-btn-primary" onClick={loadSkillTree}>重试加载</button>
    </div>
  );

  const categories = data.categories || {};

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
        <button className="lf-btn lf-btn-ghost" onClick={() => navigate('/student')} aria-label="返回首页"><ArrowLeft size={18} /></button>
        <h1 style={{ fontSize: 'var(--lf-text-2xl)', fontWeight: 800 }}>🌳 学习技能树</h1>
      </div>

      {/* 总览：等级 + 使用次数（成长的可感知里程碑） */}
      <div className="lf-card" style={{ marginBottom: 20, textAlign: 'center', background: 'linear-gradient(135deg, var(--lf-sem-hint-soft, #E6F4F9), var(--lf-neutral-50))' }}>
        <div style={{ fontSize: 42, fontWeight: 800, color: 'var(--lf-primary-high)' }}>Lv.{data.meta_level}</div>
        <div style={{ fontSize: 'var(--lf-text-lg)', color: 'var(--lf-neutral-600)' }}>{data.meta_title}</div>
        <div style={{ fontSize: 'var(--lf-text-sm)', color: 'var(--lf-neutral-500)', marginTop: 8 }}>
          总使用次数 {data.total_times_used} · 激活组合 {data.combo_bonus?.active_combos || 0}
        </div>
      </div>

      {data.combo_bonus?.bonuses?.length > 0 && (
        <div className="lf-card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 'var(--lf-text-md)', fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Zap size={18} color="var(--lf-warning)" /> 技能组合加成
          </h2>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {data.combo_bonus.bonuses.map((bonus: any, i: number) => (
              <div key={i} style={{ padding: '8px 12px', background: 'var(--lf-warning-soft, #FEF3C7)', borderRadius: 'var(--lf-radius-sm)', fontSize: 13 }}>
                <span style={{ marginRight: 4 }}>{bonus.icon}</span>
                <strong>{bonus.name}</strong> Lv.{bonus.level} · {bonus.effect}
              </div>
            ))}
          </div>
        </div>
      )}

      {Object.entries(categories).map(([category, categoryData]: [string, any]) => (
        <div key={category} className="lf-card" style={{ marginBottom: 16 }}>
          <h2 style={{ fontSize: 'var(--lf-text-md)', fontWeight: 700, marginBottom: 12, textTransform: 'capitalize' }}>
            {category === 'memory' && '🧠 记忆'}
            {category === 'understanding' && '💡 理解'}
            {category === 'practice' && '✏️ 练习'}
            {category === 'focus' && '🎯 专注'}
            {category === 'mindset' && '🌱 心态'}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {categoryData.skills.map((skill: Skill) => (
              <div
                key={skill.id}
                style={{
                  padding: 14, borderRadius: 'var(--lf-radius-md)',
                  border: `1px solid ${skill.unlocked ? 'var(--lf-primary-low)' : 'var(--lf-neutral-200)'}`,
                  background: skill.unlocked ? 'white' : 'var(--lf-neutral-50)',
                  opacity: skill.unlocked ? 1 : 0.7,
                  boxShadow: skill.unlocked ? 'var(--lf-elev-1)' : 'none',
                }}
                aria-label={`${skill.name}，等级 ${skill.level}${skill.unlocked ? '' : '，未解锁'}`}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ fontSize: 24 }}>{skill.unlocked ? skill.icon : <Lock size={20} color="var(--lf-neutral-400)" />}</div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--lf-primary-high)' }}>Lv.{skill.level}</div>
                </div>
                <div style={{ fontWeight: 600, fontSize: 'var(--lf-text-md)', marginBottom: 4 }}>{skill.name}</div>
                <div className="progress-bar" style={{ marginBottom: 8, background: 'var(--lf-neutral-100)' }}>
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${skill.progress_pct}%`, background: skill.unlocked ? 'linear-gradient(90deg, var(--lf-primary-low), var(--lf-primary-high))' : 'var(--lf-neutral-300)' }}
                  />
                </div>
                <div style={{ fontSize: 11, color: 'var(--lf-neutral-500)' }}>
                  XP {skill.xp}/{skill.xp_to_next} · 使用 {skill.times_used} 次
                </div>
                {skill.unlocked && skill.next_bonus && skill.next_bonus !== '已满级' && (
                  <div style={{ fontSize: 11, color: 'var(--lf-warning-text, #B45309)', marginTop: 6 }}>⭐ {skill.next_bonus}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
