import { test, expect } from "@playwright/test";
import { nameFixture } from "../tests/character-name.fixture";
import { selectCharacter } from "./character-select-helper";

test("character selection separates the selected checkmark from pointer and keyboard focus", async ({
  page,
  isMobile,
}, testInfo) => {
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(nameFixture()),
  });
  const combo = page.getByRole("combobox", { name: "角色槽", exact: true });
  const list = page.getByRole("listbox", { name: "角色", exact: true });
  await selectCharacter(page, 1);
  await combo.click();
  const first = list.getByRole("option").nth(0),
    second = list.getByRole("option").nth(1);
  await expect(first).toHaveAttribute("aria-selected", "false");
  await expect(second).toHaveAttribute("aria-selected", "true");
  await expect(second.locator("svg")).toHaveCount(1);
  await expect(list.locator(".active")).toHaveCount(0);
  if (!isMobile) {
    await first.hover();
    await expect(list.locator(".active")).toHaveCount(1);
    await expect(first).toHaveClass(/active/);
    await expect(second).not.toHaveClass(/active/);
    await page.screenshot({
      path: testInfo.outputPath("hover-first-selected-second.png"),
    });
    await second.hover();
    await expect(list.locator(".active")).toHaveCount(1);
    await expect(second).toHaveClass(/active/);
    await combo.hover();
    await expect(list.locator(".active")).toHaveCount(0);
  } else {
    await page.screenshot({
      path: testInfo.outputPath("touch-character-list.png"),
    });
    await first.tap();
    await expect(combo).toHaveText("01 · OvO");
    await selectCharacter(page, 1);
    await combo.click();
  }
  expect(
    await list.evaluate((el) => {
      const rect = el.getBoundingClientRect();
      return (
        el.scrollWidth <= el.clientWidth &&
        rect.left >= 0 &&
        rect.right <= innerWidth
      );
    }),
  ).toBe(true);
  await combo.press("Home");
  await expect(first).toHaveClass(/active/);
  await expect(second).toHaveAttribute("aria-selected", "true");
  await combo.press("Escape");
  await expect(list).toHaveCount(0);
  await expect(combo).toHaveText("02 · ,>_<,");
  await combo.press("ArrowDown");
  await combo.press("Home");
  await combo.press("Enter");
  await expect(combo).toHaveText("01 · OvO");
  await expect(combo).toBeFocused();
  await combo.press(" ");
  await combo.press("End");
  await combo.press("Enter");
  await expect(combo).toHaveText("02 · ,>_<,");
  await combo.click();
  await page.locator(".wordmark").click();
  await expect(list).toHaveCount(0);
  await combo.press("ArrowDown");
  await combo.press("Tab");
  await expect(list).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "角色改名", exact: true }),
  ).toBeFocused();
  // Switching must retain the existing unsaved-edit confirmation.
  await page.getByLabel("Item ID").fill("101");
  page.once("dialog", (d) => d.dismiss());
  await selectCharacter(page, 0);
  await expect(combo).toHaveText("02 · ,>_<,");
  await expect(page.getByLabel("Item ID")).toHaveValue("101");
});
