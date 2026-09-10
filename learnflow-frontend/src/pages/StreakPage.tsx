import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gamificationApi } from '../services/api';
import { ArrowLeft, CalendarDays, CheckCircle2, HeartHandshake, ShieldCheck } from 'lucide-react';

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
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: 0 }}>学习节奏</h1>
          <p className="lf-text-secondary" style={{ fontSize: 13, margin: '2px 0 0' }}>记录你的投入，也为休息留出空间。</p>
        </div>
      </div>

      <div className="lf-card" style={{ marginBottom: 20, overflow: 'hidden', background: 'linear-gradient(135deg, #E6F4F9 0%, #F1ECFB 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
          <div aria-hidden="true" style={{
            width: 72, height: 72, borderRadius: 24, display: 'grid', placeItems: 'center', flexShrink: 0,
            background: '#FFFFFFB8', boxShadow: '0 8px 22px rgba(44,110,143,0.12)', fontSize: 32,
          }}>🌱</div>
          <div style={{ flex: 1, minWidth: 180 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--lf-sem-hint-text)' }}>当前学习节奏</div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, margin: '3px 0 6px' }}>
              <strong style={{ fontSize: 42, lineHeight: 1, color: 'var(--lf-primary-high)' }}>{data.current_streak}</strong>
              <span className="lf-text-secondary" style={{ fontSize: 14 }}>个已完成学习日</span>
            </div>
            <p className="lf-text-secondary" style={{ fontSize: 13, lineHeight: 1.6, margin: 0 }}>
              暂停、休整或换一种安排都不会抹去已完成的学习。
            </p>
          </div>
          <div style={{ padding: '10px 12px', borderRadius: 14, background: 'rgba(255,255,255,0.72)', maxWidth: 260 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, color: 'var(--lf-sem-rest-text)' }}>
              <HeartHandshake size={15} /> 给自己一点弹性
            </div>
            <div className="lf-text-secondary" style={{ fontSize: 12, lineHeight: 1.55, marginTop: 3 }}>
              平台只呈现进步，不用中断来惩罚你。
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        <div className="lf-card" style={{ textAlign: 'center' }}>
          <CalendarDays size={28} color="#2C6E8F" style={{ marginBottom: 8 }} />
          <div style={{ fontSize: 28, fontWeight: 700 }}>{data.best_streak}</div>
          <div className="lf-text-secondary" style={{ fontSize: 13 }}>最长连续投入</div>
        </div>
        <div className="lf-card" style={{ textAlign: 'center' }}>
          <ShieldCheck size={28} color="#3FA66A" style={{ marginBottom: 8 }} />
          <div style={{ fontSize: 20, fontWeight: 700, lineHeight: 1.4 }}>灵活安排</div>
          <div className="lf-text-secondary" style={{ fontSize: 13 }}>休整不影响掌握记录</div>
        </div>
      </div>

      <div className="lf-card">
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
          <CheckCircle2 size={18} color="#3FA66A" /> 节奏回顾
        </h2>
        <div style={{ display: 'grid', gap: 10 }}>
          {[
            { days: 3, label: '初步节奏', desc: '完成几次学习后，记下最适合你的时间和方式。' },
            { days: 7, label: '一周回顾', desc: '回看本周掌握的内容，选择一个想巩固的知识点。' },
            { days: 30, label: '稳定投入', desc: '把有效方法保留下来；需要休整时也可以安心暂停。' },
            { days: 100, label: '长期成长', desc: '持续的成长来自可调整的计划，而不是强迫在线。' },
          ].map((m) => (
            <div key={m.days} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: 12, borderRadius: 14, background: data.current_streak >= m.days ? '#E7F6EE' : '#F8FAFC' }}>
              <div style={{ fontSize: 20, color: data.current_streak >= m.days ? '#1F8A51' : '#94A3B8' }}>
                {data.current_streak >= m.days ? <CheckCircle2 size={20} /> : <CalendarDays size={20} />}
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{m.label}</div>
                <div className="lf-text-secondary" style={{ fontSize: 12, lineHeight: 1.55 }}>{m.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
