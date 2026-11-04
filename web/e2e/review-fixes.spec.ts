import { test, expect, type Page } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { character, fixture } from "../tests/fixtures";
import { Binary } from "../src/core/binary";
import { Character } from "../src/core/character";
import { Session } from "../src/core/session";
import { fixedRoll } from "../src/core/rules";

async function load(page: Page, raw = fixture()) {
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(raw),
  });
}

test("game-encoded character and preset names display their native symbols", async ({
  page,
}) => {
  const raw = character();
  new Binary(raw).putText(new Character(raw).nameOffset, 16, ",㉒_㉑,⑲⑳㉓㉔㉕");
  const s = Session.open(fixture({ 0: raw }), "test");
  s.apply(0, {
    type: "preset",
    hero: 7,
    vessel: 19000,
    handles: [0xc0800054, 0, 0, 0, 0, 0],
    name: "<隐士>#?%＼¥",
  });
  await load(page, s.export());
  await expect(page.getByLabel("角色槽")).toContainText(",>_<,#?%＼¥");
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await expect(page.locator(".preset-card")).toContainText("<隐士>#?%＼¥");
  await page.locator(".preset-card").click();
  await expect(page.getByLabel("预设名称")).toHaveValue("<隐士>#?%＼¥");
});

test("shop picker distinguishes ordinary and deep relics with identical names", async ({
  page,
}, testInfo) => {
  await load(page);
  for (const [id, kind, effect] of [
    [2060, "普通", 7260700],
    [19063, "深层", 7037501],
  ] as const) {
    await page.getByRole("button", { name: "新增遗物", exact: true }).click();
    await page.getByRole("button", { name: "商店遗物", exact: true }).click();
    await page.getByLabel("搜索遗物类型").fill("雾霾的黑夜");
    await expect(page.locator(".picker-row")).toHaveCount(2);
    const row = page
      .locator(".picker-row")
      .filter({ has: page.locator("code", { hasText: String(id) }) });
    await expect(row.locator(".relic-kind")).toHaveText(kind);
    await page.screenshot({ path: testInfo.outputPath(`shop-${id}.png`) });
    expect(
      await page
        .getByRole("dialog")
        .evaluate((el) => el.scrollWidth <= el.clientWidth),
    ).toBe(true);
    await row.click();
    await expect(page.getByLabel("Item ID")).toHaveValue(String(id));
    await expect(page.locator(".type-chip")).toContainText(
      `商店遗物 · ${kind}`,
    );
    await expect(page.locator(".effect-grid")).toContainText(String(effect));
    await page.getByRole("button", { name: "应用修改", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "删除遗物", exact: true }),
    ).toBeDisabled();
  }
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const reopened = Session.open(
    new Uint8Array(await readFile((await (await download).path())!)),
    "reopen",
  );
  for (const id of [2060, 19063])
    expect(reopened.view(0).relics.find((r) => r.id === id)?.roll).toEqual(
      fixedRoll(id),
    );
});

test("invalid effects and both conflicting curses show warning icons", async ({
  page,
}, testInfo) => {
  const raw = character();
  const state = new Character(raw).relics[0].stateOffset;
  const b = new Binary(raw);
  b.put32(state + 16, 99999999);
  b.put32(state + 56, 6840200);
  b.put32(state + 60, 6840200);
  await load(page, fixture({ 0: raw }));
  await expect(page.locator(".effect-cell.invalid")).toHaveCount(3);
  await expect(page.locator(".effect-cell.curse.invalid")).toHaveCount(2);
  await expect(page.locator(".effect-warning")).toHaveCount(3);
  await expect(
    page.getByRole("button", { name: "应用修改", exact: true }),
  ).toBeDisabled();
  for (const cell of await page.locator(".effect-cell.invalid").all()) {
    await expect(cell).toHaveAttribute("aria-invalid", "true");
    await cell.hover();
    await expect(cell.locator(".effect-warning")).toBeVisible();
    await expect(cell).toHaveCSS("border-top-style", "solid");
  }
  await page.mouse.move(0, 0);
  await page.screenshot({
    path: testInfo.outputPath("invalid-curses.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
