import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture } from "../tests/fixtures";
import { Session } from "../src/core/session";
import { catalog, effectName } from "../src/core/catalog";
import { fixedRoll, toRoll } from "../src/core/rules";
import { EMPTY } from "../src/core/binary";

test("reaches candidates beyond the old limit, searches curses and saves the chosen instance", async ({
  page,
  isMobile,
}, testInfo) => {
  const session = Session.open(fixture(), "test");
  const ordinary = session.view(0).relics[0];
  let last = ordinary.handle;
  for (let i = 0; i < 85; i++)
    last = session.apply(0, {
      type: "add",
      id: ordinary.id,
      roll: ordinary.roll,
    })!;
  session.apply(0, { type: "favorite", handle: last, value: true });
  const shop = session.apply(0, {
    type: "add",
    id: 10004,
    roll: fixedRoll(10004)!,
  })!;
  session.apply(0, {
    type: "preset",
    hero: 7,
    vessel: 19000,
    name: "分页与负面词条",
    handles: [ordinary.handle, 0, 0, shop, 0, 0],
  });
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(session.export()),
  });
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.locator(".preset-card").click();
  await page.getByRole("button", { name: "预设遗物 1", exact: true }).click();
  const picker = page.getByRole("complementary", { name: "选择预设遗物" });
  await expect(picker.getByRole("status")).toHaveText("86 件");
  await expect(picker.locator(".relic-option")).toHaveCount(18);
  for (let i = 0; i < 4; i++)
    await picker.getByRole("button", { name: "下一页遗物" }).click();
  await expect(
    picker.getByRole("button", { name: "下一页遗物" }),
  ).toBeDisabled();
  const lastOption = picker.getByRole("button", {
    name: `选择遗物 ${ordinary.id} · ${last}`,
    exact: true,
  });
  await expect(lastOption).toHaveCount(1);
  // Filtering resets pagination, and opening details must not select a candidate.
  await picker.getByRole("button", { name: "仅显示收藏遗物" }).click();
  await expect(picker.getByRole("status")).toHaveText("1 件");
  await expect(
    picker.getByRole("button", { name: "上一页遗物" }),
  ).toBeDisabled();
  const effect = picker.locator(".effect-inspect").first();
  if (isMobile) {
    await effect.scrollIntoViewIfNeeded();
    const box = (await effect.boundingBox())!;
    const client = await page.context().newCDPSession(page);
    await client.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: [{ x: box.x + box.width / 2, y: box.y + box.height / 2 }],
    });
    await expect(
      page.getByRole("dialog", { name: "词条详情", exact: true }),
    ).toBeVisible();
    await client.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await client.detach();
    await page.getByRole("button", { name: "关闭词条详情" }).click();
  } else {
    await effect.hover();
    await expect(
      page.getByRole("dialog", { name: "词条详情", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "关闭词条详情" }).click();
  }
  await expect(lastOption).toHaveAttribute("aria-pressed", "false");
  await lastOption.click();
  await expect(picker).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "预设遗物 1", exact: true }),
  ).toBeFocused();
  await expect(page.locator(".preset-save-state")).toHaveText("未保存");
  await page.getByRole("button", { name: "预设遗物 4", exact: true }).click();
  const curse = fixedRoll(10004)!.find(
    (p) => p.curse !== EMPTY && p.curse !== 0,
  )!.curse;
  await page.getByLabel("搜索预设遗物").fill(effectName(curse));
  await expect(picker.locator(".relic-option")).toHaveCount(1);
  await expect(picker.locator(".preset-effect.curse")).toContainText(
    effectName(curse),
  );
  await expect(picker.locator(".relic-option")).toContainText(
    catalog.relics[10004].name.zh_CN,
  );
  await page.getByLabel("搜索预设遗物").fill("不存在的遗物");
  await expect(picker.getByText("无匹配", { exact: true })).toBeVisible();
  await picker.getByRole("button", { name: "重置筛选" }).click();
  await expect(picker.locator(".relic-option")).toHaveCount(1);
  await page.screenshot({ path: testInfo.outputPath("preset-candidate.png") });
  expect(
    await page
      .locator(".preset-dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await expect(
    picker.getByRole("button", { name: "清空当前遗物槽" }),
  ).toBeInViewport();
  await picker.getByRole("button", { name: "清空当前遗物槽" }).click();
  await expect(
    page.getByRole("button", { name: "预设遗物 4", exact: true }),
  ).toContainText("选择遗物");
  await page.getByRole("button", { name: "预设遗物 4", exact: true }).click();
  await picker
    .getByRole("button", { name: `选择遗物 10004 · ${shop}`, exact: true })
    .click();
  await page.getByRole("button", { name: "预设遗物 4", exact: true }).click();
  // Escape returns to the draft first, without discarding the chosen relic.
  if (isMobile)
    await picker.getByRole("button", { name: "关闭遗物选择" }).click();
  else await page.keyboard.press("Escape");
  await expect(picker).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "预设遗物 4", exact: true }),
  ).toBeFocused();
  await page.getByRole("button", { name: "保存预设", exact: true }).click();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const bytes = new Uint8Array(await readFile((await (await pending).path())!));
  const result = Session.open(bytes, "result").view(0);
  expect(result.relics.map(({ owners, ...r }) => r)).toEqual(
    session.view(0).relics.map(({ owners, ...r }) => r),
  );
  expect(result.loadouts!.presets[0].handles).toEqual([last, 0, 0, shop, 0, 0]);
});

