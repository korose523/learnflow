import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, RadialBarChart, RadialBar,
} from 'recharts';
import { CalendarDays, Clock, ShieldAlert, ShieldCheck, Gauge } from 'lucide-react';
import { parentApi, laiApi } from '../services/api';
import LAIHealthCard from '../components/common/LAIHealthCard';
import MascotBubble from '../components/common/MascotBubble';
import { useMotionPref } from '../contexts/MotionContext';
import { EASE_SOFT, subjectColor, subjectMeta } from '../theme/tokens';

interface SkillMastery { skill: string; score: number; mastery: number }
interface WeeklyReport {
  duration?: { minutes?: number; sessions?: number };
  difficulty_curve?: { date: string; avg_difficulty: number }[];
  mastery?: { avg_score?: number; skills?: SkillMastery[] };
  risk_level?: 'low' | 'medium' | 'high' | 'green' | 'yellow' | 'red';
}

const RISK_META: Record<string, { label: string; color: string; icon: JSX.Element }> = {
  low: { label: '低风险', color: '#3FA66A', icon: <ShieldCheck size={16} /> },
  medium: { label: '需关注', color: '#E68A3C', icon: <ShieldAlert size={16} /> },
  high: { label: '高风险', color: '#E0533D', icon: <ShieldAlert size={16} /> },
  // 后端 /parent/weekly-report 返回的是 AlertSeverity 词汇（green / yellow / red），
  // 与前端 low / medium / high 并不一致。缺映射时 RISK_META[...] === undefined，
  // 随后读 risk.color 会抛 "Cannot read properties of undefined (reading 'color')"
  // 并整页白屏 —— 这里补齐后端词汇别名。
  green: { label: '低风险', color: '#3FA66A', icon: <ShieldCheck size={16} /> },
  yellow: { label: '需关注', color: '#E68A3C', icon: <ShieldAlert size={16} /> },
  red: { label: '高风险', color: '#E0533D', icon: <ShieldAlert size={16} /> },
};

