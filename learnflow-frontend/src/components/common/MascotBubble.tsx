import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, RefreshCw } from 'lucide-react';
import { useMotionPref } from '../../contexts/MotionContext';
import { EASE_SOFT } from '../../theme/tokens';

/**
 * 陪伴型吉祥物（情感化角色 / emotion-powered character）。
 * 设计意图（对应研究结论）：
 *  - GameFlow/SDT「归属感(relatedness)」：一个稳定的、有温度的伙伴在场；
 *  - 2025 视觉趋势「emotion-powered characters」：用角色承载鼓励而非说教；
 *  - 伦理游戏化（Eyal/McGonigal）：所有提示都是「自我拓展」导向——鼓励休息、
 *    关注自身节奏、去攀比，绝不使用负罪感 / 损失厌恶 / 强迫回流等黑暗模式。
 * 提示内容可在外部按角色/学情注入；默认给一组健康正向的通用提示。
 */
const DEFAULT_TIPS = [
  '你今天的专注度很棒！记得每 20 分钟抬头看看远处 🌿',
  '完成一个小目标就值得鼓掌，不必和别人比 👏',
  '如果有点累，试试顶部的「放松模式」深呼吸一会儿 🧘',
  '大脑喜欢规律作息，今晚早点睡能记得更牢 🌙',
  '遇到难题别急，拆成小步更容易进入心流 💡',
  '你刚才坚持了一会儿，这就是成长型思维在发芽 🌱',
];

export default function MascotBubble({
  tips = DEFAULT_TIPS,
  emoji = '🦉',
  name = '小流',
}: {
  tips?: string[];
  emoji?: string;
  name?: string;
}) {
  const { reduced } = useMotionPref();
  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(() => Math.floor(Math.random() * tips.length));
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  const tip = tips[idx];
  const next = () => setIdx((i) => (i + 1) % tips.length);

  return (
    <div className="lf-mascot" aria-live="polite">
      <AnimatePresence>
        {open && (
          <motion.div
            key="bubble"
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: 12, scale: 0.94 }}
            transition={{ duration: 0.3, ease: EASE_SOFT }}
            className="lf-glass"
            style={{
              maxWidth: 280,
              padding: '12px 14px',
              borderRadius: 18,
              borderBottomLeftRadius: 6,
              fontSize: 13,
              lineHeight: 1.6,
              color: '#2C6E8F',
              position: 'relative',
            }}
          >
            <button
              onClick={() => setDismissed(true)}
              aria-label="关闭陪伴提示"
              className="tap-target"
              style={{ position: 'absolute', top: 6, right: 6, border: 'none', background: 'transparent', color: '#94A3B8', cursor: 'pointer', padding: 4, borderRadius: 8 }}
            >
              <X size={14} />
            </button>
            <div style={{ fontWeight: 700, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>{emoji}</span> {name}说
            </div>
            <div>{tip}</div>
            <button
              onClick={next}
              className="tap-target lf-btn"
              style={{ marginTop: 10, padding: '6px 12px', fontSize: 12, background: '#EAF6FB', color: '#2C6E8F', borderRadius: 12, border: 'none', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 4 }}
            >
              <RefreshCw size={12} /> 换一条
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? '收起陪伴提示' : '查看陪伴提示'}
        aria-expanded={open}
        className="lf-glass lf-glow tap-target"
        whileTap={reduced ? undefined : { scale: 0.9 }}
        style={{
          width: 56, height: 56, borderRadius: '50%',
          border: 'none', cursor: 'pointer',
          fontSize: 30, lineHeight: 1,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        }}
      >
        {emoji}
      </motion.button>
    </div>
  );
}
