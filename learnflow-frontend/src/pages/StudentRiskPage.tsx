import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, Sparkles, Moon, Sun, RefreshCw, AlertTriangle } from 'lucide-react';
import { analyticsApi } from '../services/api';
import { seedDemoEvents, DEMO_STUDENTS, DemoStudent } from '../utils/analyticsDemo';
import { Card, RiskGauge, RiskTierBadge, Bar, EmptyState, Badge } from '../components/common/ui';
import PageHeader from '../components/common/PageHeader';
import { EASE_SOFT } from '../theme/tokens';

interface RiskData {
  user_id: string;
  ml_risk: number;
  risk_tier: number;
  top_factors: Array<[string, number]>;
}

function localEpoch(hour: number): number {
  const d = new Date();
  d.setHours(hour, Math.floor(Math.random() * 60), 0, 0);
  return Math.floor(d.getTime() / 1000);
}
const FACTOR_LABELS: Record<string, string> = {
  correct_rate: '正确率', hint_rate: '提示依赖', skip_rate: '跳过率',
  wrong_streak: '连续错误', thinking_norm: '思考时长', night_ratio: '夜间占比',
  intensity_10m: '近10分钟强度', variability: '间隔波动', difficulty_mean: '平均难度',
  immersive_ratio: '沉浸占比', session_switch: '会话切换', recency_gap: '距上次间隔',
  duration_norm: '窗口时长', engagement: '参与强度',
};

