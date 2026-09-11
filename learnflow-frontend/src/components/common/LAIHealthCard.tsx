import React from 'react';
import { motion } from 'framer-motion';
import { Activity, ShieldAlert, Bell, Coffee, Sparkles, Lightbulb } from 'lucide-react';
import { EASE_SOFT } from '../../theme/tokens';
import { Bar, Badge } from './ui';

// LAI 风险档 → 颜色 / 文案（与后端 LAIRiskTier 对齐）
const TIER_META: Record<string, { label: string; color: string; bg: string }> = {
  L1_NORMAL: { label: '健康动机层', color: '#3FA66A', bg: '#F0FDF4' },
  L2_WATCH: { label: '投入关注层', color: '#3BA9C9', bg: '#EAF6FB' },
  L3_DEEP: { label: '深度成瘾层', color: '#F59E0B', bg: '#FEFCE8' },
  L4_PATHOLOGICAL: { label: '病理成瘾层', color: '#E0533D', bg: '#FEF2F2' },
};

// 五维：键 → { 中文标签, 权重 }（键需与后端 learning_addiction_index.py dimensions 对齐）
const DIM_META: Record<string, { label: string; weight: number }> = {
  time: { label: '时间投入', weight: 0.30 },
  motivation: { label: '动机结构', weight: 0.25 },
  control: { label: '行为控制', weight: 0.25 },
  cognition: { label: '认知', weight: 0.10 },
  function: { label: '功能影响', weight: 0.10 },
};

// 分数(0-100, 越高越健康) → 颜色（与风险仪表相反的语义）
function scoreColor(score: number): string {
  if (score >= 80) return '#3FA66A';
  if (score >= 50) return '#3BA9C9';
  if (score >= 20) return '#F59E0B';
  return '#E0533D';
}

function Gauge({ score, size = 132 }: { score: number; size?: number }) {
  const color = scoreColor(score);
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score)) / 100;
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EEF2F6" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }} animate={{ strokeDashoffset: c * (1 - pct) }}
          transition={{ duration: 0.9, ease: EASE_SOFT }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontSize: size * 0.24, fontWeight: 800, color, fontFamily: "'Baloo 2',sans-serif" }}>{Math.round(score)}</div>
        <div style={{ fontSize: 11, color: '#94A3B8' }}>学习健康分</div>
      </div>
    </div>
  );
}

function Flag({ on, icon, label }: { on: boolean; icon: React.ReactNode; label: string }) {
  if (!on) return null;
  return (
    <Badge color="#E0533D" bg="#FEF2F2">
      {icon}{label}
    </Badge>
  );
}

