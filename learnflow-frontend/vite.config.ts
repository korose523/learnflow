import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// vendor 分包：将重库各自独立 chunk，避免主包过大（Spec AC7：主包 < 300KB gzip）
function manualChunks(id: string): string | undefined {
  if (!id.includes('node_modules')) return undefined;

  // react 核心（含 scheduler / react-dom）
  if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) {
    return 'vendor-react';
  }
  // recharts 及其底层 d3 依赖
  if (/[\\/]node_modules[\\/](recharts|d3-|victory-vendor|@reduxjs)[\\/]/.test(id)) {
    return 'vendor-recharts';
  }
  // framer-motion
  if (/[\\/]node_modules[\\/](framer-motion|motion-dom|motion-utils|popmotion|@motionone)[\\/]/.test(id)) {
    return 'vendor-motion';
  }
  // 路由
  if (/[\\/]node_modules[\\/](react-router|react-router-dom|@remix-run)[\\/]/.test(id)) {
    return 'vendor-router';
  }
  // HTTP 客户端
  if (/[\\/]node_modules[\\/](axios)[\\/]/.test(id)) {
    return 'vendor-axios';
  }
  // 图标库
  if (/[\\/]node_modules[\\/](lucide-react)[\\/]/.test(id)) {
    return 'vendor-icons';
  }
  // 其余第三方库
  return 'vendor';
}

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    target: 'es2020',
    cssCodeSplit: true,
    reportCompressedSize: true,
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks,
        // 稳定的 chunk 命名，便于缓存
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash][extname]',
      },
    },
  },
});
