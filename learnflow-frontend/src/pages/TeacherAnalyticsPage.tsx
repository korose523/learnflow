import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Activity, ShieldAlert, RefreshCw, TrendingUp, AlertTriangle, Info } from 'lucide-react';
import { analyticsApi } from '../services/api';
import { seedDemoEvents, DEMO_STUDENTS, DEMO_CLASS_ID, DemoStudent } from '../utils/analyticsDemo';
import { Card, StatTile, RiskTierBadge, Bar, EmptyState, Badge, RISK_TIERS } from '../components/common/ui';
import PageHeader from '../components/common/PageHeader';
import { EASE_SOFT } from '../theme/tokens';

// 论文表 3 / 图 3 权威数值（来自 artifacts/ai_layer/result.json）
const PAPER = { auroc: 0.966, recall: 0.98, delta: 0.468, n: 600 };

interface ClassRisk { mean_risk: number; students: number; distribution: Record<string, number>; }
interface Warning { user_id: string; risk: number; factors: Array<[string, number]>; }

const nameOf = (id: string) => DEMO_STUDENTS.find((s) => s.id === id)?.name || id;
const FACTOR_LABELS: Record<string, string> = {
  correct_rate: '正确率', hint_rate: '提示依赖', skip_rate: '跳过率', wrong_streak: '连续错误',
  thinking_norm: '思考时长', night_ratio: '夜间占比', intensity_10m: '强度', variability: '间隔波动',
  difficulty_mean: '难度', immersive_ratio: '沉浸占比', session_switch: '切换', recency_gap: '间隔',
  duration_norm: '时长', engagement: '参与',
};

