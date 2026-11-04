import { test, expect, type Page, type Locator } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { fixture } from "../tests/fixtures";
import { Session } from "../src/core/session";
import { fixedRoll } from "../src/core/rules";

async function load(page: import("@playwright/test").Page, bytes = fixture()) {
  await page.goto("/");
  await page.getByLabel("打开存档文件").setInputFiles({
    name: "NR0000.dbb",
    mimeType: "application/octet-stream",
    buffer: Buffer.from(bytes),
  });
}

async function longPress(page: Page, target: Locator) {
  await target.scrollIntoViewIfNeeded();
  const box = (await target.boundingBox())!;
  const client = await page.context().newCDPSession(page);
  await client.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [{ x: box.x + box.width / 2, y: box.y + box.height / 2 }],
  });
  try {
    await expect(
      page.getByRole("dialog", { name: "词条详情", exact: true }),
    ).toBeVisible();
  } finally {
    await client.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await client.detach();
  }
}

const decodedMechanics = [
  [7290000, ["重演伤害比例", "50% → 60%", "不可叠加", "不提高重演的削韧"]],
  [7280000, ["弱点最长持续时间", "17 → 22 秒", "不可叠加", "不补回弱点耐久"]],
  [7034300, ["鲜血烙印持续时间", "12.5 → 20 秒", "不可叠加", "普通版与延长版不会叠加恢复量"]],
  [7121000, ["道具栏位", "+1", "可叠加", "与小型随身包合计最多 +4 格"]],
  [7121100, ["×2（学者 ×4）", "数量相加，按单格上限分装"]],
  [7126000, ["星光碎片", "×2（学者 ×4）", "可叠加"]],
  [6621100, ["红结晶露滴", "×1（学者 ×2）"]],
  [7120000, ["物理攻击力", "-30／-40／-50／-60", "魔力攻击力", "+33／+44／+55／+66", "出击武器的属性／异常附加只生效一种"]],
  [7120400, ["攻击力", "-15%", "基础冻伤累积", "35", "不可叠加"]],
  [7120500, ["基础中毒累积", "35", "-15%"]],
  [7120600, ["基础出血累积", "25", "-15%"]],
  [7011000, ["旋风持续时间", "正常释放", "1 → 7 秒", "提前松开按键", "1 → 4 秒", "不可叠加"]],
  [6500300, ["无敌时间", "0.4 秒", "不可叠加", "再次触发刷新时长"]],
  [6500700, ["最大值的 0.27% + 3", "60 秒", "触发周期 1 秒", "恢复量相加、分别计时", "不可叠加"]],
  [7034800, ["异常状态抵抗力", "-80", "+20% → +26%", "20 秒", "倍率相乘、分别计时"]],
  [7034801, ["+20% → +26%", "不可叠加"]],
  [6840200, ["绝招量表累积（所有来源）", "-15%", "可叠加"]],
  [6500100, ["承伤倍率", "-18%", "30 秒", "自身及周围友方", "半径 8 米", "同类效果再次施加刷新时长"]],
  [7037000, ["物理攻击倍率", "+19%", "60 秒", "再次触发刷新时长", "恢复类祷告和武器附魔也可触发", "远方之恢复的触发待确认"]],
  [7034400, ["+35%", "+40%", "5 秒", "前段不适用，后段适用", "收刀不会提前解除", "不可叠加"]],
  [7011100, ["最大值的 15%", "半径 8 米", "自身及周围友方", "重复装备不增加单次恢复量", "可能合并或延后恢复"]],
  [7011101, ["最大值的 15%", "不可叠加"]],
  [7035400, ["基础发狂累积", "每 0.1 秒", "最大值的 10% + 100", "FP 损失", "30", "不同版本的累积相加", "同版重复无效"]],
  [7035410, ["实际发狂时", "免疫发狂", "不会因此损失 HP／FP"]],
  [7010900, ["最大值的 50%", "最大值的 100%", "半径 30 米", "不含自身", "获救时", "0.5 秒", "持续恢复"]],
  [16002, ["最大值的 50%", "不可叠加"]],
  [7032900, ["最大值的 20%", "HP 归零", "+16%", "30 秒", "+34.56%", "免疫时也不会获得增攻"]],
  [17002, ["最大值的 20%", "+16%", "不可叠加"]],
  [7340000, ["15", "约 1 秒内只触发一次", "连续命中不会延长间隔", "回血与回蓝可同时生效"]],
  [7352800, ["恢复参数", "实际触发待确认", "待确认"]],
  [7034500, ["最大值的 5% + 100", "维持解放状态不会反复恢复", "不可叠加"]],
  [12002, ["最大值的 10% + 12", "半径 15 米", "约每秒恢复一次", "只刷新有效期", "尚未到期的效果仍可能再恢复一次"]],
  [7012000, ["最大值的 10% + 12", "半径 15 米", "不可叠加"]],
  [7220200, ["+15%", "20 秒", "最大值的 10%", "15 秒", "每 2 秒", "+32.25%", "未消耗的机会在窗口结束时结算"]],
  [7032700, ["+5% 或 +15%", "30 秒", "12.5 秒", "倍率相乘", "不可叠加"]],
  [7034100, ["血量上限", "+50%", "前约 30 秒不因受损结束", "之后持续至下次受到损伤"]],
  [7033300, ["攻击倍率", "精力上限", "承伤倍率", "+20%", "40 秒", "不可叠加"]],
  [7033500, ["+10%", "10 秒", "重复装备不增加单次触发收益", "+21%"]],
  [7036800, ["+18%", "40 秒", "不可叠加"]],
  [7310000, ["图腾持续时间", "20 → 30 秒", "30 → 45 秒", "不可叠加"]],
  [7030000, ["强韧度损耗", "-90%", "30 秒"]],
  [7090300, ["+20% 或 +50% 最大 HP", "恢复量随敌人类型变化", "覆盖并刷新"]],
  [7032800, ["魔法阵持续时间", "30 秒", "半径 4.2 米", "1.5 秒", "不自动保留较强者"]],
  [7060000, ["约 +5%", "约 +1.5%", "拟态敌人最多计 2 档（需击败变身后的目标）", "倍率相乘"]],
  [7036200, ["-62.5%", "不可叠加"]],
  [7036300, ["+15%", "30 秒", "不可叠加"]],
  [7150000, ["当前 HP 的 5%", "物理伤害"]],
  [6632300, ["武器倾向", "弓", "替换角色默认倾向", "具体概率随奖池和候选权重变化", "不可叠加"]],
  [6633600, ["武器倾向", "调香瓶", "替换角色默认倾向"]],
] as const;

