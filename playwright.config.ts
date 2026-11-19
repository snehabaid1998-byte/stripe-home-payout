import { defineConfig } from "@playwright/test";

// Runs against the live Vercel site by default. Override with HOME_URL=http://localhost:3000
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  reporter: [["list"]],
  use: {
    baseURL: process.env.HOME_URL ?? "https://stripe-home-payout-sixz.vercel.app",
    viewport: { width: 1440, height: 900 },
    ...(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {}),
  },
});
