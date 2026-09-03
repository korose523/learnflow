// 设计 Token 的 JS 常量（与 tailwind.config.js / index.css 保持一致，Spec §7）

export const COLORS = {
  primaryLow: '#3BA9C9',
  primaryHigh: '#2C6E8F',
  subject: {
    math: '#4F5BD5',
    chinese: '#E0533D',
    english: '#3FA66A',
    science: '#E68A3C',
    other: '#6B7C99',
  },
  semantic: {
    success: '#3FA66A',
    hint: '#3BA9C9',
    rest: '#9B7EDE',
    risk: '#E0533D',
  },
} as const;

export type SubjectKey = keyof typeof COLORS.subject;

/** 由学科 code/名称推断主题色（大小写不敏感、支持中文名） */
export function subjectColor(subject?: string | null): string {
  if (!subject) return COLORS.subject.other;
  const s = subject.toLowerCase();
  if (s.includes('math') || s.includes('数')) return COLORS.subject.math;
  if (s.includes('chinese') || s.includes('语文') || s.includes('语')) return COLORS.subject.chinese;
  if (s.includes('english') || s.includes('英语') || s.includes('英')) return COLORS.subject.english;
  if (s.includes('science') || s.includes('科学') || s.includes('科')) return COLORS.subject.science;
  return COLORS.subject.other;
}

export const SUBJECT_META: Record<string, { label: string; emoji: string }> = {
  math: { label: '数学', emoji: '🔢' },
  chinese: { label: '语文', emoji: '📖' },
  english: { label: '英语', emoji: '🔤' },
  science: { label: '科学', emoji: '🔬' },
};

export function subjectMeta(subject?: string | null): { label: string; emoji: string } {
  if (!subject) return { label: '其他', emoji: '📚' };
  const key = subject.toLowerCase();
  if (key.includes('math') || key.includes('数')) return SUBJECT_META.math;
  if (key.includes('chinese') || key.includes('语文') || key.includes('语')) return SUBJECT_META.chinese;
  if (key.includes('english') || key.includes('英语') || key.includes('英')) return SUBJECT_META.english;
  if (key.includes('science') || key.includes('科学') || key.includes('科')) return SUBJECT_META.science;
  return { label: subject, emoji: '📚' };
}

export const EASE_SOFT = [0.22, 1, 0.36, 1] as const;
export const RADIUS = { card: 20, btn: 14, badge: 999 } as const;
export const SHADOW_SOFT = '0 4px 16px rgba(0,0,0,0.06)';

// 难度通道（Spec：75–85% 维持心流）
export const CHALLENGE_BAND = { low: 75, high: 85 } as const;
