import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const apiProxyTarget = loadEnv(mode, ".", "").VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: "127.0.0.1",
      allowedHosts: [".cloudstudio.club"],
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true
        },
        "/health": {
          target: apiProxyTarget,
          changeOrigin: true
        }
      }
    }
  };
});
