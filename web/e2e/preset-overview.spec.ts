import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture } from "../tests/fixtures";
import { Session } from "../src/core/session";
import { effectName, relicDefinitions } from "../src/core/catalog";
import { fixedRoll } from "../src/core/rules";
import { EMPTY } from "../src/core/binary";

test("preset overview exposes every equipped effect and curse without opening relics", async ({
  page,
  isMobile,
}, testInfo) => {
  const session = Session.open(fixture(), "test");
  const handles = [0xc0800054];
  for (const deep of [false, false, true, true, true]) {
    const used = session.view(0).relics.map((r) => r.id);
    const meta = relicDefinitions.find((r) => {
      if (!r.shop || r.deep !== deep || used.includes(r.id)) return false;
      const roll = fixedRoll(r.id);
      return roll?.every((p) => p.effect !== EMPTY && p.effect !== 0);
    })!;
    handles.push(
      session.apply(0, {
        type: "add",
        id: meta.id,
        roll: fixedRoll(meta.id)!,
      })!,
    );
  }
  session.apply(0, {
    type: "preset",
    hero: 7,
    vessel: 19000,
    handles,
    name: "全部词条",
  });
  const original = session.export();
  await page.goto("/");
  await page
    .getByLabel("打开存档文件")
    .setInputFiles({
      name: "NR0000.dbb",
      mimeType: "application/octet-stream",
      buffer: Buffer.from(original),
    });
  await page.getByRole("button", { name: "预设", exact: true }).click();
  await page.locator(".preset-card").click();
  await expect(page.locator(".preset-effects")).toHaveCount(6);
  const curseCount = session
    .view(0)
    .relics.filter((r) => handles.includes(r.handle))
    .flatMap((r) => r.roll)
    .filter((p) => p.curse !== EMPTY && p.curse !== 0).length;
  expect(curseCount).toBeGreaterThan(0);
  await expect(page.locator(".preset-effect.curse")).toHaveCount(curseCount);
  for (const [index, handle] of handles.entries()) {
    const relic = session.view(0).relics.find((r) => r.handle === handle)!;
    const expected = relic.roll
      .flatMap((p) => [p.effect, p.curse])
      .filter((id) => id !== EMPTY && id !== 0);
    const rows = page
      .locator(".preset-slot-cell")
      .nth(index)
      .locator(".preset-effect");
    await expect(rows).toHaveCount(expected.length);
    for (const [i, id] of expected.entries()) {
      await expect(rows.nth(i).locator("span")).toHaveText(effectName(id));
    }
  }
  expect(
    await page
      .locator(".preset-effect")
      .evaluateAll((rows) =>
        rows.every((row) => row.scrollWidth <= row.clientWidth),
      ),
  ).toBe(true);
  expect(
    await page
      .locator(".preset-dialog")
      .evaluate((el) => el.scrollWidth <= el.clientWidth),
  ).toBe(true);
  const target = page.locator(".preset-effects .effect-inspect").first();
  if (isMobile) {
    await target.scrollIntoViewIfNeeded();
    const box = (await target.boundingBox())!;
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
  } else {
    await target.hover();
  }
  await expect(
    page.getByRole("dialog", { name: "词条详情", exact: true }),
  ).toContainText("+1");
  await page.getByRole("button", { name: "关闭词条详情" }).click();
  await expect(page.locator(".slot-picker, .preset-relic-editor")).toHaveCount(
    0,
  );
  await page.locator(".preset-dialog").evaluate((el) => el.scrollTo(0, 0));
  await page.screenshot({ path: testInfo.outputPath("preset-overview.png") });
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  expect(
    (await readFile((await (await download).path())!)).equals(
      Buffer.from(original),
    ),
  ).toBe(true);
});
