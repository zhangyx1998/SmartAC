import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";

const proxy = {
  target: process.env.PROXY || "http://localhost:3000",
  changeOrigin: true,
};

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: "../static",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        history: resolve(__dirname, "history.html"),
      },
    },
  },
  server: {
    proxy: {
      "/status": proxy,
      "/history/": proxy,
    },
  },
});
