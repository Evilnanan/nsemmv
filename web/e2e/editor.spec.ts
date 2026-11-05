import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture, character } from "../tests/fixtures";
import { Session } from "../src/core/session";
import { equal } from "../src/core/binary";
import { selectCharacter } from "./character-select-helper";

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
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(bytes),
  });
  await expect(page.getByLabel("角色槽")).toBeVisible();
  await expect(page.getByLabel("Item ID")).toHaveValue("100");
  await selectCharacter(page, 1);
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
  await page.getByLabel("打开存档文件").setInputFiles({
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
  await page.getByLabel("打开存档文件").setInputFiles({
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

test("edits a preset relic in place, retains the preset draft and protects shop relics", async ({
  page,
}, testInfo) => {
  const session = Session.open(fixture(), "test");
  const { fixedRoll } = await import("../src/core/rules");
  const shop = session.apply(0, {
    type: "add",
    id: 11015,
    roll: fixedRoll(11015)!,
  })!;
  const handles = [0xc0800054, 0, 0, shop, 0, 0];
  for (const name of ["预设一", "预设二"])
    session.apply(0, { type: "preset", hero: 7, vessel: 19000, handles, name });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(session.export()),
  });
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.locator(".preset-card").filter({ hasText: "预设一" }).click();
  await page.getByLabel("预设名称").fill("保留中文草稿");
  await expect(
    page.getByRole("button", { name: "编辑预设遗物 2", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "编辑预设遗物 1", exact: true })
    .click();
  await page.locator(".preset-relic-editor .effect-cell").first().click();
  await page.getByLabel("词条分类").selectOption("30000");
  await page.getByLabel("搜索词条").fill("7000100");
  await page.locator(".picker-row").filter({ hasText: "7000100" }).click();
  await page.screenshot({
    path: testInfo.outputPath("preset-relic-editor.png"),
  });
  expect(
    await page
      .locator("dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await page.getByRole("button", { name: "应用修改", exact: true }).click();
  await expect(page.getByLabel("预设名称")).toHaveValue("保留中文草稿");
  await expect(
    page.locator(".preset-slot-cell").first().locator(".preset-effect"),
  ).toContainText("集中力");
  await page
    .getByRole("button", { name: "编辑预设遗物 1", exact: true })
    .click();
  await expect(page.locator(".effect-cell").first()).toContainText("7000100");
  await page.locator(".effect-cell").first().click();
  await page.getByLabel("搜索词条").fill("7000000");
  await page.locator(".picker-row").filter({ hasText: "7000000" }).click();
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await expect(page.getByLabel("预设名称")).toHaveValue("保留中文草稿");
  await expect(
    page.locator(".preset-slot-cell").first().locator(".preset-effect"),
  ).toContainText("集中力");
  await page
    .getByRole("button", { name: "查看预设遗物 4", exact: true })
    .click();
  await expect(page.getByLabel("Item ID")).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "应用修改", exact: true }),
  ).toBeDisabled();
  for (const cell of await page.locator(".effect-cell").all())
    await expect(cell).toBeDisabled();
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await page.getByRole("button", { name: "保存预设", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const result = Session.open(
    new Uint8Array(await readFile((await (await download).path())!)),
    "result",
  );
  const view = result.view(0);
  expect(view.relics).toHaveLength(2);
  expect(view.relics.find((r) => r.handle === 0xc0800054)?.roll[0].effect).toBe(
    7000100,
  );
  expect(view.relics.find((r) => r.handle === shop)?.roll).toEqual(
    fixedRoll(11015),
  );
  expect(view.loadouts?.presets.map((p) => p.name)).toEqual([
    "保留中文草稿",
    "预设二",
  ]);
  for (const p of view.loadouts!.presets) expect(p.handles).toEqual(handles);
  expect(errors).toEqual([]);
});

test("native effect categories combine with search, page navigation and curse validation", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(fixture()),
  });
  await page.getByRole("button", { name: "新增遗物", exact: true }).click();
  await page.getByRole("button", { name: "深层", exact: true }).click();
  await page.getByLabel("搜索遗物类型").fill("2000100");
  await page.locator(".picker-list .picker-row").click();
  await page.locator(".effect-cell").first().click();
  await page.getByRole("button", { name: "下一页词条", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "上一页词条", exact: true }),
  ).toBeEnabled();
  await page.getByLabel("词条分类").selectOption("30010");
  await expect(
    page.getByRole("button", { name: "下一页词条", exact: true }),
  ).toHaveCount(0);
  await page.getByLabel("搜索词条").fill("7090000");
  await expect(
    page.locator(".picker-row").filter({ hasText: "7090000" }),
  ).toHaveCount(1);
  await page.getByLabel("词条分类").selectOption("30020");
  await expect(
    page.locator(".picker-row").filter({ hasText: "7090000" }),
  ).toHaveCount(0);
  await expect(page.getByText("无匹配", { exact: true })).toBeVisible();
  await page.getByLabel("搜索词条").fill("");
  await page.screenshot({ path: testInfo.outputPath("effect-category.png") });
  expect(
    await page
      .locator("dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  const { catalog } = await import("../src/core/catalog");
  const ids = await page
    .locator(".picker-list .picker-row code")
    .allTextContents();
  expect(ids.length).toBeGreaterThan(0);
  for (const id of ids) expect(catalog.effects[Number(id)].group).toBe(30020);
  await page.getByLabel("搜索词条").fill("6611202");
  await page.locator(".picker-row").filter({ hasText: "6611202" }).click();
  await expect(page.locator(".validation")).toContainText("缺少 Curse");
  await expect(
    page.getByRole("button", { name: "应用修改", exact: true }),
  ).toBeDisabled();
  await page.locator(".effect-cell.curse").first().click();
  await page.getByLabel("词条分类").selectOption("40010");
  const curses = await page
    .locator(".picker-list .picker-row code")
    .allTextContents();
  expect(curses.length).toBeGreaterThan(0);
  for (const id of curses)
    expect(catalog.effects[Number(id)].group).toBe(40010);
});

test("previews and excludes conflicting effects in inventory and preset pickers", async ({
  page,
}, testInfo) => {
  const session = Session.open(fixture(), "test");
  session.apply(0, {
    type: "preset",
    hero: 7,
    vessel: 19000,
    handles: [0xc0800054, 0, 0, 0, 0, 0],
    name: "冲突预览",
  });
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(session.export()),
  });
  await page.locator(".effect-cell").nth(2).click();
  await page.getByLabel("词条分类").selectOption("30000");
  await page.getByLabel("搜索词条").fill("700000");
  const conflict = page
    .locator(".picker-row")
    .filter({ has: page.locator("code", { hasText: "7000001" }) });
  await expect(conflict).toContainText("冲突");
  await expect(conflict.locator(".availability-badge")).toHaveAttribute(
    "title",
    /生命力＋１/,
  );
  await page.screenshot({ path: testInfo.outputPath("conflict-preview.png") });
  expect(
    await page
      .locator("dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await page.getByRole("checkbox", { name: "排除不可用", exact: true }).check();
  await expect(conflict).toHaveCount(0);
  await expect(page.getByText("无匹配", { exact: true })).toBeVisible();
  await expect(page.getByLabel("匹配词条数")).toHaveText("0");
  await page.getByLabel("搜索词条").fill("7000100");
  await expect(page.locator(".availability-badge")).toHaveCount(0);
  await page.locator(".picker-row").filter({ hasText: "7000100" }).click();
  await page.getByRole("button", { name: "应用修改", exact: true }).click();
  // Replacing the first field may retain or upgrade its existing effect.
  await page.locator(".effect-cell").first().click();
  await expect(
    page.getByRole("checkbox", { name: "排除不可用", exact: true }),
  ).toBeChecked();
  await page.getByLabel("搜索词条").fill("7000001");
  await expect(
    page.locator(".picker-row").filter({ hasText: "7000001" }),
  ).toHaveCount(1);
  await expect(page.locator(".availability-badge")).toHaveCount(0);
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.locator(".preset-card").click();
  await page
    .getByRole("button", { name: "编辑预设遗物 1", exact: true })
    .click();
  await page.locator(".effect-cell").nth(4).click();
  await expect(
    page.getByRole("checkbox", { name: "排除不可用", exact: true }),
  ).toBeChecked();
  await page.getByLabel("搜索词条").fill("7000000");
  await expect(
    page.locator(".picker-row").filter({ hasText: "7000000" }),
  ).toHaveCount(0);
  await page
    .getByRole("checkbox", { name: "排除不可用", exact: true })
    .uncheck();
  await expect(
    page.locator(".picker-row").filter({ hasText: "7000000" }),
  ).toContainText("冲突");
  // Merely previewing and toggling a filter never changes the stored relic.
  await page
    .getByRole("dialog")
    .last()
    .getByRole("button", { name: "关闭", exact: true })
    .click();
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const result = Session.open(
    new Uint8Array(await readFile((await (await download).path())!)),
    "result",
  );
  expect(result.view(0).relics[0].roll.map((p) => p.effect)).toEqual([
    7000000, 7000100, 0xffffffff,
  ]);
});

test("distinguishes unavailable candidates from effects that need a curse", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(fixture()),
  });
  await page.getByRole("button", { name: "新增遗物", exact: true }).click();
  await page.getByRole("button", { name: "深层", exact: true }).click();
  await page.getByLabel("搜索遗物类型").fill("2000100");
  await page.locator(".picker-list .picker-row").click();
  await page.locator(".effect-cell").first().click();
  await page.getByLabel("搜索词条").fill("999999998");
  await expect(
    page.locator(".picker-row").filter({ hasText: "999999998" }),
  ).toContainText("未知词条");
  await page.getByRole("checkbox", { name: "排除不可用", exact: true }).check();
  await expect(
    page.locator(".picker-row").filter({ hasText: "999999998" }),
  ).toHaveCount(0);
  await page.getByLabel("搜索词条").fill("6611202");
  await expect(
    page.locator(".picker-row").filter({ hasText: "6611202" }),
  ).toContainText("需 Curse");
  await page.screenshot({
    path: testInfo.outputPath("availability-preview.png"),
  });
  expect(
    await page
      .locator("dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await page.getByLabel("搜索词条").fill("7090000");
  await expect(page.locator(".availability-badge")).toHaveCount(0);
  await page.locator(".picker-row").filter({ hasText: "7090000" }).click();
  await expect(page.getByLabel("Item ID")).toHaveValue("2003100");
  await page.locator(".effect-cell.curse").first().click();
  await page
    .getByRole("checkbox", { name: "排除不可用", exact: true })
    .uncheck();
  await page.getByLabel("搜索词条").fill("7090000");
  // This candidate also duplicates the existing effect, so use a different positive ID to isolate the pool reason.
  await page.getByLabel("搜索词条").fill("6611202");
  await expect(
    page.locator(".picker-row").filter({ hasText: "6611202" }),
  ).toContainText("池不匹配");
  await page.getByLabel("搜索词条").fill("6851700");
  await expect(
    page.locator(".picker-row").filter({ hasText: "6851700" }),
  ).toContainText("组合不兼容");
  await page.getByRole("checkbox", { name: "排除不可用", exact: true }).check();
  await expect(
    page.locator(".picker-row").filter({ hasText: "6851700" }),
  ).toHaveCount(0);
});
