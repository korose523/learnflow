import React from 'react';
import { subjectColor, subjectMeta } from '../../theme/tokens';

interface SubjectBadgeProps {
  /** 学科 code 或中文名，如 'math' / '数学' / 'english' */
  subject?: string | null;
  size?: 'sm' | 'md';
}

/** 学科色标徽章（全圆，Spec §6 SubjectBadge / 课标浏览页） */
export default function SubjectBadge({ subject, size = 'md' }: SubjectBadgeProps) {
  const meta = subjectMeta(subject);
  const color = subjectColor(subject);
  const fontSize = size === 'sm' ? 12 : 13;
  const padY = size === 'sm' ? 2 : 4;

  return (
    <span
      className="lf-badge"
      style={{
        background: `${color}1A`, // 10% 透明底色
        color,
        padding: `${padY}px 14px`,
        fontSize,
      }}
    >
      <span aria-hidden>{meta.emoji}</span>
      {meta.label}
    </span>
  );
}