export default function TeacherAnalyticsPage() {
  const [seeded, setSeeded] = useState(false);
  const [classRisk, setClassRisk] = useState<ClassRisk | null>(null);
  const [warnings, setWarnings] = useState<Warning[]>([]);
  const [loading, setLoading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState('');

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const ids = DEMO_STUDENTS.map((s) => s.id);
      const [cr, ew] = await Promise.all([
        analyticsApi.classRisk(DEMO_CLASS_ID, ids),
        analyticsApi.earlyWarning(DEMO_CLASS_ID, 0.5, ids),
      ]);
      setClassRisk(cr.data);
      setWarnings(ew.data.warnings || []);
    } catch (e: any) {
      setError(e?.response?.data?.detail || '获取班级分析失败');
    } finally { setLoading(false); }
  }, []);

  const doSeed = async () => {
    setSeeding(true); setError('');
    try {
      await seedDemoEvents((events) => analyticsApi.ingest(events));
      setSeeded(true);
      await loadAll();
    } catch (e: any) {
      setError(e?.response?.data?.detail || '生成演示数据失败（请确认后端已启动且加载了训练模型）');
    } finally { setSeeding(false); }
  };

  const dist = classRisk?.distribution || { '0': 0, '1': 0, '2': 0, '3': 0 };
  const total = classRisk ? classRisk.students : 0;

  return (
    <div>
      <PageHeader
        icon={<ShieldAlert size={24} color="#2C6E8F" />}
        title="AI 实时分析 · 班级防护"
        subtitle="班级风险总览与早期预警（论文 AUROC≈0.97，召回 98%）。演示用合成数据。"
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
            title="尚未加载分析数据"
            desc="点击右上角「生成演示数据」，灌入 12 名合成学生的行为事件流，即可查看班级风险分布与高危学生早期预警名单。"
            action={<button className="lf-btn lf-btn-primary" onClick={doSeed} disabled={seeding}><Activity size={16} /> 生成演示数据</button>}
          />
        </Card>
      )}

      {seeded && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 20 }}>
            <StatTile label="班级平均风险" value={classRisk ? Math.round(classRisk.mean_risk * 100) : 0} unit="%" accent="#2C6E8F" icon={<TrendingUp size={14} />} hint="越高越需关注" />
            <StatTile label="预警学生数" value={warnings.length} accent="#E0533D" icon={<ShieldAlert size={14} />} hint="风险≥0.5 阈值" />
            <StatTile label="模型 AUROC" value={PAPER.auroc.toFixed(3)} accent="#3FA66A" icon={<Activity size={14} />} hint={`N=${PAPER.n} 合成样本`} />
            <StatTile label="早期预警召回" value={Math.round(PAPER.recall * 100)} unit="%" accent="#3BA9C9" icon={<AlertTriangle size={14} />} hint="高危识别率" />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>
            {/* 风险分布 */}
            <Card title="班级风险分布" icon={<TrendingUp size={18} />} subtitle="按风险档（健康/观察/预警/高危）统计人数">
              <div style={{ display: 'grid', gap: 12 }}>
                {RISK_TIERS.map((t) => {
                  const count = dist[String(t.tier)] || 0;
                  return (
                    <div key={t.tier}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, color: t.color }}>{t.label}</span>
                        <span style={{ color: '#64748B' }}>{count} 人 · {total ? Math.round((count / total) * 100) : 0}%</span>
                      </div>
                      <Bar value={total ? count / total : 0} color={t.color} height={10} />
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* 早期预警名单 */}
            <Card title="早期预警名单" icon={<ShieldAlert size={18} />} subtitle={`风险 ≥ 0.5，按风险降序（共 ${warnings.length} 人）`}>
              {warnings.length === 0 ? (
                <p style={{ color: '#94A3B8', fontSize: 13 }}>暂无达到预警阈值的学生 🎉</p>
              ) : (
                <div style={{ display: 'grid', gap: 10, maxHeight: 320, overflowY: 'auto' }}>
                  {warnings.map((w) => (
                    <motion.div key={w.user_id}
                      initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }}
                      style={{ border: '1px solid #FEE2E2', background: '#FFF7F7', borderRadius: 14, padding: 12 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontWeight: 700, color: '#2C6E8F' }}>{nameOf(w.user_id)}</span>
                        <RiskTierBadge tier={w.risk >= 0.6 ? 3 : w.risk >= 0.35 ? 2 : 1} />
                      </div>
                      <div style={{ fontSize: 12, color: '#64748B', marginTop: 4 }}>
                        风险指数 <b style={{ color: '#E0533D' }}>{Math.round(w.risk * 100)}</b>
                        {w.factors?.length > 0 && ` · 主要信号：${w.factors.map(([k]) => FACTOR_LABELS[k] || k).join('、')}`}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* AI 层论文支撑 */}
          <Card title="AI 实时分析层 · 论文支撑（表 3 / 图 3）" icon={<Info size={18} />}
            subtitle="时序风险模型在合成样本上的表现；ROC 曲线见下图"
            style={{ marginTop: 20 }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 240px', gap: 20, alignItems: 'center' }}>
              <div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ color: '#64748B', textAlign: 'left' }}>
                      <th style={{ padding: '6px 8px' }}>模型</th>
                      <th style={{ padding: '6px 8px' }}>AUROC</th>
                      <th style={{ padding: '6px 8px' }}>说明</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderTop: '1px solid #EEF2F6' }}>
                      <td style={{ padding: '8px' }}>规则基线（夜间比例）</td>
                      <td style={{ padding: '8px' }}>0.498</td>
                      <td style={{ padding: '8px', color: '#94A3B8' }}>纯启发式</td>
                    </tr>
                    <tr style={{ borderTop: '1px solid #EEF2F6', background: '#F0FDF4' }}>
                      <td style={{ padding: '8px', fontWeight: 700, color: '#2C6E8F' }}>ML 时序风险模型</td>
                      <td style={{ padding: '8px', fontWeight: 700, color: '#3FA66A' }}>0.966</td>
                      <td style={{ padding: '8px', color: '#94A3B8' }}>本层主模型（Δ +{PAPER.delta}）</td>
                    </tr>
                  </tbody>
                </table>
                <p style={{ fontSize: 12, color: '#94A3B8', margin: '10px 0 0' }}>
                  声明：计算式 / 设计验证（in-silico），非田野实验；proxy 标签来自植入的「成瘾签名」，用于证明管线可学习。
                </p>
              </div>
              <img src="/roc_curve.svg" alt="ROC 曲线" style={{ width: '100%', borderRadius: 12, border: '1px solid #EEF2F6' }} />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
