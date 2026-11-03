import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture, character } from "../tests/fixtures";
import { Session } from "../src/core/session";
import { equal } from "../src/core/binary";

test("local save: open, modify, undo, export, reopen and retain another slot", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const external: string[] = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:4173/")) external.push(r.url());
  });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "遗物工坊" })).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("landing.png") });
  const bytes = fixture({ 0: character(), 1: character() });
  await page
    .getByLabel("打开存档文件")
    .setInputFiles({
      name: "NR0000.dbb",
      mimeType: "application/octet-stream",
      buffer: Buffer.from(bytes),
    });
  await expect(page.getByLabel("角色槽")).toBeVisible();
  await expect(page.getByLabel("Item ID")).toHaveValue("100");
  await page.getByLabel("角色槽").selectOption("1");
  await page.getByRole("button", { name: "收藏遗物", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "取消收藏", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "撤销", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "收藏遗物", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "重做", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "取消收藏", exact: true }),
  ).toBeVisible();
  const d = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const saved = await d;
  const result = Session.open(
    new Uint8Array(await readFile((await saved.path())!)),
    "result",
  );
  expect(result.view(1).relics[0].favorite).toBe(true);
  expect(result.view(0).relics[0].favorite).toBe(false);
  await page.getByRole("button", { name: "遗物", exact: true }).click();
  await page.getByRole("button", { name: "复制遗物" }).click();
  await page.getByRole("button", { name: "应用修改" }).click();
  await expect(page.locator(".relic-card")).toHaveCount(2);
  await page.screenshot({
    path: testInfo.outputPath("editor.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.getByRole("button", { name: "新增预设" }).click();
  await page.getByLabel("预设名称").fill("搓招流隐士");
  await page.getByLabel("器皿", { exact: true }).selectOption("19000");
  await page.getByRole("button", { name: "预设遗物 1", exact: true }).click();
  await page.locator(".slot-options .picker-row").nth(1).click();
  await page.getByRole("button", { name: "保存预设" }).click();
  await expect(page.locator(".preset-card")).toHaveCount(1);
  await page.locator(".preset-card").click();
  await page.getByRole("button", { name: "装备预设" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  const d2 = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const result2 = Session.open(
    new Uint8Array(await readFile((await (await d2).path())!)),
    "result2",
  );
  expect(result2.view(1).loadouts?.presets[0].name).toBe("搓招流隐士");
  expect(
    result2.view(1).loadouts?.heroes.find((h) => h.id === 7)?.currentPreset,
  ).toBe(0);
  const original = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载原始备份" }).click();
  expect(
    equal(
      new Uint8Array(await readFile((await (await original).path())!)),
      bytes,
    ),
  ).toBe(true);
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
});

test("MMV search includes cross-item candidates and requires curse before applying", async ({
  page,
}) => {
  await page.goto("/");
  await page
    .getByLabel("打开存档文件")
    .setInputFiles({
      name: "NR0000.dbb",
      mimeType: "application/octet-stream",
      buffer: Buffer.from(fixture()),
    });
  await page.getByRole("button", { name: "新增遗物", exact: true }).click();
  await page.getByRole("button", { name: "深层", exact: true }).click();
  await page.getByLabel("搜索遗物类型").fill("2000100");
  await page.locator(".picker-list .picker-row").click();
  await page.locator(".effect-cell").first().click();
  await page.getByLabel("搜索词条").fill("7090000");
  await page.locator(".picker-row").filter({ hasText: "7090000" }).click();
  await expect(page.getByLabel("Item ID")).toHaveValue("2003100");
  await expect(page.getByRole("button", { name: "应用修改" })).toBeEnabled();
  await page.locator(".effect-cell").first().click();
  await page.getByLabel("搜索词条").fill("6611202");
  await page.locator(".picker-row").filter({ hasText: "6611202" }).click();
  await expect(page.locator(".validation")).toContainText("缺少 Curse");
  await expect(page.getByRole("button", { name: "应用修改" })).toBeDisabled();
});

test("shop relics have no editable fields or deletion action", async ({
  page,
}) => {
  const session = Session.open(fixture(), "test");
  const { fixedRoll } = await import("../src/core/rules");
  session.apply(0, { type: "add", id: 11015, roll: fixedRoll(11015)! });
  await page.goto("/");
  await page
    .getByLabel("打开存档文件")
    .setInputFiles({
      name: "NR0000.dbb",
      mimeType: "application/octet-stream",
      buffer: Buffer.from(session.export()),
    });
  await page.locator(".relic-card").filter({ hasText: "11015" }).click();
  await expect(page.getByLabel("Item ID")).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "删除遗物", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Auto Fix", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "应用修改", exact: true }),
  ).toBeDisabled();
  await expect(page.locator(".type-chip")).toContainText("商店遗物");
  for (const cell of await page.locator(".effect-cell").all())
    await expect(cell).toBeDisabled();
});
