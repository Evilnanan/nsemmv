import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture } from "../tests/fixtures";
import { Session } from "../src/core/session";
import { fixedRoll } from "../src/core/rules";

async function load(page: import("@playwright/test").Page, bytes = fixture()) {
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(bytes),
  });
}

test("effect details support hover, touch and keyboard without selecting or editing", async ({
  page,
  isMobile,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const original = fixture();
  await load(page, original);
  const first = page.locator(".effect-cell-inspect").first();
  if (isMobile) await first.getByRole("button", { name: /^词条详情/ }).click();
  else await first.hover();
  const details = page.getByRole("dialog", { name: "词条详情", exact: true });
  await expect(details).toContainText("+1");
  await expect(details).toContainText("跨遗物叠加尚未确认");
  await details.getByRole("button", { name: "关闭词条详情" }).click();
  await expect(details).toHaveCount(0);
  await page.locator(".effect-cell").first().click();
  await page.getByLabel("搜索词条").fill("6611202");
  const row = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "6611202" });
  if (isMobile) await row.getByRole("button", { name: /^词条详情/ }).click();
  else await row.hover();
  await expect(details).toContainText("+14%");
  await expect(details).not.toContainText("抽取池");
  await expect(details).not.toContainText("同件遗物");
  await expect(details).not.toContainText("互斥");
  await expect(details).not.toContainText("DPS");
  await expect(details).not.toContainText("最终伤害");
  await expect(details).toContainText("魔法 / 祷告");
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  // The card really sits above the native modal, within either viewport.
  expect(
    await details.evaluate((el) => {
      const r = el.getBoundingClientRect();
      return (
        r.left >= 0 &&
        r.right <= innerWidth &&
        r.top >= 0 &&
        r.bottom <= innerHeight &&
        el.contains(document.elementFromPoint(r.left + 15, r.top + 15))
      );
    }),
  ).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("effect-details.png") });
  await page.keyboard.press("Escape");
  await expect(details).toHaveCount(0);
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  // A separate keyboard target is available; Escape dismisses only the detail card.
  await row.getByRole("button", { name: /^词条详情/ }).focus();
  await page.keyboard.press("Enter");
  await expect(details).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("999999998");
  await page
    .locator(".effect-choice-inspect")
    .getByRole("button", { name: /^词条详情/ })
    .click();
  await expect(details).toContainText("具体数值尚未解明");
  await page.getByLabel("搜索词条").click();
  await expect(details).toHaveCount(0);
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const bytes = await readFile((await (await download).path())!);
  expect(bytes.equals(Buffer.from(original))).toBe(true);
  expect(errors).toEqual([]);
});

test("read-only shop effects expose details without unlocking edits", async ({
  page,
}) => {
  const session = Session.open(fixture(), "test");
  const shop = 11015;
  session.apply(0, { type: "add", id: shop, roll: fixedRoll(shop)! });
  await load(page, session.export());
  await page.locator(".relic-card").filter({ hasText: "11015" }).click();
  await expect(page.locator(".effect-cell").first()).toBeDisabled();
  await page
    .locator(".effect-cell-inspect")
    .first()
    .getByRole("button", { name: /^词条详情/ })
    .click();
  await expect(
    page.getByRole("dialog", { name: "词条详情", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".effect-cell").first()).toBeDisabled();
});