export default function LAIHealthCard({ data }: { data: any }) {
  const score = data?.overall_score ?? 0;
  const tierName = data?.risk_tier || 'L1_NORMAL';
  const meta = TIER_META[tierName] || TIER_META.L1_NORMAL;
  const dims: Record<string, any> = data?.dimensions || {};
  const adj = data?.gamification_adjustments || {};

  // ── 测量覆盖度 ──────────────────────────────────────────────────────────
  // 未测维度在后端不参与加权（weighted_score=0）。若把它当作「0 分」渲染，
  // 会造成与真实相反的误读（看起来像最差）。因此这里必须区分：
  //   已测 → 显示归一化后的**实际**权重占比与分数
  //   未测 → 显示「未测量」，不显示分数、不显示风险标记
  const coverage: any = data?.coverage || null;
  const measuredSet: Set<string> = new Set<string>(
    coverage?.measured ?? Object.keys(DIM_META)
  );
  const weightBasis: number = coverage?.weight_basis ?? 1;
  /** 该维度在综合分中的实际权重占比（已测维度按 weight_basis 归一化）。 */
  const effectiveWeight = (key: string): number =>
    measuredSet.has(key) && weightBasis > 0
      ? DIM_META[key].weight / weightBasis
      : DIM_META[key].weight;
  const coveragePct = Math.round(weightBasis * 100);
  const unmeasuredLabels = (coverage?.unmeasured ?? [])
    .map((k: string) => DIM_META[k]?.label ?? k);
  // 待补测的量表名（来自 dashboard 的 measurement.missing_instruments）
  const missingInstruments: string[] = (
    data?.measurement?.missing_instruments ?? data?.missing_instruments ?? []
  ).map((m: any) => m?.name_zh ?? m?.code).filter(Boolean);

  return (
    <motion.div
      className="lf-card"
      initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE_SOFT }}
      style={{ padding: 20, borderLeft: `4px solid ${meta.color}` }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <Activity size={18} color={meta.color} />
        <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#2C6E8F', fontFamily: "'Baloo 2','Nunito','Noto Sans SC',sans-serif" }}>
          学习健康分（LAI）
        </h3>
        <span style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700, color: meta.color, background: meta.bg }}>
          {meta.label}
        </span>
      </div>

      {/* 覆盖率披露：分数必须与「基于多少测量」一起呈现 */}
      {coverage && (
        <div style={{
          marginBottom: 12, padding: '8px 12px', borderRadius: 10,
          background: coverage.complete ? '#F0FDF4' : '#FFFBEB',
          border: `1px solid ${coverage.complete ? '#BBF7D0' : '#FDE68A'}`,
          fontSize: 12, color: '#64748B', lineHeight: 1.6,
        }}>
          <strong style={{ color: coverage.complete ? '#3FA66A' : '#B45309' }}>
            测量覆盖度 {coveragePct}%
          </strong>
          <span style={{ marginLeft: 4 }}>
            {coverage.complete
              ? '五个维度均已由真实数据支撑'
              : `未测量：${unmeasuredLabels.join('、')} —— 健康分仅在已测维度上重新归一化，未测维度不计入，也不视为「健康」`}
          </span>
          {!coverage.complete && missingInstruments.length > 0 && (
            <div style={{ marginTop: 4, color: '#92400E' }}>
              补测可提升覆盖度：{missingInstruments.join('、')}
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
        <Gauge score={score} />
        <div style={{ flex: 1, minWidth: 220 }}>
          {/* 五维明细 */}
          <div style={{ display: 'grid', gap: 9 }}>
            {Object.keys(DIM_META).map((key) => {
              const d = dims[key] || {};
              const measured = measuredSet.has(key);
              const w = d.weighted_score ?? 0;
              const flag = measured && d.risk_flag;
              const effW = effectiveWeight(key);
              return (
                <div key={key}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#64748B', marginBottom: 3 }}>
                    <span>{DIM_META[key].label}
                      <span style={{ color: '#94A3B8', marginLeft: 4 }}>
                        {/* 未测维度不参与加权，显示名义权重会让人误以为它计入综合分，
                            故明确标注「不计入」而非给出百分比。 */}
                        {measured
                          ? `权重 ${(effW * 100).toFixed(0)}%`
                          : `名义权重 ${(DIM_META[key].weight * 100).toFixed(0)}% · 不计入`}
                      </span>
                      {flag && <span style={{ color: '#E0533D', marginLeft: 6 }}>⚠ 风险</span>}
                      {!measured && <span style={{ color: '#B45309', marginLeft: 6 }}>未测量</span>}
                    </span>
                    <span style={{ fontWeight: 700, color: !measured ? '#CBD5E1' : flag ? '#E0533D' : '#2C6E8F' }}>
                      {measured ? Math.round(w) : '—'}
                    </span>
                  </div>
                  <Bar value={measured ? w / 100 : 0} color={flag ? '#E0533D' : measured ? scoreColor(w) : '#E2E8F0'} />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 自动干预措施（抗成瘾层 → 游戏化自适应联动） */}
      {(data?.should_reduce_gamification || data?.should_notify_guardian ||
        data?.should_force_break || data?.autonomy_support_boost) && (
        <div style={{ marginTop: 14, padding: 12, background: '#F7FBFD', borderRadius: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#2C6E8F', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <ShieldAlert size={14} color="#E0533D" /> 系统已自动采取的措施
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <Flag on={data.should_reduce_gamification} icon={<ShieldAlert size={12} />} label="降低游戏化强度" />
            <Flag on={data.should_notify_guardian} icon={<Bell size={12} />} label="已通知家长" />
            <Flag on={data.should_force_break} icon={<Coffee size={12} />} label={`强制休息 ${adj.forced_break_minutes ?? 10} 分钟`} />
            <Flag on={data.autonomy_support_boost} icon={<Sparkles size={12} />} label="增强自主性支持" />
          </div>
          <div style={{ marginTop: 8, fontSize: 11, color: '#64748B' }}>
            排行榜可见：{adj.leaderboard_visible === false ? '已隐藏（去攀比）' : '保留'} ·
            变比率奖励概率：{(adj.variable_ratio_probability ?? 0.25).toFixed(2)}
          </div>
        </div>
      )}

      {/* 个性化建议 */}
      {Array.isArray(data?.recommendations) && data.recommendations.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#2C6E8F', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Lightbulb size={14} color="#E68A3C" /> 个性化改善建议
          </div>
          <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13, color: '#475569', lineHeight: 1.7 }}>
            {data.recommendations.slice(0, 4).map((r: string, i: number) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  );
}
