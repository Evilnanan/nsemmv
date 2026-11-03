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
- 637 个可获取词条的原生分类覆盖，分类与搜索交集、分页切换、预设内筛选及 Curse 分类。
- 预设内编辑同一遗物、保留预设草稿、取消词条草稿，以及跨预设共享引用同步；预设内商店遗物只读。
- Chromium 桌面与手机视口：打开、编辑、导出、配装、词条搜索、Curse 校验、移动布局；没有文件上传请求。
- 可选 `NR_SAVE` 本地真实存档：逐字节无修改导出、已有角色读取、创建后加密并回读；个人文件不进入仓库。

这些检查不能替代在对应 MMV 版本中加载导出文件后的实际验收。未声称已完整反编译存档结构或验证全部游戏事件。
