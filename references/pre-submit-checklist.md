# XTS 上库前检查清单

> 目标：提交 PR 后门禁一次通过。每项都要有证据（命令输出、HAP 路径、日志行），不要凭“本地编过了”。

## 0. 确认范围

- [ ] 明确是动态、静态，还是两者都要。
- [ ] 明确 API 类型：Public → `xts_acts` + `Acts`；`@systemapi` → **HITS 独立仓（闭源，仓名/流程以 HITS 团队为准）** + `Hits` + 系统签名。
- [ ] 明确 suite 的 `<subsystem>`、`<part>`、`<Target>`、`hap_name`。
- [ ] 确认没有把 system API 用例放进 acts，或把普通 API 放进 HITS。
- [ ] 明确被测 API 的 `@syscap`、是否 `@systemapi`、是否新接口。
- [ ] 新接口：确认 `interface/sdk-js` 声明（参数个数/类型/重载）与 spec 一致。
- [ ] 新接口：确认接口 PR 已合入，门禁使用的 SDK 已包含该声明。

## 1. 目录与注册

- [ ] suite 在 `test/xts/acts/<subsystem>/<part>/<suite>`。
- [ ] 父 `BUILD.gn` 的 `group("<part>")` deps 包含 `"<suite>:<Target>"`。
- [ ] 若是新 subsystem，`test_targets.gni` 的 `all_test_targets` 包含 `"${ACTS_ROOT}/<subsystem>:<subsystem>"`。
- [ ] `part_name`/`subsystem_name` 与部件 `bundle.json` 一致。
- [ ] 目录名与 target 名不要混用；门禁认的是 `ohos_js_app_suite("...")`。
- [ ] 只有一个 suite 时，`build.py` 的 `suite=<Target>` 能命中；group 编译时父 group 能命中。

## 2. BUILD.gn

- [ ] 动态：`ohos_js_app_suite`，`test_hap = true`（未被注释）。
- [ ] 静态：`ohos_js_app_static_suite`，`test_hap` 已注释/删除。
- [ ] `hap_name` 按仓使用 `Acts`/`Hits` 前缀（acts R014；HITS 用 `Hits`）。
- [ ] `certificate_profile` 文件存在。
- [ ] 没有把 `final_hap_path` 等旧字段与新模板混用。
- [ ] BUILD.gn 为 LF、UTF-8；没有 CRLF 导致的 GN 解析问题。

## 3. 配置文件

- [ ] `build-profile.json5`：
  - [ ] API ≥26 时 `compileSdkVersion`/`compatibleSdkVersion` 是字符串；<26 是数字。
  - [ ] 静态有 `arkTSVersion: "1.2"`。
  - [ ] `runtimeOS: "OpenHarmony"`。
  - [ ] `strictMode.caseSensitiveCheck: true`（建议）。
- [ ] `hvigor/hvigor-config.json5` 与 `oh-package.json5` 的 `modelVersion` 一致，且与 hvigor 代际匹配（门禁 26.x → `26.0.0`）。
- [ ] `oh-package.json5` 使用 `@ohos/hypium-dynamic` / `@ohos/hypium-static` 的本地 har 路径；不要改成 registry 版本。
- [ ] `Test.json`：
  - [ ] `test-file-name` = `hap_name.hap`。
  - [ ] `bundle-name` = `AppScope/app.json5` 的 `bundleName`。
  - [ ] `module-name` 动态 `entry_test`、静态 `entry`，与 module.json5 一致。
- [ ] `module.json5`：
  - [ ] `extensionAbilities[]` 没有 `process`。
  - [ ] 需要独立进程时使用 `extensionProcessMode`。
  - [ ] `srcEntry` 大小写与真实文件一致。
- [ ] `syscap.json`：`custom[].xts` 至少包含 API 的 `@syscap`；调用 bundleManager 等能力时补齐。
- [ ] 系统 API：profile 与 `certificate_profile` 能系统签名。

## 4. 代码