export default function ParentPage() {
  const { reduced } = useMotionPref();
  const [report, setReport] = useState<WeeklyReport | null>(null);
  const [lai, setLai] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  // 孩子 id 解析状态：resolved 表示已尝试解析（成功或失败），hasChild 表示存在孩子账号
  const [resolved, setResolved] = useState(false);
  const [hasChild, setHasChild] = useState(true);
  // 家长端：真实孩子 id（统一使用 localStorage 单一规范键 'parent_child_id'）
  const [childId, setChildId] = useState('');
  // 每日使用时长上限（分钟）：默认 40，真实值从后端加载；后端返回 null 时保留默认显示，不静默持久化
  const [limit, setLimit] = useState<number>(40);
  const [limitSaved, setLimitSaved] = useState(false);
  const [limitSaving, setLimitSaving] = useState(false);
  const [limitError, setLimitError] = useState('');

  // 解析真实孩子 id：优先读取已存储的 'parent_child_id'，否则取 /parent/children 的第一个孩子
  useEffect(() => {
    let alive = true;
    const stored = localStorage.getItem('parent_child_id');
    if (stored) {
      setChildId(stored);
      setResolved(true);
      return;
    }
    parentApi.children()
      .then(({ data }) => {
        if (!alive) return;
        const children = data?.children || [];
        if (children.length === 0) {
          setHasChild(false);
          setLoading(false);
          setResolved(true);
          return;
        }
        const firstId = children[0].id;
        localStorage.setItem('parent_child_id', firstId);
        setChildId(firstId);
        setResolved(true);
      })
      .catch((err: any) => {
        if (!alive) return;
        setError(err?.response?.data?.detail || '无法获取孩子列表，请稍后重试');
        setLoading(false);
        setResolved(true);
      });
    return () => { alive = false; };
  }, []);

  // 孩子 id 解析完成且存在孩子时，加载周报、LAI 与每日时长上限（失败上报 error，不再静默伪装为零）
  useEffect(() => {
    if (!resolved || !hasChild || !childId) return;
    let alive = true;
    Promise.all([
      parentApi.weeklyReport({ student_id: childId }).then(({ data }) => data),
      laiApi.dashboard(childId).then(({ data }) => data),
      // 每日时长上限：失败时静默回退到默认显示值，不阻断整页加载
      parentApi.dailyLimit(childId)
        .then(({ data }) => (data?.daily_limit_minutes ?? null))
        .catch(() => null),
    ])
      .then(([rep, laiData, dailyLimit]) => {
        if (!alive) return;
        setReport(rep);
        setLai(laiData);
        if (dailyLimit !== null) setLimit(dailyLimit);
        setLoading(false);
      })
      .catch((err: any) => {
        if (!alive) return;
        setError(err?.response?.data?.detail || '加载周报失败，请稍后重试');
        setLoading(false);
      });
    return () => { alive = false; };
  }, [resolved, hasChild, childId]);

  const saveLimit = async () => {
    if (!childId) return; // 尚未解析到孩子 id：no-op，避免写入虚无
    setLimitSaving(true);
    setLimitError('');
    setLimitSaved(false);
    try {
      await parentApi.setDailyLimit(childId, limit);
      setLimitSaved(true);
      setTimeout(() => setLimitSaved(false), 2000);
    } catch (err: any) {
      setLimitError(err?.response?.data?.detail || '保存每日使用时长上限失败，请稍后重试');
    } finally {
      setLimitSaving(false);
    }
  };

  if (loading) return <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>周报加载中...</div>;
  if (error) return <div style={{ textAlign: 'center', padding: 60, color: '#E0533D' }}>{error}</div>;
  if (!hasChild) return <div style={{ textAlign: 'center', padding: 60, color: '#64748b' }}>尚未绑定孩子账号</div>;

  const risk = RISK_META[report?.risk_level ?? 'low'] ?? RISK_META.low;
  const skills = report?.mastery?.skills ?? [];

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
            {report?.duration?.minutes ?? 0} <span style={{ fontSize: 14, fontWeight: 500, color: '#94A3B8' }}>分钟</span>
          </div>
          <div style={{ fontSize: 12, color: '#94A3B8' }}>约 {Math.round((report?.duration?.minutes ?? 0) / 60 * 10) / 10} 小时</div>
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
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ borderRadius: 12, border: '1px solid #E3EEF3', fontSize: 12 }} />
              <Line type="monotone" dataKey="avg_difficulty" stroke="#3BA9C9" strokeWidth={3} dot={{ r: 3 }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <p style={{ fontSize: 11, color: '#94A3B8', margin: '4px 0 0' }}>难度按天聚合（1–10）。理想状态是维持在心流通道，过高或过低都会提示调整。</p>
      </motion.div>

      {/* 掌握度（非分数，用进度环） */}
      <motion.div className="lf-card" style={{ marginTop: 16 }} initial={reduced ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: EASE_SOFT }}>
        <div style={{ fontSize: 13, color: '#64748b', marginBottom: 12, fontWeight: 600 }}>学科掌握度（相对自身）</div>
        {skills.length === 0 && <div style={{ color: '#94A3B8', fontSize: 13 }}>暂无掌握度数据</div>}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12 }}>
          {skills.map((s) => (
            <div key={s.skill} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 56, height: 56 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadialBarChart innerRadius="70%" outerRadius="100%" data={[{ name: s.skill, value: Math.round(s.score ?? 0), fill: subjectColor(s.skill) }]} startAngle={90} endAngle={-270}>
                    <RadialBar background dataKey="value" cornerRadius={10} />
                  </RadialBarChart>
                </ResponsiveContainer>
              </div>
              <div>
                <div style={{ fontWeight: 600, color: '#2C6E8F', fontSize: 13 }}>{subjectMeta(s.skill).label}</div>
                <div style={{ fontSize: 12, color: '#94A3B8' }}>掌握 {Math.round(s.score ?? 0)}%</div>
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
            type="range" min={20} max={180} step={5} value={limit}
            onChange={e => setLimit(Number(e.target.value))}
            style={{ flex: 1, accentColor: '#3BA9C9' }}
            aria-label="每日学习时长上限（分钟）"
            disabled={!childId}
          />
          <span style={{ fontSize: 18, fontWeight: 800, color: '#2C6E8F', minWidth: 70 }}>{limit} 分钟</span>
          <button className="lf-btn lf-btn-primary" onClick={saveLimit} disabled={!childId || limitSaving}>
            {limitSaving ? '保存中…' : limitSaved ? '已保存 ✓' : '保存'}
          </button>
        </div>
        {limitError && (
          <p style={{ fontSize: 12, color: '#E0533D', margin: '8px 0 0' }}>{limitError}</p>
        )}
        <p style={{ fontSize: 11, color: '#94A3B8', margin: '8px 0 0' }}>
          该上限会保存到 LearnFlow 服务端，并在孩子端生效；达到上限后 LearnFlow 会温柔提醒休息，保护孩子的用眼与专注健康。
        </p>
      </motion.div>
    </div>
  );
}
