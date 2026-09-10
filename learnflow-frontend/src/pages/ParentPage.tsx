import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, RadialBarChart, RadialBar,
} from 'recharts';
import { CalendarDays, Clock, ShieldAlert, ShieldCheck, Gauge } from 'lucide-react';
import { parentApi, laiApi } from '../services/api';
import LAIHealthCard from '../components/common/LAIHealthCard';
import MascotBubble from '../components/common/MascotBubble';
import { useAuth } from '../contexts/AuthContext';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';

interface WeeklyReport {
  duration?: { total_minutes?: number; days?: number };
  difficulty_curve?: { day: string; value: number }[];
  mastery?: Record<string, number>;
  risk_level?: 'low' | 'medium' | 'high';
}

const RISK_META: Record<string, { label: string; color: string; icon: JSX.Element }> = {
  low: { label: '低风险', color: '#3FA66A', icon: <ShieldCheck size={16} /> },
  medium: { label: '需关注', color: '#E68A3C', icon: <ShieldAlert size={16} /> },
  high: { label: '高风险', color: '#E0533D', icon: <ShieldAlert size={16} /> },
};

export default function ParentPage() {
  const { user } = useAuth();
  const { reduced } = useMotionPref();
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [lai, setLai] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // 家长端：孩子 id（演示用，可在真实环境从 /parent/children 选取）
  const childId = (user as any)?.child_id || localStorage.getItem('lf_child_id') || 'me';
  const [limit, setLimit] = useState<number>(() => Number(localStorage.getItem('lf_daily_limit') || 40));
  const [limitSaved, setLimitSaved] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.all([
      parentApi.weeklyReport({ student_id: childId }).then(({ data }) => data).catch(() => null),
      laiApi.dashboard(childId === 'me' ? undefined : childId).then(({ data }) => data).catch(() => null),
    ]).then(([rep, laiData]) => {
      if (!alive) return;
      setReport(rep);
      setLai(laiData);
      setLoading(false);
    });
    return () => { alive = false; };
  }, [childId]);

  const saveLimit = () => {
    localStorage.setItem('lf_daily_limit', String(limit));
    setLimitSaved(true);
    setTimeout(() => setLimitSaved(false), 2000);
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>周报加载中...</div>;
  if (error) return <div style={{ textAlign: 'center', padding: 60, color: '#E0533D' }}>{error}</div>;

  const risk = RISK_META[report?.risk_level || 'low'];
  const masteryEntries = Object.entries(report?.mastery || {});

  return (
    <div>
      <h1 style={{ fontSize: 24, fontWeight: 800, color: '#2C6E8F', margin: '0 0 4px', fontFamily: "'Baloo 2',sans-serif" }}>
        👨‍👩‍👧 家长周报
      </h1>
      <p style={{ color: '#64748b', margin: '0 0 20px', fontSize: 14 }}>
        关注孩子的学习节奏与状态（非分数排名），陪伴而非比较。
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* 时长 */}
        <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#64748b', fontSize: 13, marginBottom: 8 }}>
            <Clock size={14} color="#3BA9C9" /> 本周学习时长
          </div>
          <div style={{ fontSize: 32, fontWeight: 800, color: '#2C6E8F' }}>
            {report?.duration?.total_minutes ?? 0} <span style={{ fontSize: 14, fontWeight: 500, color: '#94A3B8' }}>分钟</span>
          </div>
          <div style={{ fontSize: 12, color: '#94A3B8' }}>约 {Math.round((report?.duration?.total_minutes ?? 0) / 60 * 10) / 10} 小时</div>
        </motion.div>

        {/* 风险 */}
        <motion.div className="lf-card" initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#64748b', fontSize: 13, marginBottom: 8 }}>
            <Gauge size={14} /> 状态评估
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: risk.color, display: 'inline-flex' }}>{risk.icon}</span>
            <span style={{ fontSize: 22, fontWeight: 800, color: risk.color }}>{risk.label}</span>
          </div>
          <div style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>基于专注度与休息节奏的综合判断</div>
        </motion.div>
      </div>

      {/* 孩子的学习健康分（LAI）— 论文核心构念，数据驱动自真实行为日志 */}
      {lai && <LAIHealthCard data={lai} />}

      {/* 难度曲线 */}
      <motion.div className="lf-card" style={{ marginTop: 16 }} initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#64748b', fontSize: 13, marginBottom: 12 }}>
          <CalendarDays size={14} color="#9B7EDE" /> 难度曲线（维持心流通道）
        </div>
        <div style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={report?.difficulty_curve ?? []}>
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #E3EEF3', fontSize: 12 }} />
              <Line type="monotone" dataKey="value" stroke="#3BA9C9" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p style={{ fontSize: 11, color: '#94A3B8', margin: '4px 0 0' }}>理想区间 75–85%（绿色），过高或过低都会提示调整。</p>
      </motion.div>

      {/* 掌握度（非分数，用进度环） */}
      <motion.div className="lf-card" style={{ marginTop: 16 }} initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
        <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12, fontWeight: 600 }}>学科掌握度（相对自身）</div>
        {masteryEntries.length === 0 && <div style={{ color: '#94A3B8', fontSize: 13 }}>暂无掌握度数据</div>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
          {masteryEntries.map(([subj, val]) => (
            <div key={subj} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 56, height: 56 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadialBarChart innerRadius="70%" outerRadius="100%" data={[{ name: subj, value: val, fill: subjectColor(subj) }]} startAngle={90} endAngle={-270}>
                    <RadialBar background dataKey="value" cornerRadius={10} />
                  </RadialBarChart>
                </ResponsiveContainer>
              </div>
              <div>
                <div style={{ fontWeight: 600, color: '#2C6E8F', fontSize: 13 }}>{subjectMeta(subj).label}</div>
                <div style={{ fontSize: 12, color: '#94A3B8' }}>掌握 {val}%</div>
              </div>
            </div>
          ))}
        </div>
      </motion.div>

      {/* 使用时长限制设置 */}
      <motion.div className="lf-card" style={{ marginTop: 16 }} initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
        <div style={{ fontSize: 13, color: '#64748b', marginBottom: 8, fontWeight: 600 }}>每日学习时长上限</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <input
            type="range" min={20} max={120} step={5} value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            style={{ flex: 1, accentColor: '#3BA9C9' }}
            aria-label="每日学习时长上限（分钟）"
          />
          <span style={{ fontSize: 18, fontWeight: 800, color: '#2C6E8F', minWidth: 70 }}>{limit} 分钟</span>
          <button className="lf-btn lf-btn-primary" onClick={saveLimit}>{limitSaved ? '已保存 ✓' : '保存'}</button>
        </div>
        <p style={{ fontSize: 11, color: '#94A3B8', margin: '8px 0 0' }}>
          达到上限后 LearnFlow 会温柔提醒休息，保护孩子的用眼与专注健康。
        </p>
      </motion.div>
    </div>
  );
}