test("retains compatible relics on vessel changes and keeps save reachable at narrow widths", async ({
  page,
  isMobile,
}, testInfo) => {
  const session = Session.open(fixture(), "test");
  const simple = toRoll([7000000, EMPTY, EMPTY, EMPTY, EMPTY, EMPTY]);
  const blue = session.apply(0, { type: "add", id: 109, roll: simple })!;
  const green = session.apply(0, { type: "add", id: 127, roll: simple })!;
  session.apply(0, {
    type: "preset",
    name: "保留配装",
    hero: 7,
    vessel: 19000,
    handles: [0xc0800054, blue, green, 0, 0, 0],
  });
  await page.goto("/");
  if (isMobile) await page.setViewportSize({ width: 320, height: 640 });
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(session.export()),
  });
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.locator(".preset-card").click();
  await page.getByLabel("器皿", { exact: true }).selectOption("7000");
  // Red is unmatched, blue and green retain their original matching slots.
  await expect(
    page.getByRole("button", { name: "预设遗物 1", exact: true }),
  ).toContainText("选择遗物");
  await expect(page.locator(".preset-slot-cell").nth(1)).toContainText(
    "生命力",
  );
  await expect(page.locator(".preset-slot-cell").nth(2)).toContainText(
    "生命力",
  );
  await page.getByRole("button", { name: "预设遗物 4", exact: true }).click();
  await expect(page.locator(".slot-no-results")).toContainText("无匹配");
  expect(
    await page
      .locator(".slot-pagination")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await page.getByRole("button", { name: "关闭遗物选择" }).click();
  const overview = page.locator(".preset-overview");
  await overview.evaluate((el) => el.scrollTo(0, el.scrollHeight));
  const save = page.getByRole("button", { name: "保存预设", exact: true });
  await expect(save).toBeInViewport();
  expect(
    await page
      .locator(".preset-dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  if (isMobile) {
    await page
      .getByRole("button", { name: "定位普通遗物 2", exact: true })
      .click();
    await expect(
      page.getByRole("button", { name: "预设遗物 2", exact: true }),
    ).toBeInViewport();
  }
  const editRelic = page.getByRole("button", {
    name: "编辑预设遗物 2",
    exact: true,
  });
  await editRelic.scrollIntoViewIfNeeded();
  const previousScroll = await overview.evaluate((el) => el.scrollTop);
  await editRelic.click();
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  expect(await overview.evaluate((el) => el.scrollTop)).toBe(previousScroll);
  await expect(page.getByLabel("器皿", { exact: true })).toHaveValue("7000");
  const bounds = (await page.locator(".preset-dialog").boundingBox())!;
  const viewport = page.viewportSize()!;
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.y).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width);
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height);
  await expect(save).toBeInViewport({ ratio: 1 });
  await page.screenshot({ path: testInfo.outputPath("preset-narrow.png") });
  await save.click();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const result = Session.open(
    new Uint8Array(await readFile((await (await pending).path())!)),
    "result",
  ).view(0);
  expect(result.loadouts!.presets[0]).toMatchObject({
    vessel: 7000,
    handles: [0, blue, green, 0, 0, 0],
  });
  expect(result.relics.map(({ owners, ...r }) => r)).toEqual(
    session.view(0).relics.map(({ owners, ...r }) => r),
  );
});