// Keep mobile long-press checks in bounded groups as the research catalog grows.
for (let offset = 0; offset < decodedMechanics.length; offset += 12) {
  const cases = decodedMechanics.slice(offset, offset + 12);
  test(`newly decoded mechanics remain readable: group ${offset / 12 + 1}`, async ({ page, isMobile }, testInfo) => {
    await load(page);
    await page.locator(".effect-cell").first().click();
    const details = page.getByRole("dialog", { name: "词条详情", exact: true });
    for (const [id, expected] of cases) {
      await page.getByLabel("搜索词条").fill(String(id));
      const row = page.locator(".effect-choice-inspect").filter({ hasText: String(id) });
      if (isMobile) await longPress(page, row.locator(".picker-row"));
      else await row.hover();
      for (const text of expected) await expect(details).toContainText(text);
      await expect(details).not.toContainText("部分触发条件尚未确认");
      expect(await details.evaluate((el) => {
        const rect = el.getBoundingClientRect();
        return el.scrollWidth <= el.clientWidth && rect.left >= 0 && rect.right <= innerWidth;
      })).toBe(true);
      if (id === 7032800 || id === 7060000 || id === 6632300)
        await page.screenshot({ path: testInfo.outputPath(`mechanics-${id}.png`) });
      await details.getByRole("button", { name: "关闭词条详情" }).click();
      await expect(details).toHaveCount(0);
    }
    await expect(page.locator(".effect-cell").first()).toContainText("生命力");
  });
}