export default function StudentRiskPage() {
  const [seeded, setSeeded] = useState(false);
  const [students, setStudents] = useState<DemoStudent[]>([]);
  const [selected, setSelected] = useState<string>('');
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState('');

  const loadRisk = useCallback(async (userId: string) => {
    setLoading(true);
    try {
      const { data } = await analyticsApi.studentRisk(userId);
      setRisk(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || '获取风险失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const doSeed = async () => {
    setSeeding(true); setError('');
    try {
      const list = await seedDemoEvents((events) => analyticsApi.ingest(events));
      setStudents(list);
      setSeeded(true);
      const first = list[0].id;
      setSelected(first);
      await loadRisk(first);
    } catch (e: any) {
      setError(e?.response?.data?.detail || '生成演示数据失败（请确认后端已启动且加载了训练模型）');
    } finally {
      setSeeding(false);
    }
  };

  const simulate = async (kind: 'risky' | 'healthy') => {
    if (!selected) return;
    const event =
      kind === 'risky'
        ? { user_id: selected, event_type: 'ANSWERED', created_at: localEpoch(1), is_correct: false,
            hints_used: 6, thinking_ms: 1800, skipped: true, session_id: `${selected}-s1`,
            decision_snapshot: { fused_d: 92, zone: 'surface' } }
        : { user_id: selected, event_type: 'ANSWERED', created_at: localEpoch(15), is_correct: true,
            hints_used: 0, thinking_ms: 21000, skipped: false, session_id: `${selected}-s1`,
            decision_snapshot: { fused_d: 48, zone: 'flow' } };
    setLoading(true);
    try {
      await analyticsApi.studentEvent(selected, event);
      await loadRisk(selected);
    } finally { setLoading(false); }
  };

  const selectStudent = (id: string) => { setSelected(id); loadRisk(id); };

  return (
    <div>
      <PageHeader
        icon={<Activity size={24} color="#2C6E8F" />}
        title="AI 实时风险洞察"
        subtitle="基于「特征管线 → 时序风险模型」的在线评估（论文 AUROC≈0.97）。数据为演示用合成行为流。"
        action={
          <button className="lf-btn lf-btn-primary" onClick={doSeed} disabled={seeding} style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
            <RefreshCw size={16} className={seeding ? 'spin' : ''} /> {seeded ? '重新生成演示数据' : '生成演示数据'}
          </button>
        }
      />

      {error && (
        <div className="lf-card" style={{ background: '#FEF2F2', borderLeft: '4px solid #E0533D', color: '#B91C1C', fontSize: 14, padding: 14 }}>
          <AlertTriangle size={16} style={{ verticalAlign: 'middle', marginRight: 6 }} />{error}
        </div>
      )}

      {!seeded && (
        <Card>
          <EmptyState
            title="尚无分析数据"
            desc="点击右上角「生成演示数据」，将灌入 12 名合成学生的行为事件流，随后即可查看每位学生的实时风险与早期预警。"
            action={<button className="lf-btn lf-btn-primary" onClick={doSeed} disabled={seeding}><Sparkles size={16} /> 生成演示数据</button>}
          />
        </Card>
      )}

      {seeded && (
        <>
          {/* 学生选择 */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
            {students.map((s) => {
              const active = s.id === selected;
              return (
                <button key={s.id} onClick={() => selectStudent(s.id)}
                  style={{
                    padding: '8px 14px', borderRadius: 999, border: '1px solid', cursor: 'pointer',
                    borderColor: active ? '#3BA9C9' : '#E3EEF3',
                    background: active ? '#EAF6FB' : '#fff', color: active ? '#2C6E8F' : '#64748B',
                    fontWeight: active ? 700 : 500, fontSize: 13, transition: 'all 0.2s',
                  }}>
                  {s.name}
                  <span style={{ marginLeft: 6, fontSize: 11, color: s.profile === 'high' ? '#E0533D' : s.profile === 'watch' ? '#F59E0B' : '#3FA66A' }}>
                    {s.profile === 'high' ? '高危' : s.profile === 'watch' ? '观察' : '健康'}
                  </span>
                </button>
              );
            })}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, 320px) 1fr', gap: 20, alignItems: 'start' }}>
            {/* 左：风险仪表 */}
            <Card title="实时风险" icon={<Activity size={18} />} subtitle="数值越高，成瘾化风险越大">
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
                <AnimatePresence mode="wait">
                  <motion.div key={risk ? Math.round(risk.ml_risk * 1000) : 'x'} initial={{ opacity: 0.4 }} animate={{ opacity: 1 }}>
                    {risk && <RiskGauge value={risk.ml_risk} tier={risk.risk_tier} size={170} />}
                  </motion.div>
                </AnimatePresence>
                {risk && <RiskTierBadge tier={risk.risk_tier} />}
                <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                  <button className="lf-btn lf-btn-ghost" onClick={() => simulate('risky')} disabled={loading} style={{ display: 'inline-flex', gap: 5, alignItems: 'center', color: '#E0533D' }}>
                    <Moon size={14} /> 深夜疲劳答题
                  </button>
                  <button className="lf-btn lf-btn-ghost" onClick={() => simulate('healthy')} disabled={loading} style={{ display: 'inline-flex', gap: 5, alignItems: 'center', color: '#3FA66A' }}>
                    <Sun size={14} /> 心流健康答题
                  </button>
                </div>
                <p style={{ fontSize: 12, color: '#94A3B8', textAlign: 'center', margin: 0 }}>点击上方按钮模拟一次答题，观察风险实时变化</p>
              </div>
            </Card>

            {/* 右：驱动因子 + 说明 */}
            <div style={{ display: 'grid', gap: 20 }}>
              <Card title="风险驱动因子（Top 3）" icon={<AlertTriangle size={18} />} subtitle="当前窗口内贡献最大的行为特征">
                {risk && risk.top_factors.length > 0 ? (
                  <div style={{ display: 'grid', gap: 12 }}>
                    {risk.top_factors.map(([k, v], i) => (
                      <div key={k}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                          <span style={{ fontWeight: 600, color: '#2C6E8F' }}>{FACTOR_LABELS[k] || k}</span>
                          <span style={{ color: '#64748B' }}>{v.toFixed(2)}</span>
                        </div>
                        <Bar value={v} color={v > 0.6 ? '#E0533D' : v > 0.35 ? '#F59E0B' : '#3BA9C9'} />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: '#94A3B8', fontSize: 13 }}>暂无足够行为数据。</p>
                )}
              </Card>

              <Card title="闭环说明" icon={<Sparkles size={18} />}>
                <p style={{ margin: 0, fontSize: 14, color: '#475569', lineHeight: 1.7 }}>
                  风险模型实时消费你的行为事件流（正确率、提示依赖、夜间占比、思考时长、沉浸占比等 14 维特征），
                  经滚动窗口聚合后由时序 MLP 输出 0–1 风险指数。该指数驱动
                  <Badge color="#9B7EDE">RL 仲裁器</Badge> 在风险档下选择干预机制，并以
                  <b style={{ color: '#2C6E8F' }}> LAI 改善</b>作为奖励信号在线学习——
                  与抗成瘾层（班级宠物 + 风险自适应降权）共同构成「实时识别 + 自适应干预」双层防护。
                </p>
              </Card>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
