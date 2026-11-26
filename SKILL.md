---
name: xts-gate-windows
description: Use when building OpenHarmony XTS test suites on a Windows host through WSL with the Linux gate toolchain, or preparing an XTS suite for repository submission — covers WSL + Linux SDK/hvigor/node gate setup, acts vs system-API HITS repo/naming/system signing, BUILD.gn/module.json5/Test.json/syscap/hypium configuration, dynamic vs static builds, no-prebuilt-binary rules, gate-only compile errors, and the full pre-submit checklist. Windows-native hvigor is explicitly not gate-identical.
---

# XTS 门禁 Windows 编译与上库前准备

## 核心原则

**Windows 上编过 ≠ 门禁能过。** 门禁是 Linux 上的 `build.py → GN/ninja → hvigor`，它会额外检查 BUILD.gn 注册、schema、hap 命名、syscap、Test.json、大小写路径，并使用与本地 DevEco 不同版本的 hvigor/SDK。

本 skill 的唯一门禁一致路线是：**Windows 宿主 + WSL Ubuntu + 门禁 Linux 工具链（Linux SDK / Linux hvigor / node 18.20.1）**。Windows 原生 hvigor/DevEco 只能做语法和工程检查，**不能作为门禁结论**。

本 skill 只负责准备与本地验证，**不执行 git commit/push，也不提交 PR**；提交由你们按仓的流程完成。

## 硬性禁令（先读，任何理由都不例外）

- **禁止** `repo init`、`repo sync`、`git clone` OpenHarmony 整仓。XTS 叶子编译不需要整仓；门禁的 `build.py` 链路本地也跑不起来。
- **禁止** 运行 `build/prebuilts_download.sh` / `prebuilts_download.py`。它会拉全部 prebuilts（数 GB～数十 GB），而且**不包含**静态 hvigor。
- **下载预算**：单次下载 > 200 MB 必须先停下来问用户；只允许下载本 skill 明确列出的包（node 18.20.1、command-line-tools 26.0.1.290、`7.26.0-arkts1.2` 静态包、SDK）。
- 缺工具时**报告缺什么、给出官方下载地址**，然后停下；不要“顺手”把整仓拉下来。
- 只按 `references/windows-gate-build.md` 的叶子 hvigor 命令编译。违反以上任一条视为任务失败，**“为了和门禁一致”不是理由**。

先跑 `scripts/preflight.sh` 检查四件套，缺什么补什么，不要整仓。

## 先选路线

| 目标 | 路线 | 说明 |
|------|------|------|
| 门禁一致（唯一推荐） | **WSL Ubuntu + 门禁 Linux SDK + 门禁 hvigor 6.26.21 + node 18.20.1** | 已验证；本 skill 的主路线 |
| 只查工程问题、不编译 | `scripts/check_xts_project.py` + 生成 skill 的 `validate_test.py` + `ohos-test-xts-code-quality` | 零下载、最快 |
| Windows 原生 hvigor | 仅语法参考 | schema/API/编译器版本均与门禁不同，**不得**作为门禁通过依据 |
| 静态套件 | WSL + 公开镜像 `7.26.0-arkts1.2-0601-02` 工具包（解到 `7.26.0.static/hvigor`）+ Linux SDK 26.1.0 | 与门禁 `prebuilts/hvigor/7.26.0.static/hvigor` 同一 7.26.0 线；本地 5.14.2 仅作老近似，不作门禁证据 |

> 门禁本体是 Linux。不要把 Windows 原生 hvigor 的 `BUILD SUCCESSFUL` 当作门禁证据；所有编译结论都应在 WSL 内产生。

## 工作流 A：Windows 宿主 + WSL 门禁编译

完整步骤、路径校验、坑位见 `references/windows-gate-build.md`。所有编译命令都在 WSL 内执行。

1. 在 Windows 上确认 WSL：
   ```powershell
   wsl -l -v
   wsl -d Ubuntu -e bash -lc "uname -a && df -h /"
   ```
2. 在 WSL 内先跑 `scripts/preflight.sh`（只检查不下载），再准备四样东西（优先用本地已有包，不强制联网）：
   - `node-v18.20.1-linux-x64`（门禁 node 版本）
   - `command-line-tools 26.0.1.290`（动态门禁同款 hvigor 6.26.21）
   - 静态：`command-line-tools` `7.26.0-arkts1.2-0601-02`，解压到 `.../7.26.0.static/hvigor`（与门禁 `prebuilts/hvigor/7.26.0.static/hvigor` 布局一致）
   - 门禁 Linux SDK（`prebuilts/ohos-sdk/linux/<version>` 或每日 `ohos-sdk-full[_Dyn_Sta]` 的 linux 组件）
   - JDK 17（WSL 内 `java`，仅 HAP 打包需要）
