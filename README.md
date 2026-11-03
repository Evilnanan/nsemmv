# NSE MMV

[打开编辑器](https://evilnanan.github.io/nsemmv/)

Daybreak / MMV 的 Nightreign 遗物存档编辑器。纯静态网页，支持桌面、平板和手机浏览器；文件在浏览器本地解析、校验和导出，无上传接口。

- PC BND4 加密存档：`.dbb`、`.co2`、`.sl2`、`.CL_SAVE`，角色数据版本 `308`。
- 多角色槽、遗物增删改、收藏、预设编辑与装备、预设内编辑遗物、撤销与重做。
- MMV 六池精确匹配、词条互斥、Curse 配对、商店遗物校验。
- 商店遗物按游戏 `EquipParamAntique.isSalable = 0` 分类，禁止修改与删除；收藏及配装仍可使用。
- Auto Fix 保持正负词条配对，先找完整合法的同色同类型 Item ID；其次仅放宽 Curse 数量要求，缺失或多余的 Curse 仍须修正后才能写入。
- 原始文件下载、未导出修改的离开提醒。导出文件需自行替换游戏存档；浏览器不能直接修改游戏目录。

数据固定为 **Daybreak 2.1.9 Beta2-Release / regulation 10350000**。不解析 PS 存档，不宣称兼容其它 Mod 参数版本。

## 开发

Node.js 24：

```sh
cd web
npm ci
npm run dev
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

用自己的存档运行额外本地测试（文件不会进入测试仓库）：

```sh
NR_SAVE=/absolute/path/NR0000.dbb npm test
```

## 部署

仓库 **Settings → Pages → Source → GitHub Actions**。推送 `main` 后，工作流运行核心与浏览器测试，再发布 `web/dist`。资源使用相对路径，可部署于 `/nsemmv/` 或其它静态站点子目录。没有运行时 CDN 依赖。

## 结构

| 层 | 职责 |
| --- | --- |
| `web/src/core/container.ts` | BND4、AES-CBC、MD5、区段边界与无修改原样导出 |
| `web/src/core/character.ts` | 有界记录解析、引用关系、局部修改与结构校验 |
| `web/src/core/rules.ts` | 与文件读写解耦的 MMV 合法性与候选规则 |
| `web/src/core/session.ts` | 独立会话、原始基线、事务、历史、导出回读 |
| `web/src/worker.ts` | 将解析和加密移出 UI 线程 |
| `tools/build_web_catalog.py` | 将固定版本 PARAM / FMG 归一化为浏览器目录 |

读取不修复或重排存档。未识别的原有词条可以原样保留，新增或变更必须通过校验。配装定位依赖完整结构验证，不依赖前一段的固定字节串。未识别布局不开放新增、删除、换色等依赖引用关系的操作。

[格式证据与边界](docs/save-format.md) · [数据与验证](docs/validation.md)

## 许可

代码遵循 [MIT](LICENSE)。游戏及 Mod 的名称、文本、参数归各自权利人所有。仓库不包含游戏可执行文件、完整 regulation 或个人存档。
