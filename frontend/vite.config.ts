import { defineConfig } from "vite";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  build: {
    // Bundle hygiene: warn only on chunks > 600 kB instead of the default 500.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // Split heavy 3rd-party libs into their own chunks so the main bundle
        // stays small and route-level lazy chunks load faster.
        manualChunks(id: string): string | undefined {
          if (!id.includes("node_modules")) return undefined;
          if (id.includes("/jspdf") || id.includes("jspdf-autotable")) {
            return "pdf-vendor";
          }
          if (id.includes("/antd/") || id.includes("@ant-design/")) {
            return "antd-vendor";
          }
          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("react-router") ||
            id.includes("/scheduler/")
          ) {
            return "react-vendor";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    proxy: {
      '/api/v1': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
    fs: {
      allow: [
        '.',
        '../docs/assets', // Allow serving files from docs/assets
      ],
    },
  },
});
