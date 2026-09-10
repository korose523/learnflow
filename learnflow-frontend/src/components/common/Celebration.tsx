import React, { useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMotionPref } from '../../contexts/MotionContext';

/**
 * 庆祝动效（成功庆祝 / celebration of success，对应游戏感要素）。
 * 伦理约束（Nir Eyal / McGonigal「自我拓展」）：
 *  - 仅在「真实学习里程碑」触发——完成目标、健康状态、与宠物互动等用户自主行为；
 *  - 文案庆祝「掌握与成长」，绝不暗示「断了连胜就前功尽弃」等损失厌恶；
 *  - 减弱动效时仅显示文案卡片、不放粒子，保证可达性。
 * 不依赖任何第三方 confetti 库（纯 framer-motion 实现，零新增依赖）。
 */
const COLORS = ['#3BA9C9', '#9B7EDE', '#E68A3C', '#3FA66A', '#E0533D', '#FBBF24'];

export default function Celebration({
  fire,
  message,
  emoji = '🎉',
  onDone,
}: {
  fire: boolean;
  message?: string;
  emoji?: string;
  onDone?: () => void;
}) {
  const { reduced } = useMotionPref();

  const pieces = useMemo(
    () =>
      Array.from({ length: 30 }, (_, i) => ({
        id: i,
        x: (Math.random() * 2 - 1) * 200,
        y: -(120 + Math.random() * 170),
        rot: Math.random() * 540 - 270,
        color: COLORS[i % COLORS.length],
        delay: Math.random() * 0.12,
        size: 6 + Math.random() * 9,
        round: Math.random() > 0.5,
      })),
    // 仅在 fire 边沿重新生成粒子
    [fire],
  );

  useEffect(() => {
    if (!fire) return;
    const t = setTimeout(() => onDone?.(), reduced ? 1400 : 1700);
    return () => clearTimeout(t);
  }, [fire, reduced, onDone]);

  return (
    <AnimatePresence>
      {fire && (
        <motion.div
          key="celebrate"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          aria-live="polite"
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9998,
            pointerEvents: 'none',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 14,
          }}
        >
          {!reduced &&
            pieces.map((p) => (
              <motion.span
                key={p.id}
                initial={{ x: 0, y: 0, opacity: 1, rotate: 0, scale: 1 }}
                animate={{ x: p.x, y: p.y, opacity: [1, 1, 0], rotate: p.rot, scale: 0.6 }}
                transition={{ duration: 1.3, delay: p.delay, ease: 'easeOut' }}
                style={{
                  position: 'absolute',
                  width: p.size,
                  height: p.size,
                  borderRadius: p.round ? '50%' : 2,
                  background: p.color,
                }}
              />
            ))}

          {message && (
            <motion.div
              initial={reduced ? { opacity: 0 } : { opacity: 0, scale: 0.85, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              className="lf-glass lf-pop"
              style={{
                padding: '16px 22px',
                borderRadius: 18,
                fontSize: 16,
                fontWeight: 700,
                color: '#2C6E8F',
                textAlign: 'center',
                maxWidth: 360,
                boxShadow: '0 18px 44px rgba(44, 110, 143, 0.22)',
              }}
            >
              <div style={{ fontSize: 30, marginBottom: 6 }}>{emoji}</div>
              {message}
            </motion.div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
