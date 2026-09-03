import React from 'react';
import { motion } from 'framer-motion';
import { Target } from 'lucide-react';
import { useMotionPref } from '../../contexts/MotionContext';
import { EASE_SOFT, CHALLENGE_BAND } from '../../theme/tokens';

interface ChallengeBarProps {
  /** 当前难度/掌握度值（0–100）。建议维持于心流通道 75–85% 之间 */
  value: number;
  low?: number;
  high?: number;
  label?: string;
}

/**
 * 难度通道可视化（Spec §7 / Onboarding & Learn）。
 * 高亮 75–85% 的"心流通道"，标记当前值并给出颜色反馈。
 */
export default function ChallengeBar({
  value,
  low = CHALLENGE_BAND.low,
  high = CHALLENGE_BAND.high,
  label = '难度通道',
}: ChallengeBarProps) {
  const { reduced } = useMotionPref();
  const clamped = Math.max(0, Math.min(100, value));
  const inBand = clamped >= low && clamped <= high;
  const color = inBand ? '#3FA66A' : clamped < low ? '#3BA9C9' : '#E0533D';

  return (
    <div
      role="img"
      aria-label={`${label}：当前 ${clamped}%，心流通道 ${low}% 至 ${high}%`}
      style={{ width: '100%' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#64748b', fontWeight: 600 }}>
          <Target size={14} color={color} />
          {label}
        </span>
        <span style={{ fontSize: 13, fontWeight: 700, color }}>{clamped}%</span>
      </div>

      <div
        style={{
          position: 'relative',
          height: 14,
          borderRadius: 999,
          background: '#EAF6FB',
          overflow: 'hidden',
        }}
      >
        {/* 心流通道（75–85%）高亮 */}
        <div
          style={{
            position: 'absolute',
            left: `${low}%`,
            width: `${high - low}%`,
            top: 0,
            bottom: 0,
            background: 'repeating-linear-gradient(45deg, #D6F0E0, #D6F0E0 6px, #C6EBD5 6px, #C6EBD5 12px)',
          }}
        />
        {/* 当前值标记 */}
        <motion.div
          initial={reduced ? false : { left: '0%' }}
          animate={{ left: `${clamped}%` }}
          transition={{ duration: reduced ? 0 : 0.5, ease: EASE_SOFT }}
          style={{
            position: 'absolute',
            top: -3,
            width: 6,
            height: 20,
            marginLeft: -3,
            borderRadius: 999,
            background: color,
            boxShadow: '0 1px 4px rgba(0,0,0,0.2)',
          }}
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4, fontSize: 11, color: '#94A3B8' }}>
        <span>太简单</span>
        <span style={{ color: '#3FA66A', fontWeight: 600 }}>心流区 {low}–{high}%</span>
        <span>太难</span>
      </div>
    </div>
  );
}
