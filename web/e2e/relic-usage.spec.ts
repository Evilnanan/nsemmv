import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { usageFixture, longPresetName } from "../tests/relic-usage.fixture";

test("shows equipment and preset references in both relic editors without changing the save", async ({
  page,
}, testInfo) => {
  const { bytes } = usageFixture();
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(bytes),
  });
  const usage = page.getByRole("region", { name: "遗物使用情况" });
  await expect(usage.locator(".usage-hero")).toHaveCount(3);
  await expect(usage.locator(".usage-equipped")).toHaveCount(1);
  await expect(usage.locator(".usage-equipped")).toContainText("装备中");
  for (const name of [
    "追踪者",
    "守护者",
    "隐士",
    "共享配置",
    "搓招流",
    longPresetName,
  ])
    await expect(usage).toContainText(name);
  const guardian = usage.locator(".usage-hero").filter({ hasText: "守护者" });
  await expect(guardian.locator("li")).toHaveCount(2);
  await expect(guardian.locator("small")).toHaveText(["器皿", "预设"]);
  await usage.scrollIntoViewIfNeeded();
  expect(await usage.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  await page.screenshot({ path: testInfo.outputPath("inventory-usage.png") });
  await page.locator(".relic-card").nth(1).click();
  await expect(usage).toContainText("未使用");
  await page.getByLabel("角色槽").selectOption("1");
  await expect(usage).toContainText("未使用");
  await page.getByLabel("角色槽").selectOption("0");
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.locator(".preset-card").filter({ hasText: "搓招流" }).click();
  await expect(
    page.locator(".preset-slot-cell").first().locator(".usage-summary"),
  ).toContainText("追踪者");
  await page.getByRole("button", { name: "预设遗物 1", exact: true }).click();
  const options = page.locator(".slot-options .relic-option");
  await expect(options).toHaveCount(3);
  await expect(options.first()).toContainText("追踪者");
  await expect(options.first()).toContainText("预设 2");
  const filter = page.getByLabel("筛选遗物使用情况");
  await filter.selectOption("unshared");
  await expect(options).toHaveCount(2);
  for (const row of await options.all())
    await expect(row).not.toContainText("追踪者");
  await filter.selectOption("unused");
  await expect(options).toHaveCount(1);
  await expect(options).toContainText("未使用");
  await filter.selectOption("current");
  await expect(options).toHaveCount(2);
  await filter.selectOption("other");
  await expect(options).toHaveCount(1);
  await expect(options).toContainText("追踪者");
  await filter.selectOption("all");
  await options.first().scrollIntoViewIfNeeded();
  expect(
    await page
      .locator(".preset-dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("usage-filter.png") });
  await page.getByRole("button", { name: "关闭遗物选择", exact: true }).click();
  await page
    .getByRole("button", { name: "编辑预设遗物 1", exact: true })
    .click();
  await expect(usage.locator(".usage-hero")).toHaveCount(3);
  await expect(usage).toContainText(longPresetName);
  await expect(usage).toContainText("共享配置");
  expect(await usage.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  await page.screenshot({ path: testInfo.outputPath("preset-usage.png") });
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  expect(
    (await readFile((await (await pending).path())!)).equals(
      Buffer.from(bytes),
    ),
  ).toBe(true);
});
