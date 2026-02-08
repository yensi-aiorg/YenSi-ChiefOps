import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 23100,
    host: true,
    proxy: {
      "/api": {
        target: "http://host.docker.internal:23101",
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: "ws://host.docker.internal:23101",
        ws: true,
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 23100,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          charts: ["echarts", "echarts-for-react"],
          state: ["zustand", "axios"],
        },
      },
    },
  },
});
