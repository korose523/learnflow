import React from 'react';
import { motion } from 'framer-motion';
import { EASE_SOFT } from '../../theme/tokens';
import { useMotionPref } from '../../contexts/MotionContext';

// ─── 风险档元数据（与后端 TemporalRiskModel.risk_tier 阈值对齐）───
// 0:<0.15  1:<0.35  2:<0.6  3:else
export const RISK_TIERS = [
  { tier: 0, label: '健康', short: '健康', color: '#3FA66A', bg: '#F0FDF4', desc: '学习状态良好，无成瘾化迹象' },
  { tier: 1, label: '观察', short: '观察', color: '#3BA9C9', bg: '#EAF6FB', desc: '存在轻度风险信号，建议持续观察' },
  { tier: 2, label: '预警', short: '预警', color: '#F59E0B', bg: '#FEFCE8', desc: '风险信号明显，需主动干预' },
  { tier: 3, label: '高危', short: '高危', color: '#E0533D', bg: '#FEF2F2', desc: '高度成瘾化风险，应立即介入' },
] as const;

export function tierFromRisk(risk: number): number {
  if (risk < 0.15) return 0;
  if (risk < 0.35) return 1;
  if (risk < 0.6) return 2;
  return 3;
}
export function tierMeta(tier: number) {
  return RISK_TIERS[Math.max(0, Math.min(3, tier))];
}

// ─── Card ───────────────────────────────────────────────
export function Card({
  children, title, icon, subtitle, style, bodyStyle, delay = 0, hover = true,
}: {
  children: React.ReactNode;
  title?: React.ReactNode;
  icon?: React.ReactNode;
  subtitle?: React.ReactNode;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
  delay?: number;
  hover?: boolean;
}) {
  const { reduced } = useMotionPref();
  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE_SOFT, delay }}
      whileHover={hover && !reduced ? { y: -3 } : undefined}
      className="lf-card"
      style={{ padding: 20, ...style }}
    >
      {(title || icon) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: subtitle ? 4 : 14 }}>
          {icon && <span style={{ color: '#3BA9C9', display: 'inline-flex' }}>{icon}</span>}
          {title && <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#2C6E8F', fontFamily: "'Baloo 2','Nunito','Noto Sans SC',sans-serif" }}>{title}</h3>}
        </div>
      )}
      {subtitle && <p style={{ margin: '0 0 14px', fontSize: 13, color: '#64748B' }}>{subtitle}</p>}
      <div style={bodyStyle}>{children}</div>
    </motion.div>
  );
}

// ─── StatTile ───────────────────────────────────────────
export function StatTile({
  label, value, unit, accent = '#2C6E8F', icon, hint,
}: {
  label: string; value: React.ReactNode; unit?: string; accent?: string; icon?: React.ReactNode; hint?: string;
}) {
  return (
    <div className="lf-stat-tile" style={{
      background: '#fff', borderRadius: 16, padding: '14px 16px',
      boxShadow: '0 4px 16px rgba(0,0,0,0.05)', position: 'relative',
    }}>
      <div style={{ fontSize: 12, color: '#64748B', display: 'flex', alignItems: 'center', gap: 6 }}>{icon}{label}</div>
      <div style={{ marginTop: 6, fontSize: 26, fontWeight: 800, color: accent, fontFamily: "'Baloo 2','Nunito',sans-serif", lineHeight: 1.1 }}>
        {value}{unit && <span style={{ fontSize: 14, fontWeight: 600, marginLeft: 2, color: '#94A3B8' }}>{unit}</span>}
      </div>
      {hint && <div style={{ fontSize: 11, color: '#94A3B8', marginTop: 2 }}>{hint}</div>}
      <span style={{ position: 'absolute', right: -10, top: -10, width: 44, height: 44, borderRadius: '50%', background: accent + '14', display: 'block' }} />
    </div>
  );
}

// ─── RiskGauge（环形风险仪表）────────────────────────────
export function RiskGauge({ value, size = 150, tier }: { value: number; size?: number; tier?: number }) {
  const t = tier ?? tierFromRisk(value);
  const meta = tierMeta(t);
  const stroke = 12;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#EEF2F6" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={meta.color} strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={{ strokeDashoffset: c * (1 - pct) }}
          transition={{ duration: 0.9, ease: EASE_SOFT }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ fontSize: size * 0.22, fontWeight: 800, color: meta.color, fontFamily: "'Baloo 2',sans-serif" }}>
          {Math.round(pct * 100)}
        </div>
        <div style={{ fontSize: 11, color: '#94A3B8' }}>风险指数</div>
        <div style={{ marginTop: 2, fontSize: 12, fontWeight: 700, color: meta.color }}>{meta.short}</div>
      </div>
    </div>
  );
}

// ─── Badge ──────────────────────────────────────────────
export function Badge({ children, color = '#3BA9C9', bg }: { children: React.ReactNode; color?: string; bg?: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4, padding: '3px 10px', borderRadius: 999,
      fontSize: 12, fontWeight: 700, color, background: bg || color + '1A',
    }}>
      {children}
    </span>
  );
}

// ─── RiskTierBadge ──────────────────────────────────────
export function RiskTierBadge({ tier }: { tier: number }) {
  const m = tierMeta(tier);
  return <Badge color={m.color} bg={m.bg}>{m.label}</Badge>;
}

// ─── SectionTitle ───────────────────────────────────────
export function SectionTitle({ children, icon }: { children: React.ReactNode; icon?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '8px 0 14px' }}>
      {icon && <span style={{ color: '#3BA9C9', display: 'inline-flex' }}>{icon}</span>}
      <h2 style={{ margin: 0, fontSize: 20, fontWeight: 800, color: '#2C6E8F', fontFamily: "'Baloo 2','Nunito','Noto Sans SC',sans-serif" }}>{children}</h2>
    </div>
  );
}

// ─── EmptyState ─────────────────────────────────────────
export function EmptyState({ title, desc, action }: { title: string; desc?: string; action?: React.ReactNode }) {
  return (
    <div style={{ textAlign: 'center', padding: '48px 20px', color: '#94A3B8' }}>
      <div style={{ fontSize: 40, marginBottom: 8 }}>🪴</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: '#475569' }}>{title}</div>
      {desc && <div style={{ fontSize: 13, marginTop: 6, maxWidth: 420, margin: '6px auto 0' }}>{desc}</div>}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  );
}

// ─── Bar（横向占比条）───────────────────────────────────
export function Bar({ value, color = '#3BA9C9', height = 8 }: { value: number; color?: string; height?: number }) {
  return (
    <div style={{ background: '#EEF2F6', borderRadius: 999, height, overflow: 'hidden' }}>
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }}
        transition={{ duration: 0.8, ease: EASE_SOFT }}
        style={{ height, background: color, borderRadius: 999 }}
      />
    </div>
  );
}
