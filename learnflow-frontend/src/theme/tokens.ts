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
export const SHADOW_SOFT = '0 4px 16px rgba(0,0,0,0.06)';

// 间距阶梯（与 CSS --lf-space-* 对齐，单位 px）
export const SPACE = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 20, 6: 24, 8: 32, 10: 40 } as const;

// 难度通道（Spec：75–85% 维持心流）
export const CHALLENGE_BAND = { low: 75, high: 85 } as const;

// 注：DURATION / ELEVATION / TYPE / RADIUS_SCALE 的权威定义在**文件末尾的 v4 段**
// （标注「单一事实来源」）。本处不再重复声明——历史上此处曾有一套 v2 副本，
// 与 v4 值不一致（如 DURATION.fast 一边 0.15 一边 0.18），导致同一语义两种时长、
// 页面表现不统一，并使 tsc 报 TS2451 重复声明（被 tsbuildinfo 增量缓存掩盖）。
// RADIUS 保留为 v4 RADIUS_SCALE 的语义别名，供既有代码继续以 .card/.btn/.badge 访问。

/* =========================================================
   统一设计 Token（v4，单一事实来源）
   与 tailwind.config.js / index.css 中的 --lf-* 变量保持一致。
   配色目标：面向 K12 明快不刺眼，语义色均提供「fill 亮 / text 深一档」
   两档，文字档满足 WCAG AA（≥4.5:1）。
   ========================================================= */

// ── 中性色阶：文字 / 边框 / 背景（与 index.css --lf-neutral-* 对齐）──
export const NEUTRAL = {
  '50': '#F8FAFC',
  '100': '#F1F5F9',
  '200': '#E2E8F0',
  '300': '#CBD5E1',
  '400': '#94A3B8', // 占位 / 禁用（仅用于非必要信息）
  '500': '#64748B', // 第三级文字（AA）
  '600': '#475569', // 次要文字（AA）
  '700': '#334155',
  '800': '#1E293B',
  '900': '#0F172A', // 主文字（深青蓝黑）
} as const;

// ── 语义色：fill 用于填充/图标，text 用于小字（AA），soft 用于浅底色 ──
// 与 index.css --lf-sem-*-soft / --lf-warning-* 对齐
export const SEMANTIC = {
  success: { fill: '#3FA66A', text: '#1F8A51', soft: '#E7F6EE' },
  hint: { fill: '#3BA9C9', text: '#1F7393', soft: '#E6F4F9' },
  rest: { fill: '#9B7EDE', text: '#6D4FC0', soft: '#F1ECFB' },
  risk: { fill: '#E0533D', text: '#C0392B', soft: '#FCEDEC' },
  warning: { fill: '#E0901A', text: '#B45309', soft: '#FEF3C7' },
} as const;

// 取语义色（默认 fill 档）
export function semantic(key: keyof typeof SEMANTIC, tier: 'fill' | 'text' | 'soft' = 'fill'): string {
  return SEMANTIC[key][tier];
}

// 取中性色
export function neutral(step: keyof typeof NEUTRAL): string {
  return NEUTRAL[step];
}

// ── 圆角分级 ──
export const RADIUS_SCALE = { sm: 10, md: 14, lg: 20, pill: 999 } as const;

// ── 层次 / 阴影分级 ──
export const ELEVATION = {
  flat: '0 1px 2px rgba(15,42,74,0.04)',
  soft: '0 4px 16px rgba(15,42,74,0.06)',
  raised: '0 10px 30px rgba(44,110,143,0.10)',
  overlay: '0 18px 44px rgba(44,110,143,0.16)',
} as const;

// ── 字号阶梯（h1–h4 / body / caption / micro）──
export const TYPE = {
  h1: 26, h2: 20, h3: 16, h4: 14, body: 15, caption: 13, micro: 11,
} as const;

// ── 动效时长（与 CSS --lf-dur-* 共用一套）──
export const DURATION = { fast: 0.18, base: 0.32, slow: 0.45 } as const;

// ── 圆角语义别名：既有代码以 RADIUS.card / .btn / .badge 访问，
//    统一指向 RADIUS_SCALE，避免出现第二套圆角数值 ──
export const RADIUS = { card: RADIUS_SCALE.lg, btn: RADIUS_SCALE.md, badge: RADIUS_SCALE.pill } as const;