3. 工程放到 WSL 的 `test/xts/acts/...` 深度，确保 `oh-package.json5` 里
   `file:../../../../../tools/hypium_prepare/*.har` 能解析到 `test/xts/tools/hypium_prepare`。
4. 在 WSL 内设置：
   ```bash
   export DEVECO_NODE_HOME=/root/ohos-gate/toolchain/node-v18.20.1-linux-x64
   export PATH=$DEVECO_NODE_HOME/bin:$PATH
   export OHOS_BASE_SDK_HOME=/root/ohos-gate/sdk   # 其下有 26.1.0/{ets,js,native,previewer,toolchains}
   export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
   ```
   `local.properties` 写 `sdk.dir=/root/ohos-gate/sdk`。
5. 在 WSL 内安装依赖：`ohpm install`。先确认 registry 是公开源（7.26 包内 ohpm 默认是华为内网，外网会报 hypium/hamock NOTFOUND）：
   ```bash
   printf 'registry=https://ohpm.openharmony.cn/ohpm/\n' > .ohpmrc
   ```
   若 ohpm 因 node 版本报 `ERR_REQUIRE_ESM`，按 §手动安装 hypium 处理。
6. 动态（`BUILD.gn` 里 `test_hap = true`）：
   ```bash
   cd <suite>
   /root/ohos-gate/toolchain/clt-26.0.1.290/bin/hvigorw \
     --mode module -p module=entry@ohosTest assembleHap \
     -p debuggable=false -p hvigor-obfuscation=false --no-daemon
   ```
   产物：`entry/build/default/outputs/ohosTest/entry-ohosTest-unsigned.hap`
7. 静态（`ohos_js_app_static_suite`，`test_hap` 注释掉）：
   ```bash
   /root/ohos-gate/toolchain/hvigor-static/7.26.0.static/hvigor/bin/hvigorw \
     --mode project -p product=default assembleApp \
     -p debuggable=false -p hvigor-obfuscation=false --no-daemon
   ```
   工程配置须为门禁静态模板：`modelVersion "26.0.0"`（`hvigor-config.json5` 与 `oh-package.json5`）、`compileSdkVersion "26.1.0"`、`compatibleSdkVersion "22"`、`arkTSVersion "1.2"`。
   产物：`entry/build/default/outputs/default/entry-default-unsigned.hap` 和 `<suite>/build/outputs/default/<suite>-default-unsigned.app`
8. 用 `scripts/run-gate-build.ps1`（Windows 侧调用 WSL）或 `scripts/run-gate-build.sh`（WSL 内）可一次完成校验 + 构建 + 产物检查。

### 两个高频环境坑（WSL 内）

- `spawn .../node ENOENT`：hvigor 6.26.21 期望 SDK 有 `ets/build-tools/ets-loader`；26.1.0.22 是 `ets/dynamic/build-tools`。在 WSL 的 SDK 内建兼容链接：
  `ln -sfn dynamic/build-tools <sdk>/26.1.0/ets/build-tools`（仅本地临时 SDK；优先用 26.1.0.27+ 门禁 SDK）。
- `spawn java ENOENT`：HAP 打包需要 Java；WSL 内安装 `openjdk-17-jre-headless`，设置 `JAVA_HOME`。

## 工作流 B：完善 XTS 工程

字段级规则、目录结构、动态/静态差异见 `references/project-completion.md`。

必须同时满足：

