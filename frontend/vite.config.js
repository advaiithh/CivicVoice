import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In production, set VITE_API_URL as an env var (e.g. on Vercel) to your
// deployed backend URL. Locally it falls back to the proxy below.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
