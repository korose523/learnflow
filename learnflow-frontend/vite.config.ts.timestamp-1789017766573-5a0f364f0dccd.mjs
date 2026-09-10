// vite.config.ts
import { defineConfig } from "file:///E:/learnflow/learnflow-frontend/node_modules/vite/dist/node/index.js";
import react from "file:///E:/learnflow/learnflow-frontend/node_modules/@vitejs/plugin-react/dist/index.js";
function manualChunks(id) {
  if (!id.includes("node_modules")) return void 0;
  if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) {
    return "vendor-react";
  }
  if (/[\\/]node_modules[\\/](recharts|d3-|victory-vendor|@reduxjs)[\\/]/.test(id)) {
    return "vendor-recharts";
  }
  if (/[\\/]node_modules[\\/](framer-motion|motion-dom|motion-utils|popmotion|@motionone)[\\/]/.test(id)) {
    return "vendor-motion";
  }
  if (/[\\/]node_modules[\\/](react-router|react-router-dom|@remix-run)[\\/]/.test(id)) {
    return "vendor-router";
  }
  if (/[\\/]node_modules[\\/](axios)[\\/]/.test(id)) {
    return "vendor-axios";
  }
  if (/[\\/]node_modules[\\/](lucide-react)[\\/]/.test(id)) {
    return "vendor-icons";
  }
  return "vendor";
}
var vite_config_default = defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true
      }
    }
  },
  build: {
    target: "es2020",
    cssCodeSplit: true,
    reportCompressedSize: true,
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks,
        // 稳定的 chunk 命名，便于缓存
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]"
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJFOlxcXFxsZWFybmZsb3dcXFxcbGVhcm5mbG93LWZyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJFOlxcXFxsZWFybmZsb3dcXFxcbGVhcm5mbG93LWZyb250ZW5kXFxcXHZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9FOi9sZWFybmZsb3cvbGVhcm5mbG93LWZyb250ZW5kL3ZpdGUuY29uZmlnLnRzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSc7XG5pbXBvcnQgcmVhY3QgZnJvbSAnQHZpdGVqcy9wbHVnaW4tcmVhY3QnO1xuXG4vLyB2ZW5kb3IgXHU1MjA2XHU1MzA1XHVGRjFBXHU1QzA2XHU5MUNEXHU1RTkzXHU1NDA0XHU4MUVBXHU3MkVDXHU3QUNCIGNodW5rXHVGRjBDXHU5MDdGXHU1MTREXHU0RTNCXHU1MzA1XHU4RkM3XHU1OTI3XHVGRjA4U3BlYyBBQzdcdUZGMUFcdTRFM0JcdTUzMDUgPCAzMDBLQiBnemlwXHVGRjA5XG5mdW5jdGlvbiBtYW51YWxDaHVua3MoaWQ6IHN0cmluZyk6IHN0cmluZyB8IHVuZGVmaW5lZCB7XG4gIGlmICghaWQuaW5jbHVkZXMoJ25vZGVfbW9kdWxlcycpKSByZXR1cm4gdW5kZWZpbmVkO1xuXG4gIC8vIHJlYWN0IFx1NjgzOFx1NUZDM1x1RkYwOFx1NTQyQiBzY2hlZHVsZXIgLyByZWFjdC1kb21cdUZGMDlcbiAgaWYgKC9bXFxcXC9dbm9kZV9tb2R1bGVzW1xcXFwvXShyZWFjdHxyZWFjdC1kb218c2NoZWR1bGVyKVtcXFxcL10vLnRlc3QoaWQpKSB7XG4gICAgcmV0dXJuICd2ZW5kb3ItcmVhY3QnO1xuICB9XG4gIC8vIHJlY2hhcnRzIFx1NTNDQVx1NTE3Nlx1NUU5NVx1NUM0MiBkMyBcdTRGOURcdThENTZcbiAgaWYgKC9bXFxcXC9dbm9kZV9tb2R1bGVzW1xcXFwvXShyZWNoYXJ0c3xkMy18dmljdG9yeS12ZW5kb3J8QHJlZHV4anMpW1xcXFwvXS8udGVzdChpZCkpIHtcbiAgICByZXR1cm4gJ3ZlbmRvci1yZWNoYXJ0cyc7XG4gIH1cbiAgLy8gZnJhbWVyLW1vdGlvblxuICBpZiAoL1tcXFxcL11ub2RlX21vZHVsZXNbXFxcXC9dKGZyYW1lci1tb3Rpb258bW90aW9uLWRvbXxtb3Rpb24tdXRpbHN8cG9wbW90aW9ufEBtb3Rpb25vbmUpW1xcXFwvXS8udGVzdChpZCkpIHtcbiAgICByZXR1cm4gJ3ZlbmRvci1tb3Rpb24nO1xuICB9XG4gIC8vIFx1OERFRlx1NzUzMVxuICBpZiAoL1tcXFxcL11ub2RlX21vZHVsZXNbXFxcXC9dKHJlYWN0LXJvdXRlcnxyZWFjdC1yb3V0ZXItZG9tfEByZW1peC1ydW4pW1xcXFwvXS8udGVzdChpZCkpIHtcbiAgICByZXR1cm4gJ3ZlbmRvci1yb3V0ZXInO1xuICB9XG4gIC8vIEhUVFAgXHU1QkEyXHU2MjM3XHU3QUVGXG4gIGlmICgvW1xcXFwvXW5vZGVfbW9kdWxlc1tcXFxcL10oYXhpb3MpW1xcXFwvXS8udGVzdChpZCkpIHtcbiAgICByZXR1cm4gJ3ZlbmRvci1heGlvcyc7XG4gIH1cbiAgLy8gXHU1NkZFXHU2ODA3XHU1RTkzXG4gIGlmICgvW1xcXFwvXW5vZGVfbW9kdWxlc1tcXFxcL10obHVjaWRlLXJlYWN0KVtcXFxcL10vLnRlc3QoaWQpKSB7XG4gICAgcmV0dXJuICd2ZW5kb3ItaWNvbnMnO1xuICB9XG4gIC8vIFx1NTE3Nlx1NEY1OVx1N0IyQ1x1NEUwOVx1NjVCOVx1NUU5M1xuICByZXR1cm4gJ3ZlbmRvcic7XG59XG5cbmV4cG9ydCBkZWZhdWx0IGRlZmluZUNvbmZpZyh7XG4gIHBsdWdpbnM6IFtyZWFjdCgpXSxcbiAgc2VydmVyOiB7XG4gICAgcG9ydDogNTE3MyxcbiAgICBwcm94eToge1xuICAgICAgJy9hcGknOiB7XG4gICAgICAgIHRhcmdldDogJ2h0dHA6Ly9sb2NhbGhvc3Q6ODAwMCcsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgIH0sXG4gICAgfSxcbiAgfSxcbiAgYnVpbGQ6IHtcbiAgICB0YXJnZXQ6ICdlczIwMjAnLFxuICAgIGNzc0NvZGVTcGxpdDogdHJ1ZSxcbiAgICByZXBvcnRDb21wcmVzc2VkU2l6ZTogdHJ1ZSxcbiAgICBjaHVua1NpemVXYXJuaW5nTGltaXQ6IDgwMCxcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBvdXRwdXQ6IHtcbiAgICAgICAgbWFudWFsQ2h1bmtzLFxuICAgICAgICAvLyBcdTdBMzNcdTVCOUFcdTc2ODQgY2h1bmsgXHU1NDdEXHU1NDBEXHVGRjBDXHU0RkJGXHU0RThFXHU3RjEzXHU1QjU4XG4gICAgICAgIGNodW5rRmlsZU5hbWVzOiAnYXNzZXRzL1tuYW1lXS1baGFzaF0uanMnLFxuICAgICAgICBlbnRyeUZpbGVOYW1lczogJ2Fzc2V0cy9bbmFtZV0tW2hhc2hdLmpzJyxcbiAgICAgICAgYXNzZXRGaWxlTmFtZXM6ICdhc3NldHMvW25hbWVdLVtoYXNoXVtleHRuYW1lXScsXG4gICAgICB9LFxuICAgIH0sXG4gIH0sXG59KTtcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBcVIsU0FBUyxvQkFBb0I7QUFDbFQsT0FBTyxXQUFXO0FBR2xCLFNBQVMsYUFBYSxJQUFnQztBQUNwRCxNQUFJLENBQUMsR0FBRyxTQUFTLGNBQWMsRUFBRyxRQUFPO0FBR3pDLE1BQUkseURBQXlELEtBQUssRUFBRSxHQUFHO0FBQ3JFLFdBQU87QUFBQSxFQUNUO0FBRUEsTUFBSSxvRUFBb0UsS0FBSyxFQUFFLEdBQUc7QUFDaEYsV0FBTztBQUFBLEVBQ1Q7QUFFQSxNQUFJLDBGQUEwRixLQUFLLEVBQUUsR0FBRztBQUN0RyxXQUFPO0FBQUEsRUFDVDtBQUVBLE1BQUksd0VBQXdFLEtBQUssRUFBRSxHQUFHO0FBQ3BGLFdBQU87QUFBQSxFQUNUO0FBRUEsTUFBSSxxQ0FBcUMsS0FBSyxFQUFFLEdBQUc7QUFDakQsV0FBTztBQUFBLEVBQ1Q7QUFFQSxNQUFJLDRDQUE0QyxLQUFLLEVBQUUsR0FBRztBQUN4RCxXQUFPO0FBQUEsRUFDVDtBQUVBLFNBQU87QUFDVDtBQUVBLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxNQUFNLENBQUM7QUFBQSxFQUNqQixRQUFRO0FBQUEsSUFDTixNQUFNO0FBQUEsSUFDTixPQUFPO0FBQUEsTUFDTCxRQUFRO0FBQUEsUUFDTixRQUFRO0FBQUEsUUFDUixjQUFjO0FBQUEsTUFDaEI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsT0FBTztBQUFBLElBQ0wsUUFBUTtBQUFBLElBQ1IsY0FBYztBQUFBLElBQ2Qsc0JBQXNCO0FBQUEsSUFDdEIsdUJBQXVCO0FBQUEsSUFDdkIsZUFBZTtBQUFBLE1BQ2IsUUFBUTtBQUFBLFFBQ047QUFBQTtBQUFBLFFBRUEsZ0JBQWdCO0FBQUEsUUFDaEIsZ0JBQWdCO0FBQUEsUUFDaEIsZ0JBQWdCO0FBQUEsTUFDbEI7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUNGLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