0. **选仓/命名**：普通 Public API → `xts_acts` + `Acts` 前缀；`@systemapi`/系统权限 → **HITS 独立仓（闭源，仓名与流程以 HITS 团队/CI 为准）** + `Hits` 前缀 + 系统签名。不要把 system API 用例提交到 `xts_acts`，也不要混用前缀。详见 `references/system-api-hits.md`。
1. **目录/注册**：suite 放在对应仓的 `<subsystem>/<part>/<suite>` 下；父 `BUILD.gn` 的 `group("<part>")` 的 deps 里追加 `"<suite>:<Target>"`；若是新子系统，还要在 `test_targets.gni` 的 `all_test_targets` 增加该子系统 group。
2. **BUILD.gn**：动态 `ohos_js_app_suite` + `test_hap = true`；静态 `ohos_js_app_static_suite` + `# test_hap = true`；`hap_name` 按仓用 `Acts`/`Hits` 前缀；`part_name`/`subsystem_name` 与 `bundle.json` 一致；`certificate_profile` 指向存在的 p7b。
3. **module.json5**：`extensionAbilities[]` 不允许 `process`；需要独立进程用 `extensionProcessMode`（`bundle|type|instance`）。`process` 只能写在 `abilities[]` 下。
4. **Test.json**：`test-file-name` 与 `hap_name.hap` 一致；`bundle-name` 与 `AppScope/app.json5` 一致；`module-name` 动态=`entry_test`、静态=`entry`，与 module.json5 的 `module.name` 一致。
5. **syscap.json**：动态检查 `entry/src/ohosTest/syscap.json`，静态检查 `entry/src/main/syscap.json`；`custom[].xts` 至少包含被测 API 的 `@syscap`（如 `SystemCapability.Ability.AbilityRuntime.Core`）。
6. **oh-package.json5**：动态 `@ohos/hypium-dynamic`、静态 `@ohos/hypium-static`，路径指向 `file:../../../../../tools/hypium_prepare/*.har`；`modelVersion` 与 hvigor 代际匹配（门禁 26.x → `26.0.0`）。
7. **build-profile.json5**：API ≥26 时 `compileSdkVersion`/`compatibleSdkVersion` 用字符串（如 `"26.1.0"`/`"26.0.0"`），<26 用数字；静态加 `arkTSVersion: "1.2"`；`runtimeOS: "OpenHarmony"`；建议开 `strictMode.caseSensitiveCheck`。
8. **代码**：动态用 `rpc.MessageParcel`，静态用 `rpc.MessageSequence`；`parameters` 先判空；禁止 `globalThis`；静态用 `int`/`long`，回调按 `AsyncCallback<T>` 推断；`@tc.number` 唯一；清理用 `try/finally`。
9. **接口**：新接口的 callback/Promise 重载必须由 `interface/sdk-js` 按 spec 提供；测试保留 spec 要求的用例，不要为了本地编译删掉。接口未合入前，门禁必挂。
10. **禁止预编译二进制**：工程内不得携带 `.hsp`、`.hap`、`.har`、`.so`、`.abc`、`.jar` 等预编译产物；所有模块必须在门禁中从源码编译。HSP 依赖必须改为源码模块，不能把现成 HSP 塞进工程。

## 工作流 C：提交前检查

完整清单见 `references/pre-submit-checklist.md`。最少执行：

```powershell
python scripts\check_xts_project.py <suite_dir>
```

检查器覆盖：BUILD.gn 模板/test_hap/hap_name/part、module.json5 `process`/`extensionProcessMode`、Test.json 名称一致性、syscap、hypium har、compileSdkVersion 类型、动态/静态 RPC 类型、`parameters` 判空、`globalThis`、`@tc.number` 重复、大小写敏感 import、父 group 注册、构建残留。

再按顺序跑：

1. `python .../ohos-test-xts-code-quality/scripts/main.py <suite> --level all --sta-mode dyn|sta`
2. `python .../ohos-test-arkts-xts-generation/scripts/validate_test.py <test_file>`
3. **在 WSL 内**跑动态门禁命令 + 静态 7.26.0 命令，确认 HAP/APP 产物
4. `git status`：不得提交 `oh_modules/`、`build/`、`.hvigor/`、`local.properties`、`oh-package-lock.json5`

## 门禁专属失败速查

Windows 本地编过、门禁却失败的常见原因：

