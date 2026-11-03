# 参数与验证

## 固定版本

Daybreak 2.1.9 Beta2-Release，regulation 内部版本 `10350000`。

SHA-256：`3305ac374b4da1db440e2b6644bc2c3c0ae96b98df9627f1a0e7a2b06d265c06`。

`data/source-profile.json` 保存输入身份、资源哈希和获取来源。`tools/build_web_catalog.py <resources>` 验证输入哈希，再归一化四类 PARAM CSV 和中英文 FMG。目录保留 1515 个遗物定义及 885 个有效获取来源定义；不会把 PARAM 中出现的所有测试条目都开放为可创建遗物。重复抽取表 ID 按多行合并，DLC 权重优先，权重为零或负的词条不进入候选。

## 词条分类

分类来自相同 MMV regulation 的三张原生表：`AttachEffectFilterParam`、`AttachEffectFilterCategoryParam`、`AttachEffectFilterSubCategoryParam`。`AttachEffectParam.attachFilterParamId` 指向筛选行，再由 `attachEffectFilterCategory` 指向子分类；子分类的 `filterCategory` 指向大分类。分类名称取同版本 `CL_MenuText` 和 DLC 覆盖文本，不依据词条名称中的关键词推断。

归一化后有 4 个大分类、64 个子分类；885 个可获取遗物定义所涉及的 637 个不同词条都有有效映射。不同等级可共用一个筛选行，如 `6611202` 通过 `6611200` 归入攻击力；角色专属词条保留其原生角色分类。没有映射的未来词条保留在“全部词条”和“未分类”，不静默丢弃。

`data/effect-filter-source.json` 保存筛选表、必要菜单文本和输入哈希。可用自己的 Smithbox、游戏及 MMV 文件重新提取：

```sh
dotnet build tools/ExtractEffectFilters/ExtractEffectFilters.csproj -p:SmithboxDir=<Smithbox目录>
dotnet tools/ExtractEffectFilters/bin/Debug/net10.0/ExtractEffectFilters.dll <Smithbox目录> <游戏目录> <MMV的mod目录> data/effect-filter-source.json
python tools/build_web_catalog.py <参数与文本资源目录>
```

提取工具需要游戏自带的 Oodle 库；Windows 直接运行，Linux 环境可通过 Wine 和 Windows .NET 运行提取器。仅输出派生 JSON，不改写输入。当前固定 regulation 哈希不匹配时拒绝提取。

界面分类与名称 / ID 搜索取交集，且仅在原有合法候选池上筛选；选定分类时手动 ID 不绕过分类。分类不模拟游戏的菜单解锁事件标志，也不据其隐藏 MMV 中有效可抽取的词条。保存仍经过同一套六池与 Curse 校验。

## 商店遗物

分类只取 `EquipParamAntique.isSalable`：`0` 为商店遗物，`1` 为可出售遗物。不使用 ID 区间、命名或独立硬编码名单，也不以 ShopLineup 获取来源替代可出售属性。所有 206 个不可出售定义都受保护；其中 134 个具有有效获取来源，当前版本均可确定完整固定词条。

已有商店遗物禁止修改 Item ID、词条和删除，也禁止将可编辑遗物转换成商店遗物。收藏与配装不改变遗物主体，仍可使用。创建只开放有效来源且完整合法的组合，并防止新增同 ID 的商店遗物副本；读取保留既有重复副本，不主动清理。没有获取来源的不可出售定义不会因归类而被开放创建。

## 选择前的可用性预览

以候选替换指定字段后检查完整组合，排除被替换的旧值，覆盖正面与 Curse 六个字段。重复、非 `-1` 的 compatibility 和 exclusivity 分组与保存校验共用冲突谓词。相关冲突会列出冲突对象，当前组合中其他字段已有的错误也会阻止该组合立即使用。

在与 Auto Fix 相同的同色同类型候选 Item ID 中，枚举六种正负配对排列。所有已填字段必须匹配对应池；尚未填写的字段及需要移除的多余 Curse 可作为待补齐状态。预编译分配方案，再逐候选检查，避免每次输入都对全部候选重复执行完整 Auto Fix。

界面区分三种状态：

- 可立即使用：存在完整合法的候选 Item ID，必要时可由 Auto Fix 换 ID；不显示错误标记。
- 待补齐：显示“需 Curse”“多余 Curse”或“待补词条”，允许继续选择和补齐。此状态只确认已填字段与抽取池兼容，不承诺任意补全都合法。
- 不可用：显示“冲突”“未知词条”“无效遗物”“池不匹配”或“组合不兼容”，悬停查看具体原因。

“排除不可用”与分类、搜索取交集，也作用于手动 ID；待补齐状态仍然可见。默认显示全部，本次页面会话中在库存和预设编辑之间保留开关状态。预览及切换筛选不修改遗物，保存前仍执行完整校验。

## 合法性

按六个抽取池验证三个正负词条配对，对三个配对的六种排列精确匹配。检查词条存在、重复、compatibility/exclusivity 冲突、正负词条数量及最终排序。Auto Fix 保留配对，在同色同类型的可出售遗物中寻找 ID；找不到完整匹配时仅放宽 Curse 数量来给出候选，缺失或多余 Curse 的组合仍不能写入。商店遗物不进入普通遗物的自动候选集。

原有未识别或不合法的组合按原始签名计数保留；不能新增同样的不合法副本。输入失败不会替换当前会话，每次操作独立事务，导出前重新验证。

## 自动验证范围

