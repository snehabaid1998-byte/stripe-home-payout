// Live check of Home on Maria's held-out data (17 to 30 Nov 2026).
// For each day: the page loads, the payout card shows the expected state and the
// API's message, and the whole card sits above the fold at 1440×900.
// Run: npx playwright install chromium   (first time only)
//      npx playwright test
import { test, expect } from "@playwright/test";

// Expected state per day, from reading the held-out transactions (see README).
// 27 Nov has no transactions, so Home shows the state as of 26 Nov.
const EXPECTED: Record<string, string> = {
  "2026-11-17": "no_payout",
  "2026-11-18": "no_payout",
  "2026-11-19": "no_payout",
  "2026-11-20": "negative_after_refund",
  "2026-11-21": "negative_after_refund",
  "2026-11-22": "negative_after_refund",
  "2026-11-23": "no_payout",
  "2026-11-24": "no_payout",
  "2026-11-25": "no_payout",
  "2026-11-26": "pending_only",
  "2026-11-28": "no_payout",
  "2026-11-29": "no_payout",
  "2026-11-30": "payout_scheduled",
};

for (const [day, state] of Object.entries(EXPECTED)) {
  test(`${day}: ${state}, card above the fold`, async ({ page, request }) => {
    const api = await (await request.get(`/api/payout-state?as_of=${day}`)).json();
    expect(api.state).toBe(state);
    expect(api.message).not.toMatch(/[{}]/);

    const res = await page.goto(`/?as_of=${day}`);
    expect(res?.status()).toBe(200);

    const card = page.getByTestId("payout-status");
    await expect(card).toHaveAttribute("data-state", state);
    await expect(card).toContainText(api.message);

    const box = await card.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.y).toBeGreaterThanOrEqual(0);
    expect(box!.y + box!.height).toBeLessThanOrEqual(900);
  });
}

test("default view is payroll day with the next payout first", async ({ page }) => {
  await page.goto("/");
  const card = page.getByTestId("payout-status");
  await expect(card).toHaveAttribute("data-state", "payout_scheduled");
  await expect(card).toContainText("$40.00");
});

test("failed $300 payout is explained in the Balance panel", async ({ page, request }) => {
  await page.goto("/?as_of=2026-11-20");
  const notice = page.getByTestId("balance-notice");
  await expect(notice).toHaveCount(1);
  await expect(notice).toContainText("$300.00");
  // The contract figures stay as recorded: the notice explains the gap, it doesn't change the state.
  const api = await (await request.get("/api/payout-state?as_of=2026-11-20")).json();
  expect(api.available_balance).toBe(-2492);
});
