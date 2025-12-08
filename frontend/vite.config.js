import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const proxy = {
  target: process.env.PROXY || "http://localhost:3000",
  changeOrigin: true,
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/status": proxy,
      "/history": proxy,
      "/detections": proxy,
      "/unit": proxy,
    },
  },
});
