import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { nameFixture } from "../tests/character-name.fixture";
import { Session } from "../src/core/session";
import { SaveContainer } from "../src/core/container";
import { Binary } from "../src/core/binary";
import { displayGameText } from "../src/core/game-text";

test("renames the selected character and selection summary, and gives dropdown options contrasting colors", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await page
    .getByLabel("打开存档文件")
    .setInputFiles({
      name: "NR0000.dbb",
      mimeType: "application/octet-stream",
      buffer: Buffer.from(nameFixture()),
    });
  const slots = page.getByLabel("角色槽");
  await slots.selectOption("1");
  expect(
    await slots.locator("option").evaluateAll((options) =>
      options.every((option) => {
        const style = getComputedStyle(option);
        const luminance = (color: string) => {
          const c = color
            .match(/[\d.]+/g)!
            .slice(0, 3)
            .map(Number)
            .map((v) => {
              v /= 255;
              return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
            });
          return c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722;
        };
        const a = luminance(style.color),
          b = luminance(style.backgroundColor);
        return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) >= 4.5;
      }),
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "角色改名", exact: true }).click();
  const input = page.getByLabel("角色名称", { exact: true });
  await expect(input).toHaveValue(",>_<,");
  await input.fill("");
  await expect(
    page.getByRole("button", { name: "保存角色名称" }),
  ).toBeDisabled();
  await input.fill("<搓招>隐士🪄");
  await page.screenshot({ path: testInfo.outputPath("rename-character.png") });
  await page.getByRole("button", { name: "保存角色名称" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(slots.locator("option:checked")).toHaveText("02 · <搓招>隐士🪄");
  await page.getByRole("button", { name: "撤销", exact: true }).click();
  await expect(slots.locator("option:checked")).toHaveText("02 · ,>_<,");
  await page.getByRole("button", { name: "重做", exact: true }).click();
  await expect(slots.locator("option:checked")).toHaveText("02 · <搓招>隐士🪄");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const bytes = new Uint8Array(await readFile((await (await pending).path())!));
  const result = Session.open(bytes, "result");
  expect(result.view(1).name).toBe("<搓招>隐士🪄");
  expect(result.view(0).name).toBe("OvO");
  expect(
    displayGameText(
      new Binary(SaveContainer.open(bytes).entries[10].plain).text(
        42 + 0x290,
        16,
      ),
    ),
  ).toBe("<搓招>隐士🪄");
  await page.screenshot({ path: testInfo.outputPath("renamed-character.png") });
});
