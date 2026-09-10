/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      // 兼容旧组件使用的品牌色（保留，避免破坏既有页面）
      colors: {
        brand: {
          50: '#F5F3FF',
          100: '#EDE9FE',
          200: '#DDD6FE',
          300: '#C4B5FD',
          400: '#A78BFA',
          500: '#8B5CF6',
          600: '#7C3AED',
          700: '#6D28D9',
          800: '#5B21B6',
          900: '#4C1D95',
        },
        gold: {
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706',
        },
        surface: {
          dark: '#0F0F23',
          card: '#1E1D35',
          muted: '#27273B',
        },
        // ── Spec §7 锁定设计 Token ──
        primary: {
          // 低年级（高饱和友好青蓝）
          low: '#3BA9C9',
          // 高年级（渐沉稳）
          high: '#2C6E8F',
          50: '#EAF6FB',
          100: '#D4EDF5',
          200: '#A9DBEC',
          300: '#7CC6DD',
          400: '#3BA9C9',
          500: '#2C6E8F',
          600: '#245A75',
          700: '#1C465C',
          800: '#153645',
        },
        // 学科色
        subject: {
          math: '#4F5BD5',     // 数学=靛
          chinese: '#E0533D',  // 语文=朱
          english: '#3FA66A',  // 英语=草绿
          science: '#E68A3C',  // 科学=橙
          other: '#6B7C99',    // 其他=中性灰蓝
        },
        // 中性色阶（文字 / 边框 / 背景）
        ink: {
          900: '#14384A',  // 主文字（深青蓝黑）
          700: '#475569',  // 次要文字（AA）
          500: '#64748B',  // 第三级文字（AA）
          400: '#94A3B8',  // 占位 / 禁用
          line: '#E2E8F0', // 边框线
        },
        canvas: {
          DEFAULT: '#FFFFFF', // 卡片底
          2: '#F1F5F9',       // 浅底区块
          3: '#F8FAFC',       // 更浅内嵌底
        },
        // 语义色（fill 亮 / text 深一档满足 AA / soft 浅底色）
        success: { DEFAULT: '#3FA66A', text: '#1F8A51', soft: '#E7F6EE' },
        hint: { DEFAULT: '#3BA9C9', text: '#1F7393', soft: '#E6F4F9' },
        rest: { DEFAULT: '#9B7EDE', text: '#6D4FC0', soft: '#F1ECFB' },
        risk: { DEFAULT: '#E0533D', text: '#C0392B', soft: '#FCEDEC' },
        warning: { DEFAULT: '#E0901A', text: '#B45309', soft: '#FEF3C7' },
        // 语义色（旧命名保留，向后兼容）
        semantic: {
          success: '#3FA66A',  // 成功/掌握
          hint: '#3BA9C9',     // 提示
          rest: '#9B7EDE',     // 休息
          risk: '#E0533D',     // 风险
        },
      },
      fontFamily: {
        // 标题：圆润友好（中文 Noto Sans SC 回退）
        display: ['"Baloo 2"', '"Nunito"', '"Noto Sans SC"', 'PingFang SC', 'sans-serif'],
        // 正文：高可读无衬线（中文 Noto Sans SC 回退）
        body: ['"Inter"', 'system-ui', 'PingFang SC', '"Noto Sans SC"', 'Microsoft YaHei', 'sans-serif'],
      },
      // 字号阶梯（h1–h4 / body / caption / micro），与 theme/tokens.ts TYPE 对齐
      fontSize: {
        h1: ['26px', { lineHeight: '1.2', fontWeight: '800' }],
        h2: ['20px', { lineHeight: '1.3', fontWeight: '800' }],
        h3: ['16px', { lineHeight: '1.4', fontWeight: '700' }],
        h4: ['14px', { lineHeight: '1.4', fontWeight: '600' }],
        body: ['15px', { lineHeight: '1.6' }],
        caption: ['13px', { lineHeight: '1.6' }],
        micro: ['11px', { lineHeight: '1.5' }],
      },
      borderRadius: {
        'sm': '10px',
        'md': '14px',
        'card': '20px',  // 卡片 20px
        'btn': '14px',   // 按钮 14px
        'badge': '999px', // 徽章全圆
      },
      boxShadow: {
        // 柔和阴影（青蓝体系，替代旧 purple/clay）
        flat: '0 1px 2px rgba(15,42,74,0.04)',
        soft: '0 4px 16px rgba(15,42,74,0.06)',
        'soft-lg': '0 8px 28px rgba(44,110,143,0.10)',
        raised: '0 10px 30px rgba(44,110,143,0.10)',
        overlay: '0 18px 44px rgba(44,110,143,0.16)',
        gold: '0 4px 16px rgba(251, 191, 36, 0.4)',
      },
      transitionTimingFunction: {
        // 统一缓动
        soft: 'cubic-bezier(.22,1,.36,1)',
      },
      transitionDuration: {
        fast: '180ms',
        base: '320ms',
        slow: '450ms',
        soft: '450ms',
      },
    },
  },
  plugins: [],
};
