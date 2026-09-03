import React from 'react';
import { motion } from 'framer-motion';
import { Coffee, Leaf } from 'lucide-react';
import { useMotionPref } from '../../contexts/MotionContext';
import { EASE_SOFT } from '../../theme/tokens';

interface RestGuideProps {
  /** 已专注分钟数 */
  minutes: number;
  /** 建议休息阈值（分钟） */
  threshold?: number;
  /** 用户关闭提示 */
  onDismiss?: () => void;
}

const REST_TIPS = [
  '站起来伸个懒腰，给眼睛放个假 👀',
  '喝一口温水，补充水分 💧',
  '看看窗外远处，放松睫状肌 🌿',
  '做三次深呼吸，回到平静 🧘',
];

/**
 * 25 分钟休息引导（Spec §8 AC9）。
 * 达到阈值后显示鼓励式休息提示，尊重"动效减弱"。
 */
export default function RestGuide({ minutes, threshold = 25, onDismiss }: RestGuideProps) {
  const { reduced } = useMotionPref();
  const shouldRest = minutes >= threshold;
  if (!shouldRest) return null;

  const tip = REST_TIPS[Math.floor(minutes / threshold) % REST_TIPS.length];

  return (
    <motion.div
      initial={reduced ? false : { opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.45, ease: EASE_SOFT }}
      role="status"
      aria-live="polite"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        padding: '16px 20px',
        borderRadius: 20,
        background: 'linear-gradient(135deg, #F3EEFC 0%, #EAF6FB 100%)',
        boxShadow: '0 4px 16px rgba(155,126,222,0.18)',
        border: '1px solid #E6DEF8',
      }}
    >
      <motion.div
        className="pet-breathing"
        animate={reduced ? {} : { scale: [1, 1.08, 1] }}
        transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          width: 48, height: 48, flexShrink: 0,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: '#fff', borderRadius: 16, fontSize: 26,
        }}
      >
        🌿
      </motion.div>

      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 700, color: '#2C6E8F', fontSize: 15 }}>
          <Leaf size={16} color="#9B7EDE" />
          你已经专注 {minutes} 分钟啦！
        </div>
        <div style={{ fontSize: 13, color: '#64748b', marginTop: 2 }}>
          休息一下更聪明：{tip}
        </div>
      </div>

      {onDismiss && (
        <button
          onClick={onDismiss}
          className="tap-target"
          aria-label="我知道了"
          style={{
            border: 'none', background: 'rgba(255,255,255,0.7)', color: '#9B7EDE',
            borderRadius: 14, padding: '8px 14px', fontWeight: 600, cursor: 'pointer',
            fontSize: 13, fontFamily: "'Inter','Noto Sans SC',sans-serif",
          }}
        >
          <Coffee size={14} style={{ verticalAlign: 'middle', marginRight: 4 }} />
          稍后
        </button>
      )}
    </motion.div>
  );
}
