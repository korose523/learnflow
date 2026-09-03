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
        // 语义色
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
      borderRadius: {
        'card': '20px',  // 卡片 20px
        'btn': '14px',   // 按钮 14px
        'badge': '999px', // 徽章全圆
      },
      boxShadow: {
        // 柔和阴影
        soft: '0 4px 16px rgba(0,0,0,0.06)',
        'soft-lg': '0 8px 28px rgba(0,0,0,0.08)',
        'clay': '0 6px 20px rgba(139, 92, 246, 0.08), inset 0 1px 0 rgba(255, 255, 255, 0.4)',
        'clay-dark': '0 8px 24px rgba(139, 92, 246, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.05)',
        purple: '0 6px 20px rgba(139, 92, 246, 0.15)',
        gold: '0 4px 16px rgba(251, 191, 36, 0.4)',
      },
      transitionTimingFunction: {
        // 统一缓动
        soft: 'cubic-bezier(.22,1,.36,1)',
      },
      transitionDuration: {
        soft: '450ms',
      },
    },
  },
  plugins: [],
};
