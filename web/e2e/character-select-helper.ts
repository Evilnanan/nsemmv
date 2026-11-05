import type { Page } from "@playwright/test";

export async function selectCharacter(page: Page, slot: number) {
  await page.getByRole("combobox", { name: "角色槽", exact: true }).click();
  await page
    .getByRole("listbox", { name: "角色", exact: true })
    .getByRole("option", {
      name: new RegExp(`^${String(slot + 1).padStart(2, "0")} ·`),
    })
    .click();
}
