import React from 'react';
import { motion } from 'framer-motion';
import { EASE_SOFT } from '../../theme/tokens';

/**
 * 统一页面标题（v3 视觉语言）：左侧渐变图标芯片 + 渐变大标题 + 副标题，
 * 右侧放置操作按钮。全站复用，保证标题层级一致。
 */
export default function PageHeader({
  title, subtitle, icon, action, delay = 0,
}: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ReactNode;
  action?: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: EASE_SOFT, delay }}
      style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20, flexWrap: 'wrap' }}
    >
      {icon && (
        <span style={{
          fontSize: 26, width: 52, height: 52, flexShrink: 0,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          background: 'linear-gradient(135deg, #EAF6FB, #F2ECFE)',
          borderRadius: 16, boxShadow: '0 6px 16px rgba(44,110,143,0.10)',
        }}>
          {icon}
        </span>
      )}
      <div style={{ flex: 1, minWidth: 200 }}>
        <h1 className="lf-gradient-text" style={{ margin: 0, fontSize: 26, fontWeight: 800, lineHeight: 1.2, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {title}
          <span className="lf-deco-dots" aria-hidden style={{ marginTop: 2 }}>
            <span style={{ background: '#3BA9C9' }} />
            <span style={{ background: '#9B7EDE' }} />
            <span style={{ background: '#E68A3C' }} />
          </span>
        </h1>
        {subtitle && <p style={{ margin: '4px 0 0', color: '#64748B', fontSize: 14 }}>{subtitle}</p>}
      </div>
      {action && <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>{action}</div>}
    </motion.div>
  );
}
