import React from 'react';
import { useMotionPref } from '../../contexts/MotionContext';

/**
 * 柔光氛围球背景 — 把界面「游戏世界化」的第一步（2025 视觉趋势：diffuse-light gradients）。
 * 纯装饰、无交互、无信息载荷，因此：
 *  - 固定定位 + pointer-events:none，绝不影响页面操作；
 *  - 用户开启「减弱动效」或系统偏好 reduce 时整体不渲染（呼应平台可达性基线）。
 */
const ORBS = [
  { size: 340, top: '-70px', left: '-50px', color: 'rgba(59, 169, 201, 0.34)', dur: 19, anim: 'lf-orb-float-a' },
  { size: 270, top: '26%', right: '-70px', left: undefined as any, color: 'rgba(155, 126, 222, 0.30)', dur: 23, anim: 'lf-orb-float-b' },
  { size: 230, bottom: '-50px', left: '18%', top: undefined as any, color: 'rgba(63, 166, 106, 0.26)', dur: 21, anim: 'lf-orb-float-a' },
  { size: 180, top: '58%', left: '46%', color: 'rgba(230, 138, 60, 0.20)', dur: 25, anim: 'lf-orb-float-b' },
];

export default function AmbientOrbs() {
  const { reduced } = useMotionPref();
  if (reduced) return null;
  return (
    <div aria-hidden style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden' }}>
      {ORBS.map((o, i) => (
        <span
          key={i}
          className="lf-orb"
          style={{
            width: o.size,
            height: o.size,
            top: o.top,
            left: o.left,
            right: o.right,
            bottom: o.bottom,
            background: o.color,
            animation: `${o.anim} ${o.dur}s ease-in-out infinite`,
          }}
        />
      ))}
    </div>
  );
}