- 5310 个独立 Python 校验结果，覆盖全部 885 个可获取 ID。
- 所有可获取商店遗物的固定组合与可出售属性分类。
- 原生 72 字节初始化及预设创建/删除输出对照；具体桩与范围见格式文档。
- 无修改逐字节相同、损坏区段拒绝、另一角色密文保留、撤销/重做、Unicode 名称、物理预设空洞、引用保护。
- 库存分区隔离、主库存满时拒绝、实例索引边界、获取序号单调推进。
- 商店遗物的界面锁定及写入层拒绝。
- 替换自身不误报、正负六槽冲突、互斥分组、筛选计数、开关跨编辑器保留及预览不改动存档。
- 区分未知 ID、池外词条、不能抽取的正负组合、待补或多余 Curse；代表性场景的全部候选与 Auto Fix 结果交叉核对。
- 637 个可获取词条的原生分类覆盖，分类与搜索交集、分页切换、预设内筛选及 Curse 分类。
- 预设内编辑同一遗物、保留预设草稿、取消词条草稿，以及跨预设共享引用同步；预设内商店遗物只读。
- Chromium 桌面与手机视口：打开、编辑、导出、配装、词条搜索、Curse 校验、移动布局；没有文件上传请求。
- 可选 `NR_SAVE` 本地真实存档：逐字节无修改导出、已有角色读取、创建后加密并回读；个人文件不进入仓库。

这些检查不能替代在对应 MMV 版本中加载导出文件后的实际验收。未声称已完整反编译存档结构或验证全部游戏事件。

## 词条详情

`tools/ExtractEffectDetails` 从固定 MMV 文件只读提取 `AttachEffectParam`、`SpEffectParam`、`HeroStatusParam`、`EquipParamGoods` 和中英文 FMG。`tools/build_effect_details.py --extract <提取结果.json>` 检查 regulation 的版本与 SHA-256，保留必要引用、字段及说明到 `data/effect-detail-source.json`，生成浏览器用的 `web/src/data/effect-details.json`。原始全表提取结果不提交。之后运行 `python tools/build_effect_details.py` 即可从仓库内快照复现。

```sh
dotnet build tools/ExtractEffectDetails/ExtractEffectDetails.csproj -p:SmithboxDir=<Smithbox目录>
dotnet tools/ExtractEffectDetails/bin/Debug/net10.0/ExtractEffectDetails.dll <Smithbox目录> <游戏目录> <MMV的mod目录> <临时提取结果.json>
python tools/build_effect_details.py --extract <临时提取结果.json>
```

当前全部 2241 个目录词条有详情记录。637 个可获取词条中，447 个有可展示字段，其中 432 个有已解读的数值、15 个有出击替换法术名称；其余显示原生说明或“具体数值尚未解明”。这些覆盖数不表示每个词条都已完全解明。提取字段包括能力值、HP/FP/精力上限、攻击倍率、承伤倍率、FP 消耗、定值恢复、绝招量表、持续及周期。百分比按字段实际单位换算，承伤与减伤不混用，绝招量表按原生结算使用最大量表百分比。每个数值块保留 SpEffect 来源 ID，便于追溯。

沿十一类显式效果引用最多追踪六层，去除循环；只展示有已解读数值的节点。不同触发分支各自显示，不相加，不把子效果持续时间称为冷却。法术通道标志保留在研究数据中，界面不显示泛化的“法术适用”一行；混合魔法、重力魔法、近战等实际类别限制仍显示。名称及 FMG 提供玩法条件，自动提取并不代表已解明全部触发路径。比如 `7034200` 的链包含 +35% 攻击倍率与 +30% 法术 FP 消耗的两个三秒节点，其它强化效果及刷新机制仍待追踪。

详情卡只呈现游戏内生效规则，不显示抽取池、同件遗物互斥或合法性说明；已有选择列表中的可用性标记保留。不依据 `isNumericEffect`、`isStrongestEffect`、compatibility、菜单分组或同名程度自动判断跨遗物叠加；装备 exclusivity 仅作为进一步核对原生注入路径时的限制条件。普通杀敌回绝招 `7090000` 与 +1 版 `6090000` 经原生等级匹配、分派和数值结算确认“不同等级可叠加”，同等级重复无效。能力值、攻击、承伤、技艺冷却、绝招累积、抵抗力、FP 消耗、技艺次数、三武器条件与武器发现倾向等已核对 231 个词条的原生叠加处理。20 类角色能力调整由原生等级插值计算，覆盖 1～20 级。叠加分类统一为“不可叠加”“可叠加”“不同等级可叠加”；缺少参数及代码证据的标为“待确认”，不以使用报告作为判断依据。未声称进行了游戏内数值、全部叠加或联机实测。

经计时验证的一次性恢复不再展示节点存活时间；若会重置连续攻击累计进度，或重复触发影响再次恢复的间隔，则明确显示实际影响。真正的持续恢复、限时增益保留时长。

逐条研究记录保存在 `data/effect-research.json`，包含全部 637 个可获取词条的来源、证据和未解问题。原生隔离执行结果保存在 `data/effect-native-evidence.json`；构建核对版本及证据哈希，CI 检查派生数据可复现。具体方法、样例和边界见 [词条生效机制研究](research/effect-mechanics.md)。

详情卡在库存、预设共用的词条编辑器及选择器中提供；商店遗物只读时仍能查看。桌面延迟悬停、键盘聚焦或手机长按词条 480 毫秒可打开，无额外信息图标。长按后保持详情，阻止松手产生的选择点击；移动超过 10 像素、滚动取消、离开和多点触摸均取消尚未完成的长按。使用浏览器 popover 顶层跨越原生模态对话框与列表裁剪；支持移入卡片阅读、关闭按钮、Escape、点外部关闭及视口边界限制。查看与关闭不触发词条选择，不改动存档。