test("effect details support hover, touch and keyboard without selecting or editing", async ({
  page,
  isMobile,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const original = fixture();
  await load(page, original);
  const first = page.locator(".effect-cell-inspect").first();
  if (isMobile) await longPress(page, first.locator(".effect-cell"));
  else await first.hover();
  const details = page.getByRole("dialog", { name: "词条详情", exact: true });
  await expect(details).toContainText("+1");
  await expect(details).toContainText("可叠加");
  await expect(details).toContainText("能力值相加");
  await details.getByRole("button", { name: "关闭词条详情" }).click();
  await expect(details).toHaveCount(0);
  await page.locator(".effect-cell").first().click();
  await page.getByLabel("搜索词条").fill("6611202");
  const row = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "6611202" });
  if (isMobile) await longPress(page, row.locator(".picker-row"));
  else await row.hover();
  await expect(details).toContainText("+14%");
  await expect(details).toContainText("可叠加");
  await expect(details).toContainText("攻击倍率相乘");
  await expect(details).not.toContainText("抽取池");
  await expect(details).not.toContainText("同件遗物");
  await expect(details).not.toContainText("互斥");
  await expect(details).not.toContainText("DPS");
  await expect(details).not.toContainText("最终伤害");
  await expect(details).not.toContainText("法术适用");
  await expect(details).not.toContainText("反馈");
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  // The card really sits above the native modal, within either viewport.
  expect(
    await details.evaluate((el) => {
      const r = el.getBoundingClientRect();
      return (
        r.left >= 0 &&
        r.right <= innerWidth &&
        r.top >= 0 &&
        r.bottom <= innerHeight &&
        el.contains(document.elementFromPoint(r.left + 15, r.top + 15))
      );
    }),
  ).toBe(true);
  await page.screenshot({ path: testInfo.outputPath("effect-details.png") });
  await page.keyboard.press("Escape");
  await expect(details).toHaveCount(0);
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  // Keyboard focus and Enter open details; Escape dismisses only the detail card.
  await row.focus();
  await page.keyboard.press("Enter");
  await expect(details).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("6646100");
  const growth = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "6646100" });
  if (isMobile) await longPress(page, growth.locator(".picker-row"));
  else await growth.hover();
  await expect(details).toContainText("随等级调整能力值");
  await expect(details).toContainText("集中力 -2 / 智力 +2 / 信仰 +2");
  await expect(details).toContainText("集中力 -13 / 智力 +12 / 信仰 +12");
  expect(await details.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBe(
    true,
  );
  await page.screenshot({
    path: testInfo.outputPath("hero-growth-details.png"),
  });
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("7090000");
  const kill = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "7090000" });
  if (isMobile) await longPress(page, kill.locator(".picker-row"));
  else await kill.hover();
  await expect(details).toContainText("不同等级可叠加");
  await expect(details).toContainText("+1.65% 或 +5%");
  await expect(details).not.toContainText("反馈");
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("7036000");
  const restore = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "7036000" });
  if (isMobile) await longPress(page, restore.locator(".picker-row"));
  else await restore.hover();
  await expect(details).toContainText("最大值的 5%");
  await expect(details).toContainText("重置连续攻击累计进度");
  await expect(details).not.toContainText("此效果持续");
  await expect(details).not.toContainText("触发周期");
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("7350000");
  const hit = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "7350000" });
  if (isMobile) await longPress(page, hit.locator(".picker-row"));
  else await hit.hover();
  await expect(details).toContainText("约 1 秒内只触发一次");
  await expect(details).toContainText("连续命中不会延长间隔");
  await expect(details).not.toContainText("1.1 秒");
  await expect(details).not.toContainText("此效果持续");
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("6820000");
  const poison = page
    .locator(".effect-choice-inspect")
    .filter({ hasText: "6820000" });
  if (isMobile) await longPress(page, poison.locator(".picker-row"));
  else await poison.hover();
  await expect(details).toContainText("中毒累积");
  await expect(details).toContainText("+52 点／次");
  await expect(details).not.toContainText("HP 损失");
  await expect(details).not.toContainText("此效果持续");
  await expect(details).not.toContainText("触发周期");
  await page.keyboard.press("Escape");
  await page.getByLabel("搜索词条").fill("999999998");
  await page.locator(".effect-choice-inspect").focus();
  await expect(details).toContainText("具体数值尚未解明");
  await page.getByLabel("搜索词条").click();
  await expect(details).toHaveCount(0);
  await page.getByRole("button", { name: "关闭", exact: true }).click();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出存档", exact: true }).click();
  const bytes = await readFile((await (await download).path())!);
  expect(bytes.equals(Buffer.from(original))).toBe(true);
  expect(errors).toEqual([]);
});

test("read-only shop effects expose details without unlocking edits", async ({
  page,
  isMobile,
}) => {
  const session = Session.open(fixture(), "test");
  const shop = 11015;
  session.apply(0, { type: "add", id: shop, roll: fixedRoll(shop)! });
  await load(page, session.export());
  await page.locator(".relic-card").filter({ hasText: "11015" }).click();
  await expect(page.locator(".effect-cell").first()).toBeDisabled();
  if (isMobile) await longPress(page, page.locator(".effect-cell").first());
  else {
    await page.locator(".effect-cell-inspect").first().focus();
    await page.keyboard.press("Enter");
  }
  await expect(
    page.getByRole("dialog", { name: "词条详情", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".effect-cell").first()).toBeDisabled();
});

test("mobile long press cancels on movement and never consumes the next short tap", async ({
  page,
  isMobile,
}) => {
  test.skip(!isMobile, "Touch gesture coverage");
  await load(page);
  await expect(page.locator(".effect-info")).toHaveCount(0);
  await page.locator(".effect-cell").first().tap();
  await page.getByLabel("搜索词条").fill("7000100");
  const row = page.locator(".picker-row").filter({ hasText: "7000100" });
  const details = page.getByRole("dialog", { name: "词条详情", exact: true });
  const box = (await row.boundingBox())!;
  const client = await page.context().newCDPSession(page);
  const point = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
  await client.send("Input.dispatchTouchEvent", {
    type: "touchStart",
    touchPoints: [point],
  });
  await page.waitForTimeout(100);
  await client.send("Input.dispatchTouchEvent", {
    type: "touchMove",
    touchPoints: [{ ...point, y: point.y - 35 }],
  });
  await page.waitForTimeout(550);
  await expect(details).toHaveCount(0);
  await client.send("Input.dispatchTouchEvent", {
    type: "touchEnd",
    touchPoints: [],
  });
  await client.detach();
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  await longPress(page, row);
  await expect(details).toBeVisible();
  await expect(page.getByLabel("搜索词条")).toBeVisible();
  await expect(page.locator(".effect-cell").first()).toContainText("生命力");
  await details.getByRole("button", { name: "关闭词条详情" }).tap();
  await row.tap();
  await expect(page.getByLabel("搜索词条")).toHaveCount(0);
  await expect(page.locator(".effect-cell").first()).toContainText("集中力");
});
