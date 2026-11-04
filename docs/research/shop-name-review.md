# 同名商店遗物核对

从当前固定版本 MMV 的 `regulation.bin` 与中英文 `item_dlc01.msgbnd.dcx` 重新只读提取，核对全部 1515 个遗物的颜色、普通／深层、可出售标记、六个抽取池和名称；1173 个正权重词条池也逐一一致。摘要及输入 SHA-256 在 `data/shop-name-review.json`。

中文的两个“雾霾的黑夜”来自原始 FMG，属于不同遗物：

| Item ID | 英文名 | 类型 | 固定正面词条 ID | Curse ID |
| --- | --- | --- | --- | --- |
| 2060 | Night of the Miasma | 普通、黄、不可出售 | 7260700、7123900、7260400 | 无 |
| 19063 | Night-Hued Glass | 深层、黄、不可出售 | 7037501、6633100、6610702 | 6851000 |

2060 的词条为周围冻伤时隐身、出击战技“寒气冻雾”、对冻伤敌人强化攻击。19063 为送葬者蓄力祷告命中增防与强韧、容易找到圣印记、减少 FP 消耗＋２，搭配满血降低减伤率。词条写入后按原生排序保留正负配对。

2060 的获取来源是 `ItemTableParam:46000`；19063 是 `ShopLineupParam:13419`。二者均按不可出售规则归类为商店遗物，创建后不可修改／删除。创建器原先只显示同名文字及数字 ID，未显示深层属性，容易选错；列表现在显示普通／深层，详情也同时保留商店及深层属性。不修改源中文名，不自动转换已有存档中的遗物。

重新提取命令：

```sh
dotnet tools/ExtractEffectDetails/bin/Debug/net10.0/ExtractEffectDetails.dll <Smithbox目录> <游戏目录> <MMV的mod目录> <临时提取结果.json> --tables=EquipParamAntique,AttachEffectTableParam,ShopLineupParam
```

抽取表可能包含同 ID 多行，核对时同时读取 `tables` 和 `orderedTables`，按 DLC 权重覆盖规则聚合所有正权重效果。测试覆盖两件遗物的创建、导出回读、词条及类型保留，以及桌面／手机选择器的区别显示。这里未声称已在实际游戏中加载导出文件。