| 现象 | 根因 | 修复 |
|------|------|------|
| `Schema validate failed ... extensionAbilities[0] ... process` | extensionAbilities 不支持 `process` | 删除；用 `extensionProcessMode` |
| `Expected N arguments, got M`（某个 API 调用） | 接口缺 spec 要求的重载，或测试用了 SDK 没有的签名 | 对照 `interface/sdk-js` 与 spec；接口补齐后再编，不要删用例 |
| `XxxRemoteObject is not assignable to RemoteObject` | 动态工程用了静态 RPC 类型 | 动态改 `MessageParcel`；静态用 `MessageSequence` |
| `'data.parameters' is possibly 'undefined'` | 新 SDK 中 `parameters` 可选 | 先判空再取 |
| `arkts-no-globalthis` | ArkTS 禁止 globalThis | 删除，改用 AppStorage/参数 |
| `spawn .../node ENOENT` | SDK 无 `ets/build-tools/ets-loader` | 用 26.1.0.27+ 或建兼容链接 |
| `spawn java ENOENT` | 无 JDK | 装 JDK 17 / 指 DevEco jbr |
| ohpm `NOTFOUND '@ohos/hypium@1.0.25'` / `missing: @ohos/hamock@1.0.0` | ohpm 默认 registry 是华为内网，外网解析不到（包本身存在） | `.ohpmrc` 写 `registry=https://ohpm.openharmony.cn/ohpm/`；HSP 模块可删 hypium/hamock devDeps |
| `00303038 ... propertyName: 'alternateModule'` | SDK `toolchains/modulecheck/module.json` 旧版本缺 API 26.1 字段 | 换含该字段的 SDK；`grep -c alternateModule <sdk>/toolchains/modulecheck/module.json` 必须 > 0 |
| 静态 `Double` vs `Int` | hilog domain/参数用了 `number` | 改 `int` |
| 静态 `CommonEventSubscriber \| undefined` | 联合类型未收窄 | 取本地常量后判空 |
| 静态回调 `No matching call signature` | 显式写死 `AsyncCallback` 参数 | 用类型推断的回调，并补齐两个参数 |
| 静态 `Double` vs `Long` | connectionId 用了 `number` | 改 `long` |
| 门禁没编你的 suite | BUILD.gn 未注册/part 不在产品 | 父 group + `test_targets.gni` + part 核对 |
| system API 用例提交到 acts / 用 Acts 前缀 | 选错仓/命名 | 改提交 HITS 仓；`Hits` 前缀 + 系统签名 |
| 工程内出现 `.hsp`/`.hap`/`.har`/`.so` 等 | 携带预编译二进制，门禁禁止 | 删除；改为源码模块由门禁编译 |

更多错误原文与修复见 `references/gate-error-catalog.md`。

## 文件地图

```
xts-gate-windows/
  SKILL.md
  references/
    windows-gate-build.md      # Windows/WSL 门禁工具链、命令、坑位
    project-completion.md      # BUILD.gn/配置/代码/注册完整规则
    pre-submit-checklist.md    # 上库前逐项检查
    system-api-hits.md         # system API：HITS 仓、Hits 命名、系统签名（闭源仓不推测）
    gate-error-catalog.md      # 门禁错误原文 → 根因 → 修复
  scripts/
    check_xts_project.py       # 零依赖工程检查器（Windows/WSL 均可）
    run-gate-build.sh          # WSL 内门禁编译
    run-gate-build.ps1         # Windows 侧调用 WSL 的包装
    fetch-static-toolchain.sh  # 自动选镜像最新 7.26* 并解压（WSL 内，--list 可查）
    preflight.sh               # 四件套自检（只检查，不下载）
  templates/
    BUILD.gn.dynamic / BUILD.gn.static
    Test.json
    module.json5.snippet
    local.properties.example
    hvigor-config.json5.example
    CLAUDE.md.snippet                  # 整仓下载禁令，复制到项目/全局 CLAUDE.md
    block-full-repo-download.js        # PreToolUse hook：拦截 repo sync / prebuilts_download
    claude-settings.hooks.json.example # hook 接线示例
```

## 验证状态

- 2026-11-26 在一对真实动态/静态 XTS suite 上验证：
  - WSL + 门禁 hvigor 6.26.21 + node 18.20.1：动态 `BUILD SUCCESSFUL`。
  - WSL + 公开 `7.26.0-arkts1.2-0601-02` 工具（解为 `7.26.0.static/hvigor`）+ Linux SDK 26.1.0 + 门禁静态模板配置：静态 `BUILD SUCCESSFUL`，产出 `.hap` + `.app`。
  - 该包与门禁 `7.26.0.static` 同名线但非同一文件名，字节一致性未证明；最终以门禁 CI 为准。
- Windows 路线由门禁脚本反推（同一 hvigor JS/命令），本会话未做 Windows 字节级对照；门禁复核优先 WSL。

## 不要做

- 不要用 Windows 原生 hvigor/DevEco 编完就认为门禁会过；编译结论必须在 WSL + Linux 工具链内产生。
- 不要把 system API 用例放进 acts，或把普通 API 放进 HITS；不要猜测闭源 HITS 仓的构建命令。
- 不要在工程里放预编译 `.hsp`/`.hap`/`.har`/`.so` 等二进制；所有模块必须门禁源码编译。
- 不要为了让本地编过而删掉 spec 要求的用例或重载。
- 不要用 junction/symlink 的 SDK 根目录（node/es2panda realpath 会报 `F0019`）；用真实目录或硬链接镜像。
- 不要把 `process` 写到 `extensionAbilities`；不要提交构建残留。
- 不要在 Windows 大小写不敏感的文件系统上假设 import 路径正确；用检查器的大小写检查。