- [ ] 每个 `it` 有 `@tc.name`/`@tc.number`/`@tc.desc`/`@tc.type`。
- [ ] `@tc.number` 全局唯一（检查器会查重）。
- [ ] 动态：`onRemoteRequest` 用 `rpc.MessageParcel`。
- [ ] 静态：`onRemoteRequest` 用 `rpc.MessageSequence`。
- [ ] `parameters` 先判空；没有 `data.parameters['x']` 裸访问。
- [ ] 没有 `globalThis`。
- [ ] 静态数字类型：错误码/domain/计数用 `int`；connectionId 用 `long`；不要用 `number` 传给 `int`/`long`。
- [ ] 静态回调：用类型推断，处理 `err: BusinessError | null` 与 `data: T | undefined`；不要手写不匹配的 `AsyncCallback`。
- [ ] 静态联合类型（`CommonEventSubscriber | undefined`、`context`）先赋本地常量再判空。
- [ ] `.catch` 用 `Error`，取 `code` 前转 `BusinessError`。
- [ ] 异步用例 `await` 在 `try` 内；`afterAll` 用 `try/finally` 清理。
- [ ] 错误码断言用 `Number(error.code)` / `error.code as number`，不要只断言非空。
- [ ] 没有新增 `console.log`、硬编码 `/data/`、`C:\`/`D:\` 设备路径。
- [ ] 工程内没有 `.hsp`/`.hap`/`.har`/`.so`/`.a`/`.abc`/`.jar` 等预编译二进制；HSP 依赖已改为源码模块。
- [ ] `oh-package.json5` 的 `file:` 依赖只有 hypium har，没有 `.hsp`/其他 `.har`。
- [ ] 新文件保留 Apache 2.0 头。
- [ ] 相对 import 大小写与真实文件一致（Windows 不敏感，门禁敏感）。

## 5. 编译验证

- [ ] `python scripts/check_xts_project.py <suite>` 无 FAIL。
- [ ] `ohos-test-xts-code-quality` 扫描无 Critical；Warning 逐条确认。
- [ ] `validate_test.py` 通过（LOW 项说明原因）。
- [ ] **在 WSL + Linux 工具链内**跑动态门禁命令，`BUILD SUCCESSFUL`，产物 `entry-ohosTest-unsigned.hap`。Windows 原生 hvigor 的结果不算门禁证据。
- [ ] **在 WSL 内**用 7.26.0 ArkTS 1.2 工具（`7.26.0.static/hvigor`）跑静态 `assembleApp`：`BUILD SUCCESSFUL`，产物 `entry-default-unsigned.hap` + `<suite>-default-unsigned.app`；工程为 `modelVersion "26.0.0"`、`compileSdkVersion "26.1.0"`、`compatibleSdkVersion "22"`。
- [ ] 编译日志中无 `ERROR:`；`system api` 的 WARN 属预期。
- [ ] HITS 工程：构建/产物路径按 HITS 团队/CI 的实际流程验证，不要猜测闭源仓命令。
- [ ] 若门禁仍失败：把门禁日志的阶段/错误行与本地日志逐行对照，先判断是编译、schema、注册还是打包。

## 6. 门禁专属项（Windows 最容易漏）

- [ ] 大小写：所有 import、`srcEntry`、资源路径大小写正确。
- [ ] schema：`process` 不在 extensionAbilities；`compileSdkVersion` 类型正确。
- [ ] 命名：`hap_name` 以 `Acts` 开头；Test.json 的 hap 名一致。
- [ ] 注册：父 group + `test_targets.gni`。
- [ ] syscap：与 API 的 `@syscap` 一致。
- [ ] 接口：callback/Promise 重载与接口 master 一致，且在门禁 SDK 中存在。
- [ ] 动态/静态模板与测试目录匹配。
- [ ] 没有把本机 SDK 补丁当成已合入接口；交付说明里写清楚依赖的接口 PR/版本。

## 7. 提交卫生

- [ ] `git status` 不包含 `oh_modules/`、`build/`、`.hvigor/`、`local.properties`、`oh-package-lock.json5`、`out/`。
- [ ] 不包含 `.hsp`/`.hap`/`.har`/`.so`/`.abc`/`.jar` 等预编译二进制（`signature/*.p7b` 与图片资源除外）。
- [ ] `.gitignore` 覆盖上述目录。
- [ ] 没有把 `signature/*.p12`、密钥、密码提交。
- [ ] 没有提交 IDE 文件（`.idea/`、`.deveco/`）。
- [ ] PR 描述包含：需求号、suite 名、动态/静态、BUILD.gn target、编译命令与 HAP 路径、门禁日志结论、接口依赖。

## 8. 提交后

- [ ] 看门禁是否真的编译了你的 suite（`gn desc`/日志中出现 target），避免“未注册 → 跳过 → 假通过”。
- [ ] 若门禁报错，先取门禁的 hvigor/SDK 版本，再决定是否切 WSL 复核。
- [ ] 修复后重新跑第 4–6 节，不要只重跑编译。

## 9. 签核模板

```text
Suite: ActsXxxTest (dyn) / ActsXxxStaticTest (sta)
BUILD.gn: //test/xts/acts/...:ActsXxx
hap_name: ActsXxxTest
part/subsystem: xxx/xxx
API: @ohos.xxx (syscap ..., @systemapi yes/no)
Build:
  dynamic: BUILD SUCCESSFUL, entry-ohosTest-unsigned.hap
  static:  BUILD SUCCESSFUL, entry-default-unsigned.hap
Checks:
  check_xts_project.py: PASS (0 FAIL, N WARN)
  code-quality: PASS (0 Critical)
  validate_test.py: PASS
Gate risk:
  interface callback overload: merged / pending PR #...
  gate SDK version: 26.1.0.xx
```
