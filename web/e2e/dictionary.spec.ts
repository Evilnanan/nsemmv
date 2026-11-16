import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture } from "../tests/fixtures";
import { catalog } from "../src/core/catalog";

async function backToList(page: Page, mobile: boolean) {
  if (mobile) await page.getByRole("button", { name: "返回词条列表" }).click();
}

test("dictionary works without a save, preserves distinct variants and exposes non-pool entries", async ({
  page,
  isMobile,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await page.getByRole("button", { name: "词条词典", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "词典", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "导出存档", exact: true }),
  ).toHaveCount(0);
  const search = page.getByLabel("搜索词典词条");
  const detail = page.getByRole("region", { name: "词典详情" });
  await search.fill("6611202");
  await page.locator('[data-effect-id="6611202"]').click();
  await expect(detail).toContainText("+12%");
  await expect(detail).toContainText("可叠加");
  await page.screenshot({
    path: testInfo.outputPath("dictionary-detail.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await backToList(page, isMobile);
  await search.fill("强化致命一击＋１");
  await expect(page.locator(".dictionary-row")).toHaveCount(2);
  await page.locator('[data-effect-id="7040201"]').click();
  await expect(detail.locator(".effect-detail-rules")).toContainText(
    "不同等级可叠加",
  );
  await backToList(page, isMobile);
  await page.locator('[data-effect-id="7040202"]').click();
  await expect(detail.locator(".effect-detail-rules dd")).toHaveText("可叠加");
  await backToList(page, isMobile);
  await search.fill("310000");
  await expect(page.locator('[data-effect-id="310000"]')).toBeVisible();
  await page.getByLabel("词典分类").selectOption("30020");
  await expect(page.getByText("无匹配词条", { exact: true })).toBeVisible();
  await search.fill("6611202");
  await expect(page.locator('[data-effect-id="6611202"]')).toBeVisible();
  await page.getByLabel("词典分类").selectOption("");
  await page.getByRole("button", { name: "清空词典搜索" }).click();
  await expect(page.locator(".dictionary-pagination")).toContainText(
    `${Object.keys(catalog.effects).length - 1} 条`,
  );
  await page.getByRole("button", { name: "词典下一页" }).click();
  const first = await page
    .locator(".dictionary-row")
    .first()
    .getAttribute("data-effect-id");
  await page.locator(".dictionary-row").first().click();
  await backToList(page, isMobile);
  await expect(page.locator(".dictionary-row").first()).toHaveAttribute(
    "data-effect-id",
    first!,
  );
  await expect(page.locator(".dictionary-pagination code")).toHaveText(
    /^2 \/ /,
  );
  await page.screenshot({
    path: testInfo.outputPath("dictionary-list.png"),
    fullPage: true,
  });
  if (isMobile) {
    await page.setViewportSize({ width: 320, height: 700 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.locator(".dictionary-row").first().click();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  }
  expect(errors).toEqual([]);
});

test("dictionary leaves save bytes and pending relic edits intact", async ({
  page,
}) => {
  const bytes = fixture();
  await page.goto("/");
  await page.getByRole("button", { name: "词典", exact: true }).click();
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(bytes),
  });
  await expect(page.getByLabel("Item ID")).toHaveValue("100");
  await page.getByRole("button", { name: "词典", exact: true }).click();
  await page.getByLabel("搜索词典词条").fill("6611202");
  await page.locator('[data-effect-id="6611202"]').click();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  expect(await readFile((await (await downloaded).path())!)).toEqual(
    Buffer.from(bytes),
  );
  await page.getByRole("button", { name: "遗物", exact: true }).click();
  await page.getByLabel("Item ID").fill("101");
  await expect(
    page.getByRole("button", { name: "导出存档", exact: true }),
  ).toBeDisabled();
  const dialogs: string[] = [];
  page.on("dialog", async (dialog) => {
    dialogs.push(dialog.message());
    await dialog.dismiss();
  });
  await page.getByRole("button", { name: "词典", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "词典", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "遗物", exact: true }).click();
  await expect(page.getByLabel("Item ID")).toHaveValue("101");
  await expect(
    page.getByRole("button", { name: "导出存档", exact: true }),
  ).toBeDisabled();
  expect(dialogs).toEqual([]);
});