test("filters shop relics alongside search, favorites and usage without changing relics", async ({
  page,
  isMobile,
}, testInfo) => {
  const session = Session.open(fixture(), "test");
  const ordinary = session.view(0).relics[0];
  for (let i = 0; i < 19; i++)
    session.apply(0, { type: "add", id: ordinary.id, roll: ordinary.roll });
  const shop = session.apply(0, {
    type: "add",
    id: 1000,
    roll: fixedRoll(1000)!,
  })!;
  session.apply(0, { type: "add", id: 10004, roll: fixedRoll(10004)! });
  session.apply(0, { type: "favorite", handle: shop, value: true });
  session.apply(0, { type: "favorite", handle: ordinary.handle, value: true });
  session.apply(0, {
    type: "preset",
    hero: 7,
    vessel: 19000,
    name: "商店筛选",
    handles: [ordinary.handle, 0, 0, 0, 0, 0],
  });
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(session.export()),
  });
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.locator(".preset-card").click();
  await page.getByRole("button", { name: "预设遗物 1", exact: true }).click();
  const picker = page.getByRole("complementary", { name: "选择预设遗物" });
  const filter = picker.getByRole("button", { name: /^商店遗物筛选：/ });
  await expect(filter).toHaveAccessibleName("商店遗物筛选：全部遗物");
  await expect(filter).toHaveAttribute("aria-pressed", "false");
  await expect(picker.getByRole("status")).toHaveText("21 件");
  await picker.getByRole("button", { name: "下一页遗物" }).click();
  await filter.click();
  await expect(filter).toHaveAccessibleName("商店遗物筛选：仅商店遗物");
  await expect(filter).toHaveAttribute("aria-pressed", "true");
  await expect(picker.getByRole("status")).toHaveText("1 件");
  await expect(
    picker.getByRole("button", { name: "上一页遗物" }),
  ).toBeDisabled();
  await expect(picker.locator(".relic-option")).toContainText("商店遗物");
  await expect(picker.locator(".relic-option")).toHaveCount(1);
  await picker.getByRole("button", { name: "仅显示收藏遗物" }).click();
  if (isMobile) await filter.tap();
  else {
    await filter.focus();
    await filter.press("Space");
  }
  await expect(filter).toHaveAccessibleName("商店遗物筛选：排除商店遗物");
  await expect(filter).toHaveAttribute(
    "title",
    "排除商店遗物 · 点击切换为全部遗物",
  );
  await page.screenshot({
    path: testInfo.outputPath("shop-filter-excluded.png"),
  });
  await expect(picker.getByRole("status")).toHaveText("1 件");
  await expect(picker.locator(".relic-option")).not.toContainText("商店遗物");
  if (isMobile) await filter.tap();
  else await filter.press("Enter");
  await expect(filter).toHaveAccessibleName("商店遗物筛选：全部遗物");
  await expect(filter).toHaveAttribute("aria-pressed", "false");
  await expect(picker.getByRole("status")).toHaveText("2 件");
  await filter.click();
  await expect(filter).toHaveAccessibleName("商店遗物筛选：仅商店遗物");
  await expect(filter).toHaveAttribute("aria-pressed", "true");
  await picker.getByLabel("搜索预设遗物").fill("10004");
  await expect(picker.getByText("无匹配", { exact: true })).toBeVisible();
  await picker.getByRole("button", { name: "重置筛选" }).click();
  await expect(filter).toHaveAccessibleName("商店遗物筛选：全部遗物");
  await expect(filter).toHaveAttribute("aria-pressed", "false");
  await expect(picker.getByRole("status")).toHaveText("21 件");
  await filter.click();
  await expect(filter).toHaveAccessibleName("商店遗物筛选：仅商店遗物");
  await expect(filter).toHaveAttribute("aria-pressed", "true");
  await picker.getByLabel("筛选遗物使用情况").selectOption("current");
  await expect(picker.getByText("无匹配", { exact: true })).toBeVisible();
  await picker.getByLabel("筛选遗物使用情况").selectOption("unused");
  await picker.getByLabel("搜索预设遗物").fill("1000");
  await expect(picker.locator(".relic-option")).toHaveCount(1);
  await page.screenshot({ path: testInfo.outputPath("shop-filter.png") });
  await expect(
    picker.getByRole("button", { name: "清空当前遗物槽" }),
  ).toBeInViewport();
  expect(
    await page
      .locator(".preset-dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  await picker
    .getByRole("button", { name: `选择遗物 1000 · ${shop}`, exact: true })
    .click();
  await page.getByRole("button", { name: "保存预设", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const result = Session.open(
    new Uint8Array(await readFile((await (await download).path())!)),
    "result",
  ).view(0);
  expect(result.loadouts!.presets[0].handles).toEqual([shop, 0, 0, 0, 0, 0]);
  expect(result.relics.map(({ owners, ...r }) => r)).toEqual(
    session.view(0).relics.map(({ owners, ...r }) => r),
  );
});
