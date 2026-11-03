import { test, expect, type Page, type Locator } from "@playwright/test";
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

async function longPress(page: Page, target: Locator) {
  await target.scrollIntoViewIfNeeded();
  const box = (await target.boundingBox())!;
  const client = await page.context().newCDPSession(page);
  await client.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: box.x + box.width / 2, y: box.y + box.height / 2 }],
  });
  try {
    await expect(
      page.getByRole("dialog", { name: "词条详情", exact: true }),
    ).toBeVisible();
  } finally {
    await client.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await client.detach();
  }
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
  if (isMobile) await longPress(page, first.locator(".effect-cell"));
  else await first.hover();
  const details = page.getByRole("dialog", { name: "词条详情", exact: true });
  await expect(details).toContainText("+1");
  await expect(details).toContainText("可叠加；能力值相加");
  await details.getByRole("button", { name: "关闭词条详情" }).click();
  await expect(details).toHaveCount(0);
  await page.locator(".effect-cell").first().click();
  await page.getByLabel("搜索词条").fill("6611202");
  const row = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "6611202" });
  if (isMobile) await longPress(page, row.locator(".picker-row"));
  else await row.hover();
  await expect(details).toContainText("+14%");
  await expect(details).toContainText("可叠加；攻击倍率相乘");
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
  // Keyboard focus and Enter open details; Escape dismisses only the detail card.
  await row.focus();
  await page.keyboard.press("Enter");
  await expect(details).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("6646100");
  const growth = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "6646100" });
  if (isMobile) await longPress(page, growth.locator(".picker-row"));
  else await growth.hover();
  await expect(details).toContainText("随等级调整能力值");
  await expect(details).toContainText("集中力 -2 / 智力 +2 / 信仰 +2");
  await expect(details).toContainText("集中力 -13 / 智力 +12 / 信仰 +12");
  expect(await details.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  await page.screenshot({
    path: testInfo.outputPath("hero-growth-details.png"),
  });
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("999999998");
  await page.locator(".effect-choice-inspect").focus();
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
  isMobile,
}) => {
  const session = Session.open(fixture(), "test");
  const shop = 11015;
  session.apply(0, { type: "add", id: shop, roll: fixedRoll(shop)! });
  await load(page, session.export());
  await page.locator(".relic-card").filter({ hasText: "11015" }).click();
  await expect(page.locator(".effect-cell").first()).toBeDisabled();
  if (isMobile) await longPress(page, page.locator(".effect-cell").first());
  else {
    await page.locator(".effect-cell-inspect").first().focus();
    await page.keyboard.press("Enter");
  }
  await expect(
    page.getByRole("dialog", { name: "词条详情", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".effect-cell").first()).toBeDisabled();
});

test("mobile long press cancels on movement and never consumes the next short tap", async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, "Touch gesture coverage");
  await load(page);
  await expect(page.locator(".effect-info")).toHaveCount(0);
  await page.locator(".effect-cell").first().tap();
  await page.getByLabel("搜索词条").fill("7000100");
  const row = page.locator(".picker-row").filter({ hasText: "7000100" });
  const details = page.getByRole("dialog", { name: "词条详情", exact: true });
  const box = (await row.boundingBox())!;
  const client = await page.context().newCDPSession(page);
  const point = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  await client.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [point],
  });
  await page.waitForTimeout(100);
  await client.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ ...point, y: point.y - 35 }],
  });
  await page.waitForTimeout(550);
  await expect(details).toHaveCount(0);
  await client.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await client.detach();
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  await longPress(page, row);
  await expect(details).toBeVisible();
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  await expect(page.locator(".effect-cell").first()).toContainText("生命力");
  await details.getByRole("button", { name: "关闭词条详情" }).tap();
  await row.tap();
  await expect(page.getByLabel("搜索词条")).toHaveCount(0);
  await expect(page.locator(".effect-cell").first()).toContainText("集中力");
});
