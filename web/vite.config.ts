import { defineConfig } from "vitest/config";
export default defineConfig({
  base: "./",
  build: {
    target: "es2022",
    rollupOptions: {
      output: { manualChunks: { catalog: ["./src/data/catalog.json"] } },
    },
  },
  test: { include: ["tests/**/*.test.ts"], maxWorkers: 2, testTimeout: 30000 },
});
